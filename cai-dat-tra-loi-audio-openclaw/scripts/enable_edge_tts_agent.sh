#!/usr/bin/env bash
set -euo pipefail

CONFIG=""
AGENT=""
VOICE="vi-VN-NamMinhNeural"
AUTO_MODE="inbound"
MODE=""

usage() {
  echo "Usage: $0 --config PATH --agent ID [--voice VOICE] [--auto-mode inbound|always] --dry-run|--apply"
}

while (($#)); do
  case "$1" in
    --config) CONFIG="$2"; shift 2 ;;
    --agent) AGENT="$2"; shift 2 ;;
    --voice) VOICE="$2"; shift 2 ;;
    --auto-mode) AUTO_MODE="$2"; shift 2 ;;
    --dry-run) MODE="dry-run"; shift ;;
    --apply) MODE="apply"; shift ;;
    -h|--help) usage; exit 0 ;;
    *) usage >&2; exit 2 ;;
  esac
done

[[ -n "$CONFIG" && -n "$AGENT" && -n "$MODE" ]] || { usage >&2; exit 2; }
[[ "$AUTO_MODE" == "inbound" || "$AUTO_MODE" == "always" ]] || { echo "Invalid --auto-mode" >&2; exit 2; }
jq empty "$CONFIG"
jq -e --arg id "$AGENT" '.agents.list[] | select(.id==$id)' "$CONFIG" >/dev/null
echo "mode=$MODE config=$CONFIG agent=$AGENT voice=$VOICE auto_mode=$AUTO_MODE"
[[ "$MODE" == "dry-run" ]] && exit 0

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
BACKUP="/root/_Backups/openclaw_edge_tts_${AGENT}_$STAMP"
mkdir -p "$BACKUP"
cp -a "$CONFIG" "$BACKUP/openclaw.json"
TMP="$(mktemp)"
jq --arg id "$AGENT" --arg voice "$VOICE" --arg autoMode "$AUTO_MODE" '
  .messages.tts = ((.messages.tts // {}) + {
    auto:"off", mode:"final", provider:"microsoft", maxTextLength:800,
    providers:{microsoft:{speakerVoice:$voice,lang:"vi-VN",outputFormat:"audio-24khz-48kbitrate-mono-mp3"}}
  }) |
  .plugins.entries.microsoft = {enabled:true} |
  .agents.list |= map(if .id==$id then . + {tts:{auto:$autoMode}} else . end)
' "$CONFIG" > "$TMP"
chown --reference="$CONFIG" "$TMP"
chmod --reference="$CONFIG" "$TMP"
mv "$TMP" "$CONFIG"
jq empty "$CONFIG"
echo "Enabled inbound Edge TTS for agent $AGENT. Backup: $BACKUP"
