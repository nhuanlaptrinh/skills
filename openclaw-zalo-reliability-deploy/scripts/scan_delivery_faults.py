#!/usr/bin/env python3
"""Scan bounded OpenClaw logs without emitting IDs, text, or message content."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
from collections import Counter
from datetime import datetime, timezone

PATTERNS = (
    ("upload_timeout", re.compile(r"(?:upload|file_done|attachment).*(?:timeout|timed out|failed|failure|error|missing|stalled|pending)|(?:timeout|timed out|failed|failure|error|missing|stalled|pending).*(?:upload|file_done|attachment)", re.I)),
    ("stalled_session", re.compile(r"blocked_tool_call|stalled session|finalization_stalled|reply_operation_aborted|claim.*adoption stalled", re.I)),
    ("outbound_error", re.compile(r"OutboundDeliveryError|send_attempt_started|unknown_after_send", re.I)),
)


def line_epoch(line: str) -> float | None:
    try:
        obj = json.loads(line)
    except Exception:
        obj = None
    candidates = []
    if isinstance(obj, dict):
        candidates += [obj.get("time"), obj.get("timestamp")]
        meta = obj.get("_meta")
        if isinstance(meta, dict):
            candidates += [meta.get("date")]
    candidates += re.findall(r"\b20\d\d-\d\d-\d\d[T ][^\s\"]+", line)
    for value in candidates:
        if not value:
            continue
        text = str(value).replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(text).astimezone(timezone.utc).timestamp()
        except ValueError:
            continue
    return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("logfile")
    parser.add_argument("--window", type=int, default=300)
    args = parser.parse_args()
    now = time.time()
    categories: Counter[str] = Counter()
    latest = 0.0
    try:
        lines = open(args.logfile, encoding="utf-8", errors="replace")
    except OSError as exc:
        print(json.dumps({"error": type(exc).__name__, "count": 0}))
        return 0
    with lines:
        for line in lines:
            epoch = line_epoch(line)
            if epoch is not None and now - epoch > args.window:
                continue
            for category, pattern in PATTERNS:
                if pattern.search(line):
                    categories[category] += 1
                    latest = max(latest, epoch or now)
                    break
    raw = ",".join(f"{key}:{categories[key]}" for key in sorted(categories))
    digest = hashlib.sha256(raw.encode()).hexdigest()[:16] if raw else ""
    print(json.dumps({"count": sum(categories.values()), "categories": dict(categories), "latest_epoch": int(latest), "fingerprint": digest}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
