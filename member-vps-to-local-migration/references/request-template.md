# Mẫu thông tin yêu cầu chuyển Member VPS → Local

Copy mẫu dưới đây, điền các mục cần thiết, nhưng **không điền token, API key,
mật khẩu, cookie hoặc private key vào chat**. Hãy ghi “sẽ nạp qua file secret
local” ở các mục bí mật.

```text
Tên member:
Container VPS: user-<member>
IP VPS:
Cổng SSH member:

Máy local đích: Windows / macOS / Linux
Phiên bản OpenClaw local (nếu đã cài):
Đường dẫn workspace local (nếu có):
Local luôn bật 24/7: Có / Không

Chế độ chuyển:
- operational (khuyến nghị: bỏ chat/session cũ)
- full-state (giữ session cũ, cần cùng phiên bản OpenClaw)

Telegram account ID cần giữ: <member>
Telegram owner IDs:
Telegram group IDs:
Assistant name:
Có cần trả lời group không mention: Có / Không
BotFather Privacy Mode đã tắt: Có / Chưa biết

Provider/model cần giữ:
Secret sẽ nạp qua file local: Có
Skills/app đặc biệt cần giữ:
Zalo hoặc channel khác cần chuyển: Có / Không

Thời điểm dự kiến cutover:
Thời gian giữ VPS cũ để rollback:
Xác nhận cho phép dừng Gateway member trên VPS: Có
Xác nhận không chạy bot đồng thời VPS/local: Có
```

## Prompt dùng với Codex

```text
Dùng skill $member-vps-to-local-migration để chuyển member OpenClaw sau:

Tên member: <điền>
Container VPS: user-<điền>
IP VPS: <điền>
Cổng SSH member: <điền>
Máy local đích: <Windows/macOS/Linux>
Chế độ: <operational/full-state>
Telegram account ID: <điền>
Owner IDs: <điền>
Group IDs: <điền>
Tên trợ lý: <điền>
Workspace/skills đặc biệt cần giữ: <điền hoặc không>
Thời gian cutover: <điền>

Secret sẽ được nạp qua file quyền riêng, không đưa vào prompt.
Hãy dry-run trước, backup source, dừng đúng Gateway member, tạo bundle,
hướng dẫn/kiểm tra local, rồi chỉ start local sau khi VPS đã dừng. Không sửa
VPS chính hoặc các member khác. Không xóa VPS cũ; báo rõ rollback và các bước
chờ em/xác nhận nếu thiếu thông tin.
```
