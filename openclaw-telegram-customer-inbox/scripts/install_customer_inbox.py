#!/usr/bin/env python3
"""Install or verify the reusable Telegram customer inbox plugin."""

from __future__ import annotations

import argparse
import copy
import filecmp
import json
import os
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path


PLUGIN_ID = "telegram-customer-inbox"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--openclaw-root", default=str(Path.home() / ".openclaw"))
    parser.add_argument("--workspace")
    parser.add_argument("--account-id", required=True)
    parser.add_argument("--group-id", required=True)
    parser.add_argument("--staff-id", action="append", required=True, dest="staff_ids")
    parser.add_argument("--brand-name", default="Bot")
    parser.add_argument("--state-file")
    parser.add_argument("--backup-dir")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--apply", action="store_true")
    mode.add_argument("--check", action="store_true")
    return parser.parse_args()


def fail(message: str) -> None:
    raise SystemExit(f"ERROR: {message}")


def load_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        fail(f"missing OpenClaw config: {path}")
    except json.JSONDecodeError as error:
        fail(f"invalid JSON in {path}: {error}")
    if not isinstance(value, dict):
        fail(f"OpenClaw config must be an object: {path}")
    return value


def plugin_source() -> Path:
    source = Path(__file__).resolve().parents[1] / "assets" / "telegram-customer-inbox-plugin"
    if not source.is_dir():
        fail(f"missing bundled plugin template: {source}")
    return source


def normalized_staff_ids(values: list[str]) -> list[str]:
    result = []
    for value in values:
        item = str(value).strip()
        if not item or not item.lstrip("-").isdigit() or item.startswith("-"):
            fail("--staff-id must contain positive numeric Telegram user IDs")
        if item not in result:
            result.append(item)
    return result


def config_target(args: argparse.Namespace) -> tuple[Path, Path, Path, Path]:
    openclaw_root = Path(args.openclaw_root).expanduser().resolve()
    workspace = Path(args.workspace).expanduser().resolve() if args.workspace else openclaw_root / "workspace"
    config_path = openclaw_root / "openclaw.json"
    plugin_path = workspace / "plugins" / PLUGIN_ID
    state_file = Path(args.state_file).expanduser().resolve() if args.state_file else workspace / "state" / PLUGIN_ID / "state.json"
    return config_path, workspace, plugin_path, state_file


def validate_account(config: dict, account_id: str) -> dict:
    telegram = config.get("channels", {}).get("telegram", {})
    accounts = telegram.get("accounts", {})
    account = accounts.get(account_id)
    if not isinstance(account, dict):
        fail(f"Telegram account does not exist: {account_id}; configure tokenFile/token first")
    if not account.get("tokenFile") and not account.get("token"):
        fail(f"Telegram account has no tokenFile/token: {account_id}")
    if account.get("groupPolicy") == "disabled":
        fail(f"Telegram account groupPolicy is disabled: {account_id}")
    return account


def build_expected(args: argparse.Namespace, config: dict, state_file: Path, staff_ids: list[str]) -> tuple[dict, dict]:
    channels = config.setdefault("channels", {})
    telegram = channels.setdefault("telegram", {})
    account = validate_account(config, args.account_id)
    plugins = config.setdefault("plugins", {})
    entries = plugins.setdefault("entries", {})
    load = plugins.setdefault("load", {})
    paths = load.setdefault("paths", [])
    plugin_path = str((Path(args.workspace).expanduser().resolve() if args.workspace else Path(args.openclaw_root).expanduser().resolve() / "workspace") / "plugins" / PLUGIN_ID)
    if plugin_path not in paths:
        paths.append(plugin_path)
    entries[PLUGIN_ID] = {
        "enabled": True,
        "config": {
            "groupId": str(args.group_id).strip(),
            "accountId": args.account_id,
            "brandName": args.brand_name.strip() or "Bot",
            "staffIds": staff_ids,
            "stateFile": str(state_file),
        },
    }
    capabilities = account.get("capabilities")
    if isinstance(capabilities, dict):
        if capabilities.get("inlineButtons") not in {"group", "all", "allowlist"}:
            capabilities["inlineButtons"] = "group"
    elif isinstance(capabilities, list):
        if "inlineButtons" not in capabilities:
            capabilities.append("inlineButtons")
    else:
        account["capabilities"] = {"inlineButtons": "group"}
    groups = account.setdefault("groups", {})
    group = groups.setdefault(str(args.group_id).strip(), {})
    group["enabled"] = True
    group["requireMention"] = False
    group["allowFrom"] = staff_ids
    return config, entries[PLUGIN_ID]


def write_atomic(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def backup_paths(config_path: Path, plugin_path: Path, backup_dir: Path) -> None:
    backup_dir.mkdir(parents=True, exist_ok=True)
    os.chmod(backup_dir, 0o700)
    if config_path.exists():
        shutil.copy2(config_path, backup_dir / "openclaw.json")
    if plugin_path.exists():
        shutil.copytree(plugin_path, backup_dir / "plugin", dirs_exist_ok=True)


def install_plugin(source: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    for item in source.iterdir():
        target = destination / item.name
        if item.is_dir():
            shutil.copytree(item, target, dirs_exist_ok=True)
        else:
            shutil.copy2(item, target)
    for path in destination.rglob("*"):
        if path.is_file():
            os.chmod(path, 0o600)


def plugin_matches(source: Path, destination: Path) -> bool:
    return destination.is_dir() and all(
        (destination / item.name).is_file() and filecmp.cmp(item, destination / item.name, shallow=False)
        for item in source.iterdir() if item.is_file()
    )


def main() -> int:
    args = parse_args()
    if not args.group_id.startswith("-100") or not args.group_id[1:].isdigit():
        fail("--group-id must be the current Telegram supergroup ID (-100...)")
    args.staff_ids = normalized_staff_ids(args.staff_ids)
    config_path, workspace, plugin_path, state_file = config_target(args)
    config = load_json(config_path)
    expected_config, entry = build_expected(args, copy.deepcopy(config), state_file, args.staff_ids)
    source = plugin_source()

    if args.check:
        installed_entry = config.get("plugins", {}).get("entries", {}).get(PLUGIN_ID)
        if config != expected_config:
            fail(f"plugin config is not compliant: {config_path}")
        if not plugin_matches(source, plugin_path):
            fail(f"plugin files are missing or differ from template: {plugin_path}")
        print(f"OK: {PLUGIN_ID} is installed for account {args.account_id} with {len(args.staff_ids)} staff IDs")
        return 0

    print(f"Plan: install {PLUGIN_ID} for account {args.account_id}")
    print(f"Group: {args.group_id}; staff count: {len(args.staff_ids)}; plugin: {plugin_path}")
    if args.dry_run:
        print("Dry run only; no files changed.")
        return 0

    if config == expected_config and plugin_matches(source, plugin_path):
        print("Already installed; no files changed.")
        return 0

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_dir = Path(args.backup_dir).expanduser().resolve() if args.backup_dir else config_path.parent / "backups" / f"{PLUGIN_ID}-{timestamp}"
    backup_paths(config_path, plugin_path, backup_dir)
    install_plugin(source, plugin_path)
    write_atomic(config_path, expected_config)
    state_file.parent.mkdir(parents=True, exist_ok=True)
    os.chmod(state_file.parent, 0o700)
    print(f"Applied. Backup: {backup_dir}")
    print("Next: run `openclaw config validate`, restart the Gateway, and verify the plugin log.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
