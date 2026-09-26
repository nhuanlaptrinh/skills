#!/usr/bin/env bash
# ==============================================================================
# quick_send_zalo_qr.sh
# Tự động cấp quyền (nếu cần), dọn lock và gửi QR Zalo User trực tiếp qua Telegram
# Dùng được cho cả Host VPS và Docker Container Member VPS
# ==============================================================================
set -euo pipefail

TARGET_ID=""
CONTAINER=""
DRY_RUN=false

usage() {
  echo "Cách dùng:"
  echo "  1. Chạy trên VPS hiện tại (hoặc bên trong container):"
  echo "     $0 <TELEGRAM_USER_ID> [--dry-run]"
  echo ""
  echo "  2. Chạy từ Host điều khiển Docker container member:"
  echo "     $0 --container <CONTAINER_NAME> <TELEGRAM_USER_ID> [--dry-run]"
  echo ""
  echo "Ví dụ:"
  echo "     $0 6980864856"
  echo "     $0 --container user-anhlaptrinhthu 6980864856"
  exit 1
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --container|-c)
      CONTAINER="$2"
      shift 2
      ;;
    --dry-run)
      DRY_RUN=true
      shift
      ;;
    -h|--help)
      usage
      ;;
    *)
      if [[ -z "$TARGET_ID" && "$1" =~ ^[0-9]+$ ]]; then
        TARGET_ID="$1"
        shift
      else
        echo "Lỗi: Tham số không hợp lệ: $1"
        usage
      fi
      ;;
  esac
done

if [[ -z "$TARGET_ID" ]]; then
  echo "Lỗi: Cần cung cấp TELEGRAM_USER_ID (dạng số)"
  usage
fi

# ==============================================================================
# Trường hợp 1: Chạy từ Host vào Docker container member
# ==============================================================================
if [[ -n "$CONTAINER" ]]; then
  echo "==> Đang gửi mã QR Zalo User cho container: $CONTAINER (Telegram ID: $TARGET_ID)..."

  # Đảm bảo container đang chạy
  if ! docker ps --format '{{.Names}}' | grep -Eq "^${CONTAINER}\$"; then
    echo "Lỗi: Container $CONTAINER không đang chạy!"
    exit 1
  fi

  # Sao chép script mới nhất vào container nếu cần
  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  docker exec "$CONTAINER" mkdir -p /root/.agents/skills/openclaw-zalo-qr-login/scripts
  docker cp "${SCRIPT_DIR}/send_zalo_qr_to_telegram_owner.mjs" "${CONTAINER}:/root/.agents/skills/openclaw-zalo-qr-login/scripts/"
  docker cp "${SCRIPT_DIR}/quick_send_zalo_qr.sh" "${CONTAINER}:/root/.agents/skills/openclaw-zalo-qr-login/scripts/"
  docker exec "$CONTAINER" chmod +x /root/.agents/skills/openclaw-zalo-qr-login/scripts/quick_send_zalo_qr.sh

  DRY_FLAG=""
  if [[ "$DRY_RUN" == true ]]; then
    DRY_FLAG="--dry-run"
  fi

  # Thực thi bên trong container
  docker exec -it "$CONTAINER" bash -lc "
    set -a
    [ -f /root/.openclaw/token-codex.env ] && . /root/.openclaw/token-codex.env
    set +a
    /root/.agents/skills/openclaw-zalo-qr-login/scripts/quick_send_zalo_qr.sh $TARGET_ID $DRY_FLAG
  "
  exit $?
fi

# ==============================================================================
# Trường hợp 2: Chạy trực tiếp trên VPS / bên trong Container
# ==============================================================================
OPENCLAW_DIR="${OPENCLAW_STATE_DIR:-$HOME/.openclaw}"
CONFIG_PATH="${OPENCLAW_CONFIG_PATH:-$OPENCLAW_DIR/openclaw.json}"
LOCK_FILE="$OPENCLAW_DIR/state/zalo-qr-owner-login.lock"

echo "==> Kiểm tra và chuẩn bị gửi QR Zalo User cho Telegram ID: $TARGET_ID"

# 1. Dọn dẹp lock cũ nếu bị treo
if [[ -f "$LOCK_FILE" ]]; then
  echo "--> Xóa file lock cũ: $LOCK_FILE"
  rm -f "$LOCK_FILE"
fi

# 2. Tự động kiểm tra và phân quyền owner cho Telegram ID trong openclaw.json nếu thiếu
if [[ -f "$CONFIG_PATH" ]]; then
  python3 - <<PY
import json
import os
import sys

target = "$TARGET_ID"
config_path = "$CONFIG_PATH"

try:
    with open(config_path, "r", encoding="utf-8") as f:
        data = json.load(f)
except Exception as e:
    sys.exit(0)

changed = False

# 1. Telegram allowFrom
tg = data.setdefault("channels", {}).setdefault("telegram", {})
allow_from = tg.setdefault("allowFrom", [])
if target not in [str(x) for x in allow_from]:
    allow_from.append(target)
    changed = True

# 2. commands.ownerAllowFrom
cmd = data.setdefault("commands", {})
owner_allow = cmd.setdefault("ownerAllowFrom", [])
if target not in [str(x) for x in owner_allow] and f"telegram:{target}" not in [str(x) for x in owner_allow]:
    owner_allow.append(f"telegram:{target}")
    changed = True

# 3. tools.elevated.allowFrom.telegram
elevated = data.setdefault("tools", {}).setdefault("elevated", {}).setdefault("allowFrom", {}).setdefault("telegram", [])
if target not in [str(x) for x in elevated]:
    elevated.append(target)
    changed = True

# 4. channels.telegram.execApprovals.approvers
exec_approvers = tg.setdefault("execApprovals", {}).setdefault("approvers", [])
if target not in [str(x) for x in exec_approvers]:
    exec_approvers.append(target)
    changed = True

# 5. approvals.plugin.targets
accounts = tg.get("accounts", {})
default_account = "default" if "default" in accounts else (list(accounts.keys())[0] if accounts else "default")

approvals = data.setdefault("approvals", {}).setdefault("plugin", {})
targets = approvals.setdefault("targets", [])
has_target = any(isinstance(t, dict) and t.get("channel") == "telegram" and str(t.get("to")) == target for t in targets)
if not has_target:
    targets.append({"channel": "telegram", "to": target, "accountId": default_account})
    changed = True

# 6. Multi-agent systemAgent & ownership
agents = data.get("agents", {})
entries = agents.get("entries", {})
if len(entries) > 1:
    defaults = agents.setdefault("defaults", {})
    if "systemAgent" not in defaults or not defaults["systemAgent"].get("agentId"):
        defaults["systemAgent"] = {"agentId": "main"}
        changed = True
    if agents.get("ownership") != "explicit":
        agents["ownership"] = "explicit"
        changed = True

if changed:
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print("--> Đã tự động cập nhật phân quyền Owner và systemAgent cho Telegram ID", target)
PY
fi

# 3. Chạy helper gửi QR
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MJS_SCRIPT="${SCRIPT_DIR}/send_zalo_qr_to_telegram_owner.mjs"

if [[ ! -f "$MJS_SCRIPT" ]]; then
  echo "Lỗi: Không tìm thấy script $MJS_SCRIPT"
  exit 1
fi

ACTION_FLAG="--apply"
if [[ "$DRY_RUN" == true ]]; then
  ACTION_FLAG="--dry-run"
fi

echo "--> Bắt đầu phiên tạo QR và gửi tin nhắn ảnh tới Telegram ID $TARGET_ID..."
node "$MJS_SCRIPT" --target "$TARGET_ID" "$ACTION_FLAG"
