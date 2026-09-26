#!/usr/bin/env python3
"""Detect a recent in-flight OpenClaw turn or attachment delivery.

Exit status 0 means a recent activity marker was found; status 1 means the
bounded grace window is clear. The output contains only a category and age.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import datetime, timezone

PATTERNS = (
    ("attachment", re.compile(r"send_attempt_started|upload|file_done|attachment", re.I)),
    ("active_turn", re.compile(r"tool_execution_started|pendingReplies|embeddedRuns|sessionAdmissions", re.I)),
)


def line_epoch(line: str) -> float | None:
    try:
        obj = json.loads(line)
    except Exception:
        obj = None
    values = []
    if isinstance(obj, dict):
        values += [obj.get("time"), obj.get("timestamp")]
        meta = obj.get("_meta")
        if isinstance(meta, dict):
            values.append(meta.get("date"))
    values += re.findall(r"\b20\d\d-\d\d-\d\d[T ][^\s\"]+", line)
    for value in values:
        if not value:
            continue
        try:
            return datetime.fromisoformat(str(value).replace("Z", "+00:00")).astimezone(timezone.utc).timestamp()
        except ValueError:
            pass
    return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("logfile")
    parser.add_argument("--window", type=int, default=120)
    args = parser.parse_args()
    now = time.time()
    latest: tuple[str, float] | None = None
    try:
        handle = open(args.logfile, encoding="utf-8", errors="replace")
    except OSError:
        print(json.dumps({"active": False, "reason": "log_unavailable"}))
        return 1
    with handle:
        for line in handle:
            epoch = line_epoch(line)
            if epoch is None or now - epoch < 0 or now - epoch > args.window:
                continue
            for category, pattern in PATTERNS:
                if pattern.search(line):
                    if latest is None or epoch > latest[1]:
                        latest = (category, epoch)
                    break
    if latest is None:
        print(json.dumps({"active": False, "windowSeconds": args.window}))
        return 1
    print(json.dumps({"active": True, "category": latest[0],
                      "ageSeconds": round(now - latest[1]),
                      "windowSeconds": args.window}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
