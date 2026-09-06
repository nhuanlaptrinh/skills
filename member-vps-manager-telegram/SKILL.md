---
name: member-vps-manager-telegram
description: Vận hành bot Telegram quản trị Member VPS OpenClaw tại /root/Automation/telegram/member_vps_manager; dùng khi cần tạo member qua wizard, kiểm tra host, xem trạng thái, kiểm tra service, cập nhật bot hoặc xử lý job provision bị blocked.
---

# Member VPS Manager Telegram

## Project và service

- Project: `/root/Automation/telegram/member_vps_manager`.
- Bot script: `/root/Automation/telegram/member_vps_manager/bot.py`.
- Update helper: `/root/Automation/telegram/member_vps_manager/member_update.py`.
- Config không chứa secret: `/root/Automation/telegram/member_vps_manager/config.json`.
- Service: `member-vps-manager.service`.
- Manager token: `/root/private/member-vps-manager-telegram.token`, mode `600`.
- Factory được gọi: `/root/Apps/member_vps_factory/bin/member-vps-factory`.

## Khi dùng

Dùng skill khi người quản trị muốn tạo hoặc kiểm tra Member VPS qua Telegram.
Bot chỉ nhận private chat từ admin IDs trong `config.json`, không nhận lệnh
shell tùy ý và không hỗ trợ group quản trị.

## Dry-run/check

```bash
python3 -m py_compile /root/Automation/telegram/member_vps_manager/bot.py
python3 /root/Apps/member_vps_factory/bin/member-vps-factory doctor --target local
systemctl status member-vps-manager.service --no-pager
journalctl -u member-vps-manager.service -n 80 --no-pager
```

Không gửi Telegram test thật khi chỉ kiểm tra service. `getMe`/`getWebhookInfo`
có thể gọi read-only bằng token file nếu cần xác minh bot.

## Chạy qua Telegram

1. Nhắn `/vps` cho bot manager trong private chat.
2. Chọn `Tạo VPS thành viên`.
3. Nhập tên lowercase và tên hiển thị trợ lý.
4. Chọn `openclaw-standard`.
5. Nhập owner Telegram ID đã xác minh.
6. Chọn group, group ID và chế độ mention.
7. Chọn endpoint và model.
8. Gửi API key Codex; bot xóa message sau khi đọc.
9. Gửi token BotFather của member; bot xóa message sau khi đọc.
10. Bấm `Xác nhận tạo`.
11. Nhận job status, SSH/web port, thông số và mật khẩu bootstrap một lần.

Lệnh xem trạng thái:

```text
/vps
/vps status <member_name>
/vps info <member_name>
/vps update <member_name>
/vps host
/help
```

Danh sách và tải package trợ lý:

```text
/vps packages
/vps package <package-id>
```

Nút package trong menu gửi document trực tiếp, không yêu cầu gõ lại lệnh.
Archive được tạo tạm dưới `/root/private`, kiểm tra đường dẫn cấm trước khi
gửi và luôn xóa sau thao tác (kể cả khi Telegram trả lỗi). Package chỉ chứa
template sạch cùng `package-selection.json`; không chứa token, API key, state,
log hoặc credential.

## Input/output

Input gồm member name, profile, display name, owner ID, group ID tùy chọn,
mention policy, provider endpoint/model, API key và Telegram bot token. API key
và bot token chỉ nằm trong memory/job staging mode `600`; không ghi database,
log hoặc trả lại trong chat.

Output gồm job ID, trạng thái provision, container name, SSH/web port và các
healthcheck. `/vps info` thêm image, version, resource, ports, mount path,
OpenClaw/Gateway/config/Telegram probe, profile/model/provider và disk nhưng
chỉ báo credential present/missing. Token manager, provider key, Gateway token và secret staging
không được in vào log. Mật khẩu bootstrap chỉ tồn tại trong memory/staging
mode `600` trong job và được xóa sau đó.

## Cấu hình provider

`config.json` chỉ giữ endpoint và model mặc định. Mỗi job nhận API key riêng từ
Telegram, ghi tạm file mode `600`, rồi xóa sau khi chạy. Không đưa giá trị key
vào skill, log, commit hoặc câu trả lời.

## Update và rollback

- Sửa bot/config/unit thì chạy compile, restart service và đọc journal.
- Cập nhật Factory dùng `member-vps-factory` và dry-run trước; member cũ không
  tự thay đổi.
- `/vps update <member_name>` hỗ trợ cập nhật provider endpoint/key/model,
  Telegram bot token, group/mention, thêm Owner ID và tên trợ lý; có bước xác nhận,
  helper backup trước, validate
  config rồi restart đúng Gateway. Nếu validate lỗi, helper rollback file đã đổi.
- Không chạy lại `create` với tên member đã tồn tại.
- Không xóa SQLite state, container hoặc volume khi job lỗi.
- Nếu token manager đã lộ, tạo token mới bằng BotFather, ghi đè file mode `600`,
  rồi restart service; không ghi token mới vào tài liệu.
