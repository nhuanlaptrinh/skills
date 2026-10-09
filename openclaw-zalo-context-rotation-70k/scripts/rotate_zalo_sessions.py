#!/usr/bin/env python3
"""Reset idle Zalo sessions after a bounded token threshold."""

import argparse
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shlex
import subprocess
import time


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--container", required=True)
    parser.add_argument("--member-home", required=True)
    parser.add_argument("--agent", default="main")
    parser.add_argument("--key-prefix")
    parser.add_argument("--threshold", type=int, default=70000)
    parser.add_argument("--active-window-seconds", type=int, default=180)
    parser.add_argument("--state-dir", type=Path, default=Path("/root/Automation/watchdog/shared_self_healing/state"))
    parser.add_argument("--max-resets-per-run", type=int, default=1)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if not re.fullmatch(r"[a-zA-Z0-9_-]+", args.agent):
        parser.error("invalid agent")
    if args.key_prefix is None:
        args.key_prefix = f"agent:{args.agent}:zalouser:"
    if not re.fullmatch(r"[a-zA-Z0-9_-]+", args.container):
        parser.error("invalid container")
    if args.key_prefix != f"agent:{args.agent}:zalouser:":
        parser.error("only this agent's Zalo prefix is allowed")
    if args.threshold <= 0 or args.active_window_seconds < 180 or args.max_resets_per_run < 1:
        parser.error("positive threshold, idle >= 180 seconds and positive reset limit required")
    if not args.state_dir.is_absolute() or not Path(args.member_home).is_absolute():
        parser.error("HOME and state directory must be absolute")
    return args


def run_rpc(args, method, params):
    command = [
        "docker", "exec", "-e", f"HOME={args.member_home}", args.container,
        "sh", "-lc",
        'if [ -f "$HOME/.openclaw/gateway.env" ]; then set -a; . "$HOME/.openclaw/gateway.env"; set +a; fi; '
        "openclaw gateway call " + shlex.quote(method) + " --json --params " + shlex.quote(
            json.dumps(params, separators=(",", ":"))
        ) + " --timeout 30000",
    ]
    result = subprocess.run(command, capture_output=True, text=True, timeout=45)
    if result.returncode:
        raise RuntimeError("Gateway RPC failed")
    try:
        response = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError("Gateway RPC returned invalid JSON") from exc
    if not isinstance(response, dict) or response.get("ok") is False:
        raise RuntimeError("Gateway RPC returned an error")
    return response


def list_sessions(args):
    response = run_rpc(args, "sessions.list", {"agentId": args.agent, "limit": 1000})
    sessions = response.get("sessions")
    if not isinstance(sessions, list) or response.get("hasMore"):
        raise RuntimeError("Gateway session listing is incomplete")
    return [session for session in sessions if isinstance(session, dict)]


def label(key):
    digest = hashlib.sha256(key.encode()).hexdigest()[:10]
    parts = key.split(":")
    return ":".join(parts[:3]) + "#" + digest


def numeric(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)) and math.isfinite(value):
        return int(value)
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return None


def active(session):
    return session.get("hasActiveRun") is True or bool(session.get("activeRunIds")) or str(session.get("status", "")).lower() in {"queued", "running", "processing", "starting", "waiting"}


def candidate(session, args, now_ms):
    key = session.get("key")
    tokens = numeric(session.get("totalTokens"))
    if not isinstance(key, str) or not key.startswith(args.key_prefix) or tokens is None or tokens < args.threshold:
        return False
    if active(session) or session.get("hasActiveRun") is not False or session.get("activeRunIds") != []:
        return False
    if session.get("totalTokensFresh") is not True or session.get("archived") is True or session.get("incognito") is True:
        return False
    if not session.get("sessionId") or str(session.get("status", "")).lower() not in {"done", "completed", "succeeded", "failed", "aborted", "cancelled", "idle"}:
        return False
    timestamps = [numeric(session.get(field)) for field in ("updatedAt", "lastActivityAt", "lastInteractionAt")]
    updated = max((value for value in timestamps if value is not None), default=None)
    return updated is not None and (now_ms - updated) // 1000 >= args.active_window_seconds


def rotate(args):
    sessions = list_sessions(args)
    now_ms = int(time.time() * 1000)
    candidates = [session for session in sessions if candidate(session, args, now_ms)]
    print(f"scan member={args.container} prefix={args.key_prefix} threshold={args.threshold} sessions={len(sessions)} candidates={len(candidates)} dry_run={str(args.dry_run).lower()}")
    reset_count = 0
    seen = set()
    for session in candidates:
        if session["sessionId"] in seen:
            continue
        seen.add(session["sessionId"])
        key = session["key"]
        if args.dry_run:
            print(f"would_reset session={label(key)} tokens={numeric(session.get('totalTokens'))}")
            continue
        if reset_count >= args.max_resets_per_run:
            break
        current = next((item for item in list_sessions(args) if item.get("key") == key), None)
        if current is None or current.get("sessionId") != session["sessionId"] or not candidate(current, args, int(time.time() * 1000)):
            print(f"skip=recheck session={label(key)}")
            continue
        response = run_rpc(args, "sessions.reset", {"key": key, "agentId": args.agent, "expectedSessionId": current["sessionId"]})
        entry = response.get("entry")
        if response.get("ok") is not True or not isinstance(entry, dict) or not entry.get("sessionId") or entry["sessionId"] == current["sessionId"]:
            raise RuntimeError("Gateway reset receipt did not confirm a new session")
        reset_count += 1
        print(f"reset_ok session={label(key)} tokens={numeric(current.get('totalTokens'))}")
    print(f"summary reset={reset_count} candidates={len(candidates)}")
    return 0


def main():
    args = parse_args()
    if args.dry_run:
        return rotate(args)
    os.umask(0o077)
    scope = f"{args.container}:{args.agent}:{args.key_prefix}"
    digest = hashlib.sha256(scope.encode()).hexdigest()[:20]
    args.state_dir.mkdir(parents=True, exist_ok=True)
    with (args.state_dir / f"zalo_rotation_{digest}.lock").open("a") as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print("rotation_skipped reason=lock_busy")
            return 0
        return rotate(args)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, subprocess.TimeoutExpired, OSError):
        print("rotation_failed reason=rpc_or_receipt_error")
        raise SystemExit(1)
