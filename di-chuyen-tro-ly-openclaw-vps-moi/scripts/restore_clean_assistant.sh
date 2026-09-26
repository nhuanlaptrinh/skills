#!/usr/bin/env bash
# ==============================================================================
# restore_clean_assistant.sh
# Khôi phục và thiết lập Trợ lý OpenClaw sạch trên VPS mới:
# - Giải nén cấu hình, toàn bộ tri thức đào tạo và skills vào đúng thư mục home
# - Tự động phát hiện OpenClaw đã có sẵn hay chưa, chỉ cài các gói còn thiếu
# - Tự động sửa đường dẫn cấu hình (nếu chạy dưới /root hoặc /home/<user>)
# - Khởi động lại OpenClaw Gateway
# ==============================================================================

set -euo pipefail

TARBALL=""
TARGET_HOME="${HOME:-/root}"
INSTALL_MISSING_DEPS="true"
ACTION="dry-run"

usage() {
    cat <<EOF
Sử dụng:
  $0 --tarball <path> [options]

Các tùy chọn:
  --tarball <path>      Đường dẫn file .tar.gz sạch cần khôi phục (bắt buộc)
  --target-home <path>  Thư mục người dùng trên VPS mới (mặc định: $TARGET_HOME)
  --skip-deps           Bỏ qua bước kiểm tra và cài đặt công cụ phụ trợ còn thiếu
  --dry-run             Kiểm tra các bước mà không ghi đè dữ liệu
  --apply               Thực hiện giải nén và cấu hình thực tế
  -h, --help            Hiển thị trợ giúp này

Ví dụ:
  # Kiểm tra trước:
  $0 --tarball /root/anhlaptrinhthu_clean_export_20260926.tar.gz --target-home /root --dry-run

  # Áp dụng khôi phục thật (tự bổ sung gói còn thiếu):
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
        --skip-deps)
            INSTALL_MISSING_DEPS="false"
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
echo "File nguồn:          $TARBALL"
echo "Thư mục đích:        $TARGET_HOME"
echo "Cài gói còn thiếu:   $INSTALL_MISSING_DEPS"
echo "Chế độ:              $ACTION"
echo "======================================================================"

if [[ "$ACTION" == "dry-run" ]]; then
    echo ""
    echo "[DRY-RUN] Kiểm tra nội dung file nén:"
    tar -tf "$TARBALL" | head -n 25 | sed 's/^/   + /'
    echo "   ... (và nhiều tệp khác)"
    echo ""
    echo "[DRY-RUN] Các bước sẽ thực hiện khi chạy --apply:"
    echo "   1. Giải nén toàn bộ phần đào tạo, skills, scripts vào $TARGET_HOME"
    echo "   2. Tự động đồng bộ đường dẫn cũ (/home/anhlaptrinh -> $TARGET_HOME) trong openclaw.json & supervisor"
    if [[ "$INSTALL_MISSING_DEPS" == "true" ]]; then
        echo "   3. Kiểm tra và chỉ cài đặt các gói còn thiếu (ffmpeg, libreoffice, rapidocr, mutagen, yt-dlp)"
    fi
    echo "   4. Nạp cấu hình Supervisor và khởi động lại OpenClaw Gateway"
    echo ""
    echo "Chạy lại với cờ --apply để tiến hành khôi phục thực tế."
    exit 0
fi

# ==================== APPLY MODE ====================

if [[ "$INSTALL_MISSING_DEPS" == "true" ]]; then
    echo "[1/4] Kiểm tra các công cụ hệ thống và cài đặt những gì còn thiếu..."
    MISSING_PKGS=()
    command -v ffmpeg >/dev/null 2>&1 || MISSING_PKGS+=("ffmpeg")
    command -v libreoffice >/dev/null 2>&1 || MISSING_PKGS+=("libreoffice")

    if [ ${#MISSING_PKGS[@]} -gt 0 ]; then
        echo "   -> Đang cài đặt công cụ hệ thống còn thiếu: ${MISSING_PKGS[*]}"
        apt-get update -y
        apt-get install -y "${MISSING_PKGS[@]}"
    else
        echo "   -> Đã có sẵn: ffmpeg, libreoffice."
    fi

    echo "   -> Cài đặt/kiểm tra các thư viện Python (OCR, Audio, Media)..."
    pip install --break-system-packages rapidocr-onnxruntime onnxruntime opencv-python mutagen yt-dlp || \
    pip install rapidocr-onnxruntime onnxruntime opencv-python mutagen yt-dlp || true
fi

echo "[2/4] Giải nén bản sao lưu sạch vào thư mục tạm..."
TMP_DIR="/tmp/restore_clean_assistant_$$"
mkdir -p "$TMP_DIR"
tar -xzf "$TARBALL" -C "$TMP_DIR"

echo "[3/4] Đưa dữ liệu đào tạo, skills, cấu hình vào $TARGET_HOME..."
mkdir -p "$TARGET_HOME"
if [ -d "$TMP_DIR/home" ]; then
    cp -a "$TMP_DIR/home/"* "$TARGET_HOME/" 2>/dev/null || true
    cp -a "$TMP_DIR/home/".* "$TARGET_HOME/" 2>/dev/null || true
fi

# Chuẩn hóa đường dẫn nếu target_home khác /home/anhlaptrinh
if [[ "$TARGET_HOME" != "/home/anhlaptrinh" && -f "$TARGET_HOME/.openclaw/openclaw.json" ]]; then
    echo "   -> Chuẩn hóa đường dẫn trong openclaw.json: /home/anhlaptrinh -> $TARGET_HOME"
    sed -i "s|/home/anhlaptrinh|$TARGET_HOME|g" "$TARGET_HOME/.openclaw/openclaw.json"
fi

echo "[4/4] Khôi phục cấu hình dịch vụ..."
if [ -d "$TMP_DIR/container_root/supervisor_conf" ]; then
    mkdir -p /etc/supervisor/conf.d
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

# Khởi động lại dịch vụ
if command -v supervisorctl >/dev/null 2>&1; then
    echo "Cập nhật Supervisor..."
    supervisorctl reread || true
    supervisorctl update || true
    supervisorctl restart openclaw-gateway 2>/dev/null || true
    echo ""
    supervisorctl status || true
elif command -v openclaw >/dev/null 2>&1; then
    echo "Khởi động lại OpenClaw Gateway..."
    openclaw gateway restart || openclaw gateway run --daemon || true
fi

echo "======================================================================"
echo "KHÔI PHỤC HOÀN TẤT!"
echo "1. Telegram Bot: Tự động kết nối ngay lập tức với đầy đủ trí tuệ Nhi Biết Tuốt."
echo "2. Zalo Personal: Mở http://<IP_VPS>/openclaw-qr.png hoặc chạy 'openclaw channels login zalouser' để quét mã QR."
echo "======================================================================"
