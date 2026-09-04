#!/usr/bin/env python3

import argparse
import copy
import datetime
import json
import os
import pathlib
import re
import shutil
import stat
import sys
import tempfile

try:
    from native_approvals import (
        NativeApprovalsError,
        backup_approvals,
        load_approvals,
        save_approvals,
    )
except ImportError as error:  # pragma: no cover - protects incomplete skill syncs
    raise RuntimeError(
        "Missing native_approvals.py; sync the cap-quyen-telegram-admin-openclaw skill"
    ) from error


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
        description="Grant a verified Telegram user full VPS administration through OpenClaw."
    )
    parser.add_argument("--telegram-id", required=True)
    parser.add_argument("--openclaw-root", default="/root/.openclaw")
    parser.add_argument(
        "--runtime-openclaw-root",
        help="OpenClaw root as seen by the runtime when the config is edited through a host-mounted path",
    )
    parser.add_argument("--account-id", default="main")
    parser.add_argument("--agent-id", default="main")
    parser.add_argument("--backup-dir", default="/root/_Backups/openclaw")
    parser.add_argument("--workspace")
    parser.add_argument("--agent-dir")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--check", action="store_true")
    arguments = parser.parse_args()
    if arguments.apply and arguments.check:
        parser.error("--apply and --check cannot be used together")
    return arguments


def require_positive_telegram_id(raw_value):
    if not raw_value.isdigit() or raw_value.startswith("0"):
        raise ValueError("Telegram user ID must contain only digits and be positive")
    telegram_id = int(raw_value)
    if telegram_id <= 0:
        raise ValueError("Telegram user ID must be positive")
    return str(telegram_id), telegram_id


def require_identifier(raw_value, label):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", raw_value):
        raise ValueError(f"{label} must use only letters, digits, underscore, or hyphen")
    return raw_value


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


def agent_collection(config):
    """Return the active agent collection, preserving the current schema."""
    agents = config.get("agents")
    if not isinstance(agents, dict):
        return "list", []
    if "entries" in agents:
        entries = agents.get("entries")
        if not isinstance(entries, dict):
            raise ValueError("Expected object at agents.entries")
        return "entries", entries
    if "list" not in agents:
        return "list", []
    listed = agents.get("list")
    if not isinstance(listed, list):
        raise ValueError("Expected array at agents.list")
    return "list", listed


def find_agent(config, agent_id):
    mode, collection = agent_collection(config)
    if mode == "entries":
        entry = collection.get(agent_id)
        if entry is None:
            return None
        if not isinstance(entry, dict):
            raise ValueError(f"Agent entry must be an object: {agent_id}")
        return entry
    matches = [
        entry for entry in collection
        if isinstance(entry, dict) and entry.get("id") == agent_id
    ]
    if len(matches) > 1:
        raise ValueError(f"Duplicate agent id found: {agent_id}")
    return matches[0] if matches else None


def append_unique(values, candidate, normalize=str):
    normalized_candidate = normalize(candidate)
    if any(normalize(value) == normalized_candidate for value in values):
        return False
    values.append(candidate)
    return True


def add_change(changes, changed, description):
    if changed:
        changes.append(description)


def binding_matches_account(binding, account_id):
    match = binding.get("match")
    if not isinstance(match, dict):
        return False
    return (
        match.get("channel") == "telegram"
        and match.get("accountId") == account_id
    )


def merge_config(
    config,
    telegram_id,
    telegram_id_number,
    account_id,
    agent_id,
    workspace,
    agent_dir,
    normalize_agent_paths,
):
    changes = []
    channels = ensure_object(config, "channels")
    telegram = ensure_object(channels, "telegram")
    accounts = ensure_object(telegram, "accounts")
    if account_id not in accounts or not isinstance(accounts[account_id], dict):
        raise ValueError(f"Telegram account does not exist: {account_id}")
    account = accounts[account_id]

    if telegram.get("dmPolicy") not in {"pairing", "allowlist"}:
        telegram["dmPolicy"] = "allowlist"
        changes.append("set Telegram dmPolicy=allowlist")
    if account.get("dmPolicy") not in {"pairing", "allowlist"}:
        account["dmPolicy"] = "allowlist"
        changes.append(f"set Telegram account {account_id} dmPolicy=allowlist")

    telegram_allow_from = ensure_array(telegram, "allowFrom")
    add_change(
        changes,
        append_unique(telegram_allow_from, telegram_id),
        "add target to Telegram allowFrom",
    )
    account_allow_from = ensure_array(account, "allowFrom")
    add_change(
        changes,
        append_unique(account_allow_from, telegram_id),
        f"add target to Telegram account {account_id} allowFrom",
    )

    commands = ensure_object(config, "commands")
    owner_allow_from = ensure_array(commands, "ownerAllowFrom")
    add_change(
        changes,
        append_unique(owner_allow_from, f"telegram:{telegram_id}"),
        "add target to commands.ownerAllowFrom",
    )
    # OpenClaw 2026.8 renders raw owner IDs by default; these legacy keys are
    # doctor-only and rejected by the active config schema.
    for retired_key in ("ownerDisplay", "ownerDisplaySecret"):
        if retired_key in commands:
            commands.pop(retired_key, None)
            changes.append(f"remove unsupported commands.{retired_key}")

    exec_approvals = ensure_object(telegram, "execApprovals")
    if exec_approvals.get("enabled") != "auto":
        exec_approvals["enabled"] = "auto"
        changes.append("set Telegram exec approvals=auto")
    approvers = ensure_array(exec_approvals, "approvers")
    approver_value = telegram_id_number if approvers and all(isinstance(value, int) for value in approvers) else telegram_id
    add_change(
        changes,
        append_unique(approvers, approver_value),
        "add target to Telegram exec approvers",
    )
    if exec_approvals.get("target") != "dm":
        exec_approvals["target"] = "dm"
        changes.append("send Telegram exec approvals to DM only")

    agents = ensure_object(config, "agents")
    collection_mode, collection = agent_collection(config)
    if collection_mode == "entries":
        admin_agent = collection.get(agent_id)
        if admin_agent is not None and not isinstance(admin_agent, dict):
            raise ValueError(f"Agent entry must be an object: {agent_id}")
        if admin_agent is None:
            raise ValueError(
                f"Agent does not exist: {agent_id}. Create a new agent only when creating a new bot."
            )
    else:
        agent_list = collection
        matching_agents = [entry for entry in agent_list if isinstance(entry, dict) and entry.get("id") == agent_id]
        if len(matching_agents) > 1:
            raise ValueError(f"Duplicate agent id found: {agent_id}")
        if matching_agents:
            admin_agent = matching_agents[0]
        elif agent_id == "main":
            admin_agent = {"id": "main", "default": True}
            agent_list.insert(0, admin_agent)
            changes.append("register implicit default agent main")
        else:
            raise ValueError(
                f"Agent does not exist: {agent_id}. Create a new agent only when creating a new bot."
            )

    if not admin_agent.get("workspace") or (
        normalize_agent_paths and str(admin_agent.get("workspace")) != str(workspace)
    ):
        admin_agent["workspace"] = str(workspace)
        changes.append(f"set {agent_id} workspace")
    if not admin_agent.get("agentDir") or (
        normalize_agent_paths and str(admin_agent.get("agentDir")) != str(agent_dir)
    ):
        admin_agent["agentDir"] = str(agent_dir)
        changes.append(f"set {agent_id} agentDir")
    tools = ensure_object(admin_agent, "tools")
    if tools.get("profile") != "full":
        tools["profile"] = "full"
        changes.append(f"set {agent_id} tools.profile=full")
    exec_tools = ensure_object(tools, "exec")
    if exec_tools.get("host") != "gateway":
        exec_tools["host"] = "gateway"
        changes.append(f"set {agent_id} exec host=gateway")
    if exec_tools.get("mode") != "auto":
        exec_tools.pop("security", None)
        exec_tools.pop("ask", None)
        exec_tools["mode"] = "auto"
        changes.append(f"set {agent_id} exec mode=auto")
    if exec_tools.get("strictInlineEval") is not True:
        exec_tools["strictInlineEval"] = True
        changes.append(f"set {agent_id} strict inline exec approval")

    tools_by_sender = ensure_object(tools, "toolsBySender")
    owner_sender_key = f"channel:telegram:{telegram_id}"
    if tools_by_sender.get(owner_sender_key) != {}:
        tools_by_sender[owner_sender_key] = {}
        changes.append(f"grant owner sender full {agent_id} profile")
    wildcard = tools_by_sender.get("*")
    if not isinstance(wildcard, dict):
        wildcard = {}
        tools_by_sender["*"] = wildcard
    wildcard_deny = ensure_array(wildcard, "deny")
    for denied_tool in NON_OWNER_DENY:
        add_change(
            changes,
            append_unique(wildcard_deny, denied_tool),
            "restrict non-owner administrative tools",
        )

    global_tools = ensure_object(config, "tools")
    fs_tools = ensure_object(global_tools, "fs")
    if fs_tools.get("workspaceOnly") is not True:
        fs_tools["workspaceOnly"] = True
        changes.append("limit filesystem tools to the workspace")
    elevated = ensure_object(global_tools, "elevated")
    if elevated.get("enabled") is not True:
        elevated["enabled"] = True
        changes.append("enable guarded elevated mode")
    elevated_allow = ensure_object(elevated, "allowFrom")
    elevated_telegram = ensure_array(elevated_allow, "telegram")
    add_change(
        changes,
        append_unique(elevated_telegram, telegram_id),
        "add target to Telegram elevated allowlist",
    )

    bindings = ensure_array(config, "bindings")
    account_bindings = [
        binding
        for binding in bindings
        if isinstance(binding, dict) and binding_matches_account(binding, account_id)
    ]
    conflicting_agents = sorted(
        {
            str(binding.get("agentId"))
            for binding in account_bindings
            if binding.get("agentId") != agent_id
        }
    )
    if conflicting_agents:
        raise ValueError(
            "Telegram account already routes to another agent: "
            + ", ".join(conflicting_agents)
            + ". Use unify-openclaw-bot-workspace before granting this owner."
        )
    canonical_bindings = [
        binding
        for binding in account_bindings
        if binding.get("agentId") == agent_id
        and isinstance(binding.get("match"), dict)
        and binding["match"].get("peer") is None
    ]
    peer_bindings = [
        binding
        for binding in account_bindings
        if isinstance(binding.get("match"), dict) and binding["match"].get("peer") is not None
    ]
    if peer_bindings:
        raise ValueError(
            "Telegram account has peer-specific routing. Use unify-openclaw-bot-workspace first."
        )
    if not canonical_bindings:
        bindings.append(
            {
                "agentId": agent_id,
                "match": {"channel": "telegram", "accountId": account_id},
            }
        )
        changes.append(f"bind entire Telegram account to {agent_id}")

    return changes


def create_backup(config_path, backup_dir, telegram_id):
    backup_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.datetime.now(datetime.UTC).strftime("%Y%m%dT%H%M%SZ")
    backup_path = backup_dir / f"openclaw-before-telegram-admin-{telegram_id}-{timestamp}.json"
    shutil.copy2(config_path, backup_path)
    os.chmod(backup_path, stat.S_IRUSR | stat.S_IWUSR)
    return backup_path


def create_named_backup(source_path, backup_dir, label, telegram_id):
    backup_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.datetime.now(datetime.UTC).strftime("%Y%m%dT%H%M%SZ")
    backup_path = backup_dir / f"{label}-before-telegram-admin-{telegram_id}-{timestamp}.json"
    shutil.copy2(source_path, backup_path)
    os.chmod(backup_path, stat.S_IRUSR | stat.S_IWUSR)
    return backup_path


def atomic_write_json(config_path, config):
    serialized = json.dumps(config, ensure_ascii=False, indent=2) + "\n"
    file_descriptor, temporary_name = tempfile.mkstemp(prefix=".openclaw-admin-", suffix=".json", dir=config_path.parent)
    try:
        with os.fdopen(file_descriptor, "w", encoding="utf-8") as temporary_file:
            temporary_file.write(serialized)
            temporary_file.flush()
            os.fsync(temporary_file.fileno())
        os.chmod(temporary_name, stat.S_IRUSR | stat.S_IWUSR)
        os.replace(temporary_name, config_path)
    finally:
        if os.path.exists(temporary_name):
            os.unlink(temporary_name)


def create_admin_directories(workspace, agent_dir, references_dir):
    workspace.mkdir(parents=True, exist_ok=True)
    agent_dir.mkdir(parents=True, exist_ok=True)


def merge_host_approvals(approvals, agent_id):
    changes = []
    if approvals.get("version") != 1:
        approvals["version"] = 1
        changes.append("set host approvals schema version=1")
    desired = {
        "security": "allowlist",
        "ask": "on-miss",
        "askFallback": "deny",
        "autoAllowSkills": False,
    }
    defaults = ensure_object(approvals, "defaults")
    for key, value in desired.items():
        if defaults.get(key) != value:
            defaults[key] = value
            changes.append(f"set host approval default {key}")
    agents = ensure_object(approvals, "agents")
    agent = ensure_object(agents, agent_id)
    for key, value in desired.items():
        if agent.get(key) != value:
            agent[key] = value
            changes.append(f"set host approval {agent_id} {key}")
    if not isinstance(agent.get("allowlist"), list):
        agent["allowlist"] = []
        changes.append(f"initialize host approval {agent_id} allowlist")
    return changes


def merge_plugin_approval_target(config, account_id, agent_id, telegram_id):
    changes = []
    approvals = ensure_object(config, "approvals")
    plugin = ensure_object(approvals, "plugin")
    if plugin.get("enabled") is not True:
        plugin["enabled"] = True
        changes.append("enable plugin approval forwarding")
    if plugin.get("mode") != "targets":
        plugin["mode"] = "targets"
        changes.append("set plugin approval mode=targets")
    agent_filter = ensure_array(plugin, "agentFilter")
    add_change(
        changes,
        append_unique(agent_filter, agent_id),
        "add canonical agent to plugin approval filter",
    )
    targets = ensure_array(plugin, "targets")
    exists = any(
        isinstance(target, dict)
        and target.get("channel") == "telegram"
        and str(target.get("to")) == telegram_id
        and target.get("accountId") == account_id
        for target in targets
    )
    if not exists:
        targets.append(
            {"channel": "telegram", "to": telegram_id, "accountId": account_id}
        )
        changes.append("add owner plugin approval target")
    return changes


def print_summary(
    mode,
    config_path,
    approvals_path,
    account_id,
    agent_id,
    telegram_id,
    changes,
    host_changes,
    backup_paths=None,
):
    print(f"mode={mode}")
    print(f"config={config_path}")
    # ``approvals_path`` is a display locator; native 2026.8 uses SQLite.
    print(f"host_approvals={approvals_path}")
    print(f"telegram_id={telegram_id}")
    print(f"account_id={account_id}")
    print(f"agent_id={agent_id}")
    print(f"change_count={len(changes) + len(host_changes)}")
    for change in changes:
        print(f"change={change}")
    for change in host_changes:
        print(f"host_change={change}")
    for backup_path in backup_paths or []:
        print(f"backup={backup_path}")


def main():
    arguments = parse_args()
    if os.geteuid() != 0:
        raise PermissionError("Run this VPS administration script as root")

    telegram_id, telegram_id_number = require_positive_telegram_id(arguments.telegram_id)
    account_id = require_identifier(arguments.account_id, "Telegram account ID")
    agent_id = require_identifier(arguments.agent_id, "Agent ID")
    openclaw_root = pathlib.Path(arguments.openclaw_root).expanduser().resolve()
    runtime_openclaw_root = (
        pathlib.Path(arguments.runtime_openclaw_root).expanduser()
        if arguments.runtime_openclaw_root
        else openclaw_root
    )
    config_path = openclaw_root / "openclaw.json"
    approvals_path = openclaw_root / "exec-approvals.json"
    if not config_path.is_file():
        raise FileNotFoundError(f"OpenClaw config not found: {config_path}")
    if config_path.is_symlink():
        raise ValueError("Refusing to modify a symlinked OpenClaw config")
    if approvals_path.is_symlink():
        raise ValueError("Refusing to modify symlinked host exec approvals")

    approvals_snapshot = load_approvals(openclaw_root)

    with config_path.open("r", encoding="utf-8") as config_file:
        original_config = json.load(config_file)
    if not isinstance(original_config, dict):
        raise ValueError("OpenClaw config root must be an object")

    configured_agent = find_agent(original_config, agent_id)
    agents_config = original_config.get("agents")
    defaults = agents_config.get("defaults", {}) if isinstance(agents_config, dict) else {}
    configured_workspace = configured_agent.get("workspace") if configured_agent else None
    if not configured_workspace and agent_id == "main" and isinstance(defaults, dict):
        configured_workspace = defaults.get("workspace")
    workspace = pathlib.Path(arguments.workspace).expanduser() if arguments.workspace else pathlib.Path(configured_workspace) if configured_workspace else runtime_openclaw_root / ("workspace" if agent_id == "main" else f"workspace-{agent_id}")
    agent_dir = pathlib.Path(arguments.agent_dir).expanduser() if arguments.agent_dir else runtime_openclaw_root / "agents" / agent_id / "agent"
    try:
        workspace_relative = workspace.relative_to(runtime_openclaw_root)
        workspace_filesystem = openclaw_root / workspace_relative
    except ValueError:
        workspace_filesystem = workspace
    agent_dir_filesystem = openclaw_root / "agents" / agent_id / "agent"
    if not arguments.runtime_openclaw_root:
        workspace = workspace.resolve()
        agent_dir = agent_dir.resolve()
        workspace_filesystem = workspace
        agent_dir_filesystem = agent_dir
    backup_dir = pathlib.Path(arguments.backup_dir).expanduser().resolve()
    references_dir = pathlib.Path(__file__).resolve().parent.parent / "references"

    updated_config = copy.deepcopy(original_config)
    changes = merge_config(
        updated_config,
        telegram_id,
        telegram_id_number,
        account_id,
        agent_id,
        workspace,
        agent_dir,
        bool(arguments.runtime_openclaw_root),
    )
    changes.extend(
        merge_plugin_approval_target(
            updated_config, account_id, agent_id, telegram_id
        )
    )

    original_approvals = approvals_snapshot.document
    updated_approvals = copy.deepcopy(original_approvals)
    host_changes = merge_host_approvals(updated_approvals, agent_id)

    if arguments.check:
        print_summary(
            "check",
            config_path,
            approvals_snapshot.locator,
            account_id,
            agent_id,
            telegram_id,
            changes,
            host_changes,
        )
        if changes or host_changes:
            print("status=not-compliant")
            return 2
        print("status=compliant")
        return 0

    if not arguments.apply:
        print_summary(
            "dry-run",
            config_path,
            approvals_snapshot.locator,
            account_id,
            agent_id,
            telegram_id,
            changes,
            host_changes,
        )
        print(
            "status=changes-required"
            if changes or host_changes
            else "status=already-compliant"
        )
        return 0

    if not changes and not host_changes:
        create_admin_directories(workspace_filesystem, agent_dir_filesystem, references_dir)
        print_summary(
            "apply",
            config_path,
            approvals_snapshot.locator,
            account_id,
            agent_id,
            telegram_id,
            changes,
            host_changes,
        )
        print("status=already-compliant")
        return 0

    backup_paths = []
    if changes:
        backup_paths.append(create_backup(config_path, backup_dir, telegram_id))
    if host_changes:
        backup = backup_approvals(
            approvals_snapshot,
            backup_dir,
            f"exec-approvals-before-telegram-admin-{telegram_id}",
        )
        backup_paths.append(pathlib.Path(backup["path"]))
    create_admin_directories(workspace_filesystem, agent_dir_filesystem, references_dir)
    if changes:
        atomic_write_json(config_path, updated_config)
    if host_changes:
        save_approvals(
            approvals_snapshot,
            updated_approvals,
            config_path=config_path,
        )
    print_summary(
        "apply",
        config_path,
        approvals_snapshot.locator,
        account_id,
        agent_id,
        telegram_id,
        changes,
        host_changes,
        backup_paths,
    )
    print("status=applied")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, json.JSONDecodeError, NativeApprovalsError) as error:
        print(f"error={error}", file=sys.stderr)
        sys.exit(1)
