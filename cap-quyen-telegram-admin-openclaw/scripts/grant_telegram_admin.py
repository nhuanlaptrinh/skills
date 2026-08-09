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


def parse_args():
    parser = argparse.ArgumentParser(
        description="Grant a verified Telegram user full VPS administration through OpenClaw."
    )
    parser.add_argument("--telegram-id", required=True)
    parser.add_argument("--openclaw-root", default="/root/.openclaw")
    parser.add_argument("--account-id", default="main")
    parser.add_argument("--agent-id", default="owner-admin")
    parser.add_argument("--backup-dir", default="/root/_Backups/openclaw")
    parser.add_argument("--workspace")
    parser.add_argument("--agent-dir")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--replace-binding", action="store_true")
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


def append_unique(values, candidate, normalize=str):
    normalized_candidate = normalize(candidate)
    if any(normalize(value) == normalized_candidate for value in values):
        return False
    values.append(candidate)
    return True


def add_change(changes, changed, description):
    if changed:
        changes.append(description)


def binding_matches(binding, account_id, telegram_id):
    match = binding.get("match")
    if not isinstance(match, dict):
        return False
    peer = match.get("peer")
    if not isinstance(peer, dict):
        return False
    return (
        match.get("channel") == "telegram"
        and match.get("accountId") == account_id
        and peer.get("kind") == "direct"
        and str(peer.get("id")) == telegram_id
    )


def merge_config(config, telegram_id, telegram_id_number, account_id, agent_id, workspace, agent_dir, replace_binding):
    changes = []
    channels = ensure_object(config, "channels")
    telegram = ensure_object(channels, "telegram")
    accounts = ensure_object(telegram, "accounts")
    if account_id not in accounts or not isinstance(accounts[account_id], dict):
        raise ValueError(f"Telegram account does not exist: {account_id}")
    account = accounts[account_id]

    if telegram.get("dmPolicy") != "pairing":
        telegram["dmPolicy"] = "pairing"
        changes.append("set Telegram dmPolicy=pairing")
    if account.get("dmPolicy") != "pairing":
        account["dmPolicy"] = "pairing"
        changes.append(f"set Telegram account {account_id} dmPolicy=pairing")

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
    if commands.get("ownerDisplay") != "raw":
        commands["ownerDisplay"] = "raw"
        changes.append("set commands.ownerDisplay=raw")

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

    agents = ensure_object(config, "agents")
    agent_list = ensure_array(agents, "list")
    matching_agents = [entry for entry in agent_list if isinstance(entry, dict) and entry.get("id") == agent_id]
    if len(matching_agents) > 1:
        raise ValueError(f"Duplicate agent id found: {agent_id}")
    if matching_agents:
        admin_agent = matching_agents[0]
    else:
        admin_agent = {
            "id": agent_id,
            "name": agent_id,
            "workspace": str(workspace),
            "agentDir": str(agent_dir),
            "tools": {"profile": "full"},
        }
        agent_list.append(admin_agent)
        changes.append(f"create admin agent {agent_id}")

    if not admin_agent.get("workspace"):
        admin_agent["workspace"] = str(workspace)
        changes.append(f"set {agent_id} workspace")
    if not admin_agent.get("agentDir"):
        admin_agent["agentDir"] = str(agent_dir)
        changes.append(f"set {agent_id} agentDir")
    tools = ensure_object(admin_agent, "tools")
    if tools.get("profile") != "full":
        tools["profile"] = "full"
        changes.append(f"set {agent_id} tools.profile=full")

    bindings = ensure_array(config, "bindings")
    target_bindings = [binding for binding in bindings if isinstance(binding, dict) and binding_matches(binding, account_id, telegram_id)]
    conflicting_bindings = [binding for binding in target_bindings if binding.get("agentId") != agent_id]
    if conflicting_bindings and not replace_binding:
        conflicting_agent_names = sorted({str(binding.get("agentId")) for binding in conflicting_bindings})
        raise ValueError(
            "Target already has a direct binding to another agent: "
            + ", ".join(conflicting_agent_names)
            + ". Re-run with --replace-binding only after explicit approval."
        )
    if conflicting_bindings:
        config["bindings"] = [
            binding
            for binding in bindings
            if not (isinstance(binding, dict) and binding_matches(binding, account_id, telegram_id))
        ]
        bindings = config["bindings"]
        changes.append("remove conflicting direct binding")

    exact_binding_exists = any(
        isinstance(binding, dict)
        and binding.get("agentId") == agent_id
        and binding_matches(binding, account_id, telegram_id)
        for binding in bindings
    )
    if not exact_binding_exists:
        bindings.append(
            {
                "agentId": agent_id,
                "match": {
                    "channel": "telegram",
                    "accountId": account_id,
                    "peer": {"kind": "direct", "id": telegram_id},
                },
            }
        )
        changes.append(f"add direct Telegram binding to {agent_id}")

    effective_workspace = pathlib.Path(str(admin_agent["workspace"])).expanduser().resolve()
    effective_agent_dir = pathlib.Path(str(admin_agent["agentDir"])).expanduser().resolve()
    return changes, effective_workspace, effective_agent_dir


def create_backup(config_path, backup_dir, telegram_id):
    backup_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.datetime.now(datetime.UTC).strftime("%Y%m%dT%H%M%SZ")
    backup_path = backup_dir / f"openclaw-before-telegram-admin-{telegram_id}-{timestamp}.json"
    shutil.copy2(config_path, backup_path)
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


def create_admin_directories(workspace, agent_dir, template_path):
    workspace.mkdir(parents=True, exist_ok=True)
    agent_dir.mkdir(parents=True, exist_ok=True)
    agents_path = workspace / "AGENTS.md"
    if not agents_path.exists():
        shutil.copy2(template_path, agents_path)


def print_summary(mode, config_path, account_id, agent_id, telegram_id, changes, backup_path=None):
    print(f"mode={mode}")
    print(f"config={config_path}")
    print(f"telegram_id={telegram_id}")
    print(f"account_id={account_id}")
    print(f"agent_id={agent_id}")
    print(f"change_count={len(changes)}")
    for change in changes:
        print(f"change={change}")
    if backup_path is not None:
        print(f"backup={backup_path}")


def main():
    arguments = parse_args()
    if os.geteuid() != 0:
        raise PermissionError("Run this VPS administration script as root")

    telegram_id, telegram_id_number = require_positive_telegram_id(arguments.telegram_id)
    account_id = require_identifier(arguments.account_id, "Telegram account ID")
    agent_id = require_identifier(arguments.agent_id, "Agent ID")
    openclaw_root = pathlib.Path(arguments.openclaw_root).expanduser().resolve()
    config_path = openclaw_root / "openclaw.json"
    if not config_path.is_file():
        raise FileNotFoundError(f"OpenClaw config not found: {config_path}")
    if config_path.is_symlink():
        raise ValueError("Refusing to modify a symlinked OpenClaw config")

    workspace = pathlib.Path(arguments.workspace).expanduser().resolve() if arguments.workspace else openclaw_root / f"workspace-{agent_id}"
    agent_dir = pathlib.Path(arguments.agent_dir).expanduser().resolve() if arguments.agent_dir else openclaw_root / "agents" / agent_id / "agent"
    backup_dir = pathlib.Path(arguments.backup_dir).expanduser().resolve()
    template_path = pathlib.Path(__file__).resolve().parent.parent / "references" / "owner-admin-AGENTS.md"

    with config_path.open("r", encoding="utf-8") as config_file:
        original_config = json.load(config_file)
    if not isinstance(original_config, dict):
        raise ValueError("OpenClaw config root must be an object")

    updated_config = copy.deepcopy(original_config)
    changes, effective_workspace, effective_agent_dir = merge_config(
        updated_config,
        telegram_id,
        telegram_id_number,
        account_id,
        agent_id,
        workspace,
        agent_dir,
        arguments.replace_binding,
    )

    if arguments.check:
        print_summary("check", config_path, account_id, agent_id, telegram_id, changes)
        if changes:
            print("status=not-compliant")
            return 2
        print("status=compliant")
        return 0

    if not arguments.apply:
        print_summary("dry-run", config_path, account_id, agent_id, telegram_id, changes)
        print("status=changes-required" if changes else "status=already-compliant")
        return 0

    if not changes:
        print_summary("apply", config_path, account_id, agent_id, telegram_id, changes)
        print("status=already-compliant")
        return 0

    backup_path = create_backup(config_path, backup_dir, telegram_id)
    create_admin_directories(effective_workspace, effective_agent_dir, template_path)
    atomic_write_json(config_path, updated_config)
    print_summary("apply", config_path, account_id, agent_id, telegram_id, changes, backup_path)
    print("status=applied")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"error={error}", file=sys.stderr)
        sys.exit(1)
