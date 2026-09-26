#!/usr/bin/env bash
# ==============================================================================
# export_clean_assistant.sh
# Xuất bản sao lưu sạch (Clean Export) cho Trợ lý OpenClaw:
# - Giữ nguyên 100% phần đào tạo (Identity, Soul, Memory, User, Rules, Skills, Scripts)
# - Loại bỏ toàn bộ dữ liệu tạm, lịch sử chat cũ, cache sqlite và media rác
# ==============================================================================

set -euo pipefail

SOURCE_DIR=""
CONTAINER_NAME=""
OUTPUT_FILE=""
ACTION="dry-run"

usage() {
    cat <<EOF
Sử dụng:
  $0 --source <path> [options]

Các tùy chọn:
  --source <path>       Đường dẫn thư mục dữ liệu nguồn (bắt buộc)
  --container <name>    Tên container Docker (nếu có, để lấy cấu hình supervisor và app)
  --output <tarball>    Đường dẫn file .tar.gz xuất ra (mặc định trong /root/_Backups/)
  --dry-run             Kiểm tra danh sách thành phần sẽ sao lưu mà không nén
  --apply               Thực hiện đóng gói nén file thực tế
  -h, --help            Hiển thị trợ giúp này

Ví dụ:
  $0 --source /root/Apps/member_vps/docker-users/data/anhlaptrinhthu --container user-anhlaptrinhthu --dry-run
  $0 --source /root/Apps/member_vps/docker-users/data/anhlaptrinhthu --container user-anhlaptrinhthu --apply
EOF
    exit 1
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --source)
            SOURCE_DIR="$2"
            shift 2
            ;;
        --container)
            CONTAINER_NAME="$2"
            shift 2
            ;;
        --output)
            OUTPUT_FILE="$2"
            shift 2
            ;;
        --dry-run)
            ACTION="dry-run"
            shift
            ;;
        --apply)
            ACTION="apply"
            shift
            ;;
        -h|--help)
            usage
            ;;
        *)
            echo "Tham số không hợp lệ: $1" >&2
            usage
            ;;
    esac
done

if [[ -z "$SOURCE_DIR" || ! -d "$SOURCE_DIR" ]]; then
    echo "LỖI: Thư mục nguồn --source không tồn tại: $SOURCE_DIR" >&2
    exit 1
fi

MEMBER_NAME="$(basename "$SOURCE_DIR")"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
if [[ -z "$OUTPUT_FILE" ]]; then
    mkdir -p /root/_Backups
    OUTPUT_FILE="/root/_Backups/${MEMBER_NAME}_clean_export_${TIMESTAMP}.tar.gz"
fi

echo "======================================================================"
echo "KHỞI CHẠY XUẤT TRỢ LÝ OPENCLAW SẠCH (CLEAN EXPORT)"
echo "Nguồn:      $SOURCE_DIR"
echo "Container:  ${CONTAINER_NAME:-'(không dùng)'}"
echo "Đích:       $OUTPUT_FILE"
echo "Chế độ:     $ACTION"
echo "======================================================================"

if [[ "$ACTION" == "dry-run" ]]; then
    echo ""
    echo "[DRY-RUN] Các thành phần sẽ được đóng gói:"
    echo "1. Tri thức & Nhân cách (Training):"
    find "$SOURCE_DIR/.openclaw/workspace" -maxdepth 1 -name "*.md" 2>/dev/null | sed 's/^/   + /' || true
    [ -d "$SOURCE_DIR/.openclaw/workspace/memory" ] && echo "   + Thư mục nhật ký học hỏi: memory/ ($(find "$SOURCE_DIR/.openclaw/workspace/memory" -type f | wc -l) files)"
    [ -d "$SOURCE_DIR/.openclaw/workspace/profiles" ] && echo "   + Thư mục hồ sơ: profiles/"
    [ -d "$SOURCE_DIR/.openclaw/workspace-facebook-anvi" ] && echo "   + Workspace Trợ lý Fanpage AIA: workspace-facebook-anvi/"
    
    echo "2. Skills & Scripts:"
    [ -d "$SOURCE_DIR/.openclaw/workspace/skills" ] && echo "   + Workspace skills ($(find "$SOURCE_DIR/.openclaw/workspace/skills" -maxdepth 1 -mindepth 1 -type d | wc -l) skills)"
    [ -d "$SOURCE_DIR/.openclaw/workspace/scripts" ] && echo "   + Python scripts ($(find "$SOURCE_DIR/.openclaw/workspace/scripts" -type f | wc -l) files)"
    [ -d "$SOURCE_DIR/.openclaw/skills" ] && echo "   + Shared skills ($(find "$SOURCE_DIR/.openclaw/skills" -maxdepth 1 -mindepth 1 -type d | wc -l) skills)"
    [ -d "$SOURCE_DIR/.openclaw/agents/main/agent/workshop-skills" ] && echo "   + Workshop skills ($(find "$SOURCE_DIR/.openclaw/agents/main/agent/workshop-skills" -maxdepth 1 -mindepth 1 -type d | wc -l) skills)"
    
    echo "3. Cấu hình hệ thống:"
    [ -f "$SOURCE_DIR/.openclaw/openclaw.json" ] && echo "   + Cấu hình OpenClaw: openclaw.json"
    [ -d "$SOURCE_DIR/_Second_AI_Brain" ] && echo "   + Second AI Brain: _Second_AI_Brain/"
    [ -f "$SOURCE_DIR/openclaw-nginx.conf" ] && echo "   + Nginx config: openclaw-nginx.conf"
    
    echo ""
    echo "[DRY-RUN] Các thành phần sẽ bị LOẠI BỎ (dữ liệu tạm / rác):"
    echo "   - Toàn bộ session chat: .openclaw/agents/*/sessions/"
    echo "   - Database sqlite chat runtime: *.sqlite*"
    echo "   - Tệp media tạm / output / cache rác (.jpg, .mp4, tmp/, output/)"
    echo ""
    echo "Chạy lại với cờ --apply để tiến hành nén thực tế."
    exit 0
fi

# ==================== APPLY MODE ====================
TMP_STAGING="/tmp/clean_export_staging_${MEMBER_NAME}_$$"
rm -rf "$TMP_STAGING"
mkdir -p "$TMP_STAGING/home/.openclaw/workspace"
mkdir -p "$TMP_STAGING/home/.openclaw/agents/main/agent"
mkdir -p "$TMP_STAGING/home/.openclaw/skill-workshop"
mkdir -p "$TMP_STAGING/home/.local/bin"
mkdir -p "$TMP_STAGING/container_root/supervisor_conf"
mkdir -p "$TMP_STAGING/container_root/root_agents_skills"
mkdir -p "$TMP_STAGING/container_root/Apps"

echo "[1/4] Sao chép cấu hình gốc và Second AI Brain..."
[ -f "$SOURCE_DIR/AGENTS.md" ] && cp -a "$SOURCE_DIR/AGENTS.md" "$TMP_STAGING/home/"
[ -f "$SOURCE_DIR/openclaw-nginx.conf" ] && cp -a "$SOURCE_DIR/openclaw-nginx.conf" "$TMP_STAGING/home/"
[ -f "$SOURCE_DIR/syncthing-nginx.conf" ] && cp -a "$SOURCE_DIR/syncthing-nginx.conf" "$TMP_STAGING/home/"
[ -f "$SOURCE_DIR/deploy-demow1-host.sh" ] && cp -a "$SOURCE_DIR/deploy-demow1-host.sh" "$TMP_STAGING/home/"
[ -d "$SOURCE_DIR/_Second_AI_Brain" ] && cp -a "$SOURCE_DIR/_Second_AI_Brain" "$TMP_STAGING/home/"

echo "[2/4] Sao chép cấu hình OpenClaw & dữ liệu đào tạo sạch..."
[ -f "$SOURCE_DIR/.openclaw/openclaw.json" ] && cp -a "$SOURCE_DIR/.openclaw/openclaw.json" "$TMP_STAGING/home/.openclaw/"
[ -f "$SOURCE_DIR/.openclaw/openclaw.json.last-good" ] && cp -a "$SOURCE_DIR/.openclaw/openclaw.json.last-good" "$TMP_STAGING/home/.openclaw/"

WS="$SOURCE_DIR/.openclaw/workspace"
for f in AGENTS.md IDENTITY.md SOUL.md USER.md MEMORY.md HEARTBEAT.md TOOLS.md DREAMS.md; do
    [ -f "$WS/$f" ] && cp -a "$WS/$f" "$TMP_STAGING/home/.openclaw/workspace/"
done

[ -d "$WS/memory" ] && cp -a "$WS/memory" "$TMP_STAGING/home/.openclaw/workspace/"
[ -d "$WS/profiles" ] && cp -a "$WS/profiles" "$TMP_STAGING/home/.openclaw/workspace/"
[ -d "$WS/skills" ] && cp -a "$WS/skills" "$TMP_STAGING/home/.openclaw/workspace/"
[ -d "$WS/scripts" ] && cp -a "$WS/scripts" "$TMP_STAGING/home/.openclaw/workspace/"
[ -d "$WS/tools" ] && cp -a "$WS/tools" "$TMP_STAGING/home/.openclaw/workspace/"

if [ -d "$WS/main" ]; then
    mkdir -p "$TMP_STAGING/home/.openclaw/workspace/main"
    for f in AGENTS.md IDENTITY.md SOUL.md USER.md MEMORY.md DREAMS.md openclaw_huong_dan.md; do
        [ -f "$WS/main/$f" ] && cp -a "$WS/main/$f" "$TMP_STAGING/home/.openclaw/workspace/main/"
    done
    [ -d "$WS/main/memory" ] && cp -a "$WS/main/memory" "$TMP_STAGING/home/.openclaw/workspace/main/"
    [ -d "$WS/main/scripts" ] && cp -a "$WS/main/scripts" "$TMP_STAGING/home/.openclaw/workspace/main/"
    [ -d "$WS/main/skills" ] && cp -a "$WS/main/skills" "$TMP_STAGING/home/.openclaw/workspace/main/"
fi

[ -d "$SOURCE_DIR/.openclaw/workspace-facebook-anvi" ] && cp -a "$SOURCE_DIR/.openclaw/workspace-facebook-anvi" "$TMP_STAGING/home/.openclaw/"
[ -d "$SOURCE_DIR/.openclaw/skills" ] && cp -a "$SOURCE_DIR/.openclaw/skills" "$TMP_STAGING/home/.openclaw/"
[ -d "$SOURCE_DIR/.openclaw/agents/main/agent/workshop-skills" ] && cp -a "$SOURCE_DIR/.openclaw/agents/main/agent/workshop-skills" "$TMP_STAGING/home/.openclaw/agents/main/agent/"
[ -d "$SOURCE_DIR/.openclaw/skill-workshop/proposals" ] && cp -a "$SOURCE_DIR/.openclaw/skill-workshop/proposals" "$TMP_STAGING/home/.openclaw/skill-workshop/"

[ -f "$SOURCE_DIR/.local/bin/gan-domain" ] && cp -a "$SOURCE_DIR/.local/bin/gan-domain" "$TMP_STAGING/home/.local/bin/"
[ -f "$SOURCE_DIR/.local/bin/cloudflared" ] && cp -a "$SOURCE_DIR/.local/bin/cloudflared" "$TMP_STAGING/home/.local/bin/"

if [[ -n "$CONTAINER_NAME" ]] && docker inspect "$CONTAINER_NAME" >/dev/null 2>&1; then
    echo "[3/4] Trích xuất cấu hình Supervisor và ứng dụng từ container $CONTAINER_NAME..."
    docker cp "$CONTAINER_NAME:/etc/supervisor/conf.d/member-vps.conf" "$TMP_STAGING/container_root/supervisor_conf/" 2>/dev/null || true
    docker cp "$CONTAINER_NAME:/etc/supervisor/conf.d/facebook-fanpage-auto-reply.conf" "$TMP_STAGING/container_root/supervisor_conf/" 2>/dev/null || true
    docker cp "$CONTAINER_NAME:/root/.agents/skills" "$TMP_STAGING/container_root/root_agents_skills" 2>/dev/null || true
    if docker exec "$CONTAINER_NAME" test -d /root/Apps/facebook_fanpage_auto_reply 2>/dev/null; then
        docker cp "$CONTAINER_NAME:/root/Apps/facebook_fanpage_auto_reply" "$TMP_STAGING/container_root/Apps/" 2>/dev/null || true
        rm -rf "$TMP_STAGING/container_root/Apps/facebook_fanpage_auto_reply/01_mes_op_anvi/.venv" 2>/dev/null || true
    fi
else
    echo "[3/4] Bỏ qua trích xuất container (không cung cấp hoặc container không chạy)."
fi

echo "[4/4] Nén gói sao lưu sạch vào $OUTPUT_FILE..."
tar -czf "$OUTPUT_FILE" -C "$TMP_STAGING" .
rm -rf "$TMP_STAGING"

FINAL_SIZE="$(du -sh "$OUTPUT_FILE" | cut -f1)"
echo "======================================================================"
echo "THÀNH CÔNG!"
echo "File nén đã lưu tại: $OUTPUT_FILE ($FINAL_SIZE)"
echo "======================================================================"
