#!/usr/bin/env bash
set -euo pipefail

CONFIG="${OPENCLAW_CONFIG_PATH:-$HOME/.openclaw/openclaw.json}"
GROUP_ID=""
ACCOUNT="workspace_videofactory"
SCOPE="account"
MODE=""
NO_RESTART=0

usage() {
  printf '%s\n' "Usage: $0 --group-id ID [--account NAME] [--scope account|global] (--dry-run|--apply|--check)"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --config) CONFIG="$2"; shift 2 ;;
    --group-id) GROUP_ID="$2"; shift 2 ;;
    --account) ACCOUNT="$2"; shift 2 ;;
    --scope) SCOPE="$2"; shift 2 ;;
    --dry-run|--apply|--check)
      [[ -z "$MODE" ]] || { echo "Choose one action only" >&2; exit 2; }
      MODE="${1#--}"; shift ;;
    --no-restart) NO_RESTART=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
done

[[ -n "$GROUP_ID" && -n "$MODE" ]] || { usage >&2; exit 2; }
[[ "$SCOPE" == account || "$SCOPE" == global ]] || { echo "--scope must be account or global" >&2; exit 2; }
[[ -f "$CONFIG" ]] || { echo "Config not found: $CONFIG" >&2; exit 1; }

python3 - "$CONFIG" "$GROUP_ID" "$ACCOUNT" "$SCOPE" "$MODE" "$NO_RESTART" <<'PY'
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

config_path, group_id, account, scope, mode, no_restart = sys.argv[1:]
path = Path(config_path).expanduser().resolve()
data = json.loads(path.read_text(encoding="utf-8"))

telegram = data.setdefault("channels", {}).setdefault("telegram", {})
if scope == "global":
    groups = telegram.setdefault("groups", {})
else:
    accounts = telegram.setdefault("accounts", {})
    if account not in accounts:
        raise SystemExit(f"Telegram account not found: {account}")
    groups = accounts[account].setdefault("groups", {})

if group_id not in groups:
    raise SystemExit(f"Group not found in {scope} scope: {group_id}")

group = groups[group_id]
tools = group.setdefault("toolsBySender", {})
wildcard = tools.setdefault("*", {})
old_deny = list(wildcard.get("deny", []))
new_deny = [item for item in old_deny if item not in {"exec", "process"}]
old_allow = list(wildcard.get("alsoAllow", []))
new_allow = list(dict.fromkeys(old_allow + ["exec", "process"]))

print(f"Config: {path}")
print(f"Target: {scope} group {group_id}")
print(f"Wildcard deny: {old_deny} -> {new_deny}")
print(f"Wildcard alsoAllow: {old_allow} -> {new_allow}")

if mode == "dry-run":
    raise SystemExit(0)

wildcard["alsoAllow"] = new_allow
if new_deny:
    wildcard["deny"] = new_deny
else:
    wildcard.pop("deny", None)

if mode == "check":
    actual = tools.get("*", {})
    if "exec" not in actual.get("alsoAllow", []) or "process" not in actual.get("alsoAllow", []):
        raise SystemExit("CHECK FAILED: wildcard alsoAllow does not contain exec/process")
    if "exec" in actual.get("deny", []) or "process" in actual.get("deny", []):
        raise SystemExit("CHECK FAILED: wildcard deny still contains exec/process")
    print("CHECK OK")
    raise SystemExit(0)

backup = path.with_name(
    f"{path.name}.bak-group-{group_id.lstrip('-')}-full-exec-"
    f"{datetime.now().strftime('%Y%m%d-%H%M%S')}"
)
shutil.copy2(path, backup)
tmp = path.with_name(f".{path.name}.tmp")
tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
os.chmod(tmp, path.stat().st_mode & 0o7777)
os.replace(tmp, path)
print(f"Backup: {backup}")

try:
    subprocess.run(["openclaw", "config", "validate"], check=True)
except Exception:
    shutil.copy2(backup, path)
    raise

if no_restart != "1":
    subprocess.run(["openclaw", "gateway", "restart"], check=True)
    print("Gateway reloaded")
else:
    print("Gateway reload skipped")
PY
