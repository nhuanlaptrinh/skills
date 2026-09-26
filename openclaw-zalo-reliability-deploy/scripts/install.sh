#!/usr/bin/env bash
set -euo pipefail

CONTAINER=""; MEMBER_DATA_DIR=""; MEMBER_HOME=""; MEMBER_LABEL=""; MODE=dry-run
SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RELIABILITY_DIR="${RELIABILITY_DIR:-/root/.agents/skills/openclaw-zalo-reliability}"
CENTER_DIR="${CENTER_DIR:-/root/Automation/watchdog/shared_self_healing}"

usage() { cat <<'USAGE'
Usage: install.sh --container CONTAINER --member-data-dir DIR --member-home HOME --member-label LABEL [--dry-run|--apply]
Dry-run is the default. Apply changes only with --apply.
USAGE
}
while (($#)); do
  case "$1" in
    --container) CONTAINER=${2:-}; shift 2;;
    --member-data-dir) MEMBER_DATA_DIR=${2:-}; shift 2;;
    --member-home) MEMBER_HOME=${2:-}; shift 2;;
    --member-label) MEMBER_LABEL=${2:-}; shift 2;;
    --dry-run) MODE=dry-run; shift;;
    --apply) MODE=apply; shift;;
    -h|--help) usage; exit 0;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 2;;
  esac
done
[[ -n "$CONTAINER" && -n "$MEMBER_DATA_DIR" && -n "$MEMBER_HOME" && -n "$MEMBER_LABEL" ]] || { usage >&2; exit 2; }
[[ -d "$MEMBER_DATA_DIR/.openclaw" ]] || { echo "Missing .openclaw under $MEMBER_DATA_DIR" >&2; exit 1; }
[[ -x "$RELIABILITY_DIR/scripts/patch_zalo_core_group_guard.sh" ]] || { echo "Missing reliability skill: $RELIABILITY_DIR" >&2; exit 1; }
[[ -x "$RELIABILITY_DIR/scripts/patch_zca_upload_ack_guard_cjs.sh" ]] || { echo "Missing CommonJS guard helper" >&2; exit 1; }
docker inspect -f '{{.State.Running}}' "$CONTAINER" | grep -qx true || { echo "Container is not running: $CONTAINER" >&2; exit 1; }

key="member_${MEMBER_LABEL}_zalo_delivery"
echo "mode=$MODE container=$CONTAINER member=$MEMBER_LABEL"
echo "== core group target guard =="
bash "$RELIABILITY_DIR/scripts/patch_zalo_core_group_guard.sh" --container "$CONTAINER" --"$MODE"
echo "== ESM upload guard =="
if find "$MEMBER_DATA_DIR/.openclaw/npm/projects" -path '*/node_modules/@openclaw/zalouser/node_modules/zca-js/dist/upload-completion-guard.js' -type f -print -quit 2>/dev/null | grep -q .; then
  echo "already patched: ESM upload guard"
else
  bash "$RELIABILITY_DIR/scripts/patch_zca_upload_ack_guard.sh" --member-data-dir "$MEMBER_DATA_DIR" --"$MODE"
fi
echo "== CommonJS upload guard =="
bash "$RELIABILITY_DIR/scripts/patch_zca_upload_ack_guard_cjs.sh" --member-data-dir "$MEMBER_DATA_DIR" --"$MODE"

if [[ "$MODE" == apply ]]; then
  stamp="$(date -u +%Y%m%dT%H%M%SZ)"
  backup="/root/_Backups/${MEMBER_LABEL}-zalo-delivery-deploy/$stamp"
  mkdir -p "$backup"
  cp -a "$CENTER_DIR/project_config.json" "$backup/project_config.json.before"
  crontab -l 2>/dev/null >"$backup/crontab.before" || :
  echo "== syntax and offline tests =="
  node "$RELIABILITY_DIR/scripts/test_upload_completion_guard.mjs"
  while IFS= read -r f; do node --check "$f"; done < <(find "$MEMBER_DATA_DIR/.openclaw/npm/projects" \( -path '*/node_modules/@openclaw/zalouser/node_modules/zca-js/dist/cjs/upload-completion-guard.cjs' -o -path '*/node_modules/@openclaw/zalouser/node_modules/zca-js/dist/cjs/apis/uploadAttachment.cjs' -o -path '*/node_modules/@openclaw/zalouser/node_modules/zca-js/dist/cjs/apis/listen.cjs' \) -type f)
  docker exec "$CONTAINER" sh -lc "export HOME='$MEMBER_HOME'; openclaw config validate >/dev/null; openclaw plugins doctor >/dev/null"
  echo "== watchdog registration =="
  python3 - "$CENTER_DIR/project_config.json" "$MEMBER_LABEL" "$CONTAINER" "$MEMBER_HOME" "$SKILL_DIR" <<'PY'
import json
import pathlib
import sys
p=pathlib.Path(sys.argv[1])
label,container,home,skill=sys.argv[2:]
d=json.loads(p.read_text())
key=f'member_{label}_zalo_delivery'
d[key]={
    'project_root': str(pathlib.Path(skill)),
    'run_command': f"CONTAINER='{container}' MEMBER_HOME='{home}' MEMBER_LABEL='{label}' PROJECT_KEY='{key}' bash scripts/check_zalo_delivery_guard.sh",
    'script_to_fix': 'scripts/check_zalo_delivery_guard.sh',
    'log_file': f'/root/Automation/watchdog/shared_self_healing/logs/{key}.log',
    'type': 'openclaw_channel',
    'lock_file': f'/tmp/{key}.lock',
    'telegram_label': f'OpenClaw Zalo Delivery Guard - {label}',
    'ai_on_failure': False,
}
p.write_text(json.dumps(d, ensure_ascii=False, indent=2)+'\n')
print(f'registered={key}')
PY
  tmp="$(mktemp)"
  crontab -l 2>/dev/null >"$tmp" || true
  marker="member_${MEMBER_LABEL}_zalo_delivery_watchdog"
  if ! grep -q "BEGIN ${marker}" "$tmp"; then
    {
      echo "# BEGIN ${marker}"
      echo "*/5 * * * * $CENTER_DIR/run_project.sh $key"
      echo "# END ${marker}"
    } >>"$tmp"
    crontab "$tmp"
  fi
  rm -f "$tmp"
  echo "== probe =="
  docker exec "$CONTAINER" sh -lc "export HOME='$MEMBER_HOME'; timeout 45s openclaw channels status --probe"
  echo "backup=$backup"
fi
echo "completed mode=$MODE"
