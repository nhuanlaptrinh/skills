#!/usr/bin/env python3
"""Guard Telegram offsets before an OpenClaw Gateway starts polling."""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import shutil
import sqlite3
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit


PLUGIN_ID = "telegram"
OFFSET_NAMESPACE = "telegram.update-offsets"
DEFAULT_API_ROOT = "https://api.telegram.org"
STATE_VERSION = 1


class GuardError(RuntimeError):
    pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Repair proven Telegram offset regressions before Gateway startup"
    )
    parser.add_argument("--config", type=Path, default=Path("/root/.openclaw/openclaw.json"))
    parser.add_argument(
        "--state-db", type=Path, default=Path("/root/.openclaw/state/openclaw.sqlite")
    )
    parser.add_argument(
        "--state-file",
        type=Path,
        default=Path("/root/.openclaw/state/telegram-offset-guard.json"),
    )
    parser.add_argument("--backup-dir", type=Path, default=Path("/root/_Backups"))
    parser.add_argument("--gateway-unit", default="openclaw-gateway.service")
    parser.add_argument(
        "--lock-file",
        type=Path,
        default=Path("/run/lock/openclaw-telegram-offset-guard.lock"),
    )
    parser.add_argument("--account-id", action="append", default=[])
    parser.add_argument("--apply", action="store_true")
    return parser.parse_args()


def safe_api_root(value: str | None) -> str:
    raw = (value or DEFAULT_API_ROOT).strip() or DEFAULT_API_ROOT
    parsed = urlsplit(raw)
    if not parsed.scheme or not parsed.hostname:
        raise GuardError("invalid Telegram apiRoot")
    host = parsed.hostname
    if ":" in host and not host.startswith("["):
        host = f"[{host}]"
    port = f":{parsed.port}" if parsed.port else ""
    path = parsed.path.rstrip("/")
    return f"{parsed.scheme.lower()}://{host.lower()}{port}{path}"


def bot_id_from_token(token: str) -> str | None:
    prefix = token.split(":", 1)[0]
    return prefix if prefix.isdigit() else None


def load_accounts(config_path: Path, selected: set[str]) -> dict[str, dict[str, Any]]:
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise GuardError(f"cannot read config: {type(exc).__name__}") from None
    telegram = config.get("channels", {}).get("telegram", {})
    accounts = telegram.get("accounts", {})
    if not isinstance(accounts, dict):
        raise GuardError("Telegram accounts config is invalid")
    default_api_root = telegram.get("apiRoot")
    result: dict[str, dict[str, Any]] = {}
    for account_id, account in accounts.items():
        if selected and account_id not in selected:
            continue
        if not isinstance(account, dict) or account.get("enabled") is False:
            continue
        token = account.get("botToken")
        if not isinstance(token, str) or not token.strip():
            continue
        result[account_id] = {
            "api_root": safe_api_root(account.get("apiRoot") or default_api_root),
            "bot_id": bot_id_from_token(token.strip()),
        }
    missing = selected.difference(result)
    if missing:
        raise GuardError(f"configured Telegram account not found: {sorted(missing)[0]}")
    return result


def load_guard_state(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"version": STATE_VERSION, "accounts": {}}
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"version": STATE_VERSION, "accounts": {}}
    if not isinstance(state, dict) or not isinstance(state.get("accounts"), dict):
        return {"version": STATE_VERSION, "accounts": {}}
    return state


def gateway_is_active(unit: str) -> bool:
    result = subprocess.run(
        ["systemctl", "--user", "is-active", "--quiet", unit],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return result.returncode == 0


def read_offset(con: sqlite3.Connection, account_id: str) -> int | None:
    row = con.execute(
        "SELECT value_json FROM plugin_state_entries "
        "WHERE plugin_id=? AND namespace=? AND entry_key=?",
        (PLUGIN_ID, OFFSET_NAMESPACE, account_id),
    ).fetchone()
    if row is None:
        return None
    try:
        value = json.loads(row[0])
    except (TypeError, json.JSONDecodeError):
        return None
    offset = value.get("lastUpdateId") if isinstance(value, dict) else None
    return offset if isinstance(offset, int) and offset >= 0 else None


def read_ingress_metadata(
    con: sqlite3.Connection, account_id: str, stored_offset: int | None
) -> dict[str, int | None]:
    latest = con.execute(
        "SELECT event_id, received_at FROM channel_ingress_events "
        "WHERE channel_id='telegram' AND account_id=? "
        "ORDER BY received_at DESC LIMIT 1",
        (account_id,),
    ).fetchone()
    latest_id: int | None = None
    latest_received_at: int | None = None
    if latest is not None:
        try:
            latest_id = int(latest[0])
        except (TypeError, ValueError):
            latest_id = None
        latest_received_at = latest[1] if isinstance(latest[1], int) else None
    stored_received_at: int | None = None
    if stored_offset is not None:
        stored = con.execute(
            "SELECT received_at FROM channel_ingress_events "
            "WHERE channel_id='telegram' AND account_id=? "
            "AND CAST(event_id AS INTEGER)=? ORDER BY received_at DESC LIMIT 1",
            (account_id, stored_offset),
        ).fetchone()
        if stored is not None and isinstance(stored[0], int):
            stored_received_at = stored[0]
    return {
        "latest_update_id": latest_id,
        "latest_received_at": latest_received_at,
        "stored_received_at": stored_received_at,
    }


def inspect_account(
    con: sqlite3.Connection,
    account_id: str,
    current: dict[str, Any],
    previous: dict[str, Any] | None,
) -> dict[str, Any]:
    stored_offset = read_offset(con, account_id)
    ingress = read_ingress_metadata(con, account_id, stored_offset)
    api_root_changed = bool(
        previous
        and previous.get("api_root")
        and previous.get("api_root") != current["api_root"]
    )
    bot_id_changed = bool(
        previous
        and previous.get("bot_id")
        and current.get("bot_id")
        and previous.get("bot_id") != current.get("bot_id")
    )
    latest_id = ingress["latest_update_id"]
    latest_at = ingress["latest_received_at"]
    stored_at = ingress["stored_received_at"]
    sequence_regression = bool(
        stored_offset is not None
        and latest_id is not None
        and stored_offset > latest_id
        and stored_at is not None
        and latest_at is not None
        and latest_at > stored_at
    )
    reasons = [
        reason
        for reason, matched in (
            ("api-root-changed", api_root_changed),
            ("bot-id-changed", bot_id_changed),
            ("newer-lower-update-id", sequence_regression),
        )
        if matched
    ]
    return {
        "account_id": account_id,
        "stored_offset": stored_offset,
        "latest_update_id": latest_id,
        "api_root": current["api_root"],
        "repair_required": bool(stored_offset is not None and reasons),
        "reasons": reasons,
    }


def backup_state(db_path: Path, backup_root: Path) -> Path:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    target = backup_root / f"telegram-offset-guard-{timestamp}"
    target.mkdir(mode=0o700, parents=True, exist_ok=False)
    for source in (db_path, Path(f"{db_path}-wal"), Path(f"{db_path}-shm")):
        if source.is_file():
            destination = target / source.name
            shutil.copy2(source, destination)
            destination.chmod(0o600)
    return target


def write_guard_state(path: Path, accounts: dict[str, dict[str, Any]]) -> None:
    payload = {
        "version": STATE_VERSION,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "accounts": accounts,
    }
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
    temporary.chmod(0o600)
    os.replace(temporary, path)


def run(args: argparse.Namespace) -> dict[str, Any]:
    selected = set(args.account_id)
    accounts = load_accounts(args.config, selected)
    previous_state = load_guard_state(args.state_file)
    previous_accounts = previous_state.get("accounts", {})
    if args.apply and gateway_is_active(args.gateway_unit):
        raise GuardError(f"Gateway unit {args.gateway_unit} is active; refusing apply")
    if not args.state_db.is_file():
        raise GuardError(f"state database not found: {args.state_db}")

    con = sqlite3.connect(args.state_db, timeout=5)
    try:
        inspections = [
            inspect_account(
                con,
                account_id,
                current,
                previous_accounts.get(account_id)
                if isinstance(previous_accounts.get(account_id), dict)
                else None,
            )
            for account_id, current in sorted(accounts.items())
        ]
    finally:
        con.close()

    repairs = [item for item in inspections if item["repair_required"]]
    backup_dir: Path | None = None
    repaired_accounts: list[str] = []
    if args.apply and repairs:
        backup_dir = backup_state(args.state_db, args.backup_dir)
        con = sqlite3.connect(args.state_db, timeout=5)
        try:
            con.execute("BEGIN IMMEDIATE")
            for item in repairs:
                actual = read_offset(con, item["account_id"])
                if actual != item["stored_offset"]:
                    raise GuardError(
                        f"offset changed before repair for account {item['account_id']}"
                    )
                deleted = con.execute(
                    "DELETE FROM plugin_state_entries "
                    "WHERE plugin_id=? AND namespace=? AND entry_key=?",
                    (PLUGIN_ID, OFFSET_NAMESPACE, item["account_id"]),
                ).rowcount
                if deleted != 1:
                    raise GuardError(
                        f"expected one offset row for account {item['account_id']}"
                    )
                repaired_accounts.append(item["account_id"])
            con.commit()
        except Exception:
            con.rollback()
            raise
        finally:
            con.close()

    if args.apply:
        next_accounts = dict(previous_accounts)
        next_accounts.update(accounts)
        write_guard_state(args.state_file, next_accounts)
    return {
        "action": "applied" if args.apply else "dry-run",
        "account_count": len(accounts),
        "repair_count": len(repaired_accounts),
        "repaired_accounts": repaired_accounts,
        "backup_dir": str(backup_dir) if backup_dir else None,
        "accounts": inspections,
    }


def main() -> int:
    args = parse_args()
    args.lock_file.parent.mkdir(parents=True, exist_ok=True)
    with args.lock_file.open("a+", encoding="utf-8") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        print(json.dumps(run(args), sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except GuardError as exc:
        print(f"error={exc}", file=os.sys.stderr)
        raise SystemExit(2)
