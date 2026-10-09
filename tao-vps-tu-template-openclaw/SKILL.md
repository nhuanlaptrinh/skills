---
name: tao-vps-tu-template-openclaw
description: Bung và cấu hình nhanh VPS OpenClaw từ một template do người dùng cung cấp, cho VPS thành viên Docker hoặc VPS chính native; nhận tên, token Telegram, API key 9Router và group ID rồi cấp owner, DM allowlist và Full Exec group.
---

# Tạo VPS OpenClaw từ template

Dùng khi người dùng cung cấp đường dẫn tới một bộ template VPS OpenClaw và muốn triển khai nhanh cho VPS thành viên hoặc VPS chính.

## Thông tin cần nhận

- `template_path`: đường dẫn bộ template do người dùng cung cấp.
- `mode`: `docker` cho member VPS hoặc `native` cho VPS chính.
- `name`: tên user/member hoặc hostname.
- `telegram_token` và `nine_router_key`.
- `group_id` nếu cần bật quyền group; không tự suy đoán group ID.
- Tùy chọn `assistant_name`; mặc định `Trợ Lý Anh Hùng`.

Owner Telegram mặc định của bộ chuẩn là `8342048167` và `6980864856`. DM dùng allowlist đúng hai ID này. Khi có group ID, cấu hình `toolsBySender["*"]` của riêng group với `exec` và `process`, đồng thời bật Full Exec/auto-approval cho agent `main`.

## Quy trình

1. Đọc `/root/_Second_AI_Brain/START_HERE.md`, bản đồ VPS, project note liên quan và checklist production trước khi sửa.
2. Kiểm tra `template_path`, manifest, checksum, mode và các file cài đặt. Không dùng archive chứa token/key thật.
3. Với Docker, chạy `template_path/install.sh --mode docker` cùng `--name`, cổng, `--telegram-token`, `--nine-router-key`, `--group-id`. Với native, dùng installer native tương ứng và áp dụng cùng chính sách qua config của VPS chính.
4. Sau khi cài, chạy validate OpenClaw, kiểm tra owner/DM, group `exec`/`process`, approvals và gateway. Không tự gửi tin nhắn thử vào Telegram.
5. Chạy audio/health check nếu template có audio bootstrap.
6. Ghi nhật ký thay đổi nhưng không ghi token, API key, mật khẩu hoặc cookie.

## Ràng buộc

- Không hardcode secret vào template, Dockerfile, archive, README hoặc skill.
- Không mở quyền wildcard toàn cục; chỉ mở wildcard sender trong group ID được người dùng nêu rõ.
- Nếu thiếu group ID thì dừng phần group Full Exec và báo rõ; vẫn có thể cấu hình owner DM nếu đã đủ thông tin.
- Nếu yêu cầu Zalo, cần Zalo Personal ID riêng; không suy ra từ Telegram ID.
