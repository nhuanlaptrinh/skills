#!/usr/bin/env python3
"""Safely inspect or remove one OpenClaw Telegram polling offset."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen


NAMESPACE = "telegram.update-offsets"
PLUGIN_ID = "telegram"
DEFAULT_API_ROOT = "https://api.telegram.org"


class RepairError(RuntimeError):
    pass


def default_home() -> Path:
    return Path(os.environ.get("HOME", str(Path.home())))


def parse_args() -> argparse.Namespace:
    home = default_home()
    parser = argparse.ArgumentParser(
        description="Inspect or safely reset one OpenClaw Telegram update offset"
    )
    parser.add_argument("--account-id", required=True)
    parser.add_argument(
        "--config",
        type=Path,
        default=home / ".openclaw/openclaw.json",
    )
    parser.add_argument(
        "--state-db",
        type=Path,
        default=home / ".openclaw/state/openclaw.sqlite",
    )
    parser.add_argument(
        "--api-root",
        default=DEFAULT_API_ROOT,
        help="Bot API root used for --cloud-check",
    )
    parser.add_argument(
        "--gateway-unit",
        default="openclaw-gateway.service",
        help="systemd user unit that owns polling",
    )
    parser.add_argument("--cloud-check", action="store_true")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument(
        "--expected-offset",
        type=int,
        help="Refuse apply if the stored offset differs from this value",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Allow apply when Cloud API cannot prove a mismatch",
    )
    parser.add_argument(
        "--backup-dir",
        type=Path,
        default=home / "_Backups",
    )
    return parser.parse_args()


def load_account(config_path: Path, account_id: str) -> tuple[dict[str, Any], str]:
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RepairError(f"cannot read config: {type(exc).__name__}") from None
    accounts = config.get("channels", {}).get("telegram", {}).get("accounts", {})
    account = accounts.get(account_id)
    if not isinstance(account, dict):
        raise RepairError(f"telegram account not found: {account_id}")
    token = account.get("botToken")
    if not isinstance(token, str) or not token.strip():
        raise RepairError("account botToken is missing or not a plain string")
    return account, token.strip()


def safe_api_root(value: str) -> str:
    parsed = urlsplit(value)
    if not parsed.scheme or not parsed.netloc:
        return "invalid"
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path.rstrip('/')}"


def bot_id_from_token(token: str) -> str | None:
    raw = token.split(":", 1)[0]
    return raw if raw.isdigit() else None


def gateway_is_active(unit: str) -> bool | None:
    if shutil.which("systemctl") is None:
        return None
    result = subprocess.run(
        ["systemctl", "--user", "is-active", "--quiet", unit],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return result.returncode == 0


def read_offset(db_path: Path, account_id: str) -> tuple[dict[str, Any] | None, bool]:
    if not db_path.is_file():
        raise RepairError(f"state database not found: {db_path}")
    try:
        con = sqlite3.connect(db_path, timeout=5)
        row = con.execute(
            "SELECT value_json FROM plugin_state_entries "
            "WHERE plugin_id=? AND namespace=? AND entry_key=?",
            (PLUGIN_ID, NAMESPACE, account_id),
        ).fetchone()
    except sqlite3.Error as exc:
        raise RepairError(f"cannot read state database: {type(exc).__name__}") from None
    finally:
        try:
            con.close()
        except UnboundLocalError:
            pass
    if row is None:
        return None, False
    try:
        state = json.loads(row[0])
    except (TypeError, json.JSONDecodeError):
        return None, True
    if not isinstance(state, dict):
        return None, True
    return state, False


def bot_api_call(token: str, api_root: str, method: str, params: dict[str, Any]) -> dict[str, Any]:
    query = urlencode(params)
    url = f"{api_root.rstrip('/')}/bot{token}/{method}"
    if query:
        url = f"{url}?{query}"
    request = Request(url, headers={"Accept": "application/json"})
    try:
        with urlopen(request, timeout=12) as response:
            payload = json.loads(response.read())
    except HTTPError as exc:
        raise RepairError(f"Cloud API HTTP error: {exc.code}") from None
    except (URLError, TimeoutError, OSError, json.JSONDecodeError):
        raise RepairError("Cloud API request failed") from None
    if not isinstance(payload, dict):
        raise RepairError("Cloud API returned an invalid response")
    return payload


def cloud_summary(token: str, api_root: str) -> dict[str, Any]:
    me = bot_api_call(token, api_root, "getMe", {})
    updates_payload = bot_api_call(
        token,
        api_root,
        "getUpdates",
        {"offset": 0, "limit": 100, "timeout": 0},
    )
    updates = updates_payload.get("result")
    if not isinstance(updates, list):
        updates = []
    update_ids = sorted(
        update["update_id"]
        for update in updates
        if isinstance(update, dict)
        and isinstance(update.get("update_id"), int)
        and update["update_id"] >= 0
    )
    bot_info = me.get("result") if isinstance(me.get("result"), dict) else {}
    return {
        "api_ok": me.get("ok") is True and updates_payload.get("ok") is True,
        "bot_id": bot_info.get("id"),
        "bot_username": bot_info.get("username"),
        "update_count": len(update_ids),
        "min_update_id": update_ids[0] if update_ids else None,
        "max_update_id": update_ids[-1] if update_ids else None,
    }


def backup_state(db_path: Path, backup_root: Path, account_id: str) -> Path:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    target = backup_root / f"telegram-offset-{account_id}-{timestamp}"
    target.mkdir(mode=0o700, parents=True, exist_ok=False)
    for source in (
        db_path,
        Path(f"{db_path}-wal"),
        Path(f"{db_path}-shm"),
    ):
        if source.is_file():
            destination = target / source.name
            shutil.copy2(source, destination)
            destination.chmod(0o600)
    return target


def delete_offset(
    db_path: Path,
    account_id: str,
    expected_offset: int,
) -> int:
    con = sqlite3.connect(db_path, timeout=5)
    try:
        con.execute("BEGIN IMMEDIATE")
        row = con.execute(
            "SELECT value_json FROM plugin_state_entries "
            "WHERE plugin_id=? AND namespace=? AND entry_key=?",
            (PLUGIN_ID, NAMESPACE, account_id),
        ).fetchone()
        if row is None:
            raise RepairError("target offset row disappeared before apply")
        try:
            state = json.loads(row[0])
        except (TypeError, json.JSONDecodeError):
            raise RepairError("target offset row is invalid") from None
        actual = state.get("lastUpdateId") if isinstance(state, dict) else None
        if actual != expected_offset:
            raise RepairError(
                f"offset changed before apply: expected {expected_offset}, found {actual}"
            )
        deleted = con.execute(
            "DELETE FROM plugin_state_entries "
            "WHERE plugin_id=? AND namespace=? AND entry_key=?",
            (PLUGIN_ID, NAMESPACE, account_id),
        ).rowcount
        if deleted != 1:
            raise RepairError(f"expected one deleted row, got {deleted}")
        con.commit()
        try:
            con.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        except sqlite3.Error:
            pass
        return deleted
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


def main() -> int:
    args = parse_args()
    if args.apply and args.expected_offset is None:
        raise RepairError("--apply requires --expected-offset")
    if args.force and not args.apply:
        raise RepairError("--force requires --apply")
    if args.apply and not args.cloud_check and not args.force:
        raise RepairError("--apply requires --cloud-check or explicit --force")

    account, token = load_account(args.config.expanduser(), args.account_id)
    active = gateway_is_active(args.gateway_unit)
    if active is True and (args.cloud_check or args.apply):
        raise RepairError(
            f"Gateway unit {args.gateway_unit} is active; stop it before direct polling/state work"
        )
    if args.apply and active is None:
        raise RepairError("cannot verify Gateway state; refusing apply")

    state, invalid_state = read_offset(args.state_db.expanduser(), args.account_id)
    stored_offset = state.get("lastUpdateId") if isinstance(state, dict) else None
    api_result: dict[str, Any] | None = None
    if args.cloud_check:
        api_result = cloud_summary(token, args.api_root)

    max_cloud_id = api_result.get("max_update_id") if api_result else None
    mismatch = (
        isinstance(stored_offset, int)
        and isinstance(max_cloud_id, int)
        and stored_offset > max_cloud_id
    )
    summary: dict[str, Any] = {
        "account_id": args.account_id,
        "state_db": str(args.state_db.expanduser()),
        "gateway_active": active,
        "configured_api_root": safe_api_root(str(account.get("apiRoot", "")))
        if account.get("apiRoot")
        else None,
        "checked_api_root": safe_api_root(args.api_root) if args.cloud_check else None,
        "bot_id_from_config": bot_id_from_token(token),
        "stored_offset": stored_offset,
        "invalid_state": invalid_state,
        "offset_mismatch": mismatch,
        "action": "dry-run",
    }
    if api_result:
        summary["cloud"] = api_result

    if args.apply:
        if invalid_state or not isinstance(stored_offset, int):
            raise RepairError("cannot apply: target offset is missing or invalid")
        if stored_offset != args.expected_offset:
            raise RepairError(
                f"stored offset {stored_offset} does not match --expected-offset {args.expected_offset}"
            )
        if not mismatch and not args.force:
            raise RepairError(
                "Cloud API did not prove a high/stale offset; use --force only with independent evidence"
            )
        backup = backup_state(
            args.state_db.expanduser(), args.backup_dir.expanduser(), args.account_id
        )
        deleted = delete_offset(
            args.state_db.expanduser(), args.account_id, args.expected_offset
        )
        summary["action"] = "deleted-offset"
        summary["deleted_rows"] = deleted
        summary["backup_dir"] = str(backup)
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RepairError as exc:
        print(f"error={exc}", file=sys.stderr)
        raise SystemExit(2)
