#!/usr/bin/env python3
"""Recover completed OpenClaw tasks that produced no outbound to their Telegram requester."""

from __future__ import annotations

import argparse
import datetime as dt
import fcntl
import json
from pathlib import Path
import re
import sqlite3
import subprocess
import sys
import time


SEND_RE = re.compile(r"telegram outbound send ok accountId=([^ ]+) chatId=(-?[0-9]+)")
SESSION_RE = re.compile(r"^agent:([^:]+):telegram:(direct|group):(.+)$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--container", required=True)
    parser.add_argument("--data-dir", required=True)
    parser.add_argument("--member-home", required=True)
    parser.add_argument("--agent-id", default="main")
    parser.add_argument("--account-id", required=True)
    parser.add_argument("--state-file", required=True)
    parser.add_argument("--grace-seconds", type=int, default=180)
    parser.add_argument("--retry-seconds", type=int, default=600)
    parser.add_argument("--max-attempts", type=int, default=2)
    parser.add_argument("--apply", action="store_true")
    return parser.parse_args()


def now_ms() -> int:
    return int(time.time() * 1000)


def iso_to_ms(value: str) -> int | None:
    try:
        return int(dt.datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp() * 1000)
    except (TypeError, ValueError):
        return None


def run(cmd: list[str], *, timeout: int = 60) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, text=True, capture_output=True, timeout=timeout, check=False)


def load_state(path: Path) -> dict:
    if not path.exists():
        raise SystemExit("State file is missing; run the installer first")
    return json.loads(path.read_text(encoding="utf-8"))


def save_state(path: Path, state: dict) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.chmod(0o600)
    tmp.replace(path)


def recent_tasks(db_path: Path, cutoff_ms: int) -> list[dict]:
    uri = f"file:{db_path}?mode=ro"
    con = sqlite3.connect(uri, uri=True, timeout=5)
    try:
        rows = con.execute(
            """
            SELECT task_id, requester_session_key, agent_id, status,
                   delivery_status, notify_policy, ended_at
            FROM task_runs
            WHERE status = 'succeeded'
              AND ended_at IS NOT NULL
              AND ended_at >= ?
            ORDER BY ended_at ASC
            """,
            (cutoff_ms,),
        ).fetchall()
    finally:
        con.close()
    return [
        {
            "taskId": row[0],
            "sessionKey": row[1],
            "agentId": row[2],
            "status": row[3],
            "deliveryStatus": row[4],
            "notifyPolicy": row[5],
            "endedAt": int(row[6]),
        }
        for row in rows
    ]


def read_gateway_log_lines(container: str) -> list[str]:
    found = run(
        ["docker", "exec", container, "find", "/tmp/openclaw", "-maxdepth", "1", "-type", "f", "-name", "openclaw-*.log", "-print"],
        timeout=20,
    )
    if found.returncode != 0:
        return []
    lines: list[str] = []
    for name in found.stdout.splitlines()[-3:]:
        result = run(["docker", "exec", container, "tail", "-c", "8388608", name], timeout=30)
        if result.returncode == 0:
            lines.extend(result.stdout.splitlines())
    return lines


def extract_outbounds(lines: list[str]) -> list[tuple[int, str, str]]:
    events: list[tuple[int, str, str]] = []
    for line in lines:
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        message = str(payload.get("message") or payload.get("1") or "")
        match = SEND_RE.search(message)
        if not match:
            continue
        timestamp = payload.get("time") or (payload.get("_meta") or {}).get("date")
        timestamp_ms = iso_to_ms(timestamp)
        if timestamp_ms is not None:
            events.append((timestamp_ms, match.group(1), match.group(2)))
    return events


def requester_target(session_key: str) -> tuple[str, str, str] | None:
    match = SESSION_RE.match(session_key or "")
    if not match:
        return None
    agent_id, kind, raw_target = match.groups()
    chat_id = raw_target.split(":", 1)[0]
    if not re.fullmatch(r"-?[0-9]+", chat_id):
        return None
    return agent_id, kind, chat_id


def has_outbound(events: list[tuple[int, str, str]], ended_at: int, account_id: str, chat_id: str) -> bool:
    return any(ts >= ended_at and account == account_id and peer == chat_id for ts, account, peer in events)


def channel_ready(args: argparse.Namespace) -> bool:
    result = run(
        [
            "docker", "exec", "-e", f"HOME={args.member_home}", args.container,
            "openclaw", "channels", "status", "--channel", "telegram", "--probe", "--json",
        ],
        timeout=45,
    )
    if result.returncode != 0:
        return False
    try:
        payload = json.loads(result.stdout)
        accounts = ((payload.get("channelAccounts") or {}).get("telegram") or [])
        return any(
            item.get("accountId") == args.account_id
            and item.get("running") is True
            and item.get("connected") is True
            and not item.get("lastError")
            for item in accounts
        )
    except json.JSONDecodeError:
        return False


def recovery_turn(args: argparse.Namespace, task: dict, chat_id: str) -> bool:
    prompt = (
        "Completion-delivery watchdog recovery for task " + task["taskId"] + ". "
        "The retained background task succeeded, but no Telegram outbound was observed after completion "
        "for its exact requester session. Inspect the exact task and child result, verify any output files, "
        "and deliver exactly one completion response with all required attachments to the current explicit "
        f"Telegram account {args.account_id} and target {chat_id}. Use the message tool when available and "
        "require a real messageId; after a successful tool send return NO_REPLY. If a matching completion "
        "was already delivered, do not duplicate it and return NO_REPLY. Do not send progress text."
    )
    result = run(
        [
            "docker", "exec", "-e", f"HOME={args.member_home}", args.container,
            "openclaw", "agent", "--agent", task.get("agentId") or args.agent_id,
            "--session-key", task["sessionKey"], "--message", prompt,
            "--deliver", "--reply-channel", "telegram", "--reply-account", args.account_id,
            "--reply-to", chat_id, "--timeout", "180", "--json",
        ],
        timeout=240,
    )
    return result.returncode == 0


def main() -> int:
    args = parse_args()
    state_path = Path(args.state_file).resolve()
    state_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = state_path.with_suffix(state_path.suffix + ".lock")
    with lock_path.open("a+", encoding="utf-8") as lock:
        try:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return 0

        state = load_state(state_path)
        cutoff_ms = int(state.get("installedAtMs") or now_ms())
        db_path = Path(args.data_dir).resolve() / ".openclaw" / "state" / "openclaw.sqlite"
        if not db_path.is_file():
            print("status=error reason=state-db-missing")
            return 1

        tasks = recent_tasks(db_path, cutoff_ms)
        events = extract_outbounds(read_gateway_log_lines(args.container))
        current = now_ms()
        records = state.setdefault("tasks", {})
        pending = 0
        recovered = 0

        for task in tasks:
            target = requester_target(task["sessionKey"])
            if target is None or task.get("notifyPolicy") == "silent":
                continue
            _, kind, chat_id = target
            record = records.setdefault(task["taskId"], {"attempts": 0})
            if has_outbound(events, task["endedAt"], args.account_id, chat_id):
                record.update({"status": "delivered", "observedAtMs": current})
                continue
            if current - task["endedAt"] < args.grace_seconds * 1000:
                record["status"] = "grace"
                continue

            pending += 1
            record["status"] = "missing-outbound"
            attempts = int(record.get("attempts") or 0)
            last_attempt = int(record.get("lastAttemptAtMs") or 0)
            can_attempt = attempts < args.max_attempts and current - last_attempt >= args.retry_seconds * 1000
            print(f"status=missing-outbound task={task['taskId'][:8]} requester=telegram-{kind} mode={'apply' if args.apply else 'dry-run'}")
            if not args.apply or not can_attempt:
                continue
            if not channel_ready(args):
                record.update({"status": "channel-not-ready", "lastAttemptAtMs": current})
                continue

            fresh_events = extract_outbounds(read_gateway_log_lines(args.container))
            if has_outbound(fresh_events, task["endedAt"], args.account_id, chat_id):
                record.update({"status": "delivered", "observedAtMs": now_ms()})
                continue

            record["attempts"] = attempts + 1
            record["lastAttemptAtMs"] = now_ms()
            ok = recovery_turn(args, task, chat_id)
            record["lastRecoveryCommandOk"] = ok
            time.sleep(3)
            final_events = extract_outbounds(read_gateway_log_lines(args.container))
            if has_outbound(final_events, task["endedAt"], args.account_id, chat_id):
                record.update({"status": "recovered", "observedAtMs": now_ms()})
                recovered += 1
            else:
                record["status"] = "recovery-unverified"

        state["lastCheckAtMs"] = now_ms()
        save_state(state_path, state)
        print(f"status=ok tasks={len(tasks)} pending={pending} recovered={recovered}")
        return 0


if __name__ == "__main__":
    sys.exit(main())
