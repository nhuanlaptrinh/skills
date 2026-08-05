#!/usr/bin/env bash
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SCRIPT_PATH="$PROJECT_ROOT/scripts/Facebook_Post_Bai_Fanpage.py"
LOG_DIR="$PROJECT_ROOT/logs"
LOG_FILE="$LOG_DIR/fanpage_cron.log"
PYTHON_BIN="$PROJECT_ROOT/venv/bin/python"

mkdir -p "$LOG_DIR"
export TZ="Asia/Ho_Chi_Minh"

{
  echo "============================================================"
  echo "[$(date '+%Y-%m-%d %H:%M:%S %Z')] Start fanpage auto post"
  cd "$PROJECT_ROOT" || exit 1
  
  if [ -f "$PYTHON_BIN" ]; then
    "$PYTHON_BIN" "$SCRIPT_PATH"
  else
    echo "Thiếu $PYTHON_BIN; cài venv và dependencies trước khi chạy."
    exit 1
  fi
  
  status=$?
  echo "[$(date '+%Y-%m-%d %H:%M:%S %Z')] Finished with exit code $status"
  exit "$status"
} >> "$LOG_FILE" 2>&1
