---
name: openclaw-qr-sync
description: Tự động đồng bộ mã QR đăng nhập của OpenClaw (tạo ra khi chạy openclaw onboard) sang thư mục web công khai để hiển thị trên trình duyệt. Thích hợp dùng trên các VPS chạy headless để người dùng dễ dàng quét mã từ xa qua link web thay vì tìm file trong thư mục tạm.
---

# Skill Đồng Bộ QR Code OpenClaw Cho VPS

Skill này giúp tự động hóa quá trình đưa ảnh QR đăng nhập Zalo/Weixin (zca-js) của OpenClaw từ thư mục tạm hệ thống (`/tmp/openclaw/`) ra thư mục web công khai của Nginx để người dùng có thể quét từ xa qua trình duyệt web.

## 📋 Yêu cầu hệ thống
- Hệ điều hành: Linux/Ubuntu.
- Đã cài đặt Nginx phục vụ tên miền (ví dụ: `synalt.anhlaptrinh.vn`).
- Đã cấu hình Nginx map một URL ảnh tới thư mục Web (ví dụ: `/var/www/html/openclaw-qr.png`).

### Cấu hình Nginx tham khảo:
Thêm block sau vào file cấu hình nginx của domain:
```nginx
location = /openclaw-qr.png {
    auth_basic off;
    alias /var/www/html/openclaw-qr.png;
    etag off;
    expires -1;
    add_header Cache-Control "no-store, no-cache, must-revalidate, max-age=0" always;
    add_header Pragma "no-cache" always;
}
```

## 🛠 Hướng dẫn vận hành

### Bước 1: Phân quyền cho script
Đảm bảo script có quyền thực thi:
```bash
chmod +x .agents/skills/openclaw-qr-sync/scripts/sync_qr.sh
```

### Bước 2: Chạy tiến trình đồng bộ ngầm
Khởi chạy script đồng bộ ngầm trước khi bắt đầu chạy `openclaw onboard`.

- **Chạy trực tiếp trong terminal:**
  ```bash
  .agents/skills/openclaw-qr-sync/scripts/sync_qr.sh
  ```
- **Chạy ngầm (background) và lưu log:**
  ```bash
  nohup .agents/skills/openclaw-qr-sync/scripts/sync_qr.sh > /dev/null 2>&1 &
  ```
- **Chạy với các đường dẫn tùy chỉnh:**
  ```bash
  .agents/skills/openclaw-qr-sync/scripts/sync_qr.sh [đường_dẫn_nguồn] [đường_dẫn_đích]
  # Ví dụ:
  .agents/skills/openclaw-qr-sync/scripts/sync_qr.sh /tmp/openclaw/openclaw-zalouser-qr-default.png /var/www/html/openclaw-qr.png
  ```

### Bước 3: Thực hiện Onboard và quét QR
1. Chạy lệnh `openclaw onboard` trên terminal.
2. Truy cập vào URL web của bạn (ví dụ: `https://your-domain.com/openclaw-qr.png`).
3. Nhấn **F5** để tải mã QR mới nhất và quét bằng điện thoại.
4. Sau khi đăng nhập thành công, bạn có thể tắt tiến trình đồng bộ ngầm bằng cách tìm PID và kill nó:
   ```bash
   pkill -f sync_qr.sh
   ```
