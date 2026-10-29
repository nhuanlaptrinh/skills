---
name: member-vps-manager-telegram
description: Vận hành bot Telegram quản trị Member VPS OpenClaw tại /root/Automation/telegram/member_vps_manager; dùng khi cần tạo member qua wizard, kiểm tra host, xem trạng thái, kiểm tra service, cập nhật bot hoặc xử lý job provision bị blocked.
---

# Member VPS Manager Telegram

## Chính sách model — 2026-10-29

- Chỉ dùng đúng ba model hội thoại/suy luận: `GPT-6.1-sol`, `GPT-6.1-terra`, `GPT-6-astra`. Mặc định khi cài mới hoặc không chỉ định model là `GPT-6.1-sol`.
- Primary, fallback và lựa chọn trong wizard chỉ lấy từ danh sách này; không tự dùng alias/model cũ hoặc bật DeepSeek dù môi trường có key. Giữ provider hiện có và ghép `<provider>/<model-id>` đúng case.
- Trước khi apply, xác minh model đích trong `/v1/models` của provider thực tế; nếu không có thì dừng, không tự đổi tên hay chọn model ngoài danh sách. Chỉ cấu hình hiểu ảnh khi đã kiểm tra backend hỗ trợ.
- Đây là chính sách chọn model, không phải quyền tự đổi runtime đang chạy. Không đổi model STT/TTS/tạo ảnh thành model chat; các tính năng media chuyên dụng giữ workflow và kiểm tra riêng.

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
7. Chọn endpoint và đúng một trong `GPT-6.1-sol`, `GPT-6.1-terra`, `GPT-6-astra`; mặc định cho lượt tạo mới là `GPT-6.1-sol`. Nếu wizard triển khai chưa có lựa chọn phù hợp, dừng và báo cần cập nhật bot riêng; không chọn model cũ hoặc tự sửa service/config production.
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

## Lỗi đã gặp / Checklist

- Sự cố `/zaloqr` ngày 26/10/2026: `package.json` phải dùng `pluginApi` range, không pin exact `2026.9.9`. Bundle hiện kiểm thử `>=2026.9.9 <=2026.10.6`; kiểm tra core thực tế trước khi nới giới hạn. Giữ plugin ID legacy, không đăng ký trùng tool/command.
- Parser receipt phải lấy từng dòng/khối JSON độc lập bằng `matchAll`, chịu được log thừa trước/sau (kể cả `[state/agent-db] ... clean-close receipt`); vẫn kiểm tra đúng owner/chat, `ok` và message ID. Timeout delivery `60000` ms; không parse toàn bộ phần stdout còn lại bằng `JSON.parse`.
- Khi CLI gửi ảnh đã exit 0 nhưng chỉ đọc receipt lỗi, giữ login sống đến khi hoàn tất/hết hạn (tối đa 180 giây), không để `finally` stop sớm. Báo delivery chưa xác minh (`qrSent: null`), không tự gửi lại hoặc báo giao ảnh/đăng nhập thành công.
- Trước cài: chạy `node --test scripts/test_receipt.mjs` và `python3 -B scripts/test_deploy.py` trong skill `telegram-zalo-owner-login` (offline, không tạo QR/gửi tin). Sau cài: `openclaw plugins list --json` và `openclaw plugins inspect <id> --runtime --json` phải thấy `loaded`, tool `telegram_zalo_login_qr` và command `zaloqr`; có config/doctor sạch không đủ chứng minh plugin load.
- Khi được phép apply runtime, backup từng file `<file>.bak-<timestamp>`, giữ watchdog lock đúng member rồi `openclaw plugins reload <id> --json`; `restartRequired=false` thì KHÔNG restart. Nếu `true` hoặc reload lỗi, dừng và hỏi owner, không tự restart gateway/container/service. Sửa kho skill/template không đồng nghĩa đã reload member; không chạy helper `--apply` có stop/start khi task cấm restart.
- Probe `zalouser` mỗi **30 phút**, lệch phút giữa member; không tự đổi cron production. Không logout, tạo/gửi QR hay gửi tin Telegram/Zalo trong lượt sửa/kiểm thử offline; live test chỉ khi owner yêu cầu riêng.
