#!/usr/bin/env bash
set -euo pipefail

CONTAINER=""
CONFIG_PATH="/root/.openclaw/openclaw.json"
AGENT=""
VOICE="vi-VN-NamMinhNeural"
AUTO_MODE="always"
MODE=""

usage() {
  echo "Usage: $0 --container NAME [--config-path PATH] [--agent ID] [--voice VOICE] [--auto-mode inbound|always] --dry-run|--apply"
}

while (($#)); do
  case "$1" in
    --container) CONTAINER="$2"; shift 2 ;;
    --config-path) CONFIG_PATH="$2"; shift 2 ;;
    --agent) AGENT="$2"; shift 2 ;;
    --voice) VOICE="$2"; shift 2 ;;
    --auto-mode) AUTO_MODE="$2"; shift 2 ;;
    --dry-run) MODE="dry-run"; shift ;;
    --apply) MODE="apply"; shift ;;
    -h|--help) usage; exit 0 ;;
    *) usage >&2; exit 2 ;;
  esac
done

[[ -n "$CONTAINER" && -n "$MODE" ]] || { usage >&2; exit 2; }
[[ "$AUTO_MODE" == "inbound" || "$AUTO_MODE" == "always" ]] || { echo "Invalid --auto-mode" >&2; exit 2; }
docker inspect "$CONTAINER" >/dev/null
docker exec "$CONTAINER" test -f "$CONFIG_PATH"

TMP="$(mktemp /tmp/openclaw-edge-tts-container.XXXXXX.json)"
docker cp "$CONTAINER:$CONFIG_PATH" "$TMP"
jq empty "$TMP"
HAS_AGENT=false
if [[ -n "$AGENT" ]] && jq -e --arg id "$AGENT" '.agents.list[]? | select(.id==$id)' "$TMP" >/dev/null; then
  HAS_AGENT=true
fi
echo "mode=$MODE container=$CONTAINER config_path=$CONFIG_PATH agent=${AGENT:-global} auto_mode=$AUTO_MODE has_agent=$HAS_AGENT"
[[ "$MODE" == "dry-run" ]] && exit 0

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
SAFE_CONTAINER="${CONTAINER//[^a-zA-Z0-9_.-]/_}"
BACKUP="/root/_Backups/member_vps/${SAFE_CONTAINER}_edge_tts_$STAMP"
mkdir -p "$BACKUP"
cp -a "$TMP" "$BACKUP/openclaw.before.json"
chmod 600 "$BACKUP/openclaw.before.json"

PATCHED="$(mktemp /tmp/openclaw-edge-tts-container-patched.XXXXXX.json)"
if [[ "$HAS_AGENT" == true ]]; then
  jq --arg id "$AGENT" --arg voice "$VOICE" --arg autoMode "$AUTO_MODE" '
    .messages.tts = ((.messages.tts // {}) + {
      auto:"off", mode:"final", provider:"microsoft", maxTextLength:800,
      providers:{microsoft:{speakerVoice:$voice,lang:"vi-VN",outputFormat:"audio-24khz-48kbitrate-mono-mp3"}}
    }) |
    .plugins.entries.microsoft = {enabled:true} |
    .agents.list |= map(if .id==$id then . + {tts:{auto:$autoMode}} else . end)
  ' "$TMP" > "$PATCHED"
else
  jq --arg voice "$VOICE" --arg autoMode "$AUTO_MODE" '
    .messages.tts = ((.messages.tts // {}) + {
      auto:$autoMode, mode:"final", provider:"microsoft", maxTextLength:800,
      providers:{microsoft:{speakerVoice:$voice,lang:"vi-VN",outputFormat:"audio-24khz-48kbitrate-mono-mp3"}}
    }) |
    .plugins.entries.microsoft = {enabled:true}
  ' "$TMP" > "$PATCHED"
fi
jq empty "$PATCHED"
cp -a "$PATCHED" "$BACKUP/openclaw.after.json"
chmod 600 "$BACKUP/openclaw.after.json"
docker cp "$PATCHED" "$CONTAINER:$CONFIG_PATH"
docker exec "$CONTAINER" chmod 600 "$CONFIG_PATH"

if docker exec "$CONTAINER" tmux has-session -t openclaw 2>/dev/null; then
  docker exec "$CONTAINER" tmux respawn-pane -k -t openclaw 'HOME=/root openclaw gateway run'
  sleep 10
fi
docker exec "$CONTAINER" bash -lc 'grep -F "http server listening" /tmp/openclaw/openclaw-*.log | tail -1 | grep -q microsoft'
docker exec "$CONTAINER" bash -lc 'openclaw channels status 2>/dev/null | grep -q "Gateway reachable"'
echo "Enabled Edge TTS in container $CONTAINER. Backup: $BACKUP"
