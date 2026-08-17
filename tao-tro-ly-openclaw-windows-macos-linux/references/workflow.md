# Tóm tắt workflow

1. Nhận API key Token Codex qua kênh bảo mật hoặc xác minh provisioning backend thật trước khi tạo tài khoản; chỉ cần email khi phải tạo tài khoản dashboard.
2. Nếu sinh key mới, tạo `/root/Data/private_accounts/token_codex/` quyền `700`, lưu output một lần bằng file quyền `600` và không in full key vào chat hoặc log dùng chung.
3. Preflight manager container, image, SSH port, web port, volume và tên container thực tế; nếu đầu vào là folder đã đổi tên hoặc copy từ member cũ, phân loại cùng-member hay member-mới và đọc `member-vps-rename-copy-workflow.md`; bắt buộc có root volume persistent map vào `/root`, không giả định tồn tại dry-run.
4. Cài đúng version OpenClaw bằng root với `HOME=/root`, OpenClaw root `/root/.openclaw` và workspace `/root/.openclaw/workspace`; không dừng sau khi chỉ tạo container nền.
5. Chạy `scripts/sync_all_skills_to_root.py` từ root quản trị để copy toàn bộ skill trực tiếp vào `/root/.openclaw/workspace/skills`, sau đó chạy `--check` và `openclaw skills check` trước khi start Gateway.
6. Tạo/cấu hình member bằng key truyền qua `TOKEN_CODEX_API_KEY` hoặc `CUSTOM_PROVIDER_API_KEY`, kèm biến Telegram khi có.
7. Sau khi Telegram account tồn tại, chạy `scripts/ensure_default_telegram_owner.py` dry-run, `--apply`, rồi `--check`; bắt buộc giữ `6980864856` ở allowlist, command owner, native/forwarded approval, plugin/Skill Workshop approval và host `exec-approvals.json`.
8. Inventory agents/bindings. Với member sạch chỉ có `main`, chạy `unify-openclaw-bot-workspace` normalize-only dry-run/apply/check không có source; nếu có `owner-admin` hoặc agent/workspace legacy, dừng Gateway rồi dry-run/apply/check với đúng source để gộp về `/root/.openclaw/workspace`.
9. Chạy `set-openclaw-agent-full-exec` cho `main` sau cùng: dry-run, apply/check `--no-restart` trước lần start đầu; sau khi Gateway lên chạy lại `--check` để xác nhận runtime `full/off`.
10. Dùng Docker inspection để xác định đúng web port host map vào port `80` của container và public IPv4.
11. Lưu key tại `/root/.openclaw/token-codex.env` quyền `600`; `openclaw.json` chỉ chứa `${TOKEN_CODEX_API_KEY}` và phải source env trước mỗi lần start Gateway.
12. Chỉ cấu hình Nginx, Gateway Token, Telegram policy, Second AI Brain và shared fallback proxy khi từng thành phần tồn tại và đã validate.
13. Xác minh base URL `https://codex.anhlaptrinh.vn/v1`, API `openai-completions` và đúng ba model `GPT-5.6-sol`, `GPT-5.6-terra`, `GPT-5.6-luna`; mỗi model có `input: ["text", "image"]` và `maxTokens: 4096`; chạy smoke test đọc ảnh trước khi bàn giao; không khôi phục provider cũ hoặc thêm `/v1` hai lần.
14. Xác minh owner check, unify check, Full Exec check, config validate, dashboard public HTTP `200`, trạng thái Gateway, skill và channel; nếu đã có Telegram/Zalo/dashboard chat, kiểm tra thêm một ảnh không nhạy cảm đi qua đúng channel tới agent.
15. Chỉ bàn giao truy cập VPS member và credential dashboard Token Codex khi tài khoản thật đã được tạo; gửi `https://codex.anhlaptrinh.vn/` để xem credit và không tiết lộ full API key.
