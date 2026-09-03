#!/usr/bin/env python3
"""Synchronize verified Telegram and Zalo owner identities in OpenClaw config."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import pathlib
import shutil
import stat
import subprocess
import tempfile
from typing import Any


NON_OWNER_DENY = {
    "group:runtime",
    "group:fs",
    "group:messaging",
}


def fail(message: str) -> "NoReturn":
    raise SystemExit(f"error={message}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Add verified Telegram/Zalo co-owners without replacing existing policy."
    )
    parser.add_argument("--openclaw-root", required=True)
    parser.add_argument("--telegram-id", action="append", default=[])
    parser.add_argument("--zalo-id", action="append", default=[])
    parser.add_argument("--telegram-account-id")
    parser.add_argument("--zalo-account-id", default="default")
    parser.add_argument(
        "--open-zalo-groups",
        action="store_true",
        help="Explicitly open Zalo groups and disable mention requirements.",
    )
    parser.add_argument("--container")
    parser.add_argument("--runtime-home", default="/root")
    parser.add_argument("--runtime-openclaw-root", default="/root/.openclaw")
    parser.add_argument(
        "--backup-dir",
        help="Private directory for the pre-change config when using --apply.",
    )
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--dry-run", action="store_true")
    action.add_argument("--apply", action="store_true")
    action.add_argument("--check", action="store_true")
    return parser.parse_args()


def load_json(path: pathlib.Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        fail(f"unsafe_config_path:{path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"invalid_config:{type(exc).__name__}")
    if not isinstance(value, dict):
        fail("config_root_not_object")
    return value


def ensure_dict(parent: dict[str, Any], key: str) -> dict[str, Any]:
    value = parent.get(key)
    if value is None:
        value = {}
        parent[key] = value
    if not isinstance(value, dict):
        fail(f"expected_object:{key}")
    return value


def ensure_list(parent: dict[str, Any], key: str) -> list[Any]:
    value = parent.get(key)
    if value is None:
        value = []
        parent[key] = value
    if not isinstance(value, list):
        fail(f"expected_array:{key}")
    return value


def append_unique(values: list[Any], value: Any) -> bool:
    if value in values:
        return False
    values.append(value)
    return True


def sync_existing_group_allowlists(
    scope: dict[str, Any], owner: str, changes: list[str], label: str
) -> None:
    """Add an owner only to group allowlists that already exist."""
    group_allow = scope.get("groupAllowFrom")
    if isinstance(group_allow, list) and append_unique(group_allow, owner):
        changes.append(f"add {label} group owner allowFrom")
    groups = scope.get("groups")
    if not isinstance(groups, dict):
        return
    for group in groups.values():
        if not isinstance(group, dict):
            continue
        allow = group.get("allowFrom")
        if isinstance(allow, list) and "*" not in allow and append_unique(allow, owner):
            changes.append(f"add {label} existing group owner allowFrom")


def validate_ids(values: list[str], label: str) -> list[str]:
    output: list[str] = []
    for value in values:
        if not value.isdigit() or len(value) < 5 or len(value) > 25:
            fail(f"invalid_{label}_id_at_index:{len(output)}")
        if value not in output:
            output.append(value)
    return output


def find_main(config: dict[str, Any]) -> dict[str, Any]:
    agents = config.get("agents")
    if not isinstance(agents, dict):
        fail("agents_missing")
    entries = agents.get("list")
    if isinstance(entries, list):
        matches = [
            entry for entry in entries if isinstance(entry, dict) and entry.get("id") == "main"
        ]
    else:
        entries_by_id = agents.get("entries")
        main = entries_by_id.get("main") if isinstance(entries_by_id, dict) else None
        matches = [main] if isinstance(main, dict) else []
    if len(matches) != 1:
        fail("main_agent_not_unique")
    return matches[0]


def telegram_account(config: dict[str, Any], account_id: str) -> dict[str, Any]:
    channels = ensure_dict(config, "channels")
    telegram = ensure_dict(channels, "telegram")
    accounts = telegram.get("accounts")
    if not isinstance(accounts, dict) or not isinstance(accounts.get(account_id), dict):
        fail("telegram_account_missing")
    return accounts[account_id]


def infer_telegram_account(config: dict[str, Any], requested: str | None) -> str | None:
    if requested:
        return requested
    accounts = config.get("channels", {}).get("telegram", {}).get("accounts", {})
    if not isinstance(accounts, dict):
        return None
    enabled = [key for key, value in accounts.items() if isinstance(value, dict) and value.get("enabled")]
    return enabled[0] if len(enabled) == 1 else None


def transform(
    original: dict[str, Any], telegram_ids: list[str], zalo_ids: list[str], telegram_account_id: str | None,
    zalo_account_id: str, open_zalo_groups: bool,
) -> tuple[dict[str, Any], list[str]]:
    updated = copy.deepcopy(original)
    changes: list[str] = []

    channels = ensure_dict(updated, "channels")
    if telegram_ids:
        if not telegram_account_id:
            fail("telegram_account_id_required")
        telegram = ensure_dict(channels, "telegram")
        account = telegram_account(updated, telegram_account_id)
        top_allow = ensure_list(telegram, "allowFrom")
        account_allow = ensure_list(account, "allowFrom")
        approvals = ensure_dict(telegram, "execApprovals")
        approvers = ensure_list(approvals, "approvers")
        commands = ensure_dict(updated, "commands")
        owner_allow = ensure_list(commands, "ownerAllowFrom")
        elevated = ensure_dict(ensure_dict(updated, "tools"), "elevated")
        elevated_allow = ensure_dict(elevated, "allowFrom")
        elevated_telegram = ensure_list(elevated_allow, "telegram")
        plugin = ensure_dict(ensure_dict(updated, "approvals"), "plugin")
        targets = ensure_list(plugin, "targets")

        for owner in telegram_ids:
            if append_unique(top_allow, owner):
                changes.append("add Telegram channel allowFrom")
            if append_unique(account_allow, owner):
                changes.append("add Telegram account allowFrom")
            if append_unique(owner_allow, f"telegram:{owner}"):
                changes.append("add Telegram owner command permission")
            if append_unique(approvers, owner):
                changes.append("add Telegram exec approver")
            if append_unique(elevated_telegram, owner):
                changes.append("add Telegram elevated owner")
            target = {"channel": "telegram", "to": owner, "accountId": telegram_account_id}
            if not any(
                isinstance(item, dict)
                and item.get("channel") == "telegram"
                and str(item.get("to")) == owner
                and item.get("accountId") == telegram_account_id
                for item in targets
            ):
                targets.append(target)
                changes.append("add Telegram plugin approval target")
            sync_existing_group_allowlists(account, owner, changes, "Telegram account")

    if zalo_ids:
        zalo = ensure_dict(channels, "zalouser")
        dm_allow = ensure_list(zalo, "allowFrom")
        if open_zalo_groups:
            if zalo.get("groupPolicy") != "open":
                zalo["groupPolicy"] = "open"
                changes.append("set Zalo groupPolicy=open")
            group_allow = ensure_list(zalo, "groupAllowFrom")
            if append_unique(group_allow, "*"):
                changes.append("open Zalo group wildcard")
            groups = ensure_dict(zalo, "groups")
            wildcard = ensure_dict(groups, "*")
            if wildcard.get("enabled") is not True:
                wildcard["enabled"] = True
                changes.append("enable Zalo wildcard group")
            if wildcard.get("requireMention") is not False:
                wildcard["requireMention"] = False
                changes.append("disable Zalo group mention requirement")

        accounts = zalo.get("accounts")
        zalo_account = accounts.get(zalo_account_id) if isinstance(accounts, dict) else None
        if isinstance(zalo_account, dict):
            account_dm_allow = ensure_list(zalo_account, "allowFrom")
        else:
            account_dm_allow = None

        commands = ensure_dict(updated, "commands")
        owner_allow = ensure_list(commands, "ownerAllowFrom")
        elevated = ensure_dict(ensure_dict(updated, "tools"), "elevated")
        elevated_allow = ensure_dict(elevated, "allowFrom")
        elevated_zalo = ensure_list(elevated_allow, "zalouser")

        for owner in zalo_ids:
            if append_unique(dm_allow, owner):
                changes.append("add Zalo DM allowFrom")
            if account_dm_allow is not None and append_unique(account_dm_allow, owner):
                changes.append("add Zalo account DM allowFrom")
            if append_unique(owner_allow, f"zalouser:{owner}"):
                changes.append("add Zalo owner command permission")
            if append_unique(elevated_zalo, owner):
                changes.append("add Zalo elevated owner")
            sync_existing_group_allowlists(zalo, owner, changes, "Zalo")
            if isinstance(zalo_account, dict):
                sync_existing_group_allowlists(zalo_account, owner, changes, "Zalo account")

    agent = find_main(updated)
    tools = ensure_dict(agent, "tools")
    if tools.get("profile") != "full":
        fail("main_profile_not_full")
    exec_policy = tools.get("exec")
    if not (
        isinstance(exec_policy, dict)
        and exec_policy.get("host") == "gateway"
        and exec_policy.get("mode") == "full"
        and exec_policy.get("strictInlineEval") is False
    ):
        fail("main_full_exec_required")
    sender = ensure_dict(tools, "toolsBySender")
    wildcard = ensure_dict(sender, "*")
    deny = ensure_list(wildcard, "deny")
    for required in sorted(NON_OWNER_DENY):
        if append_unique(deny, required):
            changes.append("preserve non-owner safeguard")
    for owner in telegram_ids:
        key = f"channel:telegram:{owner}"
        if sender.get(key) != {}:
            sender[key] = {}
            changes.append("grant exact Telegram owner sender policy")
    for owner in zalo_ids:
        key = f"channel:zalouser:{owner}"
        if sender.get(key) != {}:
            sender[key] = {}
            changes.append("grant exact Zalo owner sender policy")

    skills = ensure_dict(updated, "skills")
    workshop = ensure_dict(skills, "workshop")
    if workshop.get("approvalPolicy") != "pending":
        workshop["approvalPolicy"] = "pending"
        changes.append("set Skill Workshop approvalPolicy=pending")

    return updated, changes


def validate_candidate(
    root: pathlib.Path,
    value: dict[str, Any],
    container: str | None,
    runtime_home: str,
    runtime_openclaw_root: str,
) -> None:
    fd, temp_name = tempfile.mkstemp(prefix=".owner-access-candidate-", suffix=".json", dir=root)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temp_name, 0o600)
        if container:
            runtime_path = str(pathlib.PurePosixPath(runtime_openclaw_root) / pathlib.Path(temp_name).name)
            command = [
                "docker", "exec", "-e", f"HOME={runtime_home}", "-e",
                f"OPENCLAW_CONFIG_PATH={runtime_path}", container,
                "openclaw", "config", "validate", "--json",
            ]
            environment = None
        else:
            command = ["openclaw", "config", "validate", "--json"]
            environment = os.environ.copy()
            environment["OPENCLAW_CONFIG_PATH"] = temp_name
        result = subprocess.run(
            command, check=False, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, env=environment,
        )
        if result.returncode != 0:
            fail("candidate_schema_validation_failed")
        try:
            report = json.loads(result.stdout)
        except json.JSONDecodeError:
            fail("candidate_schema_validation_unreadable")
        if report.get("valid") is not True:
            fail("candidate_schema_validation_failed")
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def atomic_write(path: pathlib.Path, value: dict[str, Any]) -> None:
    original_stat = path.stat()
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temp_name, stat.S_IMODE(original_stat.st_mode))
        os.chown(temp_name, original_stat.st_uid, original_stat.st_gid)
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def main() -> int:
    args = parse_args()
    if not (args.telegram_id or args.zalo_id):
        fail("at_least_one_owner_id_required")
    telegram_ids = validate_ids(args.telegram_id, "telegram")
    zalo_ids = validate_ids(args.zalo_id, "zalo")
    root = pathlib.Path(args.openclaw_root).expanduser().resolve()
    path = root / "openclaw.json"
    original = load_json(path)
    account_id = infer_telegram_account(original, args.telegram_account_id)
    candidate, changes = transform(
        original,
        telegram_ids,
        zalo_ids,
        account_id,
        args.zalo_account_id,
        args.open_zalo_groups,
    )
    validate_candidate(
        root, candidate, args.container, args.runtime_home, args.runtime_openclaw_root
    )

    mode = "check" if args.check else "apply" if args.apply else "dry-run"
    print(f"mode={mode}")
    print(f"telegram_owner_count={len(telegram_ids)}")
    print(f"zalo_owner_count={len(zalo_ids)}")
    print(f"changes_required={str(bool(changes)).lower()}")
    for change in changes:
        print(f"change={change}")

    if args.check:
        return 1 if changes else 0
    if not args.apply:
        return 0
    if not args.backup_dir:
        fail("backup_dir_required_for_apply")
    backup = pathlib.Path(args.backup_dir).expanduser().resolve()
    try:
        backup.mkdir(parents=True, exist_ok=False)
    except FileExistsError:
        fail("backup_dir_already_exists")
    os.chmod(backup, 0o700)
    before = backup / "openclaw.json.before"
    shutil.copy2(path, before)
    os.chmod(before, 0o600)
    digest = hashlib.sha256(before.read_bytes()).hexdigest()
    sums = backup / "SHA256SUMS"
    sums.write_text(f"{digest}  openclaw.json.before\n", encoding="ascii")
    os.chmod(sums, 0o600)
    atomic_write(path, candidate)
    # Re-read the written file so a partial or malformed write cannot be reported as success.
    load_json(path)
    print("apply=pass")
    print(f"backup_dir={backup}")
    return 0


if __name__ == "__main__":
    main()
