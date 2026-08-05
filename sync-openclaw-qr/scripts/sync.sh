#!/bin/bash

# Script đồng bộ QR Code của OpenClaw sang thư mục Nginx Web phục vụ quét mã từ xa.
# Sử dụng: ./sync.sh [source_path] [dest_path] [interval_seconds]

SOURCE_PATH=${1:-"/tmp/openclaw/openclaw-zalouser-qr-default.png"}
DEST_PATH=${2:-"/var/www/html/openclaw-qr.png"}
INTERVAL=${3:-1}

echo "=== Tiến trình đồng bộ QR OpenClaw đã bắt đầu ==="
echo "Nguồn: $SOURCE_PATH"
echo "Đích:  $DEST_PATH"
echo "Chu kỳ: $INTERVAL giây"
echo "Nhấn Ctrl+C để dừng."

# Tạo thư mục chứa file đích nếu chưa tồn tại
DEST_DIR=$(dirname "$DEST_PATH")
if [ ! -d "$DEST_DIR" ]; then
    mkdir -p "$DEST_DIR"
fi

# Xử lý tín hiệu dừng (SIGINT / SIGTERM)
cleanup() {
    echo -e "\n=== Đã dừng tiến trình đồng bộ QR. ==="
    exit 0
}
trap cleanup SIGINT SIGTERM

# Vòng lặp đồng bộ
while true; do
    if [ -f "$SOURCE_PATH" ]; then
        # Copy file và set quyền đọc cho Nginx (644)
        cp -f "$SOURCE_PATH" "$DEST_PATH" 2>/dev/null
        chmod 644 "$DEST_PATH" 2>/dev/null
    fi
    sleep "$INTERVAL"
done
