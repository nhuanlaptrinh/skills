#!/usr/bin/env bash
set -euo pipefail

CONTAINER=""
MEMBER_ROOT=""
MEMBER_ID=""
CONTAINER_OPENCLAW_HOME=""
ENDPOINT="http://172.17.0.1:18080"
SERVICE_ENV="/root/AI_Runtime/shared_local_stt/.env"
MODE=""
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

usage() {
  echo "Usage: $0 --container NAME --member-root PATH --member-id ID --container-openclaw-home PATH [--endpoint URL] [--service-env PATH] --dry-run|--apply"
}

while (($#)); do
  case "$1" in
    --container) CONTAINER="$2"; shift 2 ;;
    --member-root) MEMBER_ROOT="$2"; shift 2 ;;
    --member-id) MEMBER_ID="$2"; shift 2 ;;
    --container-openclaw-home) CONTAINER_OPENCLAW_HOME="$2"; shift 2 ;;
    --endpoint) ENDPOINT="$2"; shift 2 ;;
    --service-env) SERVICE_ENV="$2"; shift 2 ;;
    --dry-run) MODE="dry-run"; shift ;;
    --apply) MODE="apply"; shift ;;
    -h|--help) usage; exit 0 ;;
    *) usage >&2; exit 2 ;;
  esac
done

[[ -n "$CONTAINER" && -n "$MEMBER_ROOT" && -n "$MEMBER_ID" && -n "$CONTAINER_OPENCLAW_HOME" && -n "$MODE" ]] || { usage >&2; exit 2; }
CONFIG="$MEMBER_ROOT/.openclaw/openclaw.json"
WORKSPACE="$MEMBER_ROOT/.openclaw/workspace"
CREDENTIALS="$MEMBER_ROOT/.openclaw/credentials"
CLIENT_DIR="$WORKSPACE/skills/cai-dat-audio-local-openclaw/scripts"
OWNER="$(stat -c '%u:%g' "$CONFIG")"

docker inspect "$CONTAINER" >/dev/null
[[ -f "$CONFIG" && -f "$SERVICE_ENV" ]] || { echo "Required config/service env missing" >&2; exit 1; }
jq empty "$CONFIG"
docker exec "$CONTAINER" curl -fsS --max-time 5 "$ENDPOINT/health" >/dev/null

echo "mode=$MODE container=$CONTAINER member_id=$MEMBER_ID endpoint=$ENDPOINT"
echo "container_openclaw_home=$CONTAINER_OPENCLAW_HOME"
echo "config=$CONFIG"
[[ "$MODE" == "dry-run" ]] && exit 0

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
BACKUP="/root/_Backups/openclaw_audio_${MEMBER_ID}_$STAMP"
mkdir -p "$BACKUP"
cp -a "$CONFIG" "$BACKUP/openclaw.json"
[[ -f "$CREDENTIALS/shared-local-stt.token" ]] && cp -a "$CREDENTIALS/shared-local-stt.token" "$BACKUP/" || true

TOKEN="$(sed -n 's/^SHARED_STT_TOKEN=//p' "$SERVICE_ENV" | head -1)"
[[ -n "$TOKEN" ]] || { echo "SHARED_STT_TOKEN missing" >&2; exit 1; }
mkdir -p "$CLIENT_DIR" "$CREDENTIALS"
cp "$SCRIPT_DIR/transcribe_shared.py" "$CLIENT_DIR/transcribe_shared.py"
cp "$SCRIPT_DIR/transcribe_zalo_voice.py" "$CLIENT_DIR/transcribe_zalo_voice.py"
sed -i "s|^ENDPOINT = .*|ENDPOINT = \"${ENDPOINT}/v1/audio/transcriptions\"|; s|^MEMBER_ID = .*|MEMBER_ID = \"${MEMBER_ID}\"|" "$CLIENT_DIR/transcribe_shared.py"
printf '%s\n' "$TOKEN" > "$CREDENTIALS/shared-local-stt.token"
unset TOKEN
chmod 755 "$CLIENT_DIR/transcribe_shared.py" "$CLIENT_DIR/transcribe_zalo_voice.py"
chmod 600 "$CREDENTIALS/shared-local-stt.token"
chown -R "$OWNER" "$WORKSPACE/skills/cai-dat-audio-local-openclaw"
chown "$OWNER" "$CREDENTIALS/shared-local-stt.token"

TMP="$(mktemp)"
jq --arg script "$CONTAINER_OPENCLAW_HOME/workspace/skills/cai-dat-audio-local-openclaw/scripts/transcribe_shared.py" '
  .tools.media.audio.enabled = true |
  .tools.media.audio.language = "vi" |
  .tools.media.audio.models = [{
    type:"cli", command:"/usr/bin/python3", args:[$script,"{{MediaPath}}"],
    timeoutSeconds:180, maxBytes:20971520, capabilities:["audio"]
  }]' "$CONFIG" > "$TMP"
chown --reference="$CONFIG" "$TMP"
chmod --reference="$CONFIG" "$TMP"
mv "$TMP" "$CONFIG"
jq empty "$CONFIG"
docker restart "$CONTAINER" >/dev/null
echo "Installed shared STT client. Backup: $BACKUP"
