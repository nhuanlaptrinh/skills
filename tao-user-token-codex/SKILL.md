---
name: tao-user-token-codex
description: Tạo hoặc cập nhật tài khoản khách hàng và tự tạo API key trong Django Token Codex tại /root/Apps/9router_usage_dashboard từ email, với mật khẩu mặc định alt123 và hạn mức mặc định 250 USD. Use khi người dùng yêu cầu tạo user Token Codex/9Router Usage Dashboard, cấp credit ban đầu, tạo luôn API, kiểm tra trước bằng dry-run, hoặc cập nhật rõ ràng một tài khoản đã tồn tại.
---

# Tạo User Token Codex

## Khi Nào Dùng

Dùng skill này khi cần tạo tài khoản đăng nhập khách hàng cho dashboard Token Codex và tạo luôn một API key. Email được chuẩn hóa thành chữ thường và dùng cho cả `username` lẫn `email`.

Skill này là bước bắt buộc trước khi tạo member VPS bằng `tao-tro-ly-openclaw-member-vps`. Sau khi tạo, API key được nạp an toàn vào Custom Provider của member VPS; bàn giao cho khách email, mật khẩu và link `https://codex.anhlaptrinh.vn/` để xem credit còn lại, không gửi full API key.

## Project Và Dữ Liệu

- Project: `/root/Apps/9router_usage_dashboard`
- Command: `dashboard/management/commands/create_customer_account.py`
- Database được ghi: `/root/Apps/9router_usage_dashboard/db.sqlite3`
- Model: Django `User`, `CustomerAccount`, `ManagedApiKey` và `UserApiAccess`
- Mặc định: mật khẩu `alt123`, credit `250.0000` USD và 1 API mới
- API ngoài: gọi 9Router local để tạo key; không sửa trực tiếp SQLite nguồn
- Output: thông báo thành công và full API key đúng một lần; không in mật khẩu
- Sheet: không ghi

## Input

Bắt buộc có email hợp lệ. Có thể thêm tên, mật khẩu hoặc credit tùy chỉnh.

## Dry Run

Luôn chạy kiểm tra trước:

```bash
cd /root/Apps/9router_usage_dashboard
.venv/bin/python manage.py create_customer_account \
  --email 'user@example.com' \
  --dry-run
```

Dry-run chỉ xác thực input và cho biết thao tác dự kiến, không ghi database và không gọi API tạo key.

## Chạy Thật Với Mặc Định

Lệnh sau tạo user với mật khẩu mặc định `alt123`, credit mặc định `250` USD và một API key:

```bash
cd /root/Apps/9router_usage_dashboard
.venv/bin/python manage.py create_customer_account \
  --email 'user@example.com'
```

Có thể thêm tên bằng `--full-name 'Nguyễn Văn A'` hoặc đặt tên API bằng `--api-name 'Tên API'`. Nếu không truyền `--api-name`, tên API dùng tên khách hàng hoặc email.

Full API key chỉ xuất hiện một lần trên terminal. Chuyển ngay cho người nhận qua kênh an toàn; không ghi vào skill, tài liệu, nhật ký hoặc câu trả lời công khai.

## Tùy Chỉnh

```bash
.venv/bin/python manage.py create_customer_account \
  --email 'user@example.com' \
  --credit '300' \
  --password 'mat-khau-tam'
```

Mật khẩu phải có ít nhất 6 ký tự; credit không được âm. Không đưa mật khẩu riêng của khách vào tài liệu hoặc câu trả lời.

Nếu chỉ muốn tạo tài khoản mà không tạo API, thêm `--no-create-api`.

## Tài Khoản Đã Tồn Tại

Mặc định command từ chối ghi đè. Chỉ dùng `--update-existing` khi người dùng yêu cầu rõ ràng. Luôn dry-run trước:

```bash
.venv/bin/python manage.py create_customer_account \
  --email 'user@example.com' \
  --credit '250' \
  --update-existing \
  --dry-run
```

Sau khi kiểm tra, bỏ `--dry-run` để chạy thật. Cờ này cập nhật email chuẩn hóa, tên, trạng thái active, mật khẩu và credit. Nếu user đã có API đang hoạt động, command không tạo thêm key.

## Kiểm Tra

```bash
.venv/bin/python manage.py shell -c "from django.contrib.auth import get_user_model; u=get_user_model().objects.get(username='user@example.com'); print(u.username, u.is_active, u.customer_account.credit_limit)"
```

```bash
.venv/bin/python manage.py test dashboard.tests.CreateCustomerAccountCommandTests -v 1
```

Không hiển thị password hash hoặc dữ liệu nhạy cảm.

## Rerun Và Khôi Phục

- Nếu tạo mới thất bại, sửa input rồi chạy lại; transaction bảo đảm không tạo nửa chừng.
- Nếu email đã tồn tại, không dùng `--update-existing` trừ khi được yêu cầu cập nhật.
- Nếu nhập sai credit, dry-run rồi cập nhật lại với credit đúng.
- Nếu tạo API ngoài thành công nhưng lưu Django thất bại, command cố gắng thu hồi API vừa tạo.
- Nếu user đã có API active, command giữ nguyên và không tạo key trùng.

## An Toàn

- Không in hoặc lưu mật khẩu riêng, API key, token, cookie hay nội dung `.env`.
- Không sửa `/root/.9router/db/data.sqlite`, WAL/SHM hoặc credential 9Router.
- Không tự động dùng `--update-existing`.
- Không chụp màn hình hoặc ghi log chứa full API key.
- Không dùng email thật trong test tự động.
- Khi phục vụ member VPS, lưu output một lần vào `/root/Data/private_accounts/token_codex/` với quyền `600`, rồi truyền key qua `CUSTOM_PROVIDER_API_KEY`.
- Bàn giao email, mật khẩu đăng nhập và link dashboard cho đúng khách hàng; không đưa full API key vào chat.
- Khi đổi command, input/output hoặc default, cập nhật skill này, skill `9router-usage-dashboard`, project note và nhật ký VPS.
