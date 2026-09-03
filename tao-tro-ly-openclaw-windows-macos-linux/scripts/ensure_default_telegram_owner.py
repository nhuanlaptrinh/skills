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
        description="Ensure verified Telegram owners and approvers in OpenClaw config."
    )
    parser.add_argument("--openclaw-root", required=True)
    parser.add_argument("--account-id")
    parser.add_argument("--agent-id", action="append", default=[])
    parser.add_argument(
        "--owner-id",
        action="append",
        default=[],
        help="Verified Telegram owner ID; repeat for multiple owners.",
    )
    parser.add_argument("--extra-owner-id", action="append", default=[])
    parser.add_argument("--backup-dir")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--check", action="store_true")
    arguments = parser.parse_args()
    if arguments.apply and arguments.check:
        parser.error("--apply and --check cannot be used together")
    return arguments


def require_telegram_id(raw_value):
    value = str(raw_value)
    if not re.fullmatch(r"[1-9][0-9]*", value):
        raise ValueError(f"Invalid Telegram user ID: {raw_value}")
    return value


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


def ensure_dm_inline_buttons(telegram, changes):
    capabilities = telegram.get("capabilities")
    if capabilities is None:
        telegram["capabilities"] = {"inlineButtons": "allowlist"}
        changes.append("enable Telegram DM inline approval buttons")
        return
    if isinstance(capabilities, list):
        add_change(
            changes,
            append_unique(capabilities, "inlineButtons"),
            "enable Telegram inline approval buttons",
        )
        return
    if not isinstance(capabilities, dict):
        raise ValueError("Expected array or object at Telegram capabilities")
    if capabilities.get("inlineButtons") not in {"dm", "all", "allowlist"}:
        capabilities["inlineButtons"] = "allowlist"
        changes.append("enable Telegram DM inline approval buttons")


def merge_exec_approvals(parent, owner_ids, changes, label):
    approvals = ensure_object(parent, "execApprovals")
    if approvals.get("enabled") != "auto":
        approvals["enabled"] = "auto"
        changes.append(f"set {label} exec approvals=auto")
    approvers = ensure_array(approvals, "approvers")
    for owner_id in owner_ids:
        add_change(
            changes,
            append_unique(approvers, owner_id),
            f"add {owner_id} to {label} exec approvers",
        )
    if approvals.get("target") != "dm":
        approvals["target"] = "dm"
        changes.append(f"set {label} exec approval target=dm")


def merge_exec_policy(parent, changes, label):
    tools = ensure_object(parent, "tools")
    exec_tools = ensure_object(tools, "exec")
    if exec_tools.get("host") != "gateway":
        exec_tools["host"] = "gateway"
        changes.append(f"set {label} exec host=gateway")
    if exec_tools.get("mode") != "auto":
        exec_tools.pop("security", None)
        exec_tools.pop("ask", None)
        exec_tools["mode"] = "auto"
        changes.append(f"set {label} exec mode=auto")
    if exec_tools.get("strictInlineEval") is not True:
        exec_tools["strictInlineEval"] = True
        changes.append(f"enable {label} strict inline exec approval")


def merge_agent_exec_policy(config, agent_ids, changes):
    merge_exec_policy(config, changes, "global")
    agents = config.get("agents")
    if agents is None:
        return
    if not isinstance(agents, dict):
        raise ValueError("Expected object at agents")
    agent_list = agents.get("list")
    if agent_list is None:
        return
    if not isinstance(agent_list, list):
        raise ValueError("Expected array at agents.list")
    for agent_id in agent_ids:
        matches = [
            entry
            for entry in agent_list
            if isinstance(entry, dict) and entry.get("id") == agent_id
        ]
        if len(matches) > 1:
            raise ValueError(f"Duplicate agent id found: {agent_id}")
        if matches:
            merge_exec_policy(matches[0], changes, f"agent {agent_id}")


def merge_forwarded_approval(
    config, approval_kind, account_id, agent_ids, owner_ids, changes
):
    approvals = ensure_object(config, "approvals")
    approval = ensure_object(approvals, approval_kind)
    if approval.get("enabled") is not True:
        approval["enabled"] = True
        changes.append(f"enable {approval_kind} approval forwarding")
    if approval.get("mode") != "targets":
        approval["mode"] = "targets"
        changes.append(f"set {approval_kind} approval mode=targets")

    agent_filter = ensure_array(approval, "agentFilter")
    for agent_id in agent_ids:
        add_change(
            changes,
            append_unique(agent_filter, agent_id),
            f"add {agent_id} to {approval_kind} approval agent filter",
        )

    targets = ensure_array(approval, "targets")
    for owner_id in owner_ids:
        approval_target = {"channel": "telegram", "to": owner_id}
        if account_id:
            approval_target["accountId"] = account_id

        target_exists = any(
            isinstance(target, dict)
            and target.get("channel") == "telegram"
            and str(target.get("to")) == owner_id
            and (
                (account_id is None and not target.get("accountId"))
                or (account_id is not None and target.get("accountId") == account_id)
            )
            for target in targets
        )
        if not target_exists:
            targets.append(approval_target)
            changes.append(
                f"add Telegram {approval_kind} approval target {owner_id}"
            )


def merge_host_approvals(approvals, agent_ids):
    changes = []
    if approvals.get("version") != 1:
        approvals["version"] = 1
        changes.append("set host approvals schema version=1")

    defaults = ensure_object(approvals, "defaults")
    desired_policy = {
        "security": "allowlist",
        "ask": "on-miss",
        "askFallback": "deny",
    }
    for key, value in desired_policy.items():
        if defaults.get(key) != value:
            defaults[key] = value
            changes.append(f"set host approval default {key}={value}")

    agents = ensure_object(approvals, "agents")
    for agent_id in agent_ids:
        agent = ensure_object(agents, agent_id)
        for key, value in desired_policy.items():
            if agent.get(key) != value:
                agent[key] = value
                changes.append(
                    f"set host approval {agent_id} {key}={value}"
                )
    return changes


def configured_telegram_owners(config):
    commands = config.get("commands")
    if not isinstance(commands, dict):
        return []
    values = commands.get("ownerAllowFrom")
    if not isinstance(values, list):
        return []
    owners = []
    for value in values:
        text = str(value)
        if text.startswith("telegram:"):
            candidate = text.split(":", 1)[1]
            if re.fullmatch(r"[1-9][0-9]*", candidate) and candidate not in owners:
                owners.append(candidate)
    return owners


def merge_config(config, account_id, agent_ids, owner_ids):
    changes = []

    commands = ensure_object(config, "commands")
    owner_allow_from = ensure_array(commands, "ownerAllowFrom")
    for owner_id in owner_ids:
        add_change(
            changes,
            append_unique(owner_allow_from, f"telegram:{owner_id}"),
            f"add {owner_id} to command owners",
        )
    if commands.get("ownerDisplay") != "raw":
        commands["ownerDisplay"] = "raw"
        changes.append("set commands.ownerDisplay=raw")

    channels = ensure_object(config, "channels")
    telegram = ensure_object(channels, "telegram")
    if telegram.get("dmPolicy") != "pairing":
        telegram["dmPolicy"] = "pairing"
        changes.append("set Telegram dmPolicy=pairing")
    allow_from = ensure_array(telegram, "allowFrom")
    for owner_id in owner_ids:
        add_change(
            changes,
            append_unique(allow_from, owner_id),
            f"add {owner_id} to Telegram allowFrom",
        )
    ensure_dm_inline_buttons(telegram, changes)
    merge_exec_approvals(telegram, owner_ids, changes, "Telegram")

    if account_id:
        accounts = ensure_object(telegram, "accounts")
        account = accounts.get(account_id)
        if not isinstance(account, dict):
            raise ValueError(f"Telegram account does not exist: {account_id}")
        if account.get("dmPolicy") != "pairing":
            account["dmPolicy"] = "pairing"
            changes.append(f"set Telegram account {account_id} dmPolicy=pairing")
        account_allow_from = ensure_array(account, "allowFrom")
        for owner_id in owner_ids:
            add_change(
                changes,
                append_unique(account_allow_from, owner_id),
                f"add {owner_id} to Telegram account {account_id} allowFrom",
            )
        merge_exec_approvals(
            account, owner_ids, changes, f"Telegram account {account_id}"
        )

    merge_agent_exec_policy(config, agent_ids, changes)
    merge_forwarded_approval(
        config, "exec", account_id, agent_ids, owner_ids, changes
    )
    merge_forwarded_approval(
        config, "plugin", account_id, agent_ids, owner_ids, changes
    )

    skills = ensure_object(config, "skills")
    workshop = ensure_object(skills, "workshop")
    if workshop.get("approvalPolicy") != "pending":
        workshop["approvalPolicy"] = "pending"
        changes.append("set Skill Workshop approvalPolicy=pending")

    return changes


def create_backup(source_path, backup_dir, label):
    backup_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.datetime.now(datetime.UTC).strftime("%Y%m%dT%H%M%SZ")
    candidate = backup_dir / f"{label}-before-required-owner-{timestamp}.json"
    backup_path = candidate
    suffix = 1
    while backup_path.exists():
        backup_path = candidate.with_name(
            f"{candidate.stem}-{suffix}{candidate.suffix}"
        )
        suffix += 1
    shutil.copy2(source_path, backup_path)
    if os.name != "nt":
        os.chmod(backup_path, stat.S_IRUSR | stat.S_IWUSR)
    return backup_path


def atomic_write_json(destination_path, data):
    serialized = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    file_descriptor, temporary_name = tempfile.mkstemp(
        prefix=".openclaw-owner-", suffix=".json", dir=destination_path.parent
    )
    try:
        with os.fdopen(file_descriptor, "w", encoding="utf-8") as temporary_file:
            temporary_file.write(serialized)
            temporary_file.flush()
            os.fsync(temporary_file.fileno())
        if os.name != "nt":
            os.chmod(temporary_name, stat.S_IRUSR | stat.S_IWUSR)
        os.replace(temporary_name, destination_path)
    finally:
        if os.path.exists(temporary_name):
            os.unlink(temporary_name)


def print_summary(
    mode,
    config_path,
    approvals_path,
    account_id,
    agent_ids,
    owner_ids,
    config_changes,
    host_changes,
    backup_paths=None,
):
    print(f"mode={mode}")
    print(f"config={config_path}")
    print(f"host_approvals={approvals_path}")
    print(f"account_id={account_id or 'default'}")
    print(f"agent_ids={','.join(agent_ids)}")
    print(f"verified_owner_count={len(owner_ids)}")
    print(f"change_count={len(config_changes) + len(host_changes)}")
    for change in config_changes:
        print(f"config_change={change}")
    for change in host_changes:
        print(f"host_change={change}")
    for backup_path in backup_paths or []:
        print(f"backup={backup_path}")


def main():
    arguments = parse_args()
    openclaw_root = pathlib.Path(arguments.openclaw_root).expanduser().resolve()
    config_path = openclaw_root / "openclaw.json"
    approvals_path = openclaw_root / "exec-approvals.json"
    if not config_path.is_file():
        raise FileNotFoundError(f"OpenClaw config not found: {config_path}")
    if config_path.is_symlink():
        raise ValueError("Refusing to modify a symlinked OpenClaw config")
    if approvals_path.is_symlink():
        raise ValueError("Refusing to modify symlinked host exec approvals")

    account_id = (
        require_identifier(arguments.account_id, "Telegram account ID")
        if arguments.account_id
        else None
    )
    agent_ids = arguments.agent_id or ["main"]
    agent_ids = list(dict.fromkeys(require_identifier(value, "Agent ID") for value in agent_ids))
    explicit_owner_ids = [
        require_telegram_id(value)
        for value in [*arguments.owner_id, *arguments.extra_owner_id]
    ]

    with config_path.open("r", encoding="utf-8") as config_file:
        original_config = json.load(config_file)
    if not isinstance(original_config, dict):
        raise ValueError("OpenClaw config root must be an object")

    configured_owner_ids = configured_telegram_owners(original_config)
    owner_ids = list(dict.fromkeys([*configured_owner_ids, *explicit_owner_ids]))
    if not owner_ids:
        raise ValueError(
            "No verified Telegram owners found; pass --owner-id for the target VPS"
        )

    updated_config = copy.deepcopy(original_config)
    config_changes = merge_config(
        updated_config, account_id, agent_ids, owner_ids
    )

    if approvals_path.exists():
        with approvals_path.open("r", encoding="utf-8") as approvals_file:
            original_approvals = json.load(approvals_file)
        if not isinstance(original_approvals, dict):
            raise ValueError("Host exec approvals root must be an object")
    else:
        original_approvals = {}
    updated_approvals = copy.deepcopy(original_approvals)
    host_changes = merge_host_approvals(updated_approvals, agent_ids)

    if arguments.check:
        print_summary(
            "check",
            config_path,
            approvals_path,
            account_id,
            agent_ids,
            owner_ids,
            config_changes,
            host_changes,
        )
        if config_changes or host_changes:
            print("status=not-compliant")
            return 2
        print("status=compliant")
        return 0

    if not arguments.apply:
        print_summary(
            "dry-run",
            config_path,
            approvals_path,
            account_id,
            agent_ids,
            owner_ids,
            config_changes,
            host_changes,
        )
        print(
            "status=changes-required"
            if config_changes or host_changes
            else "status=already-compliant"
        )
        return 0

    if not config_changes and not host_changes:
        print_summary(
            "apply",
            config_path,
            approvals_path,
            account_id,
            agent_ids,
            owner_ids,
            config_changes,
            host_changes,
        )
        print("status=already-compliant")
        return 0

    backup_dir = (
        pathlib.Path(arguments.backup_dir).expanduser().resolve()
        if arguments.backup_dir
        else openclaw_root / "backups" / "telegram-owner"
    )
    backup_paths = []
    if config_changes:
        backup_paths.append(create_backup(config_path, backup_dir, "openclaw"))
        atomic_write_json(config_path, updated_config)
    if host_changes:
        if approvals_path.exists():
            backup_paths.append(
                create_backup(approvals_path, backup_dir, "exec-approvals")
            )
        atomic_write_json(approvals_path, updated_approvals)
    print_summary(
        "apply",
        config_path,
        approvals_path,
        account_id,
            agent_ids,
            owner_ids,
            config_changes,
        host_changes,
        backup_paths,
    )
    print("status=applied")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"error={error}", file=sys.stderr)
        sys.exit(1)
