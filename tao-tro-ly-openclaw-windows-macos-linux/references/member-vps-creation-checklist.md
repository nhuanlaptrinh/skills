# Checklist tạo OpenClaw member VPS

## Input
- [ ] Member name
- [ ] Nếu đổi tên/copy: source member/folder và mode `rename-same-member` hoặc `copy-new-member`
- [ ] Email khách hàng nếu cần tạo tài khoản dashboard Token Codex
- [ ] Token Codex API key nhận qua kênh bảo mật nếu đã có sẵn
- [ ] Telegram account ID
- [ ] Telegram user ID
- [ ] Telegram Group ID
- [ ] requireMention true/false
- [ ] BotFather Privacy Mode

## Preflight
- [ ] Kiểm tra hiện trạng
- [ ] Backup cấu hình
- [ ] Kiểm tra manager/image/container/SSH port/web port/volume thực tế; không giả định có dry-run
- [ ] Nếu folder vừa đổi tên: đối chiếu bind source trong `docker inspect` trước khi restart
- [ ] Nếu copy member cũ: exclude toàn bộ secret, identity, credential, session và dữ liệu riêng nguồn
- [ ] Không dùng `docker rename` như một migration hoàn chỉnh
- [ ] Volume persistent của member được map `<member-data>/root:/root`; không dùng filesystem tạm hoặc symlink sang `/home`
- [ ] Không lộ secret

## OpenClaw root và skills
- [ ] OpenClaw pin `2026.8.2` đã cài bằng root trong container
- [ ] `HOME=/root`, OpenClaw root `/root/.openclaw`, workspace `/root/.openclaw/workspace`
- [ ] Không dùng `--skip-skills`
- [ ] Toàn bộ folder có `SKILL.md` từ root nguồn đã nằm trực tiếp trong `/root/.openclaw/workspace/skills`
- [ ] Có `unify-openclaw-bot-workspace` và `set-openclaw-agent-full-exec` ở cả `/root/.agents/skills` host và workspace member
- [ ] Không còn `.git`, `__pycache__`, `.pyc` hoặc `node_modules` trong các skill đích
- [ ] `sync_all_skills_to_root.py --check` đạt
- [ ] `sync-openclaw-owner-training` có trong workspace và managed block có trong `AGENTS.md`
- [ ] `openclaw skills check` đạt trước khi start Gateway

## Token Codex trước VPS
- [ ] Đọc mục **Chuẩn bị Token Codex trước member VPS** trong skill chính
- [ ] `/models` trả HTTP `200` và có đủ `GPT-5.6-sol`, `GPT-5.6-terra`, `GPT-5.6-luna`
- [ ] Nếu tạo tài khoản mới: provisioning backend đã được xác minh và dry-run thực sự tồn tại
- [ ] Nếu sinh key mới: thư mục `/root/Data/private_accounts/token_codex/` quyền `700`, file output quyền `600`
- [ ] Không in full API key vào chat hoặc log chung
- [ ] Truyền key qua `TOKEN_CODEX_API_KEY`; chỉ dùng `CUSTOM_PROVIDER_API_KEY` để tương thích workflow cũ
- [ ] Lưu `/root/.openclaw/token-codex.env` quyền `600`; `openclaw.json` chỉ chứa `${TOKEN_CODEX_API_KEY}`

## Telegram DM
- [ ] Global và account `dmPolicy` là `pairing`
- [ ] Global allowFrom có đầy đủ owner Telegram đã xác minh cho VPS đích
- [ ] Account allowFrom có đầy đủ owner Telegram đã xác minh cho VPS đích
- [ ] Không sao chép owner ID từ VPS khác và không dùng wildcard owner
- [ ] `TELEGRAM_CHAT_ID` chỉ được merge thêm sau khi xác minh
- [ ] Người ngoài allowFrom phải pairing

## Command owner
- [ ] `commands.ownerAllowFrom` có các `telegram:<verified_owner_id>` tương ứng
- [ ] Không ghi `commands.ownerDisplay` (OpenClaw 2026.8 hiển thị owner ID raw mặc định)
- [ ] Khi đổi owner vẫn merge giữ owner hợp lệ hiện có; không ghi đè toàn bộ mảng

## Owner approval và Full Exec cuối
- [ ] Global và account `channels.telegram.execApprovals.enabled` là `auto`
- [ ] Global và account `execApprovals.approvers` có owner Telegram đã xác minh
- [ ] Global và account `execApprovals.target` là `dm`
- [ ] Telegram DM inline buttons đã bật
- [ ] `ensure_default_telegram_owner.py` đã chạy trước bước unify/Full Exec
- [ ] Agent `main` dùng `tools.exec.host=gateway`, `tools.exec.mode=full`, `strictInlineEval=false`
- [ ] Approval backend của `main` (SQLite `state/openclaw.sqlite#exec_approvals_config` trên OpenClaw 2026.8 hoặc legacy `exec-approvals.json`) có `security=full`, `ask=off`, `askFallback=full`, `autoAllowSkills=true`
- [ ] `set-openclaw-agent-full-exec --check` xác nhận effective runtime `full/off`
- [ ] Hiểu rõ Full Exec không hiện approval prompt cho lệnh Exec; approver vẫn dùng cho plugin/Skill Workshop theo policy riêng

## Forwarded exec approval
- [ ] `approvals.exec.enabled` true
- [ ] Mode `targets`
- [ ] Agent filter có `main`
- [ ] Target Telegram owner đã xác minh qua đúng account member

## Plugin approval
- [ ] `approvals.plugin.enabled` true
- [ ] Mode `targets`
- [ ] Agent filter có `main`
- [ ] Target Telegram owner đã xác minh qua đúng account member
- [ ] `skills.workshop.approvalPolicy` là `pending`, không phải `auto`
- [ ] Owner/approver đã xác minh nhận và xử lý được approval plugin/Skill Workshop
- [ ] Chỉ hướng dẫn Allow once hoặc `/approve <id> allow-once` cho approval còn tồn tại; không nói Exec Full cần duyệt
- [ ] Không dùng proposal ID thay approval ID

## Telegram group
- [ ] groupPolicy allowlist
- [ ] Group enabled
- [ ] Group allowFrom là `["*"]` ở top-level và account scope
- [ ] Không để group thiếu allowFrom vì sẽ fallback về DM owner allowlist
- [ ] requireMention mặc định false, trừ khi user yêu cầu true
- [ ] Toàn Telegram account có đúng một account-level binding tới `main`, không có `match.peer`
- [ ] Không còn peer-specific binding hoặc binding sang agent khác

## Không cần mention
- [ ] requireMention false
- [ ] allowFrom `["*"]` cho đúng group
- [ ] BotFather /setprivacy Disable
- [ ] Test tin thường không mention
- [ ] Log có inbound đúng group
- [ ] Bot có outbound

## Sự cố bot Telegram im lặng trong group
- [ ] Xác định `HOME` và config hiệu lực từ process `openclaw-gateway`
- [ ] So sánh `channels.telegram` và `bindings` với member cùng version đang chạy tốt
- [ ] Top-level và account scope đều có đúng Group ID, enabled, requireMention và allowFrom
- [ ] Có đúng một binding `telegram + accountId -> main`, không có peer
- [ ] `openclaw agents bindings` hiển thị route cần thiết, không trùng binding
- [ ] Không dùng `docker restart` thay cho restart Gateway nếu supervisor không quản lý OpenClaw
- [ ] Sau restart có process `openclaw-gateway` và cổng Gateway đang listen
- [ ] Chờ 45-60 giây nếu polling tạm `disconnected`, probe lại tới khi `connected`
- [ ] Log tin thử mới có inbound `telegram:group:<GROUP_ID>`
- [ ] Tạo session `agent:main:telegram:group:<GROUP_ID>` và có outbound hoặc user xác nhận phản hồi

## Runtime
- [ ] `openclaw --version` đúng `2026.8.2`
- [ ] `ensure_default_telegram_owner.py --check` đạt sau khi Telegram account tồn tại và trước Full Exec
- [ ] Member sạch đã chạy unify normalize-only dry-run/apply/check; member legacy đã chạy merge với đúng source agent
- [ ] `unify-openclaw-bot-workspace --check` đạt trước Full Exec: một account, một `main`, một workspace, một agent state
- [ ] Nếu có `owner-admin`/workspace legacy: dry-run, apply khi Gateway stopped và lưu manifest rollback
- [ ] `set-openclaw-agent-full-exec` đã chạy sau cùng và `--check` đạt sau khi Gateway lên
- [ ] Sau Full Exec không chạy ngược owner/unify check; dùng `openclaw agents list --bindings --json` để audit kiến trúc read-only
- [ ] config validate
- [ ] Restart tmux sau khi source `token-codex.env`
- [ ] gateway status OK
- [ ] channels probe OK

## Dashboard public
- [ ] Lấy đúng host web port map tới container port 80
- [ ] Lấy public IPv4 hoặc đặt `OPENCLAW_PUBLIC_IP`
- [ ] Nginx reverse proxy tới `127.0.0.1:18789` có WebSocket headers
- [ ] `allowedOrigins` đúng URL public
- [ ] Chỉ bật HTTP token-only khi `OPENCLAW_ALLOW_INSECURE_DASHBOARD=true` đã được xác nhận rõ
- [ ] `dangerouslyDisableDeviceAuth` true cho HTTP token-only
- [ ] Token lưu tại `/root/.openclaw_dashboard_token`, quyền 600
- [ ] UFW mở đúng web port
- [ ] Public URL trả HTTP 200
- [ ] Hướng dẫn nhập Token Gateway và để trống mật khẩu

## Hệ thống
- [ ] Token Codex provider dùng `https://codex.anhlaptrinh.vn/v1`
- [ ] Không thêm `/v1` lần thứ hai; API là `openai-completions`
- [ ] Cả ba model provider khai báo `input: ["text", "image"]`
- [ ] Cả ba model provider khai báo `maxTokens: 4096`
- [ ] `agents.defaults.model.primary` và `agents.defaults.imageModel.primary` là `token-codex/GPT-5.6-sol`
- [ ] Nếu cần image generation, chỉ dùng `agents.defaults.mediaModels.image.primary` sau khi provider tạo ảnh đã được cấu hình và `openclaw infer image providers --json` xác nhận; không dùng `token-codex/GPT-5.6-sol` hoặc key legacy `imageGenerationModel`
- [ ] API Token Codex đã cấu hình và cả ba model chat test thành công
- [ ] Ảnh smoke test được `openclaw infer image describe` đọc đúng chữ/nội dung đã biết
- [ ] Ảnh không nhạy cảm đi qua đúng Telegram/Zalo/dashboard được bot mô tả đúng nếu channel đó đã cấu hình
- [ ] Không bàn giao nếu chỉ validate JSON đạt nhưng chưa xác nhận đọc ảnh
- [ ] Không còn provider/model cũ trong config hoặc cache model của member
- [ ] Gọi Token Codex `/models` không lộ secret và kiểm tra chính xác model `gpt-4o-mini-transcribe`
- [ ] Chỉ bật audio/STT qua provider `token-codex` khi model được công bố; nếu không có hoặc kiểm tra lỗi, đặt `tools.media.audio.enabled=false`
- [ ] Xóa provider audio `openai` cũ; không tự thay model hoặc fallback sang provider khác
- [ ] Không tự cài `ffmpeg` chỉ để nghe voice; giữ nguyên nếu đã có, chỉ cài khi cần chuyển đổi định dạng riêng
- [ ] Chỉ gửi voice tiếng Việt để kiểm tra khi STT đã được xác nhận khả dụng và người dùng cho phép
- [ ] DuckDuckGo
- [ ] Second AI Brain
- [ ] Proxy direct-first

## Hoàn tất
- [ ] Agent cuối là `main`, workspace `/root/.openclaw/workspace`, agent state `/root/.openclaw/agents/main/agent`
- [ ] Full Exec cuối là `gateway/full`, `security=full`, `ask=off`, `strictInlineEval=false`
- [ ] Chỉ gửi email/mật khẩu Token Codex khi tài khoản thực tế đã được tạo
- [ ] Gửi link xem credit `https://codex.anhlaptrinh.vn/`
- [ ] Không gửi full API key
- [ ] Chưa test: chờ xác nhận thực tế
- [ ] Đã có inbound + outbound: hoàn tất hoàn toàn
