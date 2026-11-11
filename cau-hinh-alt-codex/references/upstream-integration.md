# Upstream Integration

Nguồn tham chiếu: `https://github.com/nhuanlaptrinh/cau-hinh-alt-codex_new`

## Đã dùng

- Danh sách model và quy tắc chuẩn hóa model.
- Mẫu provider ALT/9Router và `wire_api = "responses"`.
- Script `scripts/set_alt_model.sh` cho backup, cập nhật model Codex/OpenClaw, validate và restart gateway.

## Cố ý không dùng

- Do not copy upstream or cross-machine `auth.json`; extract only a user-authorized local API key.
- Không để credential trong thư mục skill.
- Không dùng `.codex` mặc định làm kho credential chung cho nhiều khách.
- Không sửa browser cookie hoặc ChatGPT profile của khách.

## Lý do

Thư mục cài đặt extension có thể bị thay thế khi update. Credential và cấu hình runtime phải nằm ở persistent root bên ngoài extension, được chọn bằng `CODEX_HOME` theo từng `profile_id`. Browser profile ChatGPT cũng phải tách riêng nếu khách đã đăng nhập trước khi cài Antigravity.

## Quy tắc cập nhật upstream

Khi đồng bộ lại repository upstream:

1. Đọc thay đổi trong `SKILL.md` và script model.
2. Never copy entire `auth.json`, `.env`, tokens, cookies, or credential backups; reuse only user-authorized local API keys.
3. Giữ nguyên các quy tắc cô lập trong skill này.
4. Chạy validator của skill và kiểm tra script profile bằng một `ProfileId` tạm không chứa secret.