#!/usr/bin/env python3

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


CONTROL_FILES = {
    "AGENTS.md",
    "BOOTSTRAP.md",
    "HEARTBEAT.md",
    "IDENTITY.md",
    "SOUL.md",
    "TOOLS.md",
    "USER.md",
    "openclaw-workspace-state.json",
}
SKIP_DIRS = {".git", ".venv", "venv", "node_modules", "__pycache__", ".cache"}
NON_OWNER_DENY = [
    "group:runtime",
    "group:fs",
    "group:memory",
    "group:ui",
    "group:automation",
    "group:messaging",
    "group:nodes",
    "group:agents",
    "group:plugins",
    "sessions_list",
    "sessions_history",
    "sessions_send",
    "sessions_spawn",
    "sessions_yield",
    "subagents",
    "skill_workshop",
]


def parse_args():
    parser = argparse.ArgumentParser(
        description="Normalize or merge one OpenClaw bot account into one agent and workspace."
    )
    parser.add_argument("--openclaw-root", default="/root/.openclaw")
    parser.add_argument(
        "--runtime-openclaw-root",
        help="OpenClaw root as seen by the running Gateway when editing a host bind mount",
    )
    parser.add_argument("--account-id")
    parser.add_argument("--target-agent", default="main")
    parser.add_argument("--source-agent", action="append", default=[])
    parser.add_argument(
        "--owner-id",
        action="append",
        default=[],
        help="Verified Telegram owner ID to include when bootstrapping an account with no owners",
    )
    parser.add_argument("--backup-dir", default="/root/_Backups/openclaw-bot-workspace")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--gateway-stopped", action="store_true")
    parser.add_argument("--rollback-manifest")
    args = parser.parse_args()

    modes = sum(bool(value) for value in (args.apply, args.check, args.rollback_manifest))
    if modes > 1:
        parser.error("Use only one of --apply, --check, or --rollback-manifest")
    if args.rollback_manifest:
        if not args.gateway_stopped:
            parser.error("Rollback requires --gateway-stopped")
        return args
    if not args.account_id:
        parser.error("--account-id is required")
    if args.apply and not args.gateway_stopped:
        parser.error("Apply requires --gateway-stopped")
    return args


def require_root():
    if os.geteuid() != 0:
        raise PermissionError("Run this migration as root")


def require_identifier(value, label):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", value or ""):
        raise ValueError(f"{label} must use letters, digits, underscore, or hyphen")
    return value


def utc_stamp():
    return dt.datetime.now(dt.UTC).strftime("%Y%m%dT%H%M%SZ")


def load_json(path):
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return value


def atomic_write_json(path, value, mode=0o600):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary_name, mode)
        os.replace(temporary_name, path)
    finally:
        if os.path.exists(temporary_name):
            os.unlink(temporary_name)


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def path_is_within(path, root):
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def require_root_owned_private(path, label):
    if path.is_symlink() or not path.exists():
        raise ValueError(f"Unsafe {label}: {path}")
    metadata = path.stat()
    if metadata.st_uid != 0 or metadata.st_mode & 0o022:
        raise ValueError(f"{label} must be root-owned and not group/world-writable: {path}")


def ensure_safe_destination(destination, target_root):
    root = target_root.resolve()
    destination = destination.absolute()
    if not path_is_within(destination, root):
        raise ValueError(f"Destination escapes target workspace: {destination}")
    current = destination.parent
    while True:
        if current.is_symlink():
            raise ValueError(f"Destination traverses a target symlink: {current}")
        if current.exists() and not current.is_dir():
            raise ValueError(f"Destination parent is not a directory: {current}")
        if current == root:
            break
        if current == current.parent:
            raise ValueError(f"Destination parent escapes target workspace: {destination}")
        current = current.parent
    if not path_is_within(destination.parent.resolve(strict=False), root):
        raise ValueError(f"Resolved destination escapes target workspace: {destination}")


def validate_candidate_config(config_path, value):
    executable = shutil.which("openclaw")
    if not executable:
        raise ValueError("openclaw executable is required for candidate schema validation")
    fd, temporary_name = tempfile.mkstemp(
        prefix=".openclaw-candidate-", suffix=".json", dir=config_path.parent
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary_name, 0o600)
        environment = os.environ.copy()
        environment["OPENCLAW_CONFIG_PATH"] = temporary_name
        result = subprocess.run(
            [executable, "config", "validate", "--json"],
            check=False,
            capture_output=True,
            text=True,
            env=environment,
        )
        try:
            report = json.loads(result.stdout) if result.stdout.strip() else {}
        except json.JSONDecodeError:
            report = {}
        if result.returncode != 0 or report.get("valid") is not True:
            detail = result.stderr.strip() or result.stdout.strip() or "unknown validation error"
            detail = detail.replace(temporary_name, "<candidate-config>")[:2000]
            raise ValueError(f"Candidate OpenClaw config failed schema validation: {detail}")
    finally:
        if os.path.exists(temporary_name):
            os.unlink(temporary_name)


def ensure_object(parent, key):
    value = parent.get(key)
    if value is None:
        value = {}
        parent[key] = value
    if not isinstance(value, dict):
        raise ValueError(f"Expected object at {key}")
    return value


def ensure_array(parent, key):
    value = parent.get(key)
    if value is None:
        value = []
        parent[key] = value
    if not isinstance(value, list):
        raise ValueError(f"Expected array at {key}")
    return value


def unique_strings(values):
    result = []
    seen = set()
    for value in values:
        text = str(value)
        if text not in seen:
            seen.add(text)
            result.append(text)
    return result


def telegram_owner_ids(config, requested_owners=()):
    commands = config.get("commands")
    entries = commands.get("ownerAllowFrom", []) if isinstance(commands, dict) else []
    owners = []
    for entry in entries if isinstance(entries, list) else []:
        match = re.fullmatch(r"telegram:([1-9][0-9]*)", str(entry))
        if match:
            owners.append(match.group(1))
    owners = unique_strings(owners + list(requested_owners))
    if not owners:
        raise ValueError("No Telegram owner IDs found in commands.ownerAllowFrom")
    return owners


def require_telegram_owner_ids(values):
    owners = []
    for value in values:
        if not re.fullmatch(r"[1-9][0-9]{4,19}", value or ""):
            raise ValueError("Telegram owner ID must be a positive numeric value")
        if value not in owners:
            owners.append(value)
    return owners


def find_agent(config, agent_id):
    agents = config.get("agents")
    entries = agents.get("list", []) if isinstance(agents, dict) else []
    matches = [entry for entry in entries if isinstance(entry, dict) and entry.get("id") == agent_id]
    if len(matches) > 1:
        raise ValueError(f"Duplicate agent id: {agent_id}")
    return matches[0] if matches else None


def runtime_path_for_agent(config, runtime_root, agent_id, kind):
    entry = find_agent(config, agent_id)
    agents = config.get("agents") if isinstance(config.get("agents"), dict) else {}
    defaults = agents.get("defaults") if isinstance(agents.get("defaults"), dict) else {}
    if kind == "workspace":
        if entry and entry.get("workspace"):
            return pathlib.Path(str(entry["workspace"]))
        if agent_id == "main" and defaults.get("workspace"):
            return pathlib.Path(str(defaults["workspace"]))
        suffix = "workspace" if agent_id == "main" else f"workspace-{agent_id}"
        return runtime_root / suffix
    if entry and entry.get("agentDir"):
        return pathlib.Path(str(entry["agentDir"]))
    return runtime_root / "agents" / agent_id / "agent"


def runtime_to_filesystem(path, runtime_root, filesystem_root):
    path = pathlib.Path(path)
    try:
        relative = path.relative_to(runtime_root)
    except ValueError:
        return path.expanduser().resolve()
    return (filesystem_root / relative).resolve()


def binding_for_account(binding, account_id):
    match = binding.get("match") if isinstance(binding, dict) else None
    return (
        isinstance(match, dict)
        and match.get("channel") == "telegram"
        and match.get("accountId") == account_id
    )


def replace_agent_filter(value, source_ids, target_id):
    if not isinstance(value, list):
        return value
    replaced = [target_id if str(item) in source_ids else item for item in value]
    return unique_strings(replaced)


def find_scalar_references(value, needles, prefix=()):
    matches = []
    if isinstance(value, dict):
        for key, child in value.items():
            matches.extend(find_scalar_references(child, needles, prefix + (str(key),)))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            matches.extend(find_scalar_references(child, needles, prefix + (str(index),)))
    elif isinstance(value, str) and value in needles:
        matches.append(".".join(prefix))
    return matches


def transform_config(
    config, account_id, target_id, source_ids, runtime_root, requested_owners=()
):
    updated = copy.deepcopy(config)
    source_set = set(source_ids)
    owners = telegram_owner_ids(updated, requested_owners)

    target = find_agent(updated, target_id)
    if target is None and target_id != "main":
        raise ValueError(f"Target agent does not exist: {target_id}")

    agents = ensure_object(updated, "agents")
    entries = ensure_array(agents, "list")
    defaults = ensure_object(agents, "defaults")
    if target is None:
        target = {"id": "main", "default": True}
        entries.insert(0, target)

    target_workspace = runtime_path_for_agent(config, runtime_root, target_id, "workspace")
    target_agent_dir = runtime_path_for_agent(config, runtime_root, target_id, "agentDir")
    target["workspace"] = str(target_workspace)
    target["agentDir"] = str(target_agent_dir)
    target["default"] = True

    for entry in entries:
        if isinstance(entry, dict) and entry is not target and entry.get("default") is True:
            entry.pop("default", None)
    agents["list"] = [
        entry
        for entry in entries
        if not (isinstance(entry, dict) and str(entry.get("id")) in source_set)
    ]

    bindings = ensure_array(updated, "bindings")
    for binding in bindings:
        if not isinstance(binding, dict) or binding.get("agentId") != target_id:
            continue
        match = binding.get("match")
        if not isinstance(match, dict) or match.get("channel") != "telegram":
            continue
        if match.get("accountId") != account_id:
            raise ValueError("Target agent already serves another Telegram account")
    for binding in bindings:
        if (
            isinstance(binding, dict)
            and str(binding.get("agentId")) in source_set
            and not binding_for_account(binding, account_id)
        ):
            raise ValueError("A source agent still serves another binding; split it before merging")
    updated["bindings"] = [binding for binding in bindings if not binding_for_account(binding, account_id)]
    updated["bindings"].append(
        {
            "agentId": target_id,
            "match": {"channel": "telegram", "accountId": account_id},
        }
    )

    channels = ensure_object(updated, "channels")
    telegram = ensure_object(channels, "telegram")
    accounts = ensure_object(telegram, "accounts")
    if account_id not in accounts or not isinstance(accounts[account_id], dict):
        raise ValueError(f"Telegram account does not exist: {account_id}")
    account = accounts[account_id]
    telegram["allowFrom"] = unique_strings(list(telegram.get("allowFrom", [])) + owners)
    account["allowFrom"] = unique_strings(list(account.get("allowFrom", [])) + owners)

    commands = ensure_object(updated, "commands")
    command_owners = ensure_array(commands, "ownerAllowFrom")
    commands["ownerAllowFrom"] = unique_strings(
        command_owners + [f"telegram:{owner}" for owner in owners]
    )

    exec_approvals = ensure_object(telegram, "execApprovals")
    exec_approvals["enabled"] = "auto"
    exec_approvals["target"] = "dm"
    exec_approvals["approvers"] = owners
    if "agentFilter" in exec_approvals:
        exec_approvals["agentFilter"] = replace_agent_filter(
            exec_approvals["agentFilter"], source_set, target_id
        )

    approvals = ensure_object(updated, "approvals")
    plugin = approvals.get("plugin")
    if isinstance(plugin, dict):
        plugin["agentFilter"] = replace_agent_filter(plugin.get("agentFilter", []), source_set, target_id)
        targets = plugin.get("targets", [])
        kept_targets = []
        if isinstance(targets, list):
            for item in targets:
                if not (
                    isinstance(item, dict)
                    and item.get("channel") == "telegram"
                    and item.get("accountId") == account_id
                ):
                    kept_targets.append(item)
        kept_targets.extend(
            {"channel": "telegram", "to": owner, "accountId": account_id}
            for owner in owners
        )
        plugin["targets"] = kept_targets

    tools = ensure_object(updated, "tools")
    fs_tools = ensure_object(tools, "fs")
    fs_tools["workspaceOnly"] = True
    elevated = ensure_object(tools, "elevated")
    elevated["enabled"] = True
    elevated_allow = ensure_object(elevated, "allowFrom")
    elevated_allow["telegram"] = owners

    target_tools = ensure_object(target, "tools")
    target_tools["profile"] = "full"
    target_exec = ensure_object(target_tools, "exec")
    target_exec.pop("security", None)
    target_exec.pop("ask", None)
    target_exec["host"] = "gateway"
    target_exec["mode"] = "auto"
    target_exec["strictInlineEval"] = True
    by_sender = ensure_object(target_tools, "toolsBySender")
    wildcard = by_sender.get("*")
    if not isinstance(wildcard, dict):
        wildcard = {}
        by_sender["*"] = wildcard
    wildcard["deny"] = unique_strings(list(wildcard.get("deny", [])) + NON_OWNER_DENY)
    wildcard.pop("allow", None)
    wildcard.pop("alsoAllow", None)
    for owner in owners:
        by_sender[f"channel:telegram:{owner}"] = {}

    if defaults.get("workspace") is None and target_id == "main":
        defaults["workspace"] = str(target_workspace)

    remaining = find_scalar_references(updated, source_set)
    if remaining:
        raise ValueError("Source agent still referenced at: " + ", ".join(remaining[:8]))
    return updated, owners, target_workspace, target_agent_dir


def transform_exec_approvals(value, target_id, source_ids):
    updated = copy.deepcopy(value)
    updated["version"] = 1
    defaults = ensure_object(updated, "defaults")
    defaults.update(
        {
            "security": "allowlist",
            "ask": "on-miss",
            "askFallback": "deny",
            "autoAllowSkills": False,
        }
    )
    agents = ensure_object(updated, "agents")
    target = agents.get(target_id)
    if not isinstance(target, dict):
        target = {}
        agents[target_id] = target
    target.update(
        {
            "security": "allowlist",
            "ask": "on-miss",
            "askFallback": "deny",
            "autoAllowSkills": False,
        }
    )
    if not isinstance(target.get("allowlist"), list):
        target["allowlist"] = []
    for source_id in source_ids:
        agents.pop(source_id, None)
    return updated


def is_skipped_dir(relative):
    return any(part in SKIP_DIRS or part.startswith(".tmp") for part in relative.parts)


def walk_source_files(source_root):
    for current, directories, files in os.walk(source_root, followlinks=False):
        current_path = pathlib.Path(current)
        relative_current = current_path.relative_to(source_root)
        kept = []
        for directory in directories:
            candidate = current_path / directory
            relative = relative_current / directory
            if candidate.is_symlink():
                raise ValueError(f"Refusing source workspace symlink: {relative}")
            if not is_skipped_dir(relative):
                kept.append(directory)
        directories[:] = kept
        for filename in files:
            source = current_path / filename
            relative = relative_current / filename
            if source.is_symlink():
                raise ValueError(f"Refusing source workspace symlink: {relative}")
            if source.is_file():
                yield relative, source


def safe_slug(value):
    return re.sub(r"[^A-Za-z0-9._-]+", "_", value).strip("._") or "file"


def plan_workspace_merge(source_id, source_root, target_root, stamp):
    actions = []
    counts = {"copy": 0, "identical": 0, "conflict_import": 0, "control_import": 0}
    for relative, source in walk_source_files(source_root):
        destination = target_root / relative
        if relative.name in CONTROL_FILES and len(relative.parts) == 1:
            source_hash = sha256_file(source)
            destination = (
                target_root
                / "_merged_from"
                / safe_slug(source_id)
                / stamp
                / "control"
                / relative
            )
            ensure_safe_destination(destination, target_root)
            actions.append((source, destination, relative, "control_import", source_hash))
            counts["control_import"] += 1
            continue
        source_hash = sha256_file(source)
        if not destination.exists():
            ensure_safe_destination(destination, target_root)
            actions.append((source, destination, relative, "copy", source_hash))
            counts["copy"] += 1
            continue
        if not destination.is_file():
            raise ValueError(f"Target collision is not a file: {relative}")
        if source_hash == sha256_file(destination):
            counts["identical"] += 1
            continue
        if relative.parts and relative.parts[0] == "memory" and relative.suffix.lower() == ".md":
            imported_name = f"merged-from-{safe_slug(source_id)}-{stamp}-{safe_slug(str(relative))}"
            destination = target_root / "memory" / imported_name
        else:
            destination = target_root / "_merged_from" / safe_slug(source_id) / stamp / relative
        ensure_safe_destination(destination, target_root)
        actions.append((source, destination, relative, "conflict_import", source_hash))
        counts["conflict_import"] += 1
    return actions, counts


def copy_actions(actions, target_root):
    records = []
    for source, destination, relative, kind, source_hash in actions:
        ensure_safe_destination(destination, target_root)
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            raise FileExistsError(f"Planned destination already exists: {destination}")
        shutil.copy2(source, destination)
        copied_hash = sha256_file(destination)
        if copied_hash != source_hash:
            raise OSError(f"Checksum mismatch after copying: {relative}")
        records.append(
            {
                "path": str(destination),
                "sha256": copied_hash,
                "source_relative": str(relative),
                "kind": kind,
            }
        )
    return records


def remove_added_files(records, conflict_root):
    for record in reversed(records):
        path = pathlib.Path(record["path"])
        if not path.exists():
            continue
        if path.is_symlink() or not path.is_file() or sha256_file(path) != record["sha256"]:
            conflict_root.mkdir(parents=True, exist_ok=True)
            destination = conflict_root / safe_slug(str(path))
            shutil.move(str(path), destination)
            continue
        path.unlink()
        parent = path.parent
        while parent != parent.parent:
            try:
                parent.rmdir()
            except OSError:
                break
            parent = parent.parent


def move_to_retired(path, retired_root, label):
    if not path.exists():
        return None
    destination = retired_root / safe_slug(label)
    if destination.exists():
        raise FileExistsError(f"Retired destination exists: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(path), destination)
    return {"original": str(path), "retired": str(destination)}


def restore_moved(records):
    for record in reversed(records):
        original = pathlib.Path(record["original"])
        retired = pathlib.Path(record["retired"])
        if not retired.exists():
            continue
        if original.exists():
            raise FileExistsError(f"Cannot restore over existing path: {original}")
        original.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(retired), original)


def copy_backup(source, destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    os.chmod(destination, stat.S_IRUSR | stat.S_IWUSR)


def check_config(
    config,
    exec_value,
    account_id,
    target_id,
    source_ids,
    runtime_root,
    requested_owners=(),
):
    violations = []
    owners = telegram_owner_ids(config)
    if not set(requested_owners).issubset(owners):
        violations.append("requested owner missing")
    target = find_agent(config, target_id)
    if target is None:
        violations.append("target agent missing")
    for source_id in source_ids:
        if find_agent(config, source_id) is not None:
            violations.append(f"source agent still configured: {source_id}")

    matching = [
        binding
        for binding in config.get("bindings", [])
        if isinstance(binding, dict) and binding_for_account(binding, account_id)
    ]
    if len(matching) != 1 or matching[0].get("agentId") != target_id:
        violations.append("Telegram account does not have one canonical target binding")
    elif isinstance(matching[0].get("match"), dict) and matching[0]["match"].get("peer") is not None:
        violations.append("canonical binding is peer-specific")
    for binding in config.get("bindings", []):
        if not isinstance(binding, dict) or binding.get("agentId") != target_id:
            continue
        match = binding.get("match")
        if (
            isinstance(match, dict)
            and match.get("channel") == "telegram"
            and match.get("accountId") != account_id
        ):
            violations.append("target agent serves another Telegram account")
            break

    telegram = config.get("channels", {}).get("telegram", {})
    account = telegram.get("accounts", {}).get(account_id, {})
    for label, values in (
        ("channel allowFrom", telegram.get("allowFrom", [])),
        ("account allowFrom", account.get("allowFrom", [])),
        ("exec approvers", telegram.get("execApprovals", {}).get("approvers", [])),
        ("elevated owners", config.get("tools", {}).get("elevated", {}).get("allowFrom", {}).get("telegram", [])),
    ):
        if not set(owners).issubset({str(value) for value in values}):
            violations.append(f"owner set incomplete in {label}")

    if target is not None:
        tools = target.get("tools", {})
        exec_tools = tools.get("exec", {}) if isinstance(tools, dict) else {}
        if not (
            tools.get("profile") == "full"
            and exec_tools.get("host") == "gateway"
            and exec_tools.get("mode") == "auto"
            and exec_tools.get("strictInlineEval") is True
        ):
            violations.append("target exec policy is not guarded full access")
        by_sender = tools.get("toolsBySender", {}) if isinstance(tools, dict) else {}
        wildcard_deny = set(by_sender.get("*", {}).get("deny", [])) if isinstance(by_sender, dict) else set()
        if not set(NON_OWNER_DENY).issubset(wildcard_deny):
            violations.append("non-owner sender deny policy incomplete")
        for owner in owners:
            if by_sender.get(f"channel:telegram:{owner}") != {}:
                violations.append("owner sender policy missing or restrictive")
                break

    if config.get("tools", {}).get("fs", {}).get("workspaceOnly") is not True:
        violations.append("filesystem tools are not workspace-only")

    exec_defaults = exec_value.get("defaults", {}) if isinstance(exec_value, dict) else {}
    exec_agents = exec_value.get("agents", {}) if isinstance(exec_value, dict) else {}
    target_exec = exec_agents.get(target_id, {}) if isinstance(exec_agents, dict) else {}
    for label, policy in (("exec defaults", exec_defaults), ("target host approvals", target_exec)):
        if not (
            policy.get("security") == "allowlist"
            and policy.get("ask") == "on-miss"
            and policy.get("askFallback") == "deny"
        ):
            violations.append(f"{label} is not allowlist/on-miss/deny")
    for source_id in source_ids:
        if source_id in exec_agents:
            violations.append(f"source exec approvals still active: {source_id}")

    workspace_map = {}
    agent_dir_map = {}
    for entry in config.get("agents", {}).get("list", []):
        if not isinstance(entry, dict) or not entry.get("id"):
            continue
        agent_id = str(entry["id"])
        workspace = str(runtime_path_for_agent(config, runtime_root, agent_id, "workspace"))
        agent_dir = str(runtime_path_for_agent(config, runtime_root, agent_id, "agentDir"))
        if workspace in workspace_map and workspace_map[workspace] != agent_id:
            violations.append("multiple agents share a workspace")
        if agent_dir in agent_dir_map and agent_dir_map[agent_dir] != agent_id:
            violations.append("multiple agents share an agentDir")
        workspace_map[workspace] = agent_id
        agent_dir_map[agent_dir] = agent_id
    return violations, len(owners)


def rollback_from_manifest(manifest_path):
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise ValueError(f"Safe rollback manifest not found: {manifest_path}")
    transaction = manifest_path.parent.resolve()
    require_root_owned_private(transaction, "transaction directory")
    require_root_owned_private(manifest_path, "rollback manifest")
    manifest = load_json(manifest_path)
    if manifest.get("version") != 2 or manifest.get("status") != "applied":
        raise ValueError("Unsupported or incomplete rollback manifest")
    if pathlib.Path(manifest.get("transaction_dir", "")).resolve() != transaction:
        raise ValueError("Rollback manifest transaction directory mismatch")

    filesystem_root = pathlib.Path(manifest["filesystem_root"]).resolve()
    target_workspace = pathlib.Path(manifest["target_workspace"]).resolve()
    config_path = pathlib.Path(manifest["config_path"]).absolute()
    config_backup = pathlib.Path(manifest["config_backup"]).absolute()
    exec_path = pathlib.Path(manifest["exec_path"]).absolute()
    exec_backup = pathlib.Path(manifest["exec_backup"]).absolute()
    for active_path, expected_name in (
        (config_path, "openclaw.json"),
        (exec_path, "exec-approvals.json"),
    ):
        if active_path.name != expected_name or not path_is_within(active_path, filesystem_root):
            raise ValueError(f"Unsafe active rollback path: {active_path}")
        if active_path.is_symlink() or not active_path.is_file():
            raise ValueError(f"Active rollback file is unsafe or missing: {active_path}")
    for backup_path in (config_backup, exec_backup):
        if not path_is_within(backup_path, transaction):
            raise ValueError(f"Backup escapes transaction: {backup_path}")
        require_root_owned_private(backup_path, "rollback backup")
    if sha256_file(config_path) != manifest.get("config_after_sha256"):
        raise ValueError("Refusing rollback because openclaw.json changed after migration")
    if sha256_file(exec_path) != manifest.get("exec_after_sha256"):
        raise ValueError("Refusing rollback because exec-approvals.json changed after migration")
    if sha256_file(config_backup) != manifest.get("config_before_sha256"):
        raise ValueError("Rollback config backup checksum mismatch")
    if sha256_file(exec_backup) != manifest.get("exec_before_sha256"):
        raise ValueError("Rollback exec backup checksum mismatch")

    for record in manifest.get("added_files", []):
        path = pathlib.Path(record["path"]).absolute()
        if not path_is_within(path, target_workspace):
            raise ValueError(f"Imported file escapes target workspace: {path}")
    for record in manifest.get("moved", []):
        original = pathlib.Path(record["original"]).absolute()
        retired = pathlib.Path(record["retired"]).absolute()
        if not path_is_within(original, filesystem_root):
            raise ValueError(f"Moved original escapes OpenClaw root: {original}")
        if not path_is_within(retired, transaction / "retired"):
            raise ValueError(f"Retired path escapes transaction: {retired}")
        if original.exists() or original.is_symlink():
            raise ValueError(f"Cannot rollback over recreated source path: {original}")
        if not retired.exists() or retired.is_symlink():
            raise ValueError(f"Retired source is unsafe or missing: {retired}")

    remove_added_files(
        manifest.get("added_files", []), transaction / "rollback-conflicts"
    )
    restore_moved(manifest.get("moved", []))
    copy_backup(config_backup, config_path)
    copy_backup(exec_backup, exec_path)
    print(f"mode=rollback\nmanifest={manifest_path}\nstatus=rolled-back")


def main():
    args = parse_args()
    require_root()
    if args.rollback_manifest:
        rollback_from_manifest(pathlib.Path(args.rollback_manifest).expanduser().resolve())
        return 0

    account_id = require_identifier(args.account_id, "Account ID")
    target_id = require_identifier(args.target_agent, "Target agent ID")
    source_ids = [require_identifier(value, "Source agent ID") for value in args.source_agent]
    requested_owners = require_telegram_owner_ids(args.owner_id)
    if target_id in source_ids:
        raise ValueError("Target agent cannot also be a source agent")
    if len(set(source_ids)) != len(source_ids):
        raise ValueError("Duplicate --source-agent value")

    filesystem_root = pathlib.Path(args.openclaw_root).expanduser().resolve()
    runtime_root = pathlib.Path(args.runtime_openclaw_root).expanduser() if args.runtime_openclaw_root else filesystem_root
    config_path = filesystem_root / "openclaw.json"
    exec_path = filesystem_root / "exec-approvals.json"
    if not config_path.is_file() or config_path.is_symlink():
        raise FileNotFoundError(f"Safe OpenClaw config not found: {config_path}")
    if not exec_path.is_file() or exec_path.is_symlink():
        raise FileNotFoundError(f"Safe exec approvals file not found: {exec_path}")

    config = load_json(config_path)
    exec_value = load_json(exec_path)

    if args.check:
        violations, owner_count = check_config(
            config,
            exec_value,
            account_id,
            target_id,
            source_ids,
            runtime_root,
            requested_owners,
        )
        print("mode=check")
        print(f"account_id={account_id}")
        print(f"target_agent={target_id}")
        print(f"owner_count={owner_count}")
        print(f"violation_count={len(violations)}")
        for violation in violations:
            print(f"violation={violation}")
        print("status=compliant" if not violations else "status=not-compliant")
        return 0 if not violations else 2

    updated_config, owners, target_workspace_runtime, _ = transform_config(
        config,
        account_id,
        target_id,
        source_ids,
        runtime_root,
        requested_owners,
    )
    updated_exec = transform_exec_approvals(exec_value, target_id, source_ids)
    validate_candidate_config(config_path, updated_config)
    target_workspace = runtime_to_filesystem(
        target_workspace_runtime, runtime_root, filesystem_root
    )
    if target_workspace.is_symlink() or not target_workspace.is_dir():
        raise FileNotFoundError(f"Target workspace does not exist: {target_workspace}")

    stamp = utc_stamp()
    source_records = []
    total_counts = {"copy": 0, "identical": 0, "conflict_import": 0, "control_import": 0}
    all_actions = []
    for source_id in source_ids:
        source_workspace_runtime = runtime_path_for_agent(
            config, runtime_root, source_id, "workspace"
        )
        source_agent_dir_runtime = runtime_path_for_agent(
            config, runtime_root, source_id, "agentDir"
        )
        source_workspace = runtime_to_filesystem(
            source_workspace_runtime, runtime_root, filesystem_root
        )
        source_agent_dir = runtime_to_filesystem(
            source_agent_dir_runtime, runtime_root, filesystem_root
        )
        source_agent_root = source_agent_dir.parent if source_agent_dir.name == "agent" else source_agent_dir
        if source_workspace == target_workspace:
            raise ValueError(f"Source agent already shares target workspace: {source_id}")
        if source_workspace.is_symlink() or not source_workspace.is_dir():
            raise FileNotFoundError(f"Source workspace does not exist: {source_workspace}")
        if source_agent_root.is_symlink():
            raise ValueError(f"Source agent root must not be a symlink: {source_agent_root}")
        actions, counts = plan_workspace_merge(
            source_id, source_workspace, target_workspace, stamp
        )
        all_actions.extend(actions)
        for key, value in counts.items():
            total_counts[key] += value
        source_records.append(
            {
                "id": source_id,
                "workspace": source_workspace,
                "agent_root": source_agent_root,
            }
        )

    print("mode=apply" if args.apply else "mode=dry-run")
    print(f"account_id={account_id}")
    print(f"target_agent={target_id}")
    print(f"source_agent_count={len(source_ids)}")
    print(f"owner_count={len(owners)}")
    for key in ("copy", "identical", "conflict_import", "control_import"):
        print(f"workspace_{key}={total_counts[key]}")
    if not args.apply:
        print("status=changes-required")
        return 0

    transaction = (
        pathlib.Path(args.backup_dir).expanduser().resolve()
        / safe_slug(account_id)
        / stamp
    )
    transaction.mkdir(parents=True, mode=0o700, exist_ok=False)
    os.chmod(transaction, 0o700)
    config_backup = transaction / "openclaw.before.json"
    exec_backup = transaction / "exec-approvals.before.json"
    copy_backup(config_path, config_backup)
    copy_backup(exec_path, exec_backup)

    manifest = {
        "version": 2,
        "status": "applying",
        "created_at": stamp,
        "transaction_dir": str(transaction),
        "filesystem_root": str(filesystem_root),
        "target_workspace": str(target_workspace),
        "account_id": account_id,
        "target_agent": target_id,
        "source_agents": source_ids,
        "owner_count": len(owners),
        "config_path": str(config_path),
        "config_backup": str(config_backup),
        "config_before_sha256": sha256_file(config_backup),
        "exec_path": str(exec_path),
        "exec_backup": str(exec_backup),
        "exec_before_sha256": sha256_file(exec_backup),
        "added_files": [],
        "moved": [],
        "workspace_counts": total_counts,
    }
    manifest_path = transaction / "manifest.json"
    try:
        manifest["added_files"] = copy_actions(all_actions, target_workspace)
        atomic_write_json(config_path, updated_config)
        atomic_write_json(exec_path, updated_exec)
        manifest["config_after_sha256"] = sha256_file(config_path)
        manifest["exec_after_sha256"] = sha256_file(exec_path)
        retired_root = transaction / "retired"
        for record in source_records:
            moved_workspace = move_to_retired(
                record["workspace"], retired_root, f"workspace-{record['id']}"
            )
            if moved_workspace:
                manifest["moved"].append(moved_workspace)
            moved_agent = move_to_retired(
                record["agent_root"], retired_root, f"agent-{record['id']}"
            )
            if moved_agent:
                manifest["moved"].append(moved_agent)
        manifest["status"] = "applied"
        atomic_write_json(manifest_path, manifest)
    except Exception:
        try:
            restore_moved(manifest.get("moved", []))
            remove_added_files(manifest.get("added_files", []), transaction / "rollback-conflicts")
            copy_backup(config_backup, config_path)
            copy_backup(exec_backup, exec_path)
            atomic_write_json(transaction / "failed-manifest.json", manifest)
        except Exception as rollback_error:
            print(f"rollback_error={type(rollback_error).__name__}", file=sys.stderr)
        raise

    print(f"manifest={manifest_path}")
    print("status=applied")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"error={error}", file=sys.stderr)
        sys.exit(1)
