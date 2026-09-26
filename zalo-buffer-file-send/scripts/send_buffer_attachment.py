#!/usr/bin/env python3
"""Send one Zalo attachment through the member's existing OpenClaw Gateway."""
import argparse
import base64
import json
import mimetypes
import pathlib
import hashlib
import os
import time
import urllib.error
import urllib.request

parser = argparse.ArgumentParser(description="Send a Zalo file with an explicit in-memory buffer")
parser.add_argument("--config", default="/home/anhlaptrinh/.openclaw/openclaw.json")
parser.add_argument("--target", required=True, help="user:<id> or group:<id>")
parser.add_argument("--file", required=True)
parser.add_argument("--message", default="")
parser.add_argument("--dry-run", action="store_true")
parser.add_argument("--force-retry", action="store_true", help="retry a prior unknown result after receipt reconciliation")
args = parser.parse_args()

file_path = pathlib.Path(args.file).resolve()
if not file_path.is_file() or not file_path.stat().st_size:
    raise SystemExit("file missing or empty")
if not (args.target.startswith("user:") or args.target.startswith("group:")):
    raise SystemExit("target must be user:<id> or group:<id>")

mime_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
request_hash = hashlib.sha256((args.target + "\0" + str(file_path) + "\0" + str(file_path.stat().st_size) + "\0" + args.message).encode()).hexdigest()
state_dir = pathlib.Path(os.environ.get("OPENCLAW_ZALO_DELIVERY_STATE", "/tmp/openclaw-zalo-delivery"))
state_file = state_dir / (request_hash + ".json")
if args.dry_run:
    print(json.dumps({"ok": True, "dryRun": True, "target": args.target,
                      "filename": file_path.name, "bytes": file_path.stat().st_size,
                      "mimeType": mime_type}))
    raise SystemExit(0)

if state_file.exists() and not args.force_retry:
    try:
        previous = json.loads(state_file.read_text())
    except Exception:
        previous = {"status": "unknown"}
    if previous.get("status") in {"sent", "unknown", "in_flight"}:
        raise SystemExit(json.dumps({"ok": False, "status": previous.get("status"),
                                     "requestHash": request_hash,
                                     "error": "idempotency guard: reconcile prior attempt before retry"}))
state_dir.mkdir(parents=True, exist_ok=True)
state_file.write_text(json.dumps({"status": "in_flight", "target": args.target,
                                  "filename": file_path.name, "startedAt": int(time.time())}))

# Read credentials only in memory; never print the config or token.
config = json.loads(pathlib.Path(args.config).read_text())
target_id = args.target.split(":", 1)[1]
payload = {
    "action": "send", "channel": "zalouser", "accountId": "default",
    "target": args.target, "threadId": target_id, "message": args.message,
    "buffer": base64.b64encode(file_path.read_bytes()).decode(),
    "filename": file_path.name, "mimeType": mime_type,
}
body = json.dumps({"tool": "message", "args": payload}).encode()
request = urllib.request.Request(
    "http://127.0.0.1:18789/tools/invoke", data=body,
    headers={"Authorization": "Bearer " + config["gateway"]["auth"]["token"],
             "Content-Type": "application/json"})
try:
    raw = urllib.request.urlopen(request, timeout=90).read().decode()
except urllib.error.HTTPError as error:
    state_file.write_text(json.dumps({"status": "unknown", "httpStatus": error.code,
                                      "target": args.target, "filename": file_path.name}))
    raise SystemExit(f"gateway http error {error.code}")
except Exception as error:
    state_file.write_text(json.dumps({"status": "unknown", "error": type(error).__name__,
                                      "target": args.target, "filename": file_path.name}))
    raise

outer = json.loads(raw)
if not outer.get("ok"):
    raise SystemExit(json.dumps({"ok": False, "error": outer.get("error", "gateway rejected")}))
text = outer.get("result", {}).get("content", [{}])[0].get("text", "")
result = json.loads(text) if text else outer.get("result", {}).get("details", {})
receipt = result.get("result", {}).get("receipt", result.get("receipt", {}))
status = result.get("deliveryStatus", result.get("status"))
message_id = receipt.get("primaryPlatformMessageId") or result.get("messageId")
thread_id = receipt.get("threadId") or receipt.get("conversationId")
via = result.get("via") or receipt.get("via")
kind = receipt.get("kind")
if kind is None:
    parts = receipt.get("parts") or []
    kinds = {part.get("kind") for part in parts if isinstance(part, dict) and part.get("kind")}
    if "media" in kinds:
        kind = "media"

# A group target must never silently fall back to a direct/private send.
if (status != "sent" or not message_id or thread_id != target_id or
        (args.target.startswith("group:") and kind not in (None, "media"))):
    state_file.write_text(json.dumps({"status": "unknown", "target": args.target,
                                      "filename": file_path.name, "messageId": message_id,
                                      "threadId": thread_id}))
    raise SystemExit(json.dumps({"ok": False, "status": status, "messageId": message_id,
                                 "threadId": thread_id, "via": via, "kind": kind,
                                 "target": args.target}))
state_file.write_text(json.dumps({"status": "sent", "target": args.target,
                                  "filename": file_path.name, "messageId": message_id,
                                  "threadId": thread_id}))
print(json.dumps({"ok": True, "status": "sent", "messageId": message_id,
                  "threadId": thread_id, "target": args.target,
                  "filename": file_path.name, "via": via, "kind": kind}))
