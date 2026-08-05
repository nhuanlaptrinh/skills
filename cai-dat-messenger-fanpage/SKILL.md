---
name: cai-dat-messenger-fanpage
description: Thiết lập, nhân bản, kiểm tra hoặc sửa bot tự động trả lời Facebook Messenger Fanpage trên VPS dựa trên kiến trúc FastAPI, SQLite, OpenClaw, systemd, Nginx và dispatcher của `/root/Automation/facebook/01_Mess_Fanpage/01_mes_op_oplw`. Use when Codex/OpenClaw cần tạo bot cho Fanpage mới, nối Meta webhook, tạo agent AI riêng, cấu hình auto-pause khi nhân viên tiếp quản, lưu lịch sử hội thoại, triển khai service hoặc chuẩn hóa một project Messenger tương tự OPLW/ANCL/ANVI.
---

# Cài Đặt Messenger Fanpage

## Mục Tiêu

Dựng một bot tự động trả lời Messenger Fanpage mới theo mẫu production đang dùng, nhưng không sao chép nhầm secret, dữ liệu khách hàng, database, prompt, URL hoặc kiến thức của OPLW sang Fanpage mới.

Kiến trúc chuẩn:

```text
Meta Messenger webhook
  -> Nginx public callback
  -> bot FastAPI riêng hoặc Messenger Dispatcher
  -> kiểm tra chữ ký + chống event trùng
  -> kiểm tra permanent pause + human takeover pause
  -> đọc knowledge riêng của chương trình
  -> OpenClaw agent riêng
  -> fallback provider khi được cấu hình
  -> Meta Send API
  -> SQLite + Markdown history ẩn danh
```

## Khi Nào Dùng

- Tạo bot Messenger cho một Fanpage/chương trình mới.
- Nhân bản kiến trúc OPLW sang khóa học hoặc thương hiệu khác.
- Cấu hình Meta webhook, Page ID, systemd, Nginx hoặc dispatcher.
- Tạo OpenClaw agent/workspace riêng cho Fanpage.
- Kiểm tra bot mới trước khi bật trả lời thật.
- Sửa một bot mới tạo nhưng chưa đạt chuẩn auto-pause, lưu lịch sử hoặc bảo mật secret.

Nếu chỉ vận hành bot đã có, ưu tiên skill chuyên biệt như `messenger-oplw-fanpage`, `messenger-ancl-fanpage` hoặc `messenger-anvi-fanpage`. Nếu chỉ sửa auto-pause hoặc lịch sử, đọc thêm `facebook-messenger-human-pause` và `messenger-customer-history-archive`.

## Quy Tắc An Toàn

- Đọc các tài liệu bắt buộc trong `/root/_Second_AI_Brain` và `AGENTS.md` áp dụng trước khi sửa.
- Không in, ghi vào skill, commit hoặc trả lời bằng giá trị thật từ `.env`, Meta token, App Secret, Page Access Token, admin key, gateway token, API key, cookie hoặc credential.
- Không đọc hoặc sao chép project `.env` nguồn. Chỉ dùng `.env.example` và tên biến.
- Không sao chép `data/conversations.db*`, `__pycache__`, log, lịch sử khách hàng hoặc file runtime từ project mẫu.
- Không gửi tin Messenger thật nếu người dùng chưa yêu cầu rõ. Mặc định chỉ test unit, health, webhook giả lập và AI smoke test không gọi Meta Send API.
- Không restart production service, Nginx, dispatcher hoặc OpenClaw gateway trước khi backup file liên quan vào `/root/_Backups` và validation đạt.
- Không tắt kiểm tra chữ ký webhook, chống event trùng, bot echo metadata, human takeover auto-pause hoặc ẩn danh lịch sử.
- Không tự đổi `DEFAULT_TARGET` của dispatcher hoặc callback đang dùng cho Fanpage khác.
- Không hardcode phiên bản Meta Graph API theo trí nhớ. Đọc `META_GRAPH_VERSION` của project và xác nhận phiên bản còn được hỗ trợ tại thời điểm triển khai.
- Không bật service khi Page ID, token và App Secret chưa được xác nhận thuộc đúng Fanpage/Meta App.

## Nguồn Tham Chiếu

Project mẫu chính:

```text
/root/Automation/facebook/01_Mess_Fanpage/01_mes_op_oplw
```

Đọc `references/project-map.md` để biết vai trò từng file và topology production đã quan sát. Đọc `references/meta-checklist.md` trước khi cấu hình Meta Developer.

## Input Bắt Buộc

Xác định các giá trị sau trước khi áp dụng production:

- `CODE`: mã ngắn viết thường, ví dụ `dvtl`.
- Tên project: mặc định `01_mes_op_<code>`.
- Port localhost riêng, không trùng service đang chạy.
- Knowledge root và customer history root riêng.
- Website/landing page chính xác để bot gửi cho khách.
- Meta Page ID, App ID, App Secret, Page Access Token và Verify Token; người vận hành nhập trực tiếp vào `.env`, không dán vào chat.
- Chế độ webhook: `direct` hoặc `dispatcher`.
- OpenClaw agent ID, workspace và model đã được phê duyệt.
- Nguồn fallback provider nếu cần; không sao chép key vào code.

## Output Chuẩn

- Project mới trong `/root/Automation/facebook/01_Mess_Fanpage/01_mes_op_<code>`.
- `.env.example` không có secret thật và `.env` mode `600` do người vận hành điền.
- SQLite mới, không chứa hội thoại của project mẫu.
- OpenClaw workspace/agent riêng, không dùng chung session với Fanpage khác.
- Unit systemd riêng và port localhost riêng.
- Public callback URL qua Nginx hoặc route trong dispatcher.
- Unit tests, health check, webhook verification và AI smoke test đạt.
- Project-specific global skill `messenger-<code>-fanpage`.
- Registry/project note và `/root/_Second_AI_Brain/06_Nhat_Ky_Thay_Doi.md` được cập nhật.

## 1. Preflight Chỉ Đọc

Chạy script đi kèm trước khi tạo project:

```bash
python3 /root/.agents/skills/cai-dat-messenger-fanpage/scripts/preflight_fanpage_setup.py \
  --code dvtl \
  --port 8814 \
  --knowledge-root /root/Data/second_brain/Second_Brain/01_chuong_trinh_dao_tao/35_domain_dvtl \
  --mode direct
```

Nếu dùng dispatcher chung:

```bash
python3 /root/.agents/skills/cai-dat-messenger-fanpage/scripts/preflight_fanpage_setup.py \
  --code dvtl \
  --port 8814 \
  --knowledge-root /root/Data/second_brain/Second_Brain/01_chuong_trinh_dao_tao/35_domain_dvtl \
  --mode dispatcher \
  --public-route /messenger-anvi/webhook/facebook
```

Script chỉ đọc, không tạo file, không đọc `.env`, không restart service và không gọi mạng. Xử lý mọi `CONFLICT` trước khi đi tiếp.

## 2. Chọn Kiểu Webhook

### Direct

Dùng khi Fanpage có callback riêng hoặc Meta App riêng:

```text
https://<domain>/messenger-<code>/webhook/facebook
  -> http://127.0.0.1:<port>/webhook/facebook
```

Tạo Nginx `location =` riêng. Đây là cách dễ cô lập và dễ rollback nhất.

### Dispatcher

Dùng khi nhiều Page cùng chia sẻ một callback Meta App:

```text
public callback -> 127.0.0.1:8810 -> route theo META_PAGE_ID -> bot riêng
```

Khi dùng chế độ này:

- Backup `messenger_dispatcher/app.py` và unit nếu sửa.
- Thêm đúng một source `.env` và target localhost vào `ROUTE_SOURCES`.
- Không đổi route hoặc default target đang có.
- Các Page đi qua cùng callback phải tương thích với cơ chế verify token duy nhất của dispatcher hiện tại.
- Restart dispatcher sau khi Page ID đã được nhập vào `.env`; dispatcher chỉ load route khi service khởi động.

## 3. Tạo Project Từ Mẫu

Backup mọi target/config có sẵn trước. Chỉ copy source code và tài liệu an toàn:

```bash
SOURCE=/root/Automation/facebook/01_Mess_Fanpage/01_mes_op_oplw
TARGET=/root/Automation/facebook/01_Mess_Fanpage/01_mes_op_dvtl

mkdir -p "$TARGET"
rsync -a \
  --exclude '.env' \
  --exclude 'data/conversations.db*' \
  --exclude '__pycache__' \
  --exclude '*.pyc' \
  "$SOURCE/" "$TARGET/"
mkdir -p "$TARGET/data"
```

Không chạy lệnh copy nếu target đã tồn tại. Với target đã có, audit và sửa từng file thay vì ghi đè.

Sau khi copy, tìm toàn bộ dấu vết của project mẫu:

```bash
rg -n 'OPLW|oplw|8812|03_domain_oplw|messenger-oplw|01_mes_op_oplw' "$TARGET" \
  --glob '!.env' --glob '!data/**'
```

Không được deploy khi kết quả còn chuỗi OPLW ngoài những đoạn cố ý ghi nguồn tham chiếu.

## 4. Chuyển Project Sang Fanpage Mới

Cập nhật tối thiểu:

- `app/settings.py`: `APP_NAME`, port, knowledge root, history root, database path, OpenClaw model/agent và fallback.
- `app/chatbot.py`: system prompt, tên chương trình, học phí, URL, phạm vi trả lời, session prefix và fallback behavior.
- `app/main.py`: app name/health metadata nếu có; giữ nguyên signature validation, dedupe, pause và history flow.
- `app/facebook.py`: giữ Meta signature validation, message splitting và bot reply metadata.
- `app/knowledge.py`: chỉ đọc đúng source dữ liệu mới; không fallback sang OPLW.
- `tests/test_core.py`: đổi fixture, expected URL, agent ID và project-specific assertions.
- `README.md`, `.env.example`, service template và Nginx template.

Giữ nguyên các chuẩn bắt buộc:

- SHA-256 PSID trước khi dùng làm OpenClaw session key.
- `BOT_REPLY_METADATA` riêng cho project để bỏ qua bot echo.
- `META_APP_ID` để phân biệt echo do bot gửi khi Meta cung cấp `app_id`.
- `HUMAN_PAUSE_MINUTES=60` mặc định.
- Permanent admin pause và timed human pause là hai trạng thái độc lập.
- Lưu role `customer`, `assistant`, `human` với mã khách ẩn danh; không ghi PSID thật vào Second Brain.
- Chống xử lý lại `mid`/event đã nhận.

## 5. Tạo Cấu Hình Môi Trường

`.env.example` chỉ chứa placeholder. Tạo `.env` trống với quyền hạn chế rồi để người vận hành nhập secret trực tiếp:

```bash
install -m 600 /dev/null /root/Automation/facebook/01_Mess_Fanpage/01_mes_op_dvtl/.env
```

Các biến chuẩn:

```text
HOST
PORT
KNOWLEDGE_ROOT
CUSTOMER_HISTORY_ROOT
DATABASE_PATH
DEEPSEEK_API_KEY
DEEPSEEK_MODEL
OPENCLAW_URL
OPENCLAW_MODEL
OPENCLAW_CONFIG_PATH
META_VERIFY_TOKEN
META_APP_SECRET
META_PAGE_ACCESS_TOKEN
META_PAGE_ID
META_APP_ID
META_GRAPH_VERSION
ADMIN_API_KEY
HISTORY_LIMIT
AI_TIMEOUT_SECONDS
HUMAN_PAUSE_MINUTES
FALLBACK_MESSAGE
```

Không bắt buộc duplicate fallback key nếu project có thể đọc từ environment file dùng chung. Luôn ghi rõ nguồn environment trong unit systemd và không in giá trị khi kiểm tra.

## 6. Tạo OpenClaw Agent Riêng

Trước khi sửa OpenClaw config, đọc skill `validate-openclaw-json` và backup config hiện tại.

Chuẩn agent:

- ID `messenger-<code>` và model alias `openclaw/messenger-<code>`.
- Workspace riêng `/root/.openclaw/workspace_messenger_<code>` hoặc đường dẫn active runtime được xác nhận tại thời điểm triển khai.
- Tool profile tối thiểu; deny runtime, filesystem, browser, messaging, gateway và web tools nếu agent chỉ cần trả lời từ prompt/knowledge được bot gửi vào.
- Không copy gateway token vào project `.env`.
- Không cho hai Fanpage dùng cùng workspace/session prefix.

Validate trước khi restart:

```bash
openclaw config validate --json
```

Chỉ restart gateway khi config thật sự thay đổi và validation đạt.

## 7. Kiểm Thử Không Gửi Tin Thật

Chạy từ project mới:

```bash
/usr/bin/python3 -m py_compile app/*.py
/usr/bin/python3 -m unittest discover -s tests -v
/usr/bin/python3 - <<'PY'
from app.knowledge import load_knowledge
knowledge = load_knowledge()
print({"knowledge_loaded": bool(knowledge), "characters": len(knowledge)})
PY
```

Chạy local app trên port đã chọn:

```bash
/usr/bin/python3 -m uvicorn app.main:app --host 127.0.0.1 --port <port>
curl -fsS http://127.0.0.1:<port>/health
```

Sau đó:

- Test GET webhook verification bằng token đọc nội bộ từ `.env`, không echo token ra terminal/log.
- Test chữ ký POST bằng payload giả và App Secret nội bộ.
- Test `message_echoes` bằng PSID giả theo skill `facebook-messenger-human-pause`.
- Xóa dữ liệu giả khỏi SQLite sau test.
- Gọi trực tiếp `answer_question()` với câu hỏi tổng hợp để kiểm tra OpenClaw; không gọi `send_text()`.
- Nếu test fallback provider thật, dùng câu hỏi synthetic, không chứa dữ liệu khách hàng và ghi rõ có thể phát sinh chi phí API.

## 8. Triển Khai Production

Backup trước khi sửa:

- Unit systemd hiện có.
- Nginx site hiện có.
- `messenger_dispatcher/app.py` nếu thêm route.
- OpenClaw config/workspace nếu sửa.
- Project target nếu đã tồn tại.

Thứ tự triển khai:

1. Unit tests và local health đạt.
2. OpenClaw config validate đạt.
3. Cài/cập nhật unit systemd nhưng chưa bật nếu Meta credentials chưa sẵn sàng.
4. Thêm direct Nginx route hoặc dispatcher mapping.
5. Chạy `nginx -t` trước reload.
6. `systemctl daemon-reload` sau khi đổi unit.
7. Start/restart bot mới; không restart các bot khác nếu không cần.
8. Restart dispatcher chỉ khi route/config của dispatcher thay đổi.
9. Kiểm tra `/health`, service status và journal ngắn.
10. Xác minh callback trong Meta Developer.
11. Chỉ gửi một tin test thật từ tài khoản test khi người dùng phê duyệt rõ.

Lệnh kiểm tra chuẩn:

```bash
systemctl status 01_mes_op_<code>.service --no-pager -l
curl -fsS http://127.0.0.1:<port>/health
journalctl -u 01_mes_op_<code>.service --since '-10 minutes' --no-pager
nginx -t
```

Không chép nguyên log có PSID hoặc nội dung khách hàng vào câu trả lời; chỉ tóm tắt trạng thái.

## 9. Cấu Hình Meta Developer

Làm theo `references/meta-checklist.md`. Bot production tối thiểu cần nhận đúng Page, verify callback, kiểm tra chữ ký và subscribe các field mà code thực sự xử lý, gồm message của khách và Page echo để human takeover hoạt động.

Nếu dùng dispatcher, callback Meta trỏ tới public route của dispatcher. Nếu dùng direct, callback trỏ thẳng route riêng của bot.

## 10. Bàn Giao Và Tạo Skill Riêng

Sau khi bot mới hoạt động:

- Tạo `/root/.agents/skills/messenger-<code>-fanpage/SKILL.md` với project path, port, service, webhook, knowledge root, AI backend, dry-run, run thật, input/output, rerun/rollback và safety.
- Cập nhật `/root/_Second_AI_Brain/02_Danh_Sach_Project.md` và project note nếu cần.
- Cập nhật `/root/_Second_AI_Brain/06_Nhat_Ky_Thay_Doi.md`.
- Cập nhật skill này nếu kiến trúc setup chung thay đổi.
- Quét skill/docs để bảo đảm không có secret thật.

## Rerun Và Rollback

Rerun luôn bắt đầu bằng preflight. Không copy lại template lên project đang chạy.

Rollback theo backup tương ứng:

- Restore code/config đã backup.
- Chạy lại unit tests và `openclaw config validate --json`.
- Restore unit rồi `systemctl daemon-reload` nếu unit thay đổi.
- Restore Nginx rồi `nginx -t` trước reload.
- Restore dispatcher rồi restart đúng service nếu mapping thay đổi.
- Giữ nguyên database production trừ khi backup DB là phần của thay đổi và người dùng yêu cầu restore.

Không xóa project hoặc database để rollback.

