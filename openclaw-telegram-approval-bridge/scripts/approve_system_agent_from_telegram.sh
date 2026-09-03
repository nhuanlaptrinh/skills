#!/usr/bin/env python3
"""Validate and resolve one delegated OpenClaw system-agent approval."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path


def fail(message: str, code: int) -> "NoReturn":
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(code)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate and resolve one delegated OpenClaw system-agent approval."
    )
    parser.add_argument("--openclaw-root", default=os.environ.get("OPENCLAW_ROOT", ""))
    parser.add_argument("--telegram-id", required=True)
    parser.add_argument("--approval-id", required=True)
    parser.add_argument("--agent-id", default="main")
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--check", action="store_true")
    action.add_argument("--apply", action="store_true")
    return parser.parse_args()


def read_json(path: Path) -> dict:
    if path.is_symlink() or not path.is_file() or not os.access(path, os.R_OK):
        fail("OpenClaw config is not readable", 2)
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        fail("OpenClaw config is invalid", 2)
    if not isinstance(value, dict):
        fail("OpenClaw config root is not an object", 2)
    return value


def run_openclaw(args: list[str], config_path: Path, code: int) -> str:
    environment = os.environ.copy()
    environment["OPENCLAW_CONFIG_PATH"] = str(config_path)
    try:
        result = subprocess.run(
            ["openclaw", *args],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=environment,
        )
    except OSError:
        fail("openclaw command is unavailable", code)
    if result.returncode != 0:
        fail("openclaw command failed", code)
    return result.stdout


def parse_command_json(output: str, code: int) -> dict:
    try:
        value = json.loads(output)
    except json.JSONDecodeError:
        fail("OpenClaw returned unreadable JSON", code)
    if not isinstance(value, dict):
        fail("OpenClaw returned an unexpected JSON shape", code)
    return value


def pending_record(output: str, approval_id: str, code: int) -> dict:
    pending = parse_command_json(output, code)
    approvals = pending.get("approvals")
    if not isinstance(approvals, list):
        fail("approval queue is unreadable", code)
    matches = [item for item in approvals if isinstance(item, dict) and item.get("id") == approval_id]
    if len(matches) != 1:
        fail("approval is not uniquely pending", code)
    return matches[0]


def source_from_session(session_key: str, agent_id: str) -> tuple[str, str, str] | None:
    prefix = re.escape(agent_id)
    patterns = (
        (rf"^agent:{prefix}:telegram:direct:(\d+)$", "telegram", "direct"),
        (rf"^agent:{prefix}:telegram:[^:]+:direct:(\d+)$", "telegram", "direct"),
        (rf"^agent:{prefix}:zalouser:direct:(\d+)$", "zalouser", "direct"),
        (rf"^agent:{prefix}:zalouser:[^:]+:direct:(\d+)$", "zalouser", "direct"),
        (rf"^agent:{prefix}:zalouser:group:(\d+)$", "zalouser", "group"),
        (rf"^agent:{prefix}:zalouser:[^:]+:group:(\d+)$", "zalouser", "group"),
    )
    for pattern, channel, kind in patterns:
        match = re.fullmatch(pattern, session_key)
        if match:
            return channel, kind, match.group(1)
    return None


def verify_record(config: dict, record: dict, telegram_id: str, agent_id: str) -> None:
    if record.get("kind") != "system-agent" or record.get("agentId") != agent_id:
        fail("approval is not a system-agent proposal for the configured agent", 5)

    source = source_from_session(str(record.get("sessionKey", "")), agent_id)
    if source is None:
        fail("proposal does not belong to an approved direct chat session", 5)
    source_channel, source_kind, source_sender = source
    owner_values = config.get("commands", {}).get("ownerAllowFrom", [])
    owner_values = owner_values if isinstance(owner_values, list) else []
    owner_values = {str(value) for value in owner_values}
    if source_kind == "direct":
        if f"{source_channel}:{source_sender}" not in owner_values:
            fail("proposal source is not a configured command owner", 5)
    else:
        groups = config.get("channels", {}).get("zalouser", {}).get("groups", {})
        group = groups.get(source_sender) if isinstance(groups, dict) else None
        if not isinstance(group, dict) or group.get("enabled") is not True:
            fail("proposal source group is not explicitly enabled", 5)

    summary = str(record.get("summary", ""))
    if not summary.startswith("OpenClaw change:"):
        fail("proposal summary is not a persistent OpenClaw change", 5)
    expires_at = record.get("expiresAtMs", 0)
    try:
        expires_at = int(expires_at)
    except (TypeError, ValueError):
        expires_at = 0
    if expires_at <= int(time.time() * 1000):
        fail("proposal has expired", 5)

    command_owners = {str(value) for value in owner_values}
    if f"telegram:{telegram_id}" not in command_owners:
        fail("Telegram sender is not a configured command owner", 3)


def main() -> int:
    args = parse_args()
    if not args.openclaw_root or not args.openclaw_root.startswith("/"):
        fail("invalid OpenClaw root", 2)
    if not args.telegram_id.isdigit() or not args.agent_id:
        fail("invalid Telegram ID or agent ID", 2)
    if not args.approval_id.startswith("system-agent:"):
        fail("approval ID must start with system-agent:", 2)

    root = Path(args.openclaw_root)
    config_path = Path(os.environ.get("OPENCLAW_CONFIG_PATH", str(root / "openclaw.json")))
    config = read_json(config_path)
    command_owners = config.get("commands", {}).get("ownerAllowFrom", [])
    command_owners = command_owners if isinstance(command_owners, list) else []
    if f"telegram:{args.telegram_id}" not in {str(value) for value in command_owners}:
        fail("Telegram sender is not a configured command owner", 3)

    record = pending_record(
        run_openclaw(["approvals", "pending", "--json"], config_path, 4),
        args.approval_id,
        4,
    )
    verify_record(config, record, args.telegram_id, args.agent_id)

    print("status=pending")
    print("kind=system-agent")
    print(f"agent_id={args.agent_id}")
    print("summary_verified=true")
    if args.check:
        return 0

    result = parse_command_json(
        run_openclaw(
            [
                "approvals",
                "resolve",
                args.approval_id,
                "allow-once",
                "--json",
                "--reason",
                "Explicit approval from configured Telegram owner",
            ],
            config_path,
            6,
        ),
        6,
    )
    approval = result.get("approval")
    if not (
        result.get("applied") is True
        or (result.get("alreadyResolved") is True and isinstance(approval, dict) and approval.get("status") == "allowed")
    ):
        fail("OpenClaw did not confirm approval", 6)

    remaining = parse_command_json(
        run_openclaw(["approvals", "pending", "--json"], config_path, 7),
        7,
    )
    approvals = remaining.get("approvals")
    if isinstance(approvals, list) and any(
        isinstance(item, dict) and item.get("id") == args.approval_id for item in approvals
    ):
        fail("approval is still pending after resolution", 7)
    run_openclaw(["config", "validate"], config_path, 6)
    print("status=allowed")
    print("decision=allow-once")
    return 0


if __name__ == "__main__":
    main()
