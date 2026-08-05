#!/usr/bin/env bash
set -euo pipefail

OPENCLAW_HOME=""
MODE=""
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

usage() {
  echo "Usage: $0 --openclaw-home PATH --dry-run|--apply"
}

while (($#)); do
  case "$1" in
    --openclaw-home) OPENCLAW_HOME="$2"; shift 2 ;;
    --dry-run) MODE="dry-run"; shift ;;
    --apply) MODE="apply"; shift ;;
    -h|--help) usage; exit 0 ;;
    *) usage >&2; exit 2 ;;
  esac
done

[[ -n "$OPENCLAW_HOME" && -n "$MODE" ]] || { usage >&2; exit 2; }
CONFIG="$OPENCLAW_HOME/openclaw.json"
WORKSPACE="$OPENCLAW_HOME/workspace"
VENV="$OPENCLAW_HOME/tools/local-stt-venv"
TARGET="$WORKSPACE/skills/openclaw-local-voice-stt/scripts/transcribe_local.py"
RUNTIME_HOME="$(dirname "$OPENCLAW_HOME")"
OWNER="$(stat -c '%u:%g' "$CONFIG")"

[[ -f "$CONFIG" ]] || { echo "Missing $CONFIG" >&2; exit 1; }
command -v python3 >/dev/null
command -v ffmpeg >/dev/null
command -v ffprobe >/dev/null
command -v jq >/dev/null
jq empty "$CONFIG"
echo "mode=$MODE openclaw_home=$OPENCLAW_HOME venv=$VENV"
[[ "$MODE" == "dry-run" ]] && exit 0

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
BACKUP="/root/_Backups/openclaw_audio_standalone_$STAMP"
mkdir -p "$BACKUP"
cp -a "$CONFIG" "$BACKUP/openclaw.json"
mkdir -p "$(dirname "$TARGET")" "$OPENCLAW_HOME/tools"
cp "$SCRIPT_DIR/transcribe_local.py" "$TARGET"
chmod 755 "$TARGET"
python3 -m venv "$VENV"
"$VENV/bin/pip" install --upgrade pip
"$VENV/bin/pip" install faster-whisper==1.2.1
HOME="$RUNTIME_HOME" "$VENV/bin/python" -c 'import os; from pathlib import Path; from faster_whisper import WhisperModel; WhisperModel("small", device="cpu", compute_type="int8", cpu_threads=4, num_workers=1, download_root=str(Path.home()/".cache"/"faster-whisper"))'
chown -R "$OWNER" "$WORKSPACE/skills/openclaw-local-voice-stt" "$OPENCLAW_HOME/tools/local-stt-venv" "$RUNTIME_HOME/.cache/faster-whisper"

TMP="$(mktemp)"
jq --arg python "$VENV/bin/python" --arg script "$TARGET" '
  .tools.media.audio.enabled = true |
  .tools.media.audio.language = "vi" |
  .tools.media.audio.models = [{
    type:"cli", command:$python, args:[$script,"{{MediaPath}}"],
    timeoutSeconds:180, maxBytes:20971520, capabilities:["audio"]
  }]' "$CONFIG" > "$TMP"
chown --reference="$CONFIG" "$TMP"
chmod --reference="$CONFIG" "$TMP"
mv "$TMP" "$CONFIG"
jq empty "$CONFIG"
echo "Installed standalone local STT. Backup: $BACKUP"
echo "Restart the OpenClaw gateway using this VPS's existing service method."
