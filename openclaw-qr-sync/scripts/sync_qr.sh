#!/bin/bash
# Script tự động đồng bộ mã QR OpenClaw sang thư mục Web Nginx
# Sử dụng: ./sync_qr.sh [đường_dẫn_nguồn] [đường_dẫn_đích]

SRC_FILE=${1:-"/tmp/openclaw/openclaw-zalouser-qr-default.png"}
DEST_FILE=${2:-"/var/www/html/openclaw-qr.png"}

echo "=================================================="
echo "Bắt đầu đồng bộ QR OpenClaw..."
echo "Nguồn (Source): $SRC_FILE"
echo "Đích (Destination): $DEST_FILE"
echo "Tần suất: 1 giây / lần"
echo "Nhấn Ctrl+C để dừng."
echo "=================================================="

# Tạo thư mục đích nếu chưa có
DEST_DIR=$(dirname "$DEST_FILE")
mkdir -p "$DEST_DIR"

# Vòng lặp đồng bộ liên tục
while true; do
    if [ -f "$SRC_FILE" ]; then
        cp -f "$SRC_FILE" "$DEST_FILE" 2>/dev/null
        # Cấp quyền đọc công khai để Nginx/Web Server truy cập được
        chmod 644 "$DEST_FILE" 2>/dev/null
    fi
    sleep 1
done
