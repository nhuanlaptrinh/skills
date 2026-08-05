# Project Map: Messenger Fanpage

## Source Project

Project tham chiếu chính:

```text
/root/Automation/facebook/01_Mess_Fanpage/01_mes_op_oplw
```

Đây là bot production nên chỉ đọc/copy có chọn lọc. Không đọc `.env` và không copy database/runtime artifacts.

## File Responsibilities

| File | Vai trò | Điểm phải đổi khi tạo bot mới |
|---|---|---|
| `app/settings.py` | Load environment và đường dẫn | App name, port, knowledge/history/DB, OpenClaw model, fallback |
| `app/main.py` | FastAPI routes và webhook flow | Giữ signature, dedupe, pause, history; đổi metadata riêng nếu có |
| `app/facebook.py` | Verify Meta signature và Send API | Giữ bảo mật; dùng token từ env; giữ bot metadata |
| `app/chatbot.py` | Prompt, OpenClaw và fallback | Thay toàn bộ tên chương trình, URL, nội dung và session prefix |
| `app/knowledge.py` | Nạp Markdown/TXT knowledge | Chỉ đọc đúng domain mới |
| `app/database.py` | SQLite state, event dedupe và pause | Tạo DB mới; giữ migration và pause fields |
| `app/customer_history.py` | Lưu hội thoại Markdown ẩn danh | Đổi history root; giữ hash PSID và role labels |
| `tests/test_core.py` | Unit tests | Đổi expected project/agent/URL và thêm regression cases |
| `.env.example` | Danh sách cấu hình | Chỉ placeholder, không secret |
| `deploy/*.service` | systemd template | WorkingDirectory, env files, port, unit name |
| `deploy/*.conf.example` | Nginx route | Public route và proxy port |
| `README.md` | Runbook project | Cập nhật toàn bộ path, service, URL và kiến trúc |

## Production Topology Observed

Trạng thái quan sát ngày 2026-08-03 UTC; luôn kiểm tra lại trước khi sửa:

| Thành phần | Port | Ghi chú |
|---|---:|---|
| Messenger Dispatcher | `8810` | Route theo `META_PAGE_ID` |
| ANVI bot | `8811` | systemd active |
| OPLW bot | `8812` | systemd active |
| ANCL bot | `8813` | systemd active |

Active Nginx trên `synalt.anhlaptrinh.vn` đang có topology hỗn hợp:

- `/messenger-anvi/webhook/facebook` proxy tới dispatcher `8810`.
- `/messenger-oplw/webhook/facebook` proxy trực tiếp tới OPLW `8812`.
- `/messenger-ancl/webhook/facebook` proxy trực tiếp tới ANCL `8813`.

Dispatcher hiện vẫn có route source cho ANVI, OPLW và ANCL, nên không được giả định chỉ có một kiểu webhook. Kiểm tra callback thật trong Meta Developer trước khi đổi Nginx hoặc dispatcher.

## Dispatcher Behavior

Source:

```text
/root/Automation/facebook/01_Mess_Fanpage/messenger_dispatcher/app.py
```

- Đọc `META_PAGE_ID` từ `.env` của từng bot khi service khởi động.
- Chọn target theo `entry.id`, sau đó `recipient.id`.
- Forward raw body và header chữ ký sang bot đích.
- Có một verify token được lấy từ route source đầu tiên có giá trị.
- Có `DEFAULT_TARGET`; không đổi mặc định nếu chưa đánh giá ảnh hưởng tới webhook không match Page ID.

## Required Safety Features

- Verify `X-Hub-Signature-256`, có thể hỗ trợ legacy signature nếu code hiện có cần.
- Deduplicate incoming message/event ID.
- Bot replies gắn metadata riêng để `message_echoes` không pause nhầm.
- Human/Page echo đặt timed pause, mặc định 60 phút.
- Admin permanent pause độc lập với timed pause.
- PSID được hash trước khi dùng làm OpenClaw session/user hoặc lưu Second Brain.
- History lưu theo ngày, role rõ ràng và không chứa PSID thật.
- AI failure chỉ gửi fallback message; không loop vô hạn.
- OpenClaw là agent riêng; fallback key đọc từ environment, không hardcode.

## Related Global Skills

- `/root/.agents/skills/messenger-oplw-fanpage/SKILL.md`
- `/root/.agents/skills/messenger-ancl-fanpage/SKILL.md`
- `/root/.agents/skills/messenger-anvi-fanpage/SKILL.md`
- `/root/.agents/skills/facebook-messenger-human-pause/SKILL.md`
- `/root/.agents/skills/messenger-customer-history-archive/SKILL.md`
- `/root/.agents/skills/validate-openclaw-json/SKILL.md`

