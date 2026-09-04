#!/usr/bin/env python3
"""Orchestrate canonical Telegram owner access and final Full Exec for OpenClaw."""

from __future__ import annotations

import argparse
import copy
import datetime as dt
import hashlib
import json
import os
import pathlib
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass

try:
    from native_approvals import (
        NativeApprovalsError,
        backup_approvals,
        load_approvals,
        restore_approvals,
    )
except ImportError as error:  # pragma: no cover - protects incomplete skill syncs
    raise RuntimeError(
        "Missing native_approvals.py; sync the cap-full-quyen-telegram-openclaw skill"
    ) from error


SKILL_NAMES = (
    "unify-openclaw-bot-workspace",
    "cap-quyen-telegram-admin-openclaw",
    "set-openclaw-agent-full-exec",
    "cap-full-quyen-telegram-openclaw",
)
REQUIRED_NON_OWNER_DENY = {
    "group:runtime",
    "group:fs",
    "group:messaging",
    "sessions_send",
    "sessions_spawn",
    "subagents",
}
SECRET_PATTERNS = (
    re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
    re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"gh[pousr]_[A-Za-z0-9_]{20,}"),
    re.compile(r"AIza[0-9A-Za-z_-]{25,}"),
    re.compile(r"[0-9]{7,12}:[A-Za-z0-9_-]{25,}"),
    re.compile(r"-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----"),
)
SAFE_SUMMARY_PREFIXES = (
    "mode=",
    "status=",
    "change_count=",
    "change=",
    "host_change=",
    "source_agent_count=",
    "owner_count=",
    "violation_count=",
    "violation=",
    "workspace_",
    "changes_required=",
    "restart=",
    "apply=",
    "check=",
    "config_before=",
    "config_after=",
    "approvals_before=",
    "approvals_after=",
)


class WorkflowError(RuntimeError):
    pass


@dataclass
class Context:
    member: str
    telegram_ids: list[str]
    account_id: str
    agent_id: str
    source_agent: str | None
    routing_requires_unify: bool
    member_data_root: pathlib.Path
    openclaw_root: pathlib.Path
    runtime_openclaw_root: pathlib.PurePosixPath
    runtime_home: str
    container: str
    skills_root: pathlib.Path
    backup_root: pathlib.Path
    config_path: pathlib.Path
    approvals_path: pathlib.Path
    workspace_host: pathlib.Path


def approvals_document(ctx: Context) -> dict:
    """Read the active legacy or native approval document without creating files."""
    try:
        return load_approvals(ctx.openclaw_root).document
    except NativeApprovalsError as error:
        raise WorkflowError(f"Cannot read exec approvals: {error}") from error


def approval_backup_from_manifest(manifest: dict, key: str) -> dict:
    """Return backend-aware approval backup metadata, including old manifests."""
    metadata = manifest.get(f"{key}_backup")
    if isinstance(metadata, dict) and metadata.get("path"):
        return metadata
    path_value = manifest.get(key)
    if not path_value:
        raise WorkflowError(f"Approval rollback metadata is missing: {key}")
    path = pathlib.Path(str(path_value))
    backend = manifest.get(f"{key}_backend")
    if backend not in {"legacy", "sqlite"}:
        backend = "sqlite" if path.suffix == ".sqlite" else "legacy"
    return {
        "backend": backend,
        "path": str(path),
        "exists": bool(manifest.get(f"{key}_exists", True)),
    }


def restore_manifest_approvals(ctx: Context, manifest: dict, key: str) -> None:
    try:
        restore_approvals(
            load_approvals(ctx.openclaw_root),
            approval_backup_from_manifest(manifest, key),
            config_path=ctx.config_path,
            runtime_home=ctx.runtime_home,
        )
    except NativeApprovalsError as error:
        raise WorkflowError(f"Cannot restore exec approvals: {error}") from error


@dataclass
class GatewayHandle:
    pid: str
    manager: str
    tmux_target: str | None = None
    tmux_remain_on_exit: str | None = None


class Runner:
    def run(self, command: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            command,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        if check and result.returncode != 0:
            raise WorkflowError(
                f"Command failed ({result.returncode}): {pathlib.Path(command[0]).name}\n{result.stdout}"
            )
        return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Unify Telegram routing, grant owners, and enable final Full Exec."
    )
    parser.add_argument("--member", required=True)
    parser.add_argument("--telegram-id", action="append", default=[])
    parser.add_argument("--account-id")
    parser.add_argument("--agent-id", default="main")
    parser.add_argument("--source-agent", default="auto")
    parser.add_argument(
        "--member-data-root",
        default=os.environ.get(
            "OPENCLAW_MEMBER_DATA_ROOT", "/root/Apps/member_vps/docker-users/data"
        ),
    )
    parser.add_argument(
        "--openclaw-root",
        help=(
            "Host OpenClaw root for a nonstandard member layout; it must be "
            "inside the selected member data directory."
        ),
    )
    parser.add_argument("--container")
    parser.add_argument("--runtime-openclaw-root", default="/root/.openclaw")
    parser.add_argument("--runtime-home", default="/root")
    parser.add_argument(
        "--skills-root",
        default=str(pathlib.Path(__file__).resolve().parents[2]),
    )
    parser.add_argument(
        "--backup-root",
        default=os.environ.get(
            "OPENCLAW_OWNER_FULL_ACCESS_BACKUP_ROOT",
            "/root/_Backups/openclaw-owner-full-access",
        ),
    )
    actions = parser.add_mutually_exclusive_group(required=True)
    actions.add_argument("--dry-run", action="store_true")
    actions.add_argument("--apply", action="store_true")
    actions.add_argument("--check", action="store_true")
    actions.add_argument("--rollback-operation")
    parser.add_argument(
        "--dry-run-rollback",
        action="store_true",
        help="Validate rollback inputs without changing files; requires --rollback-operation.",
    )
    args = parser.parse_args()
    if args.dry_run_rollback and not args.rollback_operation:
        parser.error("--dry-run-rollback requires --rollback-operation")
    if not args.rollback_operation and not args.telegram_id:
        parser.error("At least one --telegram-id is required")
    return args


def require_identifier(value: str, label: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", value or ""):
        raise WorkflowError(f"Invalid {label}")
    return value


def require_telegram_ids(values: list[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        if not re.fullmatch(r"[1-9][0-9]{4,19}", value):
            raise WorkflowError("Telegram user ID must be a positive numeric value")
        if value not in result:
            result.append(value)
    return result


def load_json(path: pathlib.Path) -> dict:
    if not path.is_file() or path.is_symlink():
        raise WorkflowError(f"Required private JSON file is missing or unsafe: {path}")
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise WorkflowError(f"JSON root must be an object: {path}")
    return value


def infer_account_id(config: dict, member: str, requested: str | None) -> str:
    accounts = (
        config.get("channels", {}).get("telegram", {}).get("accounts", {})
        if isinstance(config.get("channels"), dict)
        else {}
    )
    if not isinstance(accounts, dict) or not accounts:
        raise WorkflowError("No Telegram account is configured")
    if requested:
        if requested not in accounts:
            raise WorkflowError("Requested Telegram account does not exist")
        return requested
    if member in accounts:
        return member
    if len(accounts) == 1:
        return next(iter(accounts))
    raise WorkflowError("Telegram account is ambiguous; pass --account-id")


def agent_collection(config: dict) -> tuple[str, dict | list]:
    """Return the active agent collection, preferring OpenClaw 2026.8 entries."""
    agents = config.get("agents")
    if not isinstance(agents, dict):
        return "list", []
    if "entries" in agents:
        entries = agents.get("entries")
        if not isinstance(entries, dict):
            raise WorkflowError("Expected object at agents.entries")
        return "entries", entries
    if "list" not in agents:
        return "list", []
    listed = agents.get("list")
    if not isinstance(listed, list):
        raise WorkflowError("Expected array at agents.list")
    return "list", listed


def iter_agents(config: dict):
    mode, collection = agent_collection(config)
    if mode == "entries":
        for agent_id, entry in collection.items():
            if isinstance(entry, dict):
                yield str(agent_id), entry
        return
    for entry in collection:
        if isinstance(entry, dict) and entry.get("id"):
            yield str(entry["id"]), entry


def find_agent(config: dict, agent_id: str) -> dict:
    mode, collection = agent_collection(config)
    if mode == "entries":
        entry = collection.get(agent_id)
        if not isinstance(entry, dict):
            raise WorkflowError(f"Agent must exist exactly once: {agent_id}")
        return entry
    matches = [item for item in collection if isinstance(item, dict) and item.get("id") == agent_id]
    if len(matches) != 1:
        raise WorkflowError(f"Agent must exist exactly once: {agent_id}")
    return matches[0]


def account_bindings(config: dict, account_id: str) -> list[dict]:
    result = []
    for binding in config.get("bindings", []):
        if not isinstance(binding, dict):
            continue
        match = binding.get("match")
        if (
            isinstance(match, dict)
            and match.get("channel") == "telegram"
            and match.get("accountId") == account_id
        ):
            result.append(binding)
    return result


def detect_source_agent(
    config: dict, account_id: str, target_agent: str, requested: str
) -> tuple[str | None, bool]:
    bindings = account_bindings(config, account_id)
    routing_requires_unify = (
        len(bindings) != 1
        or any(binding.get("agentId") != target_agent for binding in bindings)
        or any(isinstance(binding.get("match"), dict) and binding["match"].get("peer") is not None for binding in bindings)
    )
    agent_ids = {agent_id for agent_id, _ in iter_agents(config)}
    if requested == "none":
        return None, routing_requires_unify
    if requested != "auto":
        if requested == target_agent or requested not in agent_ids:
            raise WorkflowError("Explicit source agent is invalid")
        return requested, True
    bound_sources = {
        str(binding.get("agentId"))
        for binding in bindings
        if binding.get("agentId") and binding.get("agentId") != target_agent
    }
    if bound_sources - {"owner-admin"}:
        raise WorkflowError("Non-target Telegram routing is ambiguous; pass --source-agent")
    if "owner-admin" in bound_sources or "owner-admin" in agent_ids:
        return "owner-admin", True
    if bound_sources:
        raise WorkflowError("Multiple source agents require an explicit --source-agent")
    return None, routing_requires_unify


def runtime_to_host(
    runtime_path: str, runtime_root: pathlib.PurePosixPath, host_root: pathlib.Path
) -> pathlib.Path:
    candidate = pathlib.PurePosixPath(runtime_path)
    try:
        relative = candidate.relative_to(runtime_root)
    except ValueError as error:
        raise WorkflowError("Agent workspace must be inside runtime OpenClaw root") from error
    return host_root.joinpath(*relative.parts)


def build_context(args: argparse.Namespace) -> Context:
    member = require_identifier(args.member, "member")
    agent_id = require_identifier(args.agent_id, "agent ID")
    telegram_ids = require_telegram_ids(args.telegram_id)
    member_data_root = pathlib.Path(args.member_data_root).expanduser().resolve()
    member_root = (member_data_root / member).resolve()
    try:
        member_root.relative_to(member_data_root)
    except ValueError as error:
        raise WorkflowError("Member path escapes member data root") from error
    if args.openclaw_root:
        requested_root = pathlib.Path(args.openclaw_root).expanduser()
        if not requested_root.is_absolute() or requested_root.is_symlink():
            raise WorkflowError("Custom OpenClaw root must be an absolute non-symlink path")
        openclaw_root = requested_root.resolve()
        try:
            openclaw_root.relative_to(member_root)
        except ValueError as error:
            raise WorkflowError(
                "Custom OpenClaw root must stay inside the selected member data directory"
            ) from error
    else:
        openclaw_root = member_root / "root" / ".openclaw"
    config_path = openclaw_root / "openclaw.json"
    config = load_json(config_path)
    try:
        approvals_snapshot = load_approvals(openclaw_root)
    except NativeApprovalsError as error:
        raise WorkflowError(f"Cannot inspect exec approvals: {error}") from error
    account_id = infer_account_id(config, member, args.account_id)
    target = find_agent(config, agent_id)
    runtime_openclaw_root = pathlib.PurePosixPath(args.runtime_openclaw_root)
    expected_workspace = runtime_openclaw_root / ("workspace" if agent_id == "main" else f"workspace-{agent_id}")
    expected_agent_dir = runtime_openclaw_root / "agents" / agent_id / "agent"
    if target.get("workspace") != str(expected_workspace):
        raise WorkflowError(f"Target agent workspace is not canonical: expected {expected_workspace}")
    if target.get("agentDir") != str(expected_agent_dir):
        raise WorkflowError(f"Target agentDir is not canonical: expected {expected_agent_dir}")
    source_agent, routing_requires_unify = detect_source_agent(
        config, account_id, agent_id, args.source_agent
    )
    skills_root = pathlib.Path(args.skills_root).expanduser().resolve()
    for skill_name in SKILL_NAMES:
        if not (skills_root / skill_name / "SKILL.md").is_file():
            raise WorkflowError(f"Missing dependent global skill: {skill_name}")
    workspace_host = runtime_to_host(
        str(expected_workspace), runtime_openclaw_root, openclaw_root
    )
    if workspace_host.is_symlink() or not workspace_host.is_dir():
        raise WorkflowError("Canonical workspace is missing or symlinked")
    workspace_host = workspace_host.resolve()
    try:
        workspace_host.relative_to(openclaw_root.resolve())
    except ValueError as error:
        raise WorkflowError("Canonical workspace escapes OpenClaw root") from error
    return Context(
        member=member,
        telegram_ids=telegram_ids,
        account_id=account_id,
        agent_id=agent_id,
        source_agent=source_agent,
        routing_requires_unify=routing_requires_unify,
        member_data_root=member_data_root,
        openclaw_root=openclaw_root,
        runtime_openclaw_root=runtime_openclaw_root,
        runtime_home=args.runtime_home,
        container=args.container or f"user-{member}",
        skills_root=skills_root,
        backup_root=pathlib.Path(args.backup_root).expanduser().resolve(),
        config_path=config_path,
        # This is a display locator only; native OpenClaw uses SQLite.
        approvals_path=approvals_snapshot.path,
        workspace_host=workspace_host,
    )


def normalize_values(values: object) -> set[str]:
    if not isinstance(values, list):
        return set()
    return {str(value) for value in values}


def final_violations(ctx: Context, config: dict, approvals: dict) -> list[str]:
    violations: list[str] = []
    bindings = account_bindings(config, ctx.account_id)
    if len(bindings) != 1:
        violations.append("telegram_binding_count")
    elif (
        bindings[0].get("agentId") != ctx.agent_id
        or bindings[0].get("match", {}).get("peer") is not None
    ):
        violations.append("telegram_binding_not_canonical")
    target = find_agent(config, ctx.agent_id)
    tools = target.get("tools") if isinstance(target.get("tools"), dict) else {}
    if tools.get("profile") != "full":
        violations.append("agent_profile_not_full")
    exec_tools = tools.get("exec") if isinstance(tools.get("exec"), dict) else {}
    if not (
        exec_tools.get("host") == "gateway"
        and exec_tools.get("mode") == "full"
        and exec_tools.get("strictInlineEval") is False
    ):
        violations.append("agent_exec_not_full")
    sender_policy = tools.get("toolsBySender") if isinstance(tools.get("toolsBySender"), dict) else {}
    wildcard = sender_policy.get("*") if isinstance(sender_policy.get("*"), dict) else {}
    wildcard_deny = set(wildcard.get("deny", [])) if isinstance(wildcard.get("deny"), list) else set()
    if not REQUIRED_NON_OWNER_DENY.issubset(wildcard_deny):
        violations.append("non_owner_guard_incomplete")
    telegram = config.get("channels", {}).get("telegram", {})
    account = telegram.get("accounts", {}).get(ctx.account_id, {}) if isinstance(telegram, dict) else {}
    top_allow = normalize_values(telegram.get("allowFrom") if isinstance(telegram, dict) else [])
    account_allow = normalize_values(account.get("allowFrom") if isinstance(account, dict) else [])
    approvers = normalize_values(
        telegram.get("execApprovals", {}).get("approvers", [])
        if isinstance(telegram.get("execApprovals"), dict)
        else []
    )
    owners = normalize_values(config.get("commands", {}).get("ownerAllowFrom", []))
    elevated = normalize_values(
        config.get("tools", {}).get("elevated", {}).get("allowFrom", {}).get("telegram", [])
    )
    plugin = config.get("approvals", {}).get("plugin", {})
    plugin_targets = plugin.get("targets", []) if isinstance(plugin, dict) else []
    for telegram_id in ctx.telegram_ids:
        if telegram_id not in top_allow:
            violations.append("owner_missing_channel_allow")
        if telegram_id not in account_allow:
            violations.append("owner_missing_account_allow")
        if f"telegram:{telegram_id}" not in owners:
            violations.append("owner_missing_command_permission")
        if telegram_id not in approvers:
            violations.append("owner_missing_exec_approver")
        if telegram_id not in elevated:
            violations.append("owner_missing_elevated")
        if sender_policy.get(f"channel:telegram:{telegram_id}") != {}:
            violations.append("owner_missing_exact_sender_policy")
        if not any(
            isinstance(item, dict)
            and item.get("channel") == "telegram"
            and str(item.get("to")) == telegram_id
            and item.get("accountId") == ctx.account_id
            for item in plugin_targets
        ):
            violations.append("owner_missing_plugin_target")
    if config.get("tools", {}).get("fs", {}).get("workspaceOnly") is not True:
        violations.append("filesystem_not_workspace_only")
    agent_approval = approvals.get("agents", {}).get(ctx.agent_id, {})
    if not (
        agent_approval.get("security") == "full"
        and agent_approval.get("ask") == "off"
        and agent_approval.get("askFallback") == "full"
        and agent_approval.get("autoAllowSkills") is True
    ):
        violations.append("host_approval_not_full_off")
    return sorted(set(violations))


def sanitize_output(value: str, telegram_ids: list[str]) -> str:
    sanitized = value
    for telegram_id in telegram_ids:
        sanitized = sanitized.replace(telegram_id, "<telegram-id>")
    sanitized = re.sub(
        r"(?i)(token|secret|password|api[_-]?key)([=:])[^\s]+",
        r"\1\2<redacted>",
        sanitized,
    )
    for pattern in SECRET_PATTERNS:
        sanitized = pattern.sub("<redacted>", sanitized)
    return sanitized


def print_stage_summary(label: str, output: str, telegram_ids: list[str]) -> None:
    print(f"stage={label}")
    for line in sanitize_output(output, telegram_ids).splitlines():
        if line.startswith(SAFE_SUMMARY_PREFIXES):
            print(line)


def run_stage(
    runner: Runner,
    label: str,
    command: list[str],
    telegram_ids: list[str],
    show_summary: bool = True,
) -> str:
    result = runner.run(command, check=False)
    if result.returncode != 0:
        safe = sanitize_output(result.stdout, telegram_ids)
        raise WorkflowError(f"Stage failed: {label}\n{safe[-4000:]}")
    if show_summary:
        print_stage_summary(label, result.stdout, telegram_ids)
    else:
        print(f"stage={label} status=pass")
    return result.stdout


def dependency_commands(ctx: Context) -> tuple[pathlib.Path, pathlib.Path, pathlib.Path]:
    unify = ctx.skills_root / "unify-openclaw-bot-workspace" / "scripts" / "unify_bot_workspace.py"
    admin = ctx.skills_root / "cap-quyen-telegram-admin-openclaw" / "scripts" / "grant_telegram_admin.py"
    full_exec = ctx.skills_root / "set-openclaw-agent-full-exec" / "scripts" / "set_openclaw_agent_full_exec.sh"
    for path in (unify, admin, full_exec):
        if not path.is_file() or path.is_symlink():
            raise WorkflowError(f"Dependency script is missing or unsafe: {path}")
    return unify, admin, full_exec


def unify_command(ctx: Context, action: str, backup_dir: pathlib.Path | None = None) -> list[str]:
    unify, _, _ = dependency_commands(ctx)
    command = [
        sys.executable,
        str(unify),
        "--openclaw-root",
        str(ctx.openclaw_root),
        "--runtime-openclaw-root",
        str(ctx.runtime_openclaw_root),
        "--account-id",
        ctx.account_id,
        "--target-agent",
        ctx.agent_id,
    ]
    for telegram_id in ctx.telegram_ids:
        command.extend(["--owner-id", telegram_id])
    if ctx.source_agent:
        command.extend(["--source-agent", ctx.source_agent])
    if action == "apply":
        command.extend(["--backup-dir", str(backup_dir), "--apply", "--gateway-stopped"])
    elif action == "check":
        command.append("--check")
    return command


def admin_command(
    ctx: Context, telegram_id: str, action: str, backup_dir: pathlib.Path | None = None
) -> list[str]:
    _, admin, _ = dependency_commands(ctx)
    command = [
        sys.executable,
        str(admin),
        "--telegram-id",
        telegram_id,
        "--openclaw-root",
        str(ctx.openclaw_root),
        "--runtime-openclaw-root",
        str(ctx.runtime_openclaw_root),
        "--account-id",
        ctx.account_id,
        "--agent-id",
        ctx.agent_id,
    ]
    if action == "apply":
        command.extend(["--backup-dir", str(backup_dir), "--apply"])
    elif action == "check":
        command.append("--check")
    return command


def full_exec_command(
    ctx: Context, action: str, backup_dir: pathlib.Path | None = None, no_restart: bool = False
) -> list[str]:
    _, _, full_exec = dependency_commands(ctx)
    command = [
        "bash",
        str(full_exec),
        "--openclaw-root",
        str(ctx.openclaw_root),
        "--container",
        ctx.container,
        "--runtime-home",
        ctx.runtime_home,
        "--agent",
        ctx.agent_id,
    ]
    if backup_dir:
        command.extend(["--backup-dir", str(backup_dir)])
    if no_restart:
        command.append("--no-restart")
    command.append(f"--{action}")
    return command


def dry_run_stages(ctx: Context, runner: Runner) -> None:
    run_stage(runner, "unify-dry-run", unify_command(ctx, "dry-run"), ctx.telegram_ids)
    if ctx.routing_requires_unify:
        print("stage=owner-dry-run status=deferred-until-unify")
    else:
        for telegram_id in ctx.telegram_ids:
            run_stage(
                runner,
                "owner-dry-run",
                admin_command(ctx, telegram_id, "dry-run"),
                ctx.telegram_ids,
            )
    run_stage(
        runner,
        "full-exec-dry-run",
        full_exec_command(ctx, "dry-run", no_restart=True),
        ctx.telegram_ids,
    )


def utc_stamp() -> str:
    return dt.datetime.now(dt.UTC).strftime("%Y%m%dT%H%M%SZ")


def atomic_write_json(path: pathlib.Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def private_copy(source: pathlib.Path, destination: pathlib.Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    os.chmod(destination, 0o600)


def restore_file(source: pathlib.Path, destination: pathlib.Path) -> None:
    fd, temporary = tempfile.mkstemp(prefix=f".{destination.name}.restore.", dir=destination.parent)
    os.close(fd)
    try:
        shutil.copy2(source, temporary)
        os.replace(temporary, destination)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def create_operation(ctx: Context) -> tuple[pathlib.Path, pathlib.Path, dict]:
    operation_dir = ctx.backup_root / ctx.member / utc_stamp()
    operation_dir.mkdir(parents=True, mode=0o700, exist_ok=False)
    os.chmod(operation_dir, 0o700)
    before_dir = operation_dir / "before"
    private_copy(ctx.config_path, before_dir / "openclaw.json")
    try:
        approvals_backup = backup_approvals(
            load_approvals(ctx.openclaw_root), before_dir, "exec-approvals"
        )
    except NativeApprovalsError as error:
        raise WorkflowError(f"Cannot back up exec approvals: {error}") from error
    manifest_path = operation_dir / "operation.json"
    manifest = {
        "version": 2,
        "status": "applying",
        "created_at": operation_dir.name,
        "member": ctx.member,
        "account_id": ctx.account_id,
        "agent_id": ctx.agent_id,
        "container": ctx.container,
        "openclaw_root": str(ctx.openclaw_root),
        "owner_count": len(ctx.telegram_ids),
        "before_config": str(before_dir / "openclaw.json"),
        "before_approvals": approvals_backup["path"],
        "before_approvals_backup": approvals_backup,
        "before_approvals_backend": approvals_backup.get("backend"),
        "before_approvals_exists": bool(approvals_backup.get("exists")),
        "unify_manifest": None,
        "post_unify_config": None,
        "post_unify_approvals": None,
        "skill_sync": [],
    }
    atomic_write_json(manifest_path, manifest)
    return operation_dir, manifest_path, manifest


def parse_output_value(output: str, key: str) -> str | None:
    prefix = f"{key}="
    for line in output.splitlines():
        if line.startswith(prefix):
            return line[len(prefix) :].strip()
    return None


def sha256_file(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def scan_skill_tree(path: pathlib.Path) -> None:
    for current, directories, files in os.walk(path, followlinks=False):
        current_path = pathlib.Path(current)
        for name in list(directories) + files:
            candidate = current_path / name
            if candidate.is_symlink():
                raise WorkflowError(f"Refusing symlink in skill source: {candidate}")
        for name in files:
            candidate = current_path / name
            try:
                text = candidate.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            if any(pattern.search(text) for pattern in SECRET_PATTERNS):
                raise WorkflowError(f"Secret-like value found in skill source: {candidate}")


def sync_skills(
    ctx: Context, operation_dir: pathlib.Path, records: list[dict] | None = None
) -> list[dict]:
    target_root = ctx.workspace_host / "skills"
    target_root.mkdir(parents=True, exist_ok=True)
    backup_root = operation_dir / "skills-before"
    records = records if records is not None else []
    for skill_name in SKILL_NAMES:
        source = ctx.skills_root / skill_name
        target = target_root / skill_name
        if target.is_symlink():
            raise WorkflowError(f"Refusing symlinked target skill: {target}")
        scan_skill_tree(source)
        existed = target.is_dir()
        backup = backup_root / skill_name
        if existed:
            shutil.copytree(target, backup)
        record = {
            "name": skill_name,
            "target": str(target),
            "backup": str(backup) if existed else None,
            "existed": existed,
        }
        records.append(record)
        shutil.copytree(source, target, dirs_exist_ok=True)
        for source_file in source.rglob("*"):
            if source_file.is_file():
                relative = source_file.relative_to(source)
                target_file = target / relative
                if not target_file.is_file() or sha256_file(source_file) != sha256_file(target_file):
                    raise WorkflowError(f"Skill sync checksum mismatch: {skill_name}/{relative}")
    return records


def skills_in_sync(ctx: Context) -> bool:
    target_root = ctx.workspace_host / "skills"
    for skill_name in SKILL_NAMES:
        source = ctx.skills_root / skill_name
        target = target_root / skill_name
        if not target.is_dir() or target.is_symlink():
            return False
        for source_file in source.rglob("*"):
            if source_file.is_file():
                target_file = target / source_file.relative_to(source)
                if not target_file.is_file() or sha256_file(source_file) != sha256_file(target_file):
                    return False
    return True


def safe_rmtree(path: pathlib.Path, allowed_root: pathlib.Path) -> None:
    resolved = path.resolve()
    try:
        resolved.relative_to(allowed_root.resolve())
    except ValueError as error:
        raise WorkflowError(f"Refusing to remove path outside skill root: {path}") from error
    if resolved == allowed_root.resolve():
        raise WorkflowError("Refusing to remove the entire skills root")
    if path.exists():
        shutil.rmtree(path)


def restore_skills(ctx: Context, records: list[dict]) -> None:
    allowed_root = ctx.workspace_host / "skills"
    for record in reversed(records):
        if record.get("name") not in SKILL_NAMES:
            raise WorkflowError("Unsafe skill record in operation manifest")
        target = pathlib.Path(record["target"])
        expected = allowed_root / record["name"]
        if target.resolve() != expected.resolve():
            raise WorkflowError("Skill rollback target mismatch")
        safe_rmtree(target, allowed_root)
        if record.get("existed"):
            backup = pathlib.Path(record["backup"])
            if not backup.is_dir():
                raise WorkflowError("Skill rollback backup is missing")
            shutil.copytree(backup, target)


def tmux_target_for_gateway(panes_output: str, pid: str) -> str | None:
    matches = []
    for line in panes_output.splitlines():
        parts = line.strip().split("|")
        if len(parts) != 3:
            continue
        target, pane_pid, pane_dead = parts
        if (
            pane_pid == pid
            and pane_dead == "0"
            and re.fullmatch(r"[A-Za-z0-9_.:-]+", target)
        ):
            matches.append(target)
    return matches[0] if len(matches) == 1 else None


def tmux_pane_is_dead(panes_output: str, target: str) -> bool:
    matches = []
    for line in panes_output.splitlines():
        parts = line.strip().split("|")
        if len(parts) == 3 and parts[0] == target:
            matches.append(parts[2] == "1")
    return matches == [True]


def tmux_panes(ctx: Context, runner: Runner) -> str:
    result = runner.run(
        [
            "docker",
            "exec",
            ctx.container,
            "tmux",
            "list-panes",
            "-a",
            "-F",
            "#{session_name}:#{window_index}.#{pane_index}|#{pane_pid}|#{pane_dead}",
        ],
        check=False,
    )
    return result.stdout if result.returncode == 0 else ""


def tmux_remain_on_exit(ctx: Context, runner: Runner, target: str) -> str | None:
    result = runner.run(
        [
            "docker",
            "exec",
            ctx.container,
            "tmux",
            "show-options",
            "-w",
            "-v",
            "-t",
            target,
            "remain-on-exit",
        ],
        check=False,
    )
    value = result.stdout.strip()
    return value if result.returncode == 0 and value in {"on", "off"} else None


def quiesce_gateway(ctx: Context, runner: Runner) -> GatewayHandle:
    inspect = runner.run(
        ["docker", "inspect", ctx.container, "--format", "{{.State.Running}}"],
        check=False,
    )
    if inspect.returncode != 0 or inspect.stdout.strip() != "true":
        raise WorkflowError("Member container is not running")
    pid_result = runner.run(
        ["docker", "exec", ctx.container, "sh", "-lc", "pgrep -o -f '^openclaw-gateway$'"]
    )
    pid = pid_result.stdout.strip()
    if not pid.isdigit():
        raise WorkflowError("Gateway PID is invalid")
    parent_result = runner.run(
        [
            "docker",
            "exec",
            ctx.container,
            "sh",
            "-lc",
            f"parent=$(ps -o ppid= -p '{pid}' | tr -d ' '); ps -o comm= -p \"$parent\" | tr -d ' '",
        ]
    )
    if "supervisord" in parent_result.stdout.strip():
        handle = GatewayHandle(pid=pid, manager="supervisor")
    else:
        target = tmux_target_for_gateway(tmux_panes(ctx, runner), pid)
        if not target:
            raise WorkflowError("Gateway is not managed by Supervisor or a matching tmux pane")
        handle = GatewayHandle(pid=pid, manager="tmux", tmux_target=target)
    runner.run(["docker", "exec", ctx.container, "kill", "-STOP", pid])
    state = ""
    for _ in range(10):
        state = runner.run(
            ["docker", "exec", ctx.container, "sh", "-lc", f"ps -o stat= -p '{pid}' | tr -d ' '"]
        ).stdout.strip()
        if "T" in state:
            break
        time.sleep(0.2)
    if "T" in state:
        print("gateway=quiesced")
        return handle
    if handle.manager != "tmux" or not handle.tmux_target:
        runner.run(["docker", "exec", ctx.container, "kill", "-CONT", pid], check=False)
        raise WorkflowError("Gateway could not be quiesced")

    handle.tmux_remain_on_exit = tmux_remain_on_exit(
        ctx, runner, handle.tmux_target
    )
    if not handle.tmux_remain_on_exit:
        raise WorkflowError("tmux remain-on-exit option is unavailable")

    # Keep the existing pane while its foreground Gateway exits cleanly.
    runner.run(
        [
            "docker",
            "exec",
            ctx.container,
            "tmux",
            "set-option",
            "-w",
            "-t",
            handle.tmux_target,
            "remain-on-exit",
            "on",
        ]
    )
    runner.run(
        [
            "docker",
            "exec",
            ctx.container,
            "tmux",
            "send-keys",
            "-t",
            handle.tmux_target,
            "C-c",
        ]
    )
    stopped = False
    for _ in range(30):
        result = runner.run(
            ["docker", "exec", ctx.container, "sh", "-lc", "pgrep -o -f '^openclaw-gateway$' || true"],
            check=False,
        )
        if not result.stdout.strip() and tmux_pane_is_dead(
            tmux_panes(ctx, runner), handle.tmux_target
        ):
            stopped = True
            break
        time.sleep(1)
    if not stopped:
        runner.run(
            [
                "docker",
                "exec",
                ctx.container,
                "tmux",
                "set-option",
                "-w",
                "-t",
                handle.tmux_target,
                "remain-on-exit",
                handle.tmux_remain_on_exit,
            ],
            check=False,
        )
        raise WorkflowError("tmux Gateway could not be quiesced")
    print("gateway=quiesced")
    return handle


def respawn_gateway(ctx: Context, runner: Runner, old: GatewayHandle) -> GatewayHandle:
    runner.run(["docker", "exec", ctx.container, "kill", "-CONT", old.pid], check=False)
    if old.manager == "supervisor":
        runner.run(["docker", "exec", ctx.container, "kill", old.pid], check=False)
    elif old.manager == "tmux" and old.tmux_target:
        runner.run(
            [
                "docker",
                "exec",
                ctx.container,
                "tmux",
                "respawn-pane",
                "-k",
                "-t",
                old.tmux_target,
            ]
        )
        runner.run(
            [
                "docker",
                "exec",
                ctx.container,
                "tmux",
                "set-option",
                "-w",
                "-t",
                old.tmux_target,
                "remain-on-exit",
                old.tmux_remain_on_exit or "off",
            ]
        )
    else:
        raise WorkflowError("Gateway manager is invalid")
    new_pid = ""
    for _ in range(30):
        result = runner.run(
            ["docker", "exec", ctx.container, "sh", "-lc", "pgrep -o -f '^openclaw-gateway$' || true"],
            check=False,
        )
        candidate = result.stdout.strip()
        if candidate.isdigit() and candidate != old.pid:
            new_pid = candidate
            break
        time.sleep(1)
    if not new_pid:
        raise WorkflowError("Gateway did not respawn under its process manager")
    if old.manager == "tmux" and tmux_target_for_gateway(tmux_panes(ctx, runner), new_pid) != old.tmux_target:
        raise WorkflowError("tmux did not respawn the original Gateway pane")
    print("gateway=respawned")
    return GatewayHandle(new_pid, old.manager, old.tmux_target)


def validate_config(ctx: Context, runner: Runner) -> None:
    run_stage(
        runner,
        "config-validate",
        [
            "docker",
            "exec",
            "-e",
            f"HOME={ctx.runtime_home}",
            ctx.container,
            "openclaw",
            "config",
            "validate",
        ],
        ctx.telegram_ids,
        show_summary=False,
    )


def skills_check(ctx: Context, runner: Runner) -> None:
    output = run_stage(
        runner,
        "skills-check",
        [
            "docker",
            "exec",
            "-e",
            f"HOME={ctx.runtime_home}",
            ctx.container,
            "openclaw",
            "skills",
            "check",
        ],
        ctx.telegram_ids,
        show_summary=False,
    )
    if "cap-full-quyen-telegram-openclaw" not in output:
        raise WorkflowError("Composite skill is not visible after sync")


def telegram_status_line(output: str, account_id: str) -> str:
    return next(
        (
            item
            for item in output.splitlines()
            if f"Telegram {account_id}" in item
        ),
        "",
    )


def probe_telegram(ctx: Context, runner: Runner) -> None:
    probe_result = runner.run(
        [
            "timeout",
            "15s",
            "docker",
            "exec",
            "-e",
            f"HOME={ctx.runtime_home}",
            ctx.container,
            "openclaw",
            "channels",
            "status",
            "--probe",
        ],
        check=False,
    )
    probe_output = probe_result.stdout
    line = telegram_status_line(probe_output, ctx.account_id)
    if probe_result.returncode == 0 and all(
        marker in line for marker in ("running", "connected", "works", "audit ok")
    ):
        print("telegram_probe=connected_works_audit_ok")
        return
    if probe_result.returncode not in (0, 124):
        raise WorkflowError(
            "Telegram probe failed\n"
            + sanitize_output(probe_output[-3000:], ctx.telegram_ids)
        )

    # Some OpenClaw builds block indefinitely in --probe even while polling is healthy.
    last_output = probe_output
    for _ in range(30):
        result = runner.run(
            [
                "timeout",
                "10s",
                "docker",
                "exec",
                "-e",
                f"HOME={ctx.runtime_home}",
                ctx.container,
                "openclaw",
                "channels",
                "status",
            ],
            check=False,
        )
        last_output = result.stdout
        line = telegram_status_line(last_output, ctx.account_id)
        if result.returncode == 0 and all(
            marker in line for marker in ("configured", "running", "connected")
        ):
            print("telegram_probe=normal_status_connected_after_probe_timeout")
            return
        time.sleep(1)
    raise WorkflowError(
        "Telegram status did not become connected after probe timeout\n"
        + sanitize_output(last_output[-3000:], ctx.telegram_ids)
    )


def runtime_check(ctx: Context, runner: Runner) -> None:
    violations = final_violations(ctx, load_json(ctx.config_path), approvals_document(ctx))
    if violations:
        raise WorkflowError("Final compliance failed: " + ", ".join(violations))
    if not skills_in_sync(ctx):
        raise WorkflowError("Required operator skills are not synchronized to the workspace")
    skills_check(ctx, runner)
    run_stage(
        runner,
        "full-exec-check",
        full_exec_command(ctx, "check"),
        ctx.telegram_ids,
        show_summary=False,
    )
    probe_telegram(ctx, runner)
    print("status=compliant")


def rollback_files_and_unify(
    ctx: Context, runner: Runner, manifest: dict, operation_dir: pathlib.Path
) -> None:
    records = manifest.get("skill_sync", [])
    if records:
        restore_skills(ctx, records)
    unify_manifest_value = manifest.get("unify_manifest")
    post_config_value = manifest.get("post_unify_config")
    post_approvals_value = manifest.get("post_unify_approvals")
    if unify_manifest_value and post_config_value and post_approvals_value:
        restore_file(pathlib.Path(post_config_value), ctx.config_path)
        restore_manifest_approvals(ctx, manifest, "post_unify_approvals")
        unify, _, _ = dependency_commands(ctx)
        run_stage(
            runner,
            "unify-rollback",
            [
                sys.executable,
                str(unify),
                "--rollback-manifest",
                str(unify_manifest_value),
                "--gateway-stopped",
            ],
            ctx.telegram_ids,
        )
    else:
        restore_file(pathlib.Path(manifest["before_config"]), ctx.config_path)
        restore_manifest_approvals(ctx, manifest, "before_approvals")
    validate_config(ctx, runner)
    manifest["status"] = "rolled-back"
    manifest["rolled_back_at"] = utc_stamp()
    atomic_write_json(operation_dir / "operation.json", manifest)


def apply_workflow(ctx: Context, runner: Runner) -> None:
    violations = final_violations(ctx, load_json(ctx.config_path), approvals_document(ctx))
    skill_sync_required = not skills_in_sync(ctx)
    if not violations and not skill_sync_required:
        print("changes_required=false")
        runtime_check(ctx, runner)
        return
    if not violations and skill_sync_required:
        print("changes_required=true")
        print("final_violation=skill_sync_required")
        operation_dir, manifest_path, manifest = create_operation(ctx)
        try:
            sync_skills(ctx, operation_dir, manifest["skill_sync"])
            manifest["status"] = "applied"
            manifest["completed_at"] = utc_stamp()
            atomic_write_json(manifest_path, manifest)
            runtime_check(ctx, runner)
            print(f"operation_manifest={manifest_path}")
            print("apply=pass")
            return
        except Exception:
            restore_skills(ctx, manifest.get("skill_sync", []))
            manifest["status"] = "rolled-back"
            atomic_write_json(manifest_path, manifest)
            raise
    print("changes_required=true")
    for violation in violations:
        print(f"final_violation={violation}")
    dry_run_stages(ctx, runner)
    operation_dir, manifest_path, manifest = create_operation(ctx)
    try:
        old_gateway = quiesce_gateway(ctx, runner)
    except Exception:
        manifest["status"] = "preflight-failed"
        manifest["failed_at"] = utc_stamp()
        atomic_write_json(manifest_path, manifest)
        raise
    current_gateway = old_gateway
    gateway_quiesced = True
    try:
        unify_output = run_stage(
            runner,
            "unify-apply",
            unify_command(ctx, "apply", operation_dir / "unify"),
            ctx.telegram_ids,
        )
        unify_manifest = parse_output_value(unify_output, "manifest")
        if not unify_manifest:
            raise WorkflowError("Unify apply did not return a rollback manifest")
        post_unify_dir = operation_dir / "post-unify"
        private_copy(ctx.config_path, post_unify_dir / "openclaw.json")
        post_unify_approvals = backup_approvals(
            load_approvals(ctx.openclaw_root), post_unify_dir, "exec-approvals"
        )
        manifest.update(
            {
                "unify_manifest": unify_manifest,
                "post_unify_config": str(post_unify_dir / "openclaw.json"),
                "post_unify_approvals": post_unify_approvals["path"],
                "post_unify_approvals_backup": post_unify_approvals,
                "post_unify_approvals_backend": post_unify_approvals.get("backend"),
                "post_unify_approvals_exists": bool(post_unify_approvals.get("exists")),
            }
        )
        atomic_write_json(manifest_path, manifest)
        for telegram_id in ctx.telegram_ids:
            run_stage(
                runner,
                "owner-apply",
                admin_command(ctx, telegram_id, "apply", operation_dir / "owner"),
                ctx.telegram_ids,
            )
        run_stage(runner, "unify-guarded-check", unify_command(ctx, "check"), ctx.telegram_ids)
        for telegram_id in ctx.telegram_ids:
            run_stage(
                runner,
                "owner-guarded-check",
                admin_command(ctx, telegram_id, "check"),
                ctx.telegram_ids,
            )
        run_stage(
            runner,
            "full-exec-apply",
            full_exec_command(
                ctx, "apply", backup_dir=operation_dir / "full-exec", no_restart=True
            ),
            ctx.telegram_ids,
        )
        violations = final_violations(ctx, load_json(ctx.config_path), approvals_document(ctx))
        if violations:
            raise WorkflowError("Final file compliance failed: " + ", ".join(violations))
        sync_skills(ctx, operation_dir, manifest["skill_sync"])
        atomic_write_json(manifest_path, manifest)
        skills_check(ctx, runner)
        validate_config(ctx, runner)
        current_gateway = respawn_gateway(ctx, runner, old_gateway)
        gateway_quiesced = False
        runtime_check(ctx, runner)
        manifest["status"] = "applied"
        manifest["completed_at"] = utc_stamp()
        atomic_write_json(manifest_path, manifest)
        print(f"operation_manifest={manifest_path}")
        print("apply=pass")
    except Exception as error:
        print(f"apply_error={type(error).__name__}", file=sys.stderr)
        try:
            if not gateway_quiesced:
                current_gateway = quiesce_gateway(ctx, runner)
                gateway_quiesced = True
            rollback_files_and_unify(ctx, runner, manifest, operation_dir)
            respawn_gateway(ctx, runner, current_gateway)
            print("automatic_rollback=pass", file=sys.stderr)
        except Exception as rollback_error:
            print(
                "automatic_rollback=failed gateway_left_quiesced=true "
                f"error={type(rollback_error).__name__}",
                file=sys.stderr,
            )
        raise


def rollback_operation(
    ctx: Context, runner: Runner, manifest_path: pathlib.Path, dry_run: bool
) -> None:
    manifest_path = manifest_path.expanduser().resolve()
    if not manifest_path.is_file() or manifest_path.is_symlink():
        raise WorkflowError("Rollback operation manifest is missing or unsafe")
    manifest_stat = manifest_path.stat()
    if manifest_stat.st_uid != 0 or stat.S_IMODE(manifest_stat.st_mode) & 0o077:
        raise WorkflowError("Rollback operation manifest must be root-owned and private")
    operation_dir = manifest_path.parent.resolve()
    try:
        operation_dir.relative_to(ctx.backup_root.resolve())
    except ValueError as error:
        raise WorkflowError("Rollback manifest is outside the configured backup root") from error
    manifest = load_json(manifest_path)
    if (
        manifest.get("member") != ctx.member
        or pathlib.Path(manifest.get("openclaw_root", "")).resolve() != ctx.openclaw_root.resolve()
        or manifest.get("container") != ctx.container
    ):
        raise WorkflowError("Rollback manifest target does not match member")
    if manifest.get("status") not in {"applied", "applying"}:
        raise WorkflowError("Rollback operation is not in a reversible state")
    for key in ("before_config", "before_approvals", "post_unify_config", "post_unify_approvals"):
        value = manifest.get(key)
        if value:
            path = pathlib.Path(value).resolve()
            try:
                path.relative_to(operation_dir)
            except ValueError as error:
                raise WorkflowError(f"Unsafe rollback path in manifest: {key}") from error
            if not path.is_file():
                raise WorkflowError(f"Rollback file is missing: {key}")
    if dry_run:
        print("rollback_dry_run=pass")
        print(f"operation_status={manifest.get('status')}")
        return
    old_pid = quiesce_gateway(ctx, runner)
    try:
        rollback_files_and_unify(ctx, runner, manifest, operation_dir)
        respawn_gateway(ctx, runner, old_pid)
        probe_telegram(ctx, runner)
        print("rollback=pass")
    except Exception:
        print("rollback=failed gateway_left_quiesced=true", file=sys.stderr)
        raise


def main() -> int:
    args = parse_args()
    if os.geteuid() != 0:
        raise PermissionError("Run this VPS administration workflow as root")
    ctx = build_context(args)
    runner = Runner()
    print(f"member={ctx.member}")
    print(f"account_id={ctx.account_id}")
    print(f"agent_id={ctx.agent_id}")
    print(f"owner_count={len(ctx.telegram_ids)}")
    print(f"source_agent={ctx.source_agent or 'none'}")
    if args.rollback_operation:
        rollback_operation(
            ctx,
            runner,
            pathlib.Path(args.rollback_operation),
            args.dry_run_rollback,
        )
        return 0
    violations = final_violations(ctx, load_json(ctx.config_path), approvals_document(ctx))
    if args.dry_run:
        skill_sync_required = not skills_in_sync(ctx)
        print(f"final_violation_count={len(violations) + int(skill_sync_required)}")
        if not violations and not skill_sync_required:
            print("status=already-compliant")
            return 0
        for violation in violations:
            print(f"final_violation={violation}")
        if skill_sync_required:
            print("final_violation=skill_sync_required")
        if violations:
            dry_run_stages(ctx, runner)
        print("status=changes-required")
        return 0
    if args.check:
        skill_sync_required = not skills_in_sync(ctx)
        if violations or skill_sync_required:
            for violation in violations:
                print(f"final_violation={violation}")
            if skill_sync_required:
                print("final_violation=skill_sync_required")
            print("status=not-compliant")
            return 2
        runtime_check(ctx, runner)
        return 0
    apply_workflow(ctx, runner)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, json.JSONDecodeError, NativeApprovalsError, WorkflowError) as error:
        print(f"error={sanitize_output(str(error), [])}", file=sys.stderr)
        sys.exit(1)
