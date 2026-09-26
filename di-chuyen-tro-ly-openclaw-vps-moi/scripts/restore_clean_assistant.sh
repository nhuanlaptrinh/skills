#!/usr/bin/env bash
# ==============================================================================
# restore_clean_assistant.sh
# Khôi phục và thiết lập Trợ lý OpenClaw sạch trên VPS mới:
# - Giải nén cấu hình, toàn bộ tri thức đào tạo và skills vào đúng thư mục home
# - Tự động sửa đường dẫn cấu hình (nếu chạy dưới /root hoặc /home/<user>)
# - Nạp cấu hình Supervisor và kích hoạt các dịch vụ
# ==============================================================================

set -euo pipefail

TARBALL=""
TARGET_HOME="${HOME:-/root}"
INSTALL_DEPS="false"
ACTION="dry-run"

usage() {
    cat <<EOF
Sử dụng:
  $0 --tarball <path> [options]

Các tùy chọn:
  --tarball <path>      Đường dẫn file .tar.gz sạch cần khôi phục (bắt buộc)
  --target-home <path>  Thư mục người dùng trên VPS mới (mặc định: $TARGET_HOME)
  --install-deps        Tự động cài đặt các gói phụ thuộc hệ thống (Node, OpenClaw, Python...)
  --dry-run             Kiểm tra các bước mà không ghi đè dữ liệu
  --apply               Thực hiện giải nén và cấu hình thực tế
  -h, --help            Hiển thị trợ giúp này

Ví dụ:
  $0 --tarball /root/anhlaptrinhthu_clean_export_20260926.tar.gz --target-home /root --dry-run
  $0 --tarball /root/anhlaptrinhthu_clean_export_20260926.tar.gz --target-home /root --apply
EOF
    exit 1
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --tarball)
            TARBALL="$2"
            shift 2
            ;;
        --target-home)
            TARGET_HOME="$2"
            shift 2
            ;;
        --install-deps)
            INSTALL_DEPS="true"
            shift
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

if [[ -z "$TARBALL" || ! -f "$TARBALL" ]]; then
    echo "LỖI: File tarball không tồn tại: $TARBALL" >&2
    exit 1
fi

echo "======================================================================"
echo "KHÔI PHỤC TRỢ LÝ OPENCLAW TRÊN VPS MỚI"
echo "File nguồn:   $TARBALL"
echo "Thư mục đích: $TARGET_HOME"
echo "Cài đặt deps: $INSTALL_DEPS"
echo "Chế độ:       $ACTION"
echo "======================================================================"

if [[ "$ACTION" == "dry-run" ]]; then
    echo ""
    echo "[DRY-RUN] Kiểm tra nội dung file nén:"
    tar -tf "$TARBALL" | head -n 25 | sed 's/^/   + /'
    echo "   ... (và nhiều tệp khác)"
    echo ""
    echo "[DRY-RUN] Các thao tác sẽ thực hiện khi chạy --apply:"
    echo "   1. Giải nén vào $TARGET_HOME"
    echo "   2. Tự động đồng bộ đường dẫn cũ (/home/anhlaptrinh -> $TARGET_HOME) trong openclaw.json & supervisor"
    echo "   3. Cài file cấu hình vào /etc/supervisor/conf.d/"
    echo "   4. Cập nhật supervisorctl (reread, update)"
    if [[ "$INSTALL_DEPS" == "true" ]]; then
        echo "   5. Cài đặt các gói phụ thuộc (apt, node, npm, python deps)"
    fi
    echo ""
    echo "Chạy lại với cờ --apply để tiến hành khôi phục thực tế."
    exit 0
fi

# ==================== APPLY MODE ====================

if [[ "$INSTALL_DEPS" == "true" ]]; then
    echo "[1/4] Cài đặt các gói phụ thuộc hệ thống..."
    apt-get update -y
    apt-get install -y curl wget git ffmpeg libreoffice supervisor nginx xrdp xfce4 xfce4-goodies
    
    if ! command -v node >/dev/null 2>&1; then
        echo "Cài đặt Node.js 24..."
        curl -fsSL https://deb.nodesource.com/setup_24.x | bash -
        apt-get install -y nodejs
    fi
    
    if ! command -v openclaw >/dev/null 2>&1; then
        echo "Cài đặt OpenClaw 2026.9.5..."
        npm install -g openclaw@2026.9.5
    fi
    
    echo "Cài đặt thư viện Python..."
    pip install --break-system-packages rapidocr-onnxruntime onnxruntime opencv-python shapely pyclipper mutagen yt-dlp websockets requests certbot certbot-nginx || true
fi

echo "[2/4] Giải nén bản sao lưu vào thư mục tạm..."
TMP_DIR="/tmp/restore_clean_assistant_$$"
mkdir -p "$TMP_DIR"
tar -xzf "$TARBALL" -C "$TMP_DIR"

echo "[3/4] Đồng bộ tệp đào tạo, cấu hình và skills vào $TARGET_HOME..."
mkdir -p "$TARGET_HOME"
if [ -d "$TMP_DIR/home" ]; then
    cp -a "$TMP_DIR/home/"* "$TARGET_HOME/" 2>/dev/null || true
    cp -a "$TMP_DIR/home/".* "$TARGET_HOME/" 2>/dev/null || true
fi

# Đồng bộ đường dẫn nếu target_home khác /home/anhlaptrinh
if [[ "$TARGET_HOME" != "/home/anhlaptrinh" && -f "$TARGET_HOME/.openclaw/openclaw.json" ]]; then
    echo "   -> Chuẩn hóa đường dẫn trong openclaw.json: /home/anhlaptrinh -> $TARGET_HOME"
    sed -i "s|/home/anhlaptrinh|$TARGET_HOME|g" "$TARGET_HOME/.openclaw/openclaw.json"
fi

echo "[4/4] Khôi phục cấu hình Supervisor..."
mkdir -p /etc/supervisor/conf.d
if [ -d "$TMP_DIR/container_root/supervisor_conf" ]; then
    for conf in "$TMP_DIR/container_root/supervisor_conf/"*.conf; do
        if [ -f "$conf" ]; then
            dest_conf="/etc/supervisor/conf.d/$(basename "$conf")"
            cp -a "$conf" "$dest_conf"
            if [[ "$TARGET_HOME" != "/home/anhlaptrinh" ]]; then
                sed -i "s|/home/anhlaptrinh|$TARGET_HOME|g" "$dest_conf"
            fi
        fi
    done
fi

if [ -d "$TMP_DIR/container_root/Apps" ]; then
    mkdir -p /root/Apps
    cp -a "$TMP_DIR/container_root/Apps/"* /root/Apps/ 2>/dev/null || true
fi

rm -rf "$TMP_DIR"

echo "Cập nhật Supervisor..."
if command -v supervisorctl >/dev/null 2>&1; then
    supervisorctl reread || true
    supervisorctl update || true
    echo ""
    supervisorctl status || true
fi

echo "======================================================================"
echo "KHÔI PHỤC HOÀN TẤT!"
echo "1. Telegram Bot: Tự động kết nối ngay lập tức."
echo "2. Zalo Personal: Mở http://<IP_VPS>/openclaw-qr.png để quét QR kết nối."
echo "======================================================================"
