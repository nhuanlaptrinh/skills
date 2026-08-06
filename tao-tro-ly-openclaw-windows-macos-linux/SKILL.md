---
name: tao-tro-ly-openclaw-windows-macos-linux
description: Skill tự chứa để cài đặt, tạo, cấu hình, vận hành hoặc sửa trợ lý OpenClaw trên Windows, macOS và Linux, gồm máy cá nhân, VPS chính và VPS thành viên chạy Docker. Dùng cả khi bot Telegram không trả lời trong group, chỉ trả lời khi mention, thiếu binding group vào agent, polling chưa connected hoặc Gateway không tự lên sau restart. Bắt buộc cài OpenClaw và đồng bộ toàn bộ skill vào OpenClaw root quản trị trước khi chạy Gateway. Bao gồm workflow Node.js/Python/OpenClaw local, Gateway, Codex login, DeepSeek tùy chọn, Token Codex, Telegram, Zalo QR/voice/reliability, kiểm tra openclaw.json, Custom Provider, proxy fallback, Second AI Brain, audio, web search, xử lý ảnh và tích hợp Facebook Fanpage/CSKH.
---

# Tạo Trợ Lý OpenClaw Trên Windows, macOS Và Linux

## Mục tiêu

Điều phối đúng quy trình cài đặt, tạo, cấu hình hoặc vận hành trợ lý OpenClaw trên Windows, macOS và Linux. Mọi lượt tạo trợ lý phải cài OpenClaw, đặt runtime trong OpenClaw root quản trị và đồng bộ toàn bộ skill trước khi chạy Gateway. Trên Linux phải phân biệt máy local/server, VPS chính và VPS thành viên chạy trong container Docker; không dùng lẫn script, config, token, port hoặc dữ liệu giữa các môi trường.

## Chính sách root bắt buộc

- Không được báo hoàn tất nếu chưa cài `openclaw@2026.7.1-2`, chưa tạo OpenClaw root hoặc chưa đồng bộ đủ skill.
- Linux/VPS/container member bắt buộc chạy OpenClaw bằng `root`, `HOME=/root`, OpenClaw root `/root/.openclaw` và workspace `/root/.openclaw/workspace`.
- `/root/.openclaw` trong container phải là thư mục thật nằm trên volume persistent riêng của member; không dùng symlink sang home khác.
- macOS dùng tài khoản root quản trị với OpenClaw root `/var/root/.openclaw`. Windows dùng PowerShell **Run as Administrator** và OpenClaw root trong profile Administrator: `$env:USERPROFILE\.openclaw`.
- Tất cả folder có `SKILL.md` từ root nguồn `.agents/skills`, `.codex/skills` và nhóm `.codex/skills/.system` phải được đặt trực tiếp tại `<OPENCLAW_ROOT>/workspace/skills/<ten-skill>`; không bọc thêm folder tổng hoặc folder ngày.
- Không dùng `--skip-skills`. Sau onboarding, chạy `scripts/sync_all_skills_to_root.py`, sau đó chạy lại script với `--check` và `openclaw skills check`.
- Script đồng bộ phải loại `.git`, `__pycache__`, `.pyc`, `node_modules`; nếu skill đích đã tồn tại, script backup trước khi thay.
- Nếu trùng tên skill giữa các root nguồn, ưu tiên root nguồn xuất hiện trước; chỉ cài một folder trực tiếp cho mỗi tên skill.
- Gateway chỉ được start/restart sau khi `openclaw --version`, đồng bộ skill, `openclaw config validate` và `openclaw skills check` đều đạt.

## Tính độc lập và cách chuyển VPS

- Đây là skill điều phối tự chứa; không phụ thuộc logic của skill khác để thực hiện cài đặt, nhưng vẫn bắt buộc đóng gói toàn bộ skill khả dụng vào OpenClaw root.
- Khi chuyển sang máy khác, copy nguyên folder skill, gồm `SKILL.md`, `agents/`, `references/`, `scripts/` và `resources/`, vào root nguồn skill trước khi chạy đồng bộ.
- Các project hoặc automation được nêu trong skill vẫn phải tồn tại nếu muốn dùng đúng lệnh tự động; nếu VPS đích chưa có, thực hiện workflow thủ công tương ứng trong skill thay vì gọi một skill khác.
- Không xóa các skill độc lập cũ trên VPS nguồn vì chúng có thể đang được workflow khác sử dụng; skill này chỉ loại bỏ sự phụ thuộc vào chúng.

## Chọn hệ điều hành và môi trường trước khi thao tác

1. Xác định hệ điều hành bằng PowerShell trên Windows hoặc `uname -s` trên macOS/Linux.
2. Xác định đây là máy cá nhân/lớp học, Linux server/VPS chính hay VPS thành viên Docker.
3. Trên Windows và macOS, mặc định cài local gateway chỉ bind loopback; không áp dụng script Docker member VPS.
4. Trên Linux VPS chính, xác định runtime hiện tại; nếu chưa nằm tại `/root/.openclaw`, backup và migrate về root trước khi tiếp tục. Không duy trì thêm runtime OpenClaw mới dưới user thường.
5. Với VPS chính, không chạy workflow provisioning member; backup đúng file cấu hình sắp sửa và chỉ thay đổi runtime được yêu cầu.
6. Nếu là VPS thành viên, dùng toàn bộ workflow member trong skill này và kiểm tra trước các script provisioning thực tế; không gọi đường dẫn automation chưa tồn tại.
7. Nếu yêu cầu chưa nói rõ hệ điều hành hoặc môi trường, kiểm tra trước khi quyết định; không tự giả định Windows là WSL, Linux host là member container hoặc ngược lại.

## Cài đặt OpenClaw đa nền tảng

### Mặc định chung

- Luôn cài cố định `openclaw@2026.7.1-2`; không dùng `latest` và không tự đổi version. Sau khi cài phải xác nhận `openclaw --version` trả đúng `2026.7.1-2`.
- Cài Node.js LTS, npm, Python 3 và pip trước khi cài OpenClaw.
- Bắt buộc chạy bằng quyền root/Administrator và chuẩn bị đầy đủ root nguồn skill trước khi onboarding.
- Dashboard local mặc định: `http://127.0.0.1:18789/`.
- Gateway mặc định: mode `local`, bind `loopback`, port `18789`, auth `token`.
- Token `chatbot` chỉ được dùng cho máy local bind loopback; VPS/public/member phải dùng token ngẫu nhiên riêng.
- Chuẩn bị Codex CLI dùng đăng nhập tài khoản ChatGPT bằng `forced_login_method = "chatgpt"`; không tự chạy login và không copy auth cache.
- Chỉ bật DeepSeek khi biến `DEEPSEEK_API_KEY` đã tồn tại; không in hoặc ghi key vào skill/log.

### Windows

Chạy PowerShell bằng **Run as Administrator**. Chuyển thư mục hiện hành vào folder skill này trước khi chạy:

```powershell
winget install --id OpenJS.NodeJS.LTS --exact --accept-package-agreements --accept-source-agreements
winget install --id Python.Python.3.12 --exact --accept-package-agreements --accept-source-agreements
python -m ensurepip --upgrade
python -m pip install --upgrade pip
npm install -g openclaw@2026.7.1-2
$SkillDir = (Get-Location).Path
$OpenClawRoot = Join-Path $env:USERPROFILE ".openclaw"
$Workspace = Join-Path $OpenClawRoot "workspace"
openclaw onboard --non-interactive --accept-risk --mode local --auth-choice skip --skip-channels --skip-search --install-daemon --skip-health --workspace "$Workspace" --gateway-bind loopback --gateway-auth token --gateway-port 18789 --gateway-token chatbot
python (Join-Path $SkillDir "scripts\sync_all_skills_to_root.py") --openclaw-root "$OpenClawRoot"
python (Join-Path $SkillDir "scripts\sync_all_skills_to_root.py") --openclaw-root "$OpenClawRoot" --check
openclaw config validate
openclaw skills check
openclaw gateway restart
openclaw gateway status
```

Nếu command chưa vào PATH sau khi cài, mở PowerShell mới rồi chạy lại phần kiểm tra. Không coi WSL là Windows native; nếu đang trong WSL thì dùng nhánh Linux.

### macOS

Chuẩn bị Node.js/Python bằng tài khoản quản trị, copy toàn bộ root nguồn skill vào `/var/root/.agents/skills` và `/var/root/.codex/skills`, rồi chuyển thư mục hiện hành vào folder skill này:

```bash
brew install node python
python3 -m ensurepip --upgrade || true
python3 -m pip install --upgrade pip --break-system-packages || python3 -m pip install --upgrade pip
SKILL_DIR="$(pwd -P)"
sudo -H npm install -g openclaw@2026.7.1-2
sudo -H env HOME=/var/root openclaw onboard --non-interactive --accept-risk --mode local --auth-choice skip --skip-channels --skip-search --install-daemon --skip-health --workspace /var/root/.openclaw/workspace --gateway-bind loopback --gateway-auth token --gateway-port 18789 --gateway-token chatbot
sudo -H python3 "$SKILL_DIR/scripts/sync_all_skills_to_root.py" --openclaw-root /var/root/.openclaw
sudo -H python3 "$SKILL_DIR/scripts/sync_all_skills_to_root.py" --openclaw-root /var/root/.openclaw --check
sudo -H env HOME=/var/root openclaw config validate
sudo -H env HOME=/var/root openclaw skills check
sudo -H env HOME=/var/root openclaw gateway restart
sudo -H env HOME=/var/root openclaw gateway status
```

Hỗ trợ cả Apple Silicon (`/opt/homebrew`) và Intel (`/usr/local`). Không sửa LaunchAgent khác nếu task chỉ cài OpenClaw.

### Linux local hoặc server độc lập

Mở root shell, chuyển thư mục hiện hành vào folder skill này và kiểm tra `id -u` bằng `0`. Chọn package manager phù hợp (`apt`, `dnf`, `yum`, `pacman`) để cài Node.js, npm, Python và pip. Với Ubuntu/Debian:

```bash
test "$(id -u)" -eq 0
export HOME=/root
SKILL_DIR="$(pwd -P)"
apt-get update
apt-get install -y curl ca-certificates nodejs npm python3 python3-pip python3-venv
npm install -g openclaw@2026.7.1-2
openclaw onboard --non-interactive --accept-risk --mode local --auth-choice skip --skip-channels --skip-search --install-daemon --skip-health --workspace /root/.openclaw/workspace --gateway-bind loopback --gateway-auth token --gateway-port 18789 --gateway-token chatbot
python3 "$SKILL_DIR/scripts/sync_all_skills_to_root.py" --openclaw-root /root/.openclaw
python3 "$SKILL_DIR/scripts/sync_all_skills_to_root.py" --openclaw-root /root/.openclaw --check
openclaw config validate
openclaw skills check
openclaw gateway restart
openclaw gateway status
```

Nếu là VPS cần truy cập từ ngoài, không tự đổi bind hoặc mở port. Chỉ cấu hình reverse proxy/firewall/domain sau khi người dùng yêu cầu rõ và phải dùng token ngẫu nhiên thay cho `chatbot`.

### Codex và DeepSeek

- Codex CLI: người dùng tự chạy `codex logout`, sau đó `codex login`; máy headless dùng `codex login --device-auth`.
- Ghi `forced_login_method = "chatgpt"` vào root quản trị: Linux `/root/.codex/config.toml`, macOS `/var/root/.codex/config.toml`, Windows `%USERPROFILE%\.codex\config.toml` của Administrator; giữ nguyên các cấu hình khác.
- Không tự cài, chạy login hoặc sao chép `auth.json`/credential store.
- Nếu có `DEEPSEEK_API_KEY`, chỉ chạy lại `openclaw onboard` bằng đúng root runtime và `--workspace` hiện có với `--auth-choice deepseek-api-key`; không dùng `--skip-skills`, truyền key qua biến môi trường rồi chạy lại sync `--check`, config validate và `openclaw skills check`.

### Kiểm tra đa nền tảng

```bash
node -v
npm -v
python3 --version
python3 -m pip --version
openclaw --version
openclaw config validate
openclaw skills check
openclaw gateway status
openclaw models auth list
```

Trên Windows có thể thay `python3` bằng `python` hoặc `py -3`. Báo đúng dashboard local `http://127.0.0.1:18789/`; không quảng bá URL này là public.

## Quy trình an toàn cho VPS chính

1. Đọc tài liệu Second AI Brain, project note và `AGENTS.md` liên quan trước khi sửa.
2. Xác định runtime OpenClaw hiện tại, file `openclaw.json` và cách gateway đang được khởi chạy; chuẩn đích bắt buộc là user `root`, `HOME=/root` và workspace `/root/.openclaw/workspace`.
3. Backup file cấu hình cần sửa vào `/root/_Backups`; không sao chép secret vào backup công khai, skill, log hoặc câu trả lời.
4. Dùng đúng phần tích hợp trong skill này nếu task thuộc Telegram, Zalo, Token Codex, STT, voice, proxy, Second AI Brain hoặc kiểm tra JSON.
5. Sau thay đổi, kiểm tra config, trạng thái gateway và đúng channel được yêu cầu; không chạy automation tạo container member.

## Mục tiêu cho VPS thành viên

Trên VPS hiện tại, `/root/docker-users/manage-user.sh` chỉ tạo container nền với username, password và SSH port. Phần cài OpenClaw, dashboard, Telegram, Zalo, Token Codex và document tools phải chạy tiếp theo các mục tương ứng trong skill này; không được coi container nền là member OpenClaw hoàn chỉnh.

## Đường dẫn cho VPS thành viên

- Bộ tạo container nền trên VPS này: `/root/docker-users/manage-user.sh`
- Dữ liệu member trên host: `/root/docker-users/data/<name>`
- Root persistent trên host: `/root/docker-users/data/<name>/root`, bắt buộc mount vào `/root` trong container
- Workspace OpenClaw bên trong container: `/root/.openclaw/workspace`
- Root skill đích bên trong container: `/root/.openclaw/workspace/skills`
- Home OpenClaw bên trong container: `/root`; đặt `HOME=/root` cho mọi lệnh OpenClaw
- Backup trước khi sửa workflow: `/root/_Backups`
- Nhật ký thay đổi: `/root/_Second_AI_Brain/06_Nhat_Ky_Thay_Doi.md`
- Checklist SVG/PNG và lỗi shell approvals path: `references/svg-png-shell-checklist.md`
- Fallback tạo ảnh local SVG/Python: `references/local-svg-python-image-fallback.md`
- Checklist rút gọn tạo member VPS và Telegram group: `references/member-vps-creation-checklist.md`
- Shared fallback proxy: thực hiện trực tiếp tại mục **Shared Fallback Proxy**.
- Second AI Brain: thực hiện trực tiếp tại mục **Second AI Brain Cho Member VPS Mới**.
- Chuẩn bị/kiểm tra API Token Codex: thực hiện trực tiếp tại mục **Chuẩn bị Token Codex trước member VPS**.
- Đăng nhập Zalo Personal: thực hiện trực tiếp tại mục **Đăng nhập Zalo Personal/Zalo User**.

## Quy tắc mặc định cho VPS thành viên

- Tên container là `user-<name>`.
- Folder data member là `/root/docker-users/data/<name>` trên VPS này; nếu chuyển sang máy khác phải kiểm tra lại đường dẫn thật.
- Mật khẩu SSH mặc định luôn là `<name>123`; ví dụ `nhuan` thành `nhuan123`. Không tự sinh mật khẩu ngẫu nhiên, trừ khi người dùng yêu cầu rõ mật khẩu khác.
- Trước khi tạo **OpenClaw member VPS đầy đủ**, phải có API key Token Codex được truyền qua kênh bảo mật hoặc có provisioning backend đã được kiểm tra tồn tại. Không gọi command tạo tài khoản ở đường dẫn đoán trước.
- Nếu tài khoản được tạo qua provisioning backend, chỉ dùng mật khẩu/credit mặc định mà backend thực tế xác nhận; không tự ghi cứng mặc định vào live config.
- Khi bàn giao, gửi email/mật khẩu dashboard Token Codex nếu có và link `https://codex.anhlaptrinh.vn/`; không gửi full API key.
- `manage-user.sh` yêu cầu rõ `<username> <password> <ssh_port>` và chỉ map SSH port; phải tự chọn, kiểm tra port SSH/web và xác minh Docker mapping trước khi bàn giao.

### Không cho phép dừng ở container nền

Khi task dùng skill này để tạo **trợ lý OpenClaw**, container nền chỉ là bước trung gian:

1. Chạy `/root/docker-users/manage-user.sh create <name> <password> <ssh_port>`; không giả định script tự sinh mật khẩu hoặc tự chọn port.
2. Bắt buộc bổ sung volume persistent `/root/docker-users/data/<name>/root:/root`, cài OpenClaw trong container bằng `HOME=/root` và tạo `/root/.openclaw/workspace`.
3. Bắt buộc đồng bộ toàn bộ skill nguồn vào `/root/.openclaw/workspace/skills`, chạy kiểm tra đủ skill và validate config.
4. Chỉ sau đó mới cấu hình Telegram/Zalo/provider/document tools theo phạm vi đầu vào và chạy Gateway.
5. Nếu người dùng thực sự chỉ cần một container Linux không có OpenClaw, task đó không thuộc skill tạo trợ lý này; chuyển sang workflow quản lý container/VPS riêng và không báo đã tạo trợ lý.
- OpenClaw phải luôn cài cố định `openclaw@2026.7.1-2`; không dùng npm dist-tag `latest`, không nhận override version từ môi trường và không tự nâng cấp.
- Trước khi cài, đọc `engines.node` bằng `npm view openclaw@2026.7.1-2 engines --json`; version này yêu cầu Node `>=22.22.3 <23 || >=24.15.0 <25 || >=25.9.0`.
- Mọi member mới phải có `python3`, `python3-full`, `python3-venv`, `python3-pip`.
- Mọi member mới phải có Poppler (`pdfinfo`, `pdftotext`), `file`, `unzip`, `zip`.
- Mọi member mới phải có document venv tại `/root/.openclaw/tools/document-venv` với OpenPyXL, PyPDF, pdfplumber, PyMuPDF, Pillow, XlsxWriter và pandas.
- Nếu không có script document-tools đã được kiểm tra tồn tại, cài trực tiếp trong container theo danh sách package/venv ở mục kiểm tra; không gọi đường dẫn mẫu bị thiếu.
- Tạo symlink `document-python` và `document-pip`, đồng thời copy validator vào `/root/.openclaw/workspace/tools/validate_zalo_file.py`.
- Mọi member mới phải có toàn bộ skill nguồn tại `/root/.openclaw/workspace/skills`, mỗi skill một folder trực tiếp; không được chỉ copy riêng skill tạo trợ lý.
- Phải chạy `scripts/sync_all_skills_to_root.py --check` trên root volume đích và `openclaw skills check` trong container trước khi start Gateway.
- Gateway URL trong container là `http://127.0.0.1:18789/`.
- Gateway Token phải được sinh ngẫu nhiên riêng cho từng member, trừ khi người dùng truyền `OPENCLAW_GATEWAY_TOKEN`; không dùng token cố định dùng chung.
- Chỉ báo dashboard public sau khi Docker đã map rõ `<web_port>:80` và Nginx trong container reverse proxy port `80` tới `127.0.0.1:18789` với WebSocket headers; `manage-user.sh` hiện không tự làm hai việc này.
- Dashboard public HTTP mặc định chỉ yêu cầu Gateway Token: đặt `gateway.controlUi.allowedOrigins` đúng URL public, `gateway.controlUi.allowInsecureAuth = true`, và `gateway.controlUi.dangerouslyDisableDeviceAuth = true`.
- Lưu Gateway Token tại `/root/.openclaw_dashboard_token` với quyền `600`; khi đăng nhập nhập Token Gateway và để trống ô mật khẩu.
- Phải báo link public tương ứng web port sau khi tạo và xác minh URL trả HTTP `200`. Nếu không tự lấy được public IPv4, dùng `OPENCLAW_PUBLIC_IP`.
- Cấu hình HTTP token-only giảm bảo mật; khi có domain HTTPS phải ưu tiên HTTPS và tắt `dangerouslyDisableDeviceAuth`.
- Telegram DM mặc định phải dùng `dmPolicy: pairing` ở cả cấp chung và `channels.telegram.accounts.<account>`.
- Ba Telegram ID quản trị mặc định `7919819873`, `6980864856` và `8342048167` luôn phải có trong `channels.telegram.allowFrom` và `channels.telegram.accounts.<account>.allowFrom`; các ID này được nhắn riêng không cần pairing.
- Mặc định bắt buộc đặt `commands.ownerAllowFrom` thành `telegram:7919819873`, `telegram:6980864856`, `telegram:8342048167` và `commands.ownerDisplay = "raw"` để cả ba ID có quyền owner command.
- Chỉ thay bộ owner/approver mặc định khi người dùng chủ động yêu cầu rõ một bộ Telegram ID khác. Việc người dùng chỉ cung cấp `TELEGRAM_CHAT_ID` của member không được coi là yêu cầu thay owner.
- `TELEGRAM_CHAT_ID` nếu được truyền khi tạo member phải được merge thêm vào allowFrom, không thay thế ba ID quản trị mặc định, trừ khi người dùng yêu cầu rõ thay bộ owner/approver.
- Người mới ngoài allowFrom phải pairing; dùng `openclaw pairing list telegram` để lấy request và chỉ approve đúng người đã xác minh.
- Mọi member mới phải bật `approvals.plugin.enabled = true`, mode `targets`, `agentFilter: ["main"]`; tạo ba target Telegram tới `7919819873`, `6980864856` và `8342048167`, có `accountId` đúng bằng tên Telegram account/member.
- Cả ba ID quản trị mặc định có quyền nhận và xử lý approval bằng nút **Allow once** hoặc `/approve <id> allow-once`; phải dùng approval ID đang chờ, không dùng proposal ID của skill.
- Khi người dùng cung cấp Telegram Group ID lúc tạo nhân viên, mặc định cấu hình group allowlist với `enabled: true`, `requireMention: false`, `allowFrom: ["*"]` ở cả top-level và account scope, cùng binding riêng tới agent `main` trước khi restart gateway.
- Không được chỉ xóa `allowFrom` cấp group: OpenClaw hiện hành có thể fallback về DM/account `allowFrom` và tiếp tục chỉ cho chủ bot. Muốn mọi thành viên trong group được gọi bot, bắt buộc đặt wildcard `allowFrom: ["*"]` ngay trong đúng group.
- Giữ Telegram DM ở `pairing`; `allowFrom` chỉ chứa các ID đã duyệt/mặc định. Wildcard chỉ áp dụng cho group đã khai báo, không dùng wildcard để mở DM hoặc group khác.
- Khi cần Zalo Personal/Zalo User, cài `@openclaw/zalouser` đúng version OpenClaw, ưu tiên gửi QR trực tiếp tới Telegram ID đang có trong allowlist thay vì public QR trên web.
- Zalo mặc định giữ `dmPolicy: pairing` nếu user chưa yêu cầu policy. Nếu user yêu cầu DM allowlist, chỉ thêm sender đã xác minh qua pairing request vào `channels.zalouser.allowFrom`; không approve sender lạ.
- Khi user yêu cầu mở toàn bộ Zalo group, có thể đặt `channels.zalouser.groupPolicy: open`. Khi chỉ mở một hoặc vài group cụ thể và không cần mention, phải dùng `groupPolicy: allowlist`, khai báo `groups.<GROUP_ID>.enabled: true`, `groups.<GROUP_ID>.requireMention: false`, và `groupAllowFrom: ["*"]`; không dùng wildcard DM để mở group.
- Chạy gateway bằng root runtime của member và luôn nạp `/root/.openclaw/token-codex.env` trước khi chạy; nếu không, `${TOKEN_CODEX_API_KEY}` sẽ rỗng khi Gateway reload hoặc khởi động lại.
- `/root/.openclaw` phải là thư mục thật trên volume `/root`; không tạo symlink sang `/home`, `/workspace` hoặc đường dẫn khác vì exec approvals có thể từ chối traversal qua symlink.
- Mọi `docker exec ... openclaw` trong automation phải truyền `-e HOME=/root` hoặc chạy qua wrapper đã khóa `HOME`.
- **Cấu hình Custom Provider cho Token Codex (BẮT BUỘC KHI DÙNG VPS THÀNH VIÊN):** Token Codex là provider duy nhất cho member đầy đủ. Khi cấu hình thủ công vào `openclaw.json`, bắt buộc dùng đúng base URL, API, biến môi trường và ba model sau; không tự thêm `/v1` lần thứ hai hoặc thuộc tính lạ như `enabled`. Mọi model phải khai báo `input: ["text", "image"]` để member luôn nhận được ảnh input:
```json
"models": {
  "providers": {
    "token-codex": {
      "baseUrl": "https://codex.anhlaptrinh.vn/v1",
      "apiKey": "${TOKEN_CODEX_API_KEY}",
      "api": "openai-completions",
      "models": [
        {
          "id": "GPT-5.6-sol",
          "name": "GPT-5.6-sol",
          "input": ["text", "image"],
          "maxTokens": 4096
        },
        {
          "id": "GPT-5.6-terra",
          "name": "GPT-5.6-terra",
          "input": ["text", "image"],
          "maxTokens": 4096
        },
        {
          "id": "GPT-5.6-luna",
          "name": "GPT-5.6-luna",
          "input": ["text", "image"],
          "maxTokens": 4096
        }
      ]
    }
  }
},
"agents": {
  "defaults": {
    "model": {
      "primary": "token-codex/GPT-5.6-sol"
    },
    "imageModel": {
      "primary": "token-codex/GPT-5.6-sol"
    },
    "imageGenerationModel": {
      "primary": "token-codex/GPT-5.6-sol"
    },
    "models": {
      "token-codex/GPT-5.6-sol": {},
      "token-codex/GPT-5.6-terra": {},
      "token-codex/GPT-5.6-luna": {}
    }
  }
}
```
- Mặc định cấu hình hiểu ảnh bằng `token-codex/GPT-5.6-sol`: `agents.defaults.imageModel.primary` và model chính `agents.defaults.model.primary` phải dùng model này; `agents.defaults.models` phải có đủ ba model và model catalog phải giữ `input: ["text", "image"]` cùng `maxTokens: 4096`. Chỉ đặt `input: ["text"]` nếu người dùng yêu cầu rõ không hỗ trợ ảnh input (`N`).
- `imageGenerationModel.primary` chỉ dùng cho tính năng tạo ảnh, không được coi là bước thay thế cho khả năng đọc ảnh input.
- **Kiểm tra bắt buộc khả năng đọc ảnh:** sau `openclaw config validate`, tạo một ảnh kiểm thử không chứa dữ liệu riêng tư rồi chạy `openclaw infer image describe` bằng `token-codex/GPT-5.6-sol`. Kết quả phải nhận diện được chữ kiểm thử `OPENCLAW_VISION_OK_2026` hoặc nội dung hình đã biết; chỉ HTTP `200` không đủ để kết luận đọc ảnh hoạt động.

```bash
docker exec -i user-<ten_user> sh -lc '
  set -e
  set -a
  . /root/.openclaw/token-codex.env
  set +a
  /root/.openclaw/tools/document-venv/bin/python - <<"PY"
from PIL import Image, ImageDraw
image = Image.new("RGB", (720, 220), "white")
draw = ImageDraw.Draw(image)
draw.text((40, 90), "OPENCLAW_VISION_OK_2026", fill="black")
image.save("/tmp/openclaw-vision-smoke.png")
PY
  HOME=/root openclaw infer image describe \
    --file /tmp/openclaw-vision-smoke.png \
    --model token-codex/GPT-5.6-sol \
    --prompt "Đọc chính xác dòng chữ trong ảnh và trả lời nguyên văn." \
    --json
  rm -f /tmp/openclaw-vision-smoke.png
'
```

- Nếu smoke test lỗi, không bàn giao member như đã hỗ trợ ảnh; kiểm tra lại `input`, model primary, credential Token Codex, endpoint và cache model rồi validate/restart theo đúng quy trình.
- Nếu đã cấu hình Telegram, Zalo hoặc dashboard chat, bước nghiệm thu cuối phải dùng một ảnh không nhạy cảm đi vào đúng channel thực tế và yêu cầu bot mô tả chữ/vật thể đã biết. Chỉ thực hiện gửi thử khi người dùng cho phép hoặc để người dùng chủ động gửi; không kết luận hoàn tất nếu CLI đọc ảnh được nhưng channel không chuyển ảnh tới agent.
- Mặc định bật web search cho member VPS bằng plugin `duckduckgo`, vì DuckDuckGo không cần API key và tránh lỗi `no provider is available` khi bot gọi `web_search`.
- Khi tạo/cấu hình trợ lý mới, trong `/root/.openclaw/openclaw.json` của container member VPS phải có `plugins.entries.duckduckgo.enabled = true` và `tools.web.search.provider = "duckduckgo"`.
- Trước khi cấu hình audio understanding/transcription, bắt buộc gọi `GET https://codex.anhlaptrinh.vn/v1/models` bằng credential Token Codex hiện có và kiểm tra model `gpt-4o-mini-transcribe`; chỉ in HTTP status và kết quả có/không, tuyệt đối không in token.
- Chỉ bật `tools.media.audio.enabled = true` khi `/models` thực sự công bố `gpt-4o-mini-transcribe`; dùng trực tiếp provider `token-codex`, ngôn ngữ `vi`, `echoTranscript = true`. Nếu model không có hoặc không kiểm tra được, đặt `enabled = false`, xóa provider audio cũ và báo rõ STT chưa được Token Codex hỗ trợ.
- Không tự thay model STT hoặc fallback sang provider khác. Không cài `ffmpeg` chỉ để bật tính năng nghe audio; chỉ cài khi model STT đã khả dụng và có yêu cầu chuyển đổi định dạng riêng.
- Ngoại lệ Zalo Personal: plugin `zalouser` có thể chuyển voice thành URL `zdn.vn/*.aac`; endpoint STT không nhận AAC trực tiếp. Khi model STT đã khả dụng và member cần nghe voice Zalo, cài `ffmpeg` riêng cho member đó rồi áp dụng workflow AAC tích hợp tại mục audio; không cài đại trà.
- Không dùng endpoint localhost cho audio; mọi bước kiểm tra và transcription phải dùng base URL HTTPS của provider `token-codex`.
- Khi tạo VPS thành viên mới bằng pipeline này, mặc định public dashboard qua đúng web port Docker đã cấp; không mở thêm port gateway `18789` trực tiếp trên host.
- Mọi workflow tạo, cấu hình hoặc vận hành trợ lý member VPS phải áp dụng mục **Shared Fallback Proxy**; kết nối trực tiếp luôn là mặc định, proxy chỉ là fallback khi direct thất bại.
- Mỗi VPS thành viên mới phải được preflight port, bootstrap thủ công theo các mục trong skill và kiểm tra trong đúng container `user-<ten_user>`.

## Shared Fallback Proxy

Mỗi khi tạo, cấu hình hoặc vận hành trợ lý OpenClaw trong member VPS, áp dụng trực tiếp quy trình sau; không gọi skill ngoài.

Quy tắc bắt buộc:

1. Luôn thử kết nối trực tiếp trước; proxy chỉ là fallback khi direct thất bại.
2. Không bật proxy toàn hệ thống; không sửa `/etc/environment`, shell rc, Docker daemon, systemd global environment hoặc luồng mạng mặc định.
3. Chỉ dùng file secret đã được quản trị viên chỉ định qua `OPENCLAW_FALLBACK_PROXY_ENV`; kiểm tra file tồn tại, owner phù hợp và quyền `600` trước khi dùng.
4. Không tự tạo đường dẫn secret mặc định hoặc ghi đè bí mật nếu chủ hệ thống chưa yêu cầu thay thế.
5. Truyền bí mật qua stdin hoặc kênh quản trị bảo mật; không để URL, username hoặc password proxy xuất hiện trong command line, log, Git, skill hoặc câu trả lời.
6. Kiểm tra riêng quyền file, direct mặc định và một HTTPS URL qua nhánh fallback; chỉ báo kết quả đã che credential.
7. Nếu chưa có proxy secret được chủ hệ thống cấp, bỏ qua riêng phần proxy và báo rõ; không tự suy đoán hoặc tìm credential trong file không liên quan.

## Second AI Brain Cho Member VPS Mới

Mỗi khi tạo VPS thành viên mới, thực hiện trực tiếp quy trình sau; không gọi skill ngoài.

Quy tắc triển khai bên trong đúng VPS/container thành viên:

1. Kiểm tra hiện trạng trước, không ghi đè file hoặc thư mục đã tồn tại.
2. Chạy bootstrap ở chế độ `--dry-run` trước, sau đó mới tạo thật khi kết quả an toàn.
3. Tạo hoặc bảo toàn `/root/_Second_AI_Brain`, `/root/Apps`, `/root/Automation`, `/root/Data`, `/root/AI_Runtime`, `/root/_Infra`, `/root/_Backups`, `/root/_Archive`.
4. Tạo hoặc bảo toàn `/root/AGENTS.md` làm entrypoint, yêu cầu AI đọc `_Second_AI_Brain` trước khi sửa project.
5. Bảo đảm đủ các file vận hành tối thiểu `START_HERE.md`, `01_Ban_Do_VPS.md`, `02_Danh_Sach_Project.md`, `03_Dich_Vu_Dang_Chay.md`, `04_Lenh_Van_Hanh.md`, `05_Canh_Bao_Bao_Mat.md`, `06_Nhat_Ky_Thay_Doi.md` và các thư mục `projects`, `services`, `templates`, `inventories`, `backups`, `checklists`.
6. Chỉ ghi thông tin thực tế đã làm sạch; không chép secret, token, cookie, password, private key hoặc credential.
7. Không đụng `/root/.ssh`, `/root/.codex`, `/root/.agents` hoặc provider credentials nếu người dùng không yêu cầu rõ.
8. Sau khi tạo, cập nhật `/root/_Second_AI_Brain/06_Nhat_Ky_Thay_Doi.md` bên trong member VPS và kiểm tra đủ cấu trúc.
9. Mọi đường dẫn `/root/...` trong phần này là đường dẫn bên trong container `user-<ten_user>`, không phải host chính.

Dry-run thủ công khi VPS đích không có bootstrap script:

```bash
for path in /root/_Second_AI_Brain /root/Apps /root/Automation /root/Data /root/AI_Runtime /root/_Infra /root/_Backups /root/_Archive /root/AGENTS.md; do
  if [ -e "$path" ]; then printf 'KEEP %s\n' "$path"; else printf 'CREATE %s\n' "$path"; fi
done
```

Chạy thật chỉ tạo phần còn thiếu bằng `mkdir -p`; các file Markdown mới phải là skeleton không chứa secret. Không ghi đè file hiện có bằng template chung.

## Workflow Tích Hợp Bắt Buộc

Khi tạo VPS thành viên mới, thực hiện theo đúng thứ tự:

1. Đọc mục Token Codex trong skill chính này; không gọi skill ngoài.
2. Nhận API key Token Codex qua biến môi trường bảo mật hoặc dùng provisioning backend đã xác minh tồn tại; không gọi đường dẫn local bị thiếu.
3. Nếu provisioning sinh key mới, lưu output một lần vào file quyền `600`, không đưa full key vào chat hoặc log chung.
4. Thực hiện hai mục tích hợp **Shared Fallback Proxy** và **Second AI Brain Cho Member VPS Mới** trong skill này.
5. Preflight tên container, image, SSH port, web port, volume và lệnh provisioning thực tế.
6. Tạo container/member rồi nạp API qua `TOKEN_CODEX_API_KEY` hoặc `CUSTOM_PROVIDER_API_KEY` mà không in key.
7. Cấu hình dashboard public, Second AI Brain và shared fallback proxy.
8. Validate provider/model Token Codex, OpenClaw, public HTTP 200, gateway/channel, Second AI Brain và proxy fallback.
9. Bàn giao VPS cùng email/mật khẩu Token Codex và link `https://codex.anhlaptrinh.vn/` để xem credit.

## Chuẩn bị Token Codex trước member VPS

API key Token Codex là bắt buộc cho member OpenClaw đầy đủ. Ưu tiên nhận qua `TOKEN_CODEX_API_KEY`; chấp nhận `CUSTOM_PROVIDER_API_KEY` để tương thích. Không yêu cầu email nếu người dùng đã cung cấp API key hợp lệ. Ba model được chấp nhận duy nhất là `GPT-5.6-sol`, `GPT-5.6-terra` và `GPT-5.6-luna`; phải giữ nguyên chữ hoa, chữ thường và dấu chấm.

Kiểm tra key không lộ secret:

```bash
node <<'NODE'
const apiKey = process.env.TOKEN_CODEX_API_KEY || process.env.CUSTOM_PROVIDER_API_KEY;
if (!apiKey) throw new Error('Thiếu TOKEN_CODEX_API_KEY hoặc CUSTOM_PROVIDER_API_KEY');
fetch('https://codex.anhlaptrinh.vn/v1/models', {
  headers: { Authorization: `Bearer ${apiKey}` }
}).then(async (response) => {
  const payload = response.ok ? await response.json() : {};
  const models = Array.isArray(payload.data) ? payload.data : [];
  const required = ['GPT-5.6-sol', 'GPT-5.6-terra', 'GPT-5.6-luna'];
  const available = new Set(models.map((item) => String(item?.id ?? item)));
  const missing = required.filter((model) => !available.has(model));
  console.log(`models_http=${response.status} missing_count=${missing.length}`);
  if (!response.ok || missing.length) process.exitCode = 1;
}).catch((error) => {
  console.error(`token_codex_check_error=${error.message}`);
  process.exitCode = 1;
});
NODE
```

Nếu cần tạo tài khoản/key mới, chỉ chạy provisioning backend sau khi đã xác minh project, command, database và chế độ dry-run thực sự tồn tại trên VPS hiện tại. Nếu backend không có, dừng bước cấp tài khoản và dùng key người dùng/quản trị đã cung cấp; không tự dựng đường dẫn hoặc command giả định. Key mới chỉ được lưu trong file quyền `600` và không chép vào skill, README, nhật ký hoặc câu trả lời.

## Kết nối Token Codex bắt buộc

Dùng API tương thích OpenAI cho OpenClaw, Codex trong Antigravity, Hermes Agent và mã nguồn riêng. Khi skill này cấu hình Token Codex, bắt buộc giữ nguyên các giá trị sau:

- **3 MODEL ĐƯỢC CHẤP NHẬN:** `GPT-5.6-sol`, `GPT-5.6-terra`, `GPT-5.6-luna`.
- **Base URL:** `https://codex.anhlaptrinh.vn/v1`.
- **API:** `openai-completions`.
- **API key:** chỉ đọc từ biến môi trường `TOKEN_CODEX_API_KEY`; không ghi key thật vào source, config mẫu, log, tài liệu hoặc câu trả lời.
- **Không thêm `/v1` lần thứ hai** khi ghép endpoint; URL chat phải là `https://codex.anhlaptrinh.vn/v1/chat/completions`.

Quy trình an toàn gồm bốn bước: tạo/đăng nhập tài khoản Token Codex, nạp hạn mức, tạo API key, rồi lưu key vào biến môi trường hoặc file env quyền `600`. Sau khi đổi key hoặc provider, luôn validate và restart Gateway bằng shell đã source file env; không restart bằng lệnh chỉ đặt `HOME` vì sẽ làm `${TOKEN_CODEX_API_KEY}` bị rỗng.

Mẫu provider OpenClaw chuẩn nằm ở phần **Cấu hình Custom Provider Token Codex** bên dưới và là nguồn chính khi có khác biệt với cấu hình cũ.

## Checklist hệ thống bắt buộc khi cần xuất ảnh

Nếu user báo lỗi không convert được SVG sang PNG/JPG, hoặc lỗi shell dạng `Refusing to traverse symlink in exec approvals path...`, đọc và làm theo `references/svg-png-shell-checklist.md`.

Với lỗi approvals path, kiểm tra `HOME` của tiến trình Gateway trước khi sửa quyền file. Kết quả bắt buộc là `/root`; không dùng `chmod 777` và không xóa symlink để chữa lỗi này.

Tóm tắt bắt buộc:

1. Kiểm tra đang ở đường dẫn thật bằng `readlink -f .`; tránh chạy trong symlink path.
2. Kiểm tra `/tmp` phải là `1777`; nếu sai thì chạy `chmod 1777 /tmp`.
3. Nếu thiếu tool, cài `imagemagick`, `librsvg2-bin`, `python3`.
4. Test bằng cả `convert` và `rsvg-convert` với SVG mẫu.
5. Nếu làm trong member VPS, chạy checklist bên trong container `user-<ten_user>`.

## Fallback tạo ảnh khi thiếu image provider key

Nếu user yêu cầu tạo ảnh/poster/banner và bot/OpenClaw báo thiếu API key cho OpenAI/Gemini/Fal/OpenRouter image provider, không dừng ngay. Đọc `references/local-svg-python-image-fallback.md` và ưu tiên tạo ảnh bằng SVG/Python local giống member mẫu `anhlaptrinh`.

Quy tắc:

1. Poster, banner, thumbnail, cover khóa học, ảnh chữ, infographic đơn giản: tạo bằng SVG/Python local.
2. Xuất PNG bằng `rsvg-convert`; fallback sang `convert`.
3. Lưu file trong `/root/.openclaw/workspace` của container member VPS.
4. Chỉ yêu cầu API key image provider nếu user cần ảnh photorealistic/AI-art phức tạp.
5. Khi thiếu provider key, nói rõ “em sẽ fallback sang SVG/Python local” rồi tạo file, không báo dừng.

## Preflight member VPS

`manage-user.sh` hiện không có `--dry-run`. Trước khi tạo, kiểm tra thủ công và chỉ tiếp tục khi tên/port chưa bị dùng:

```bash
MEMBER_NAME='<ten_user>'
MEMBER_PASSWORD="${MEMBER_NAME}123"
SSH_PORT='<ssh_port>'
WEB_PORT='<web_port>'
SKILL_DIR='/root/.agents/skills/tao-tro-ly-openclaw-windows-macos-linux'
MEMBER_ROOT="/root/docker-users/data/${MEMBER_NAME}/root"
test -x /root/docker-users/manage-user.sh
test -x "$SKILL_DIR/scripts/sync_all_skills_to_root.py"
test -d /root/.agents/skills
docker ps -a --format '{{.Names}}' | grep -Fx "user-${MEMBER_NAME}" && exit 1 || true
ss -ltnH | awk '{print $4}' | grep -Eq "[:.](${SSH_PORT}|${WEB_PORT})$" && exit 1 || true
docker image inspect vps-user-env:latest >/dev/null
install -d -m 700 "$MEMBER_ROOT"
```

## Tạo container member VPS

Tạo container bằng đúng interface hiện tại, nhưng không dừng ở bước này:

```bash
/root/docker-users/manage-user.sh create '<ten_user>' '<ten_user>123' '<ssh_port>'
ufw allow '<ssh_port>/tcp'
/root/docker-users/manage-user.sh info '<ten_user>'
```

Lệnh trên chỉ map SSH. Trước khi cài OpenClaw, bắt buộc xác minh container có thêm mapping `<web_port>:80` và volume `/root/docker-users/data/<ten_user>/root:/root`. Root volume này đã chứa workspace `/root/.openclaw/workspace`, vì vậy không dùng `/workspace` làm OpenClaw workspace. Nếu provisioning hiện tại chưa mount `/root`, backup cấu hình rồi recreate container với volume đúng; không cài OpenClaw vào filesystem tạm của container.

Kiểm tra mount bắt buộc:

```bash
docker inspect user-<ten_user> --format '{{range .Mounts}}{{println .Source "->" .Destination}}{{end}}' | grep -F -- '-> /root'
docker inspect user-<ten_user> --format '{{range $p, $conf := .NetworkSettings.Ports}}{{println $p $conf}}{{end}}' | grep -F '80/tcp'
```

Sau khi volume `/root` đúng, cài OpenClaw trong container và onboard trực tiếp vào root. Truyền Gateway Token bằng SecretRef environment, không đặt giá trị thật trong command mẫu:

```bash
docker exec -e HOME=/root user-<ten_user> sh -lc '
  test "$(id -u)" -eq 0
  command -v node
  command -v npm
  command -v python3
  npm install -g openclaw@2026.7.1-2
  openclaw --version
'

docker exec \
  -e HOME=/root \
  -e OPENCLAW_GATEWAY_TOKEN \
  user-<ten_user> sh -lc '
    test -n "$OPENCLAW_GATEWAY_TOKEN"
    openclaw onboard \
      --non-interactive \
      --accept-risk \
      --mode local \
      --auth-choice skip \
      --skip-channels \
      --skip-search \
      --no-install-daemon \
      --skip-health \
      --workspace /root/.openclaw/workspace \
      --gateway-bind loopback \
      --gateway-auth token \
      --gateway-token-ref-env OPENCLAW_GATEWAY_TOKEN \
      --suppress-gateway-token-output \
      --gateway-port 18789
  '
```

Đồng bộ toàn bộ skill từ root nguồn của VPS chính vào root volume của member, rồi kiểm tra cả trên host và trong container:

```bash
MEMBER_ROOT='/root/docker-users/data/<ten_user>/root'
SKILL_DIR='/root/.agents/skills/tao-tro-ly-openclaw-windows-macos-linux'
python3 "$SKILL_DIR/scripts/sync_all_skills_to_root.py" \
  --openclaw-root "$MEMBER_ROOT/.openclaw" \
  --source /root/.agents/skills \
  --source /root/.codex/skills
python3 "$SKILL_DIR/scripts/sync_all_skills_to_root.py" \
  --openclaw-root "$MEMBER_ROOT/.openclaw" \
  --source /root/.agents/skills \
  --source /root/.codex/skills \
  --check
docker exec -e HOME=/root user-<ten_user> openclaw skills check
docker exec -e HOME=/root user-<ten_user> openclaw config validate
```

Không start Gateway nếu bất kỳ lệnh cài đặt, sync, `--check`, `skills check` hoặc config validate nào thất bại.

Provider sau khi container tồn tại phải dùng:

- `TOKEN_CODEX_API_KEY` hoặc `CUSTOM_PROVIDER_API_KEY`: API key thật, chỉ ghi vào config member, không in ra log.
- Provider ID: `token-codex`.
- Base URL: `https://codex.anhlaptrinh.vn/v1`.
- Model IDs: `GPT-5.6-sol`, `GPT-5.6-terra`, `GPT-5.6-luna`.
- Model input: `text+image`.
- `maxTokens`: `4096`.

Không ghi token thật vào skill, README, nhật ký, câu trả lời, Git hoặc file dùng chung. Nếu lưu Telegram settings, token/chat ID chỉ nằm trong root runtime `/root/.openclaw/` với quyền `600`.

## Cấu hình Telegram allowlist thủ công

Nếu cần đổi một trợ lý đã tạo từ `pairing` sang `allowlist`, sửa đúng config trong container member VPS, không sửa OpenClaw host chính:

```bash
docker exec -i -e HOME=/root user-<ten_user> node <<'NODE'
const fs = require('fs');
const path = '/root/.openclaw/openclaw.json';
const accountId = '<ten_user>';
const chatId = '<telegram_chat_id>';
const defaultOwnerIds = ['7919819873', '6980864856', '8342048167'];
const extraIds = chatId.startsWith('<') ? [] : [chatId];
const allowedIds = [...new Set([...defaultOwnerIds, ...extraIds])];
const config = JSON.parse(fs.readFileSync(path, 'utf8'));
config.commands ??= {};
config.commands.ownerAllowFrom = defaultOwnerIds.map((id) => `telegram:${id}`);
config.commands.ownerDisplay = 'raw';
config.channels ??= {};
config.channels.telegram ??= {};
config.channels.telegram.dmPolicy = 'pairing';
config.channels.telegram.allowFrom = Array.isArray(config.channels.telegram.allowFrom) ? config.channels.telegram.allowFrom : [];
for (const id of allowedIds) {
  if (!config.channels.telegram.allowFrom.includes(id)) config.channels.telegram.allowFrom.push(id);
}
config.channels.telegram.accounts ??= {};
config.channels.telegram.accounts[accountId] ??= {};
const account = config.channels.telegram.accounts[accountId];
account.enabled = true;
account.dmPolicy = 'pairing';
account.allowFrom = Array.isArray(account.allowFrom) ? account.allowFrom : [];
for (const id of allowedIds) {
  if (!account.allowFrom.includes(id)) account.allowFrom.push(id);
}
fs.writeFileSync(path, JSON.stringify(config, null, 2) + '\n');
NODE
```

Không dùng key `allowlist` trong OpenClaw config vì `openclaw config validate` báo invalid; key đúng là `allowFrom`.
Nếu người dùng chủ động yêu cầu bộ owner/approver khác, thay `defaultOwnerIds` bằng đúng danh sách đã xác nhận và cập nhật đồng bộ approval targets; không tự giữ hoặc thêm ID mặc định ngoài yêu cầu đó.

## Cấu hình Telegram Group ID khi tạo nhân viên

Khi người dùng cung cấp một hoặc nhiều Telegram Group ID lúc tạo nhân viên, coi đây là input bắt buộc của quy trình tạo và thực hiện toàn bộ các bước sau:

Trước khi thao tác, đọc `references/member-vps-creation-checklist.md` và dùng checklist đó để đối chiếu đầu vào, preflight, runtime và tiêu chí hoàn tất.

1. Thu thập tên member, Telegram `accountId`, user ID chủ bot dùng cho DM, và từng Group ID dạng string. Mặc định `requireMention: false`; chỉ đổi thành `true` khi người dùng yêu cầu. Nhận bot token và credential qua kênh bảo mật, không ghi vào checklist hoặc báo cáo.
2. Đặt `groupPolicy: "allowlist"` tại đúng cấp Telegram/account theo schema của phiên bản OpenClaw đang cài.
3. Thêm từng Group ID vào cả `channels.telegram.groups` và `channels.telegram.accounts.<accountId>.groups`; đặt `enabled: true`, `requireMention` theo yêu cầu và `allowFrom: ["*"]` để mọi thành viên trong đúng group được gọi bot.
4. Không bỏ trống group `allowFrom`: OpenClaw hiện hành có thể fallback về account/DM `allowFrom` và vô tình chỉ cho user chủ bot. Không đưa Telegram user ID chủ bot vào group `allowFrom` nếu mục tiêu là mở cho mọi thành viên.
5. Tạo binding từ đúng Telegram `accountId` tới agent `main` cho từng Group ID.
6. Mỗi binding group phải có `match.peer.kind: "group"` và `match.peer.id` là Group ID dạng string.
7. Tạo một binding riêng cho mỗi group; không gộp nhiều Group ID vào một binding.
8. Trước khi thêm, kiểm tra toàn bộ `bindings` và không tạo bản ghi trùng bộ khóa `agentId + channel + accountId + peer.kind + peer.id`.
9. Chạy `openclaw config validate` thành công trước khi restart gateway. Nếu validate lỗi, không restart và không báo cấu hình đã hoàn tất.
10. Kiểm tra BotFather `Group Privacy` đã tắt nếu group cần nhận tin nhắn thường không mention. Việc này cần người quản trị bot xác nhận hoặc thao tác bằng `/setprivacy` → chọn bot → `Disable`.
11. Sau restart, chạy `openclaw gateway status` và `openclaw channels status --probe`, rồi kiểm tra log có inbound từ đúng Group ID và outbound gửi thành công.
12. Không báo thành công hoàn toàn nếu mới chỉ validate/configure mà chưa thấy cả inbound và outbound thực tế.

Mẫu binding cho một group:

```json
{
  "agentId": "main",
  "match": {
    "channel": "telegram",
    "accountId": "<telegram_account_id>",
    "peer": {
      "kind": "group",
      "id": "<telegram_group_id>"
    }
  }
}
```

Thứ tự kiểm tra bắt buộc:

```bash
docker exec user-<ten_user> sh -lc 'set -a; . /root/.openclaw/token-codex.env; set +a; HOME=/root openclaw config validate'
docker exec user-<ten_user> tmux kill-session -t openclaw 2>/dev/null || true
docker exec user-<ten_user> tmux new-session -d -s openclaw sh -lc 'set -a; . /root/.openclaw/token-codex.env; set +a; HOME=/root openclaw skills check; exec env HOME=/root openclaw gateway run'
sleep 8
docker exec user-<ten_user> sh -lc 'set -a; . /root/.openclaw/token-codex.env; set +a; HOME=/root openclaw gateway status'
docker exec -e HOME=/root user-<ten_user> sh -lc 'journalctl --user -u openclaw-gateway.service --since "10 minutes ago" --no-pager -o cat 2>/dev/null | rg -i "telegram:group|inbound|outbound send ok" || true'
```

Nếu gateway trong container không chạy bằng user systemd, đọc log của tmux/process hoặc log OpenClaw tương ứng. Yêu cầu người dùng gửi một tin nhắn thử trong từng group; nếu `requireMention: false`, phải thử tin nhắn không mention. Chỉ báo **hoàn tất cấu hình, chờ xác nhận thực tế** khi chưa có tin thử; chỉ báo **hoàn tất hoàn toàn** sau khi thấy inbound và outbound của đúng group.

Nếu không có inbound, kiểm tra lại Group ID hiện tại, binding, group allowlist, user `allowFrom` và BotFather Privacy Mode. Nếu có inbound nhưng không có phản hồi, kiểm tra routing tới `main`, provider/model và log gateway.

## Sửa bot Telegram không trả lời trong group

Dùng phần này khi user báo bot Telegram im lặng trong group, mọi người nhắn không được, bot chỉ trả lời DM hoặc đã sửa `requireMention`/`allowFrom` nhiều lần vẫn không hoạt động. Không tiếp tục đổi policy theo phỏng đoán; kiểm tra tuần tự quyền group, binding, runtime Gateway và log tin thử mới.

### 1. Xác định đúng runtime và config hiệu lực

- Xác định container/process đang chạy bot và `HOME` thật của `openclaw-gateway`; không mặc định `HOME=/root` cho một container legacy đang dùng `/home/<member>`.
- Chuẩn provisioning mới vẫn là `root`, `HOME=/root`. Với sự cố production legacy, không migrate runtime trong lúc chữa lỗi; dùng đúng `HOME` và config hiện tại, lên kế hoạch chuẩn hóa riêng sau.
- So sánh cấu hình chọn lọc với một member cùng image/version đang trả lời group tốt; chỉ so `channels.telegram`, `bindings`, account ID, group entry và cách chạy Gateway, không in token.

```bash
docker exec user-<ten_user> sh -lc '
pid=$(pgrep -f "^openclaw-gateway" | head -n1 || true)
echo "gateway_pid=${pid:-missing}"
if [ -n "$pid" ]; then
  tr "\0" "\n" </proc/$pid/environ | grep -E "^(HOME|PWD)="
  readlink /proc/$pid/cwd
fi
'
```

### 2. Kiểm tra đủ quyền group và binding routing

Group cần có cùng cấu trúc ở top-level và account scope:

```json
{
  "enabled": true,
  "requireMention": false,
  "allowFrom": ["*"]
}
```

Giữ `groupPolicy: "allowlist"` tại cấp Telegram/account để không mở group khác. Sau đó kiểm tra binding:

```bash
HOME=<EFFECTIVE_HOME> openclaw agents bindings
```

Nếu thiếu route, thêm đúng một binding cho mỗi group theo mẫu ở phần **Cấu hình Telegram Group ID khi tạo nhân viên**:

- `agentId: "main"`
- `match.channel: "telegram"`
- `match.accountId`: đúng account đang polling
- `match.peer.kind: "group"`
- `match.peer.id`: đúng Group ID dạng string

Trường hợp đã chứng minh thực tế: group entry và wildcard đúng nhưng thiếu binding group → `main`; sửa policy lặp lại không giải quyết cho tới khi thêm binding và restart Gateway sạch.

### 3. Phân loại lỗi bằng log mới

Yêu cầu user gửi một tin thường không mention trong lúc đang theo dõi log. Không dùng log cũ trước thời điểm sửa để kết luận trạng thái hiện tại.

```bash
docker exec user-<ten_user> sh -lc \
  'tail -n 0 -F /tmp/openclaw/openclaw-$(date -u +%F).log | grep --line-buffered -Ei -- "<GROUP_ID>|skipping group message|not-allowed|not-mentioned|Inbound message telegram:group|telegram outbound send ok|telegram.*(error|conflict)"'
```

Phân loại:

- Có `not-allowed`: sai/missing group entry, sender `allowFrom`, account scope hoặc Group ID đã migrate.
- Không có inbound nào: kiểm tra đúng group hiện tại, bot còn trong group, BotFather Privacy Mode, quyền admin khi cần, polling `connected`, token có bị process khác polling gây `409 Conflict` hay không.
- Có inbound nhưng không tạo session group: kiểm tra binding account/group → `main`.
- Có session `agent:main:telegram:group:<GROUP_ID>` nhưng không outbound: kiểm tra provider/model, tool policy, lỗi agent và quota/API.
- Có inbound, session group và outbound: lỗi đã xử lý; ghi lại thời gian test và user xác nhận.

### 4. Restart Gateway đúng cơ chế đang dùng

Ưu tiên restart đúng tmux/systemd/process manager hiện hữu; không mặc định `docker restart` sẽ tự khởi động OpenClaw. Một số image member chỉ supervise SSH/nginx/XRDP, vì vậy container có thể `Up` nhưng không có process `openclaw-gateway`.

Với chuẩn member mới dùng tmux/root, dùng lệnh restart chuẩn đã nêu trong skill. Chỉ dùng fallback sau khi xác minh Gateway trước đó là process tách nền, không thuộc tmux/systemd/supervisor:

```bash
docker exec -d user-<ten_user> sh -lc '
cd /
set -a
[ -f <EFFECTIVE_HOME>/.openclaw/token-codex.env ] && . <EFFECTIVE_HOME>/.openclaw/token-codex.env
set +a
HOME=<EFFECTIVE_HOME> nohup openclaw gateway run </dev/null >>/tmp/openclaw-gateway-launch.log 2>&1 &
'
```

Sau restart, chờ ít nhất một chu kỳ polling khoảng `45-60` giây nếu probe tạm báo `disconnected`, rồi kiểm tra lại:

```bash
HOME=<EFFECTIVE_HOME> openclaw config validate
HOME=<EFFECTIVE_HOME> openclaw agents bindings
HOME=<EFFECTIVE_HOME> openclaw gateway probe
HOME=<EFFECTIVE_HOME> openclaw channels status --probe
```

Chỉ báo hoàn tất khi Telegram là `running`, `connected`, polling `works`, binding đúng và tin thử tạo session group thực tế. Backup config trước khi sửa và cập nhật nhật ký production; không tự gửi tin Telegram thật nếu user chưa cho phép.

Khi phát hiện Group ID đổi do group chuyển thành supergroup hoặc cần kiểm tra JSON, dùng quy trình tích hợp sau:

1. Tạo `/root/_Backups/openclaw/` quyền phù hợp nếu chưa có, rồi backup `openclaw.json` vào đó trước khi sửa.
2. Xem log gateway trong 7 ngày gần nhất, tìm `Group migrated`, `Migrating group config` và `telegram:group:<id>` để xác định ID mới thật.
3. Giữ ID cũ, thêm ID mới vào `channels.telegram.groups` và `channels.telegram.accounts.<accountId>.groups`; group mới phải có `requireMention: false` nếu user muốn nhắn không mention.
4. Giữ wildcard `"*": {"requireMention": true}` để group chưa xác minh không tự mở.
5. Kiểm tra không trùng binding và chạy cả `python3 -m json.tool <config>` lẫn `openclaw config validate`; chỉ restart sau khi cả hai đều đạt.
6. Sau hot reload/restart, kiểm tra inbound và outbound của ID mới; không báo hoàn tất chỉ vì JSON hợp lệ.

Approve pairing nếu user đã nhắn bot và có pairing code:

```bash
docker exec -e HOME=/root user-<ten_user> openclaw pairing approve --channel telegram --account <ten_user> <PAIRING_CODE>
```

## Đăng nhập Zalo Personal/Zalo User và gửi QR qua Telegram

Áp dụng khi người dùng muốn OpenClaw trong member VPS dùng tài khoản Zalo cá nhân, đặc biệt khi QR hết hạn nhanh hoặc việc mở QR qua web mất thời gian. Workflow QR, backup, policy, cleanup và kiểm tra đều nằm trong các mục bên dưới; với member VPS đã có Telegram thì ưu tiên gửi ảnh QR trực tiếp tới Telegram allowlist.

### Đầu vào và preflight

1. Xác định đúng container `user-<ten_user>` và kiểm tra đang running.
2. Kiểm tra OpenClaw version; plugin Zalo phải dùng cùng version, không dùng `latest`.
3. Xác nhận Telegram account hiện có `enabled`, có `tokenFile` hoặc bot token, và có ít nhất một Telegram user ID dạng số trong `allowFrom`.
4. Không coi Telegram user ID là Zalo user ID; đây là hai hệ định danh khác nhau.
5. Không in bot token, cookie Zalo, QR raw payload hoặc nội dung credential ra terminal, log, skill hay câu trả lời.

Lệnh kiểm tra:

```bash
docker ps -a --filter name='^/user-<ten_user>$'
docker exec -e HOME=/root user-<ten_user> openclaw --version
docker exec -e HOME=/root user-<ten_user> openclaw channels status --probe
```

### Backup bắt buộc

Backup config và credential Zalo nếu đã tồn tại trước khi cài plugin, login lại hoặc đổi policy:

```bash
TS=$(date -u '+%Y%m%dT%H%M%SZ')
BACKUP_DIR="/root/_Backups/<ten_user>_zalouser_$TS"
install -d -m 700 "$BACKUP_DIR"
docker exec -e HOME=/root user-<ten_user> sh -lc \
  'tar -C /root/.openclaw -czf - openclaw.json $(test -d credentials/zalouser && printf credentials/zalouser || true)' \
  > "$BACKUP_DIR/openclaw_before.tar.gz"
chmod 600 "$BACKUP_DIR/openclaw_before.tar.gz"
```

### Cài plugin Zalo đúng version

Với OpenClaw pin `2026.7.1-2`:

```bash
docker exec -e HOME=/root user-<ten_user> \
  openclaw plugins install --pin '@openclaw/zalouser@2026.7.1'
docker exec -e HOME=/root user-<ten_user> openclaw config validate
```

Trước khi cài plugin, chạy `npm view @openclaw/zalouser@2026.7.1 peerDependencies --json` và xác nhận core `2026.7.1-2` đáp ứng peer dependency `openclaw >=2026.7.1`.

### Gửi QR mới trực tiếp vào Telegram allowlist

Tạo một watcher tạm trong `/tmp` bên trong container trước khi chạy login. Watcher phải:

- Đọc `/root/.openclaw/openclaw.json` để tìm Telegram account đang enabled.
- Đọc bot token từ `tokenFile` bên trong process; không truyền token trong command line và không ghi token vào log.
- Lấy Telegram recipient từ `channels.telegram.accounts.<account>.allowFrom`, fallback về `channels.telegram.allowFrom`; chỉ nhận ID dạng số.
- Theo dõi `/tmp/openclaw/openclaw-zalouser-qr-default.png` và các file khớp `*zalouser*qr*.png`.
- Ghi nhận checksum của file có sẵn khi watcher bắt đầu để không gửi QR cũ.
- Poll khoảng `0.25` đến `1` giây; khi checksum thay đổi, gọi Telegram Bot API `sendPhoto` ngay.
- Nếu có QR mới thay QR cũ, gửi ảnh mới trước rồi mới xóa tin nhắn QR cũ nếu có `message_id`.
- Log chỉ ghi bot username, số recipient, tên file và trạng thái gửi; không ghi token, Telegram ID hoặc QR payload.
- Chỉ chạy trong thời gian login; phải dừng và xóa watcher sau khi thành công hoặc hủy.

Caption nên ngắn và rõ: `QR đăng nhập Zalo Personal mới của OpenClaw <ten_user>. Hãy quét ngay vì QR có thời hạn ngắn.`

Nếu Telegram chưa sẵn sàng, fallback sang web QR theo thứ tự: copy QR mới từ `/tmp/openclaw/openclaw-zalouser-qr-default.png` tới file public `/var/www/html/openclaw-qr.png`, đặt quyền đọc phù hợp, kiểm tra URL `https://<domain>/openclaw-qr.png`, rồi xóa QR sau khi đăng nhập thành công. Không mở URL public nếu đã gửi Telegram được; không ghi QR raw payload, cookie hoặc token vào log.

### Tạo QR và chờ đăng nhập

Ưu tiên lệnh login riêng thay vì chạy toàn bộ `openclaw onboard`:

```bash
docker exec -it -e HOME=/root user-<ten_user> \
  openclaw channels login --channel zalouser --verbose
```

Khi terminal báo:

```text
Scan QR image: /tmp/openclaw/openclaw-zalouser-qr-default.png
```

watcher phải gửi ảnh tới Telegram allowlist gần như ngay lập tức. Giữ phiên PTY mở cho tới khi OpenClaw báo `Login successful`. Nếu QR hết hạn, tạo QR mới; watcher tự nhận checksum mới và gửi lại.

Sau login, credential thường nằm tại:

```text
/root/.openclaw/credentials/zalouser/credentials.json
```

Không đọc/in cookie thật. Chỉ kiểm tra file tồn tại và quyền truy cập phù hợp.

### Chọn policy Zalo

Nếu user chưa yêu cầu, giữ DM `pairing`. Nếu user yêu cầu DM allowlist và group open, làm đúng thứ tự sau:

1. Yêu cầu người dùng nhắn Zalo Personal bot một tin để tạo pairing request.
2. Chạy `openclaw pairing list zalouser`.
3. Đối chiếu tên người gửi với user; không approve request khác dù xuất hiện cùng lúc.
4. Approve đúng pairing code.
5. Lấy đúng `userId` của sender vừa approve và ghi rõ vào `channels.zalouser.allowFrom`.
6. Đặt `channels.zalouser.dmPolicy: allowlist` và `channels.zalouser.groupPolicy: open`.

Lệnh mẫu:

```bash
docker exec -e HOME=/root user-<ten_user> openclaw pairing list zalouser
docker exec -e HOME=/root user-<ten_user> \
  openclaw pairing approve zalouser <PAIRING_CODE>
docker exec -e HOME=/root user-<ten_user> \
  openclaw config set channels.zalouser.dmPolicy allowlist
docker exec -e HOME=/root user-<ten_user> \
  openclaw config set channels.zalouser.allowFrom '["<ZALO_USER_ID>"]' --strict-json
docker exec -e HOME=/root user-<ten_user> \
  openclaw config set channels.zalouser.groupPolicy open
```

Lưu ý với OpenClaw hiện hành: `pairing approve` có thể ghi sender vào file credential `zalouser-default-allowFrom.json`, nhưng `openclaw config validate` vẫn có thể cảnh báo nếu `channels.zalouser.allowFrom` rỗng. Vì vậy, khi dùng `dmPolicy: allowlist`, bắt buộc đồng bộ sender ID vào `channels.zalouser.allowFrom`; không chỉ approve pairing rồi dừng.

Không dùng `allowFrom: ["*"]` cho Zalo DM. Wildcard DM sẽ mở tin nhắn riêng ngoài ý muốn.

### Chỉ mở một Zalo group và không cần mention

Khi user yêu cầu bot chỉ phản hồi trong một group Zalo cụ thể mà thành viên không cần mention, không dùng `groupPolicy: open` vì giá trị đó mở tất cả group mà tài khoản Zalo tham gia.

Trigger bắt buộc dùng phần này gồm các cách nói như: `Zalo group không cần mention`, `không cần tag bot vẫn trả lời`, `chỉ áp dụng group này`, `thêm Zalo Group ID`, `add group Zalo`, `requireMention false`, hoặc yêu cầu tương đương về việc bot đọc tin nhắn thường trong một group Zalo cụ thể.

1. Lấy Group ID thật bằng directory API; ưu tiên ID số, không dùng tên nếu không cần:

```bash
docker exec -e HOME=/root user-<ten_user> \
  openclaw directory groups list --channel zalouser --json
```

Output có thể trả `id: "group:<GROUP_ID>"`; key trong `channels.zalouser.groups` dùng phần số `<GROUP_ID>`.

2. Cấu hình route allowlist cho đúng group, cho mọi sender trong group đó và tắt mention:

```bash
docker exec -e HOME=/root user-<ten_user> \
  openclaw config set channels.zalouser.groupPolicy allowlist
docker exec -e HOME=/root user-<ten_user> \
  openclaw config set channels.zalouser.groupAllowFrom '["*"]' --strict-json
docker exec -e HOME=/root user-<ten_user> \
  openclaw config set 'channels.zalouser.groups["<GROUP_ID>"]' \
  '{"enabled":true,"requireMention":false}' --strict-json
```

Ý nghĩa và phạm vi:

- `groupPolicy: allowlist` chặn mọi group không có trong `channels.zalouser.groups`.
- `groups.<GROUP_ID>.enabled: true` chỉ mở đúng group đã chọn.
- `groups.<GROUP_ID>.requireMention: false` cho phép tin nhắn thường kích hoạt bot.
- `groupAllowFrom: ["*"]` cho phép mọi thành viên gửi tin trong các group đã route-allowlist; không mở DM và không mở group ngoài danh sách.
- Không bỏ `groupAllowFrom` khi `groupPolicy: allowlist`: OpenClaw hiện hành có thể chặn toàn bộ sender group vì group sender allowlist rỗng.
- Nếu chỉ có một group trong `groups`, wildcard sender vẫn chỉ có hiệu lực trong group đó do route policy chạy trước sender policy.

3. Validate, restart và kiểm tra:

```bash
docker exec user-<ten_user> sh -lc 'set -a; . /root/.openclaw/token-codex.env; set +a; HOME=/root openclaw config validate'
docker exec user-<ten_user> tmux kill-session -t openclaw 2>/dev/null || true
sleep 1
docker exec user-<ten_user> tmux new-session -d -s openclaw sh -lc 'set -a; . /root/.openclaw/token-codex.env; set +a; HOME=/root openclaw skills check; exec env HOME=/root openclaw gateway run'
sleep 8
docker exec user-<ten_user> sh -lc 'set -a; . /root/.openclaw/token-codex.env; set +a; HOME=/root openclaw channels status --probe'
```

Yêu cầu user gửi một tin nhắn chữ bình thường trong group, không mention và không reply bot. Chỉ báo **cấu hình hoàn tất, chờ test thực tế** nếu chưa thấy inbound/outbound; chỉ báo **hoàn tất hoàn toàn** sau khi bot phản hồi tin không mention trong đúng group. Đồng thời thử một group Zalo khác nếu có để xác nhận group ngoài allowlist bị chặn.

### Restart, kiểm tra và dọn dẹp

```bash
docker exec user-<ten_user> sh -lc 'set -a; . /root/.openclaw/token-codex.env; set +a; HOME=/root openclaw config validate'
docker exec user-<ten_user> tmux kill-session -t openclaw 2>/dev/null || true
sleep 1
docker exec user-<ten_user> tmux new-session -d -s openclaw sh -lc 'set -a; . /root/.openclaw/token-codex.env; set +a; HOME=/root openclaw skills check; exec env HOME=/root openclaw gateway run'
sleep 8
docker exec user-<ten_user> sh -lc 'set -a; . /root/.openclaw/token-codex.env; set +a; HOME=/root openclaw channels status --probe'
```

Tiêu chí hoàn tất:

- Zalo Personal: `enabled`, `configured`, `running`, `works`.
- Nếu DM allowlist: probe hiển thị `dm:allowlist` và config có ít nhất một `allowFrom` đã xác minh.
- Nếu group open: `channels.zalouser.groupPolicy` là `open`.
- Telegram account cũ vẫn `running`, `works`, `audit ok`; trạng thái `disconnected` ngay sau restart có thể là tạm thời, chờ vài giây rồi probe lại.
- Không còn watcher tạm hoặc file `*zalouser*qr*.png` trong `/tmp/openclaw`.
- Pairing request của sender lạ không được approve.

Dọn file/process tạm sau thành công:

```bash
docker exec -e HOME=/root user-<ten_user> sh -lc '
  test -f /tmp/<ten_user>_zalo_qr_sender.pid && \
    kill "$(cat /tmp/<ten_user>_zalo_qr_sender.pid)" 2>/dev/null || true
  rm -f /tmp/<ten_user>_zalo_qr_sender.py \
        /tmp/<ten_user>_zalo_qr_sender.pid \
        /tmp/<ten_user>_zalo_qr_sender.log \
        /tmp/openclaw/openclaw-zalouser-qr-default.png
'
```

Sau thay đổi, cập nhật `/root/_Second_AI_Brain/06_Nhat_Ky_Thay_Doi.md`, nhưng không ghi bot token, Telegram/Zalo user ID thật, cookie hoặc QR payload.

## Chạy gateway bằng tmux trong member VPS

Trong container member VPS, cài tmux và chạy gateway theo yêu cầu chuẩn:

```bash
docker exec -e HOME=/root user-<ten_user> sh -lc 'apt update && apt install tmux -y'
docker exec user-<ten_user> tmux kill-session -t openclaw 2>/dev/null || true
docker exec user-<ten_user> tmux new-session -d -s openclaw sh -lc 'set -a; . /root/.openclaw/token-codex.env; set +a; HOME=/root openclaw skills check; exec env HOME=/root openclaw gateway run'
```

Kiểm tra:

```bash
docker exec user-<ten_user> sh -lc 'tmux ls; set -a; . /root/.openclaw/token-codex.env; set +a; HOME=/root openclaw gateway status; HOME=/root openclaw channels status --probe'
```

## Cấu hình Custom Provider Token Codex

Tham khảo schema từ một member đang chạy sau khi kiểm tra bằng `docker inspect`; không giả định member mẫu hoặc đường dẫn host cố định. Khi cấu hình member VPS mới, sửa config bên trong container `user-<ten_user>` tại `/root/.openclaw/openclaw.json` với `HOME=/root`.

Không ghi API key thật vào skill, README, nhật ký hoặc câu trả lời. Với member mới, lưu key vào `/root/.openclaw/token-codex.env` quyền `600`, rồi chỉ ghi chuỗi `${TOKEN_CODEX_API_KEY}` vào `openclaw.json`:

```bash
docker exec -e TOKEN_CODEX_API_KEY user-<ten_user> sh -lc '
  test -n "$TOKEN_CODEX_API_KEY"
  umask 077
  printf "TOKEN_CODEX_API_KEY=%s\n" "$TOKEN_CODEX_API_KEY" > /root/.openclaw/token-codex.env
  chmod 600 /root/.openclaw/token-codex.env
'
```

Mẫu script cấu hình đọc key từ biến môi trường hiện có; không chèn key trực tiếp vào heredoc hoặc command line:

```bash
docker exec -i \
  -e HOME=/root \
  -e TOKEN_CODEX_API_KEY \
  -e CUSTOM_PROVIDER_API_KEY \
  user-<ten_user> node <<'NODE'
const fs = require('fs');
const path = '/root/.openclaw/openclaw.json';
const config = JSON.parse(fs.readFileSync(path, 'utf8'));
const apiKey = process.env.TOKEN_CODEX_API_KEY || process.env.CUSTOM_PROVIDER_API_KEY;
if (!apiKey) throw new Error('Thiếu TOKEN_CODEX_API_KEY hoặc CUSTOM_PROVIDER_API_KEY');
config.agents ??= {};
config.agents.defaults ??= {};
config.agents.defaults.model = { primary: 'token-codex/GPT-5.6-sol' };
config.agents.defaults.imageModel = { primary: 'token-codex/GPT-5.6-sol' };
config.agents.defaults.imageGenerationModel = { primary: 'token-codex/GPT-5.6-sol' };
const modelIds = ['GPT-5.6-sol', 'GPT-5.6-terra', 'GPT-5.6-luna'];
config.agents.defaults.models = Object.fromEntries(modelIds.map((id) => [`token-codex/${id}`, config.agents.defaults.models?.[`token-codex/${id}`] || {}]));
config.models ??= {};
config.models.mode = 'merge';
config.models.providers ??= {};
config.models.providers['token-codex'] = {
  baseUrl: 'https://codex.anhlaptrinh.vn/v1',
  api: 'openai-completions',
  apiKey: '${TOKEN_CODEX_API_KEY}',
  models: modelIds.map((id) => ({
    id,
    name: id,
    contextWindow: 1050000,
    maxTokens: 4096,
    input: ['text', 'image'],
    cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0 },
    reasoning: false
  }))
};
delete config.models.providers.openai;
fs.writeFileSync(path, JSON.stringify(config, null, 2) + '\n');
fs.chmodSync(path, 0o600);
NODE
```

Sau khi cấu hình provider, validate và restart gateway tmux:

```bash
docker exec user-<ten_user> sh -lc 'set -a; . /root/.openclaw/token-codex.env; set +a; HOME=/root openclaw config validate'
docker exec user-<ten_user> tmux kill-session -t openclaw 2>/dev/null || true
docker exec user-<ten_user> tmux new-session -d -s openclaw sh -lc 'set -a; . /root/.openclaw/token-codex.env; set +a; HOME=/root openclaw skills check; exec env HOME=/root openclaw gateway run'
sleep 8
docker exec user-<ten_user> sh -lc 'set -a; . /root/.openclaw/token-codex.env; set +a; HOME=/root openclaw gateway status; HOME=/root openclaw models list | head'
```

## Xử lý lỗi Token Codex HTTP 401

Khi Telegram trả `Authentication failed (provider returned HTTP 401)`, không thay key ở container có tên gần giống theo phỏng đoán. Thực hiện đúng thứ tự:

1. Xác định container thực sự đang chạy bot từ log có dòng `starting provider (@<bot_username>)` và `Inbound message telegram`; không tìm bằng cách in bot token.
2. Kiểm tra file `/root/.openclaw/token-codex.env` tồn tại, quyền `600` và biến `TOKEN_CODEX_API_KEY` không rỗng; chỉ in `token_env=present` hoặc `token_env=missing`.
3. Gọi `GET /v1/models` và kiểm tra đủ ba model đúng case. Nếu HTTP `401`, key đã sai/hết hiệu lực hoặc đang nạp nhầm key; thay key trong file env, không ghi key thật vào `openclaw.json`.
4. Nếu `/models` trả `200` nhưng Gateway vẫn dùng provider/model cũ, chuyển cache `/root/.openclaw/agents/main/agent/models.json` sang file backup có timestamp; không xóa không backup.
5. Validate config trong shell đã source env, restart tmux bằng lệnh chuẩn ở trên, rồi xác nhận `gateway status`, `models list` và channel probe.
6. Không sửa 401 bằng cách nối thêm `/v1`, đổi model khác case, khôi phục provider cũ, thêm fallback provider hoặc đưa key literal vào JSON.

Kiểm tra endpoint chat của cả ba model mà không in key hay nội dung phản hồi:

```bash
docker exec user-<ten_user> sh -lc '
  set -a
  . /root/.openclaw/token-codex.env
  set +a
  HOME=/root node <<'"'"'NODE'"'"'
const apiKey = process.env.TOKEN_CODEX_API_KEY;
const models = ['GPT-5.6-sol', 'GPT-5.6-terra', 'GPT-5.6-luna'];
if (!apiKey) throw new Error('Thiếu TOKEN_CODEX_API_KEY');
(async () => {
  let failed = false;
  for (const model of models) {
    const response = await fetch('https://codex.anhlaptrinh.vn/v1/chat/completions', {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${apiKey}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        model,
        messages: [{ role: 'user', content: 'Reply OK' }],
        max_tokens: 2,
        stream: false
      })
    });
    console.log(`${model}_http=${response.status}`);
    if (!response.ok) failed = true;
  }
  if (failed) process.exitCode = 1;
})().catch((error) => {
  console.error(`token_codex_chat_check_error=${error.message}`);
  process.exitCode = 1;
});
NODE
'
```

## Kiểm tra và bật audio understanding cho member VPS

Token Codex là provider duy nhất. Không giả định endpoint có STT: trước khi bật audio, phải lấy danh sách model và chỉ bật khi có đúng `gpt-4o-mini-transcribe`. Nếu API không công bố model này, giữ audio ở trạng thái tắt để OpenClaw không gọi một model không tồn tại.

Lệnh dưới đây tự kiểm tra `/models`, không in API key, xóa provider `openai` cũ nếu có và cập nhật `/root/.openclaw/openclaw.json` an toàn:

```bash
docker exec -i -e HOME=/root user-<ten_user> node <<'NODE'
const fs = require('fs');
const path = '/root/.openclaw/openclaw.json';
const config = JSON.parse(fs.readFileSync(path, 'utf8'));
const transcriptionModel = 'gpt-4o-mini-transcribe';

config.models ??= {};
config.models.mode = config.models.mode || 'merge';
config.models.providers ??= {};
const provider = config.models.providers['token-codex'];

config.tools ??= {};
config.tools.media ??= {};

delete config.models.providers.openai;

async function main() {
  let modelAvailable = false;
  let modelCheck = 'missing-token-codex-api-key';

  if (provider?.apiKey) {
    const baseUrl = String(provider.baseUrl || 'https://codex.anhlaptrinh.vn/v1').replace(/\/+$/, '');
    try {
      const response = await fetch(`${baseUrl}/models`, {
        headers: { Authorization: `Bearer ${provider.apiKey}` }
      });
      modelCheck = `http-${response.status}`;
      if (response.ok) {
        const payload = await response.json();
        const listed = Array.isArray(payload.data)
          ? payload.data
          : Array.isArray(payload.models)
            ? payload.models
            : [];
        modelAvailable = listed.some((item) => String(item?.id ?? item?.name ?? item) === transcriptionModel);
      }
    } catch {
      modelCheck = 'request-failed';
    }
  }

  if (provider && Array.isArray(provider.models)) {
    provider.models = provider.models.filter((model) => model?.id !== transcriptionModel);
  }

  if (modelAvailable) {
    provider.models ??= [];
    provider.models.push({
      id: transcriptionModel,
      name: transcriptionModel,
      input: ['audio'],
      cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0 }
    });
    config.tools.media.audio = {
      enabled: true,
      language: 'vi',
      timeoutSeconds: 60,
      echoTranscript: true,
      echoFormat: '📝 "{transcript}"',
      models: [{
        type: 'provider',
        provider: 'token-codex',
        model: transcriptionModel,
        capabilities: ['audio'],
        language: 'vi'
      }]
    };
  } else {
    config.tools.media.audio = { enabled: false };
  }

  fs.writeFileSync(path, JSON.stringify(config, null, 2) + '\n');
  console.log(`audio_stt=${modelAvailable ? 'enabled' : 'disabled'} model_check=${modelCheck}`);
}

main().catch((error) => {
  console.error(`audio_config_error=${error.message}`);
  process.exitCode = 1;
});
NODE
```

Validate và restart gateway bằng tmux vì member VPS không dùng systemd user service cho OpenClaw:

```bash
docker exec user-<ten_user> sh -lc 'set -a; . /root/.openclaw/token-codex.env; set +a; HOME=/root openclaw config validate'
docker exec user-<ten_user> tmux kill-session -t openclaw 2>/dev/null || true
docker exec user-<ten_user> tmux new-session -d -s openclaw sh -lc 'set -a; . /root/.openclaw/token-codex.env; set +a; HOME=/root openclaw skills check; exec env HOME=/root openclaw gateway run'
sleep 8
docker exec user-<ten_user> sh -lc 'set -a; . /root/.openclaw/token-codex.env; set +a; HOME=/root openclaw gateway status; HOME=/root openclaw channels status --probe'
```

Đọc kết quả lệnh vá theo quy tắc:

1. `audio_stt=enabled`: `/models` có model STT; validate, restart Gateway rồi mới kiểm tra voice.
2. `audio_stt=disabled`: đây là trạng thái đúng khi model STT không được công bố, API lỗi hoặc thiếu credential; không tự bật lại audio.
3. `model_check=http-401` hoặc `http-403`: kiểm tra credential của provider `token-codex`, không in token.
4. `model_check=request-failed`: kiểm tra DNS/TLS/kết nối tới `https://codex.anhlaptrinh.vn/v1`.
5. Chỉ test transcription bằng file voice khi `audio_stt=enabled` và người dùng cho phép; không gửi/in nội dung audio riêng tư.

### Xử lý voice Zalo dạng AAC URL

Khi plugin `zalouser` chỉ trả URL `https://*.zdn.vn/*.aac`, không đưa URL đó trực tiếp vào endpoint STT. Chỉ chấp nhận HTTPS trên `zdn.vn` hoặc subdomain, giới hạn file tải xuống tối đa `25 MB`, dùng thư mục tạm và xóa file sau khi hoàn tất:

1. Cài `ffmpeg` trong đúng VPS/container có Zalo Personal; không cài cho member chỉ dùng Telegram.
2. Tải URL vào file tạm, chuyển bằng `ffmpeg` sang MP3 mono `16 kHz`.
3. Chỉ tiếp tục khi `/models` đã xác nhận `gpt-4o-mini-transcribe`; nếu không có, giữ audio disabled và dừng workflow.
4. Đọc API key từ provider `token-codex` trong `openclaw.json`, không in key.
5. Gọi `https://codex.anhlaptrinh.vn/v1/audio/transcriptions` với model `gpt-4o-mini-transcribe`, language `vi`, rồi chỉ trả transcript.
6. Xóa AAC/MP3 tạm ngay cả khi request lỗi; không ghi audio, URL riêng tư hoặc transcript vào log.

Nếu cần tự động hóa bước này, viết script ngay trong project member theo quy tắc trên; không cài hoặc gọi một skill voice riêng.

## Bật web search DuckDuckGo cho member VPS

Khi tạo trợ lý OpenClaw trong member VPS, luôn cấu hình DuckDuckGo làm search provider mặc định để bot trả lời được các câu hỏi cần tra cứu web tổng quát. Không dùng provider cần API key nếu người dùng chưa cung cấp rõ.

Triệu chứng cần áp dụng/sửa:

- Bot báo lỗi `web_search` hoặc `no provider is available`.
- `tools.web.search.enabled` đã bật nhưng `plugins.entries` chưa có search plugin khả dụng.
- `plugins.entries` chỉ bật Telegram/Zalo hoặc các plugin không phải search provider.

Cấu hình cần có trong container `user-<ten_user>` tại `/root/.openclaw/openclaw.json`:

```json
{
  "plugins": {
    "entries": {
      "duckduckgo": {
        "enabled": true
      }
    }
  },
  "tools": {
    "profile": "full",
    "web": {
      "search": {
        "enabled": true,
        "provider": "duckduckgo",
        "openaiCodex": {
          "enabled": true
        }
      }
    }
  }
}
```

Lệnh vá an toàn cho member VPS đã tạo:

```bash
docker exec -i -e HOME=/root user-<ten_user> node <<'NODE'
const fs = require('fs');
const path = '/root/.openclaw/openclaw.json';
const config = JSON.parse(fs.readFileSync(path, 'utf8'));
config.plugins ??= {};
config.plugins.entries ??= {};
config.plugins.entries.duckduckgo = { enabled: true };
config.tools ??= {};
config.tools.profile = 'full';
config.tools.web ??= {};
config.tools.web.search ??= {};
config.tools.web.search.enabled = true;
config.tools.web.search.provider = 'duckduckgo';
config.tools.web.search.openaiCodex ??= {};
config.tools.web.search.openaiCodex.enabled = true;
fs.writeFileSync(path, JSON.stringify(config, null, 2) + '\n');
NODE
```

Sau khi vá DuckDuckGo, validate và restart gateway trong container:

```bash
docker exec user-<ten_user> sh -lc 'set -a; . /root/.openclaw/token-codex.env; set +a; HOME=/root openclaw config validate'
docker exec user-<ten_user> tmux kill-session -t openclaw 2>/dev/null || true
docker exec user-<ten_user> tmux new-session -d -s openclaw sh -lc 'set -a; . /root/.openclaw/token-codex.env; set +a; HOME=/root openclaw skills check; exec env HOME=/root openclaw gateway run'
sleep 8
docker exec user-<ten_user> sh -lc 'set -a; . /root/.openclaw/token-codex.env; set +a; HOME=/root openclaw gateway status'
```

Khi báo kết quả cho user, hướng dẫn test bằng câu hỏi cần tra cứu web, ví dụ hỏi tin mới hoặc thông tin thị trường hiện tại. Không tự gửi tin Telegram thật nếu chưa được user cho phép.

## Kiểm tra sau khi chạy

```bash
cd /root/docker-users
bash manage-user.sh info <ten_user>
docker exec -e HOME=/root user-<ten_user> sh -lc 'openclaw --version && HOME=/root openclaw gateway status && HOME=/root openclaw channels status --probe'
docker exec -e HOME=/root user-<ten_user> sh -lc 'python3 --version && document-python --version && command -v pdfinfo && command -v pdftotext'
docker exec -e HOME=/root user-<ten_user> sh -lc '/root/.openclaw/tools/document-venv/bin/python -c "import openpyxl,pypdf,pdfplumber,fitz,PIL,xlsxwriter,pandas; print(\"document_modules=OK\")"'
```

## Chuẩn độ ổn định Zalo cho member đang chạy

Khi member dùng Zalo để xử lý PDF/Excel/ảnh/video hoặc từng có hiện tượng Zalo im trong khi Telegram vẫn chạy:

1. Bật watchdog `member_anhlaptrinh_zalouser` theo mẫu shared center, kiểm tra cả `channels status --probe` và sự kiện listener cuối cùng trong log.
2. Cài bộ công cụ tài liệu trực tiếp trong đúng container hoặc dùng script chỉ sau khi đã xác minh đường dẫn thực sự tồn tại.
3. Ghi các quy tắc reliability trực tiếp vào workspace/AGENTS của member: phản hồi sớm nếu tác vụ quá 20 giây, cập nhật sau khoảng 120 giây, tách tác vụ nặng thành worker khi có thể, kiểm tra file trước khi gửi, không gửi file rỗng/hỏng, tạo bản nhẹ nếu file vượt 8 MB và chỉ báo đã gửi sau khi kiểm tra thành công.
4. Đặt `tools.sessions.visibility: agent` khi session chính cần theo dõi worker cùng agent; không đặt `all` nếu không cần cross-agent.
5. Đặt giới hạn context và session maintenance; chỉ chạy script audit/compact sau khi đã xác minh script tồn tại và backup session.
6. Không xóa transcript cũ hoặc tự logout Zalo; nếu phục hồi thất bại, yêu cầu quét QR lại.

Báo cho người dùng:

- Container: `user-<ten_user>`
- Mật khẩu: `<ten_user>123`
- Port SSH lấy từ output của `manage-user.sh info <ten_user>`; web port lấy từ `docker inspect`, không giả định manager đã map port `80`
- Dashboard nội bộ: `http://127.0.0.1:18789/`
- Dashboard public: `http://<PUBLIC_IP>:<web_port>/`; đăng nhập bằng token trong `/root/.openclaw_dashboard_token`, để trống mật khẩu
- Token Codex email/mật khẩu: chỉ báo khi provisioning backend thực tế đã tạo tài khoản
- Link đăng nhập xem credit/API usage còn lại: `https://codex.anhlaptrinh.vn/`
- Xác nhận API Token Codex đã được cấu hình vào member VPS và provider/model đã test thành công; không nêu full API key
- Nếu có Telegram group: báo `accountId`, Group ID, user ID allowlist, `requireMention`, trạng thái Privacy Mode, validate, gateway, inbound và outbound; không nêu bot token hoặc API key.

## Tích hợp Facebook Fanpage và CSKH (A/B/C — On-Demand)

Phần Facebook đã được gộp trực tiếp vào skill chính. Mã chạy kèm vẫn nằm tại `resources/post-fanpage-fb/`, gồm script đăng Fanpage, script gửi Messenger CSKH, script lấy PSID, hai Bash wrapper và ảnh mẫu. Chỉ triển khai khi người dùng yêu cầu rõ; không tự đăng bài hoặc gửi tin thật.

### A. Chuẩn bị dữ liệu và credential

1. Tạo thư mục dự án Facebook với `scripts/`, `images/`, `googlesheetcn.json` và `.env` ở thư mục gốc.
2. Tạo Google Service Account, đặt JSON thành `googlesheetcn.json`, rồi share Google Sheet quyền **Editor** cho email `client_email` trong JSON.
3. Chuẩn bị Page Access Token cho đăng bài và token Messenger cho CSKH. Script tự gọi `/me` để lấy Page ID từ token, không yêu cầu biến `FB_PAGE_ID`. Không ghi token thật vào skill, Git, log hoặc câu trả lời.
4. Dùng đúng tên biến mà script hiện tại đọc trong `.env`:

```env
SPREADSHEET_ID=<google_sheet_id>
FB_PAGE_ACCESS_TOKEN=<page_access_token>
MESSENGER_TOKEN=<messenger_page_access_token>
FB_GRAPH_API_VERSION=v25.0
WORKSHEET_CSKH=Chăm Sóc Khách Hàng
```

`MESSENGER_PAGE_ACCESS_TOKEN` cũng được chấp nhận làm tên tương thích. Nếu không có token Messenger riêng, script có thể fallback về `FB_PAGE_ACCESS_TOKEN`, nhưng khi người dùng đã cung cấp hai token thì phải lưu tách đúng biến.

5. Cài môi trường Python:

```bash
python3 -m venv venv
venv/bin/pip install --upgrade pip
venv/bin/pip install requests gspread google-auth python-dotenv pyinstaller
```

Trên Windows dùng `py -m venv venv`, `venv\Scripts\pip.exe` và `venv\Scripts\python.exe`. Thư viện `pandas` hoặc `oauth2client` chỉ cài thêm nếu project thực tế cần.

6. Đặt ảnh cần đăng trong `images/`. Cột ảnh có thể ghi tên file không đuôi hoặc tên file có đuôi; script tìm `.jpg`, `.png`, `.jpeg` và `.webp`.

### B. Chạy Auto Post và Auto CSKH

#### B1. Tab Google Sheet `Fanpage`

Các cột được script sử dụng:

| Cột | Ý nghĩa |
|---|---|
| `Tiêu Đề` | Tiêu đề, được nối vào đầu caption |
| `Mô Tả` hoặc `Nội Dung` | Nội dung bài đăng |
| `Images` hoặc `Hình ảnh` | Tên ảnh trong thư mục `images/` |
| `Status` | Trạng thái xử lý |

Script hiện tại chỉ lấy dòng `Status = UNAPPROVED`, đăng **một bài mỗi lần chạy**, rồi đổi thành `APPROVED` khi thành công. Nếu không tìm thấy ảnh, script vẫn đăng bản text và ghi cảnh báo.

#### B2. Tab Google Sheet `Chăm Sóc Khách Hàng`

Các cột được script sử dụng:

| Cột | Ý nghĩa |
|---|---|
| `ID` | PSID của khách hàng Messenger |
| `Tên Khách Hàng` | Tên để theo dõi |
| `Tin Nhắn` | Nội dung cần gửi |
| `Trạng Thái` | `UNAPPROVED`, `APPROVED` hoặc `ERROR` |

Script chỉ gửi dòng có `UNAPPROVED`, đủ PSID và đủ nội dung; mỗi lần chạy gửi tối đa một khách hàng. Gửi thành công thì đổi thành `APPROVED`, lỗi gửi thì đổi thành `ERROR`.

#### B3. Lệnh chạy thủ công

```bash
cd /root/.agents/skills/tao-tro-ly-openclaw-windows-macos-linux/resources/post-fanpage-fb
venv/bin/python scripts/Facebook_Post_Bai_Fanpage.py
venv/bin/python scripts/Facebook_Message_CSKH.py
venv/bin/python scripts/Get_PSID_List.py
```

Windows trong thư mục project:

```powershell
.\venv\Scripts\python.exe scripts\Facebook_Post_Bai_Fanpage.py
.\venv\Scripts\python.exe scripts\Facebook_Message_CSKH.py
```

`Get_PSID_List.py` đọc tối đa 50 cuộc hội thoại gần nhất, tự lấy Page ID để loại trừ chính Fanpage và in PSID khách hàng để nhập vào Sheet; không tự ghi PSID vào Sheet.

#### B4. Wrapper, lịch chạy và file `.exe`

Không đưa lệnh Python trực tiếp vào crontab. Dùng wrapper rồi đọc log tương ứng:

```bash
/bin/bash <facebook_project>/scripts/run_fanpage_cron.sh
/bin/bash <facebook_project>/scripts/run_cskh_cron.sh
```

Log nằm trong `resources/post-fanpage-fb/logs/`. Nếu chạy trực tiếp từ cron, cấp quyền `chmod +x` cho wrapper và dùng lịch mặc định sau khi người dùng xác nhận:

```cron
0 */4 * * * /bin/bash <facebook_project>/scripts/run_fanpage_cron.sh
*/5 * * * * /bin/bash <facebook_project>/scripts/run_cskh_cron.sh
```

Trên Windows có thể build file `.exe` đăng Fanpage:

```powershell
.\venv\Scripts\pyinstaller.exe --onefile --distpath . scripts\Facebook_Post_Bai_Fanpage.py
```

File `.exe` phải ở cùng cấp với `googlesheetcn.json`, `.env` và thư mục `images/`. Không đưa các file credential vào bản build công khai.

#### B5. API được sử dụng

- Tự lấy Page ID: `/me?fields=id,name` bằng Page Access Token.
- Text post: `/{PAGE_ID}/feed`.
- Post kèm ảnh: `/{PAGE_ID}/photos`.
- Messenger CSKH: `/me/messages` với PSID.
- Version Graph API lấy từ `FB_GRAPH_API_VERSION`, hiện mặc định `v25.0` và phải có thể đổi qua `.env` khi Meta nâng version.
- Việc gửi Messenger phải tuân thủ chính sách cửa sổ hội thoại và quyền của token Messenger/Page.

### C. Nối vào OpenClaw Workspace

Không copy thêm một `SKILL.md` Facebook con nữa. Khi cần OpenClaw thực thi thay vì chỉ giải thích, thêm quy tắc vận hành vào workspace của member:

1. Trỏ `AGENTS.md` hoặc automation wrapper tới đúng `<facebook_project>/scripts/run_fanpage_cron.sh` và `<facebook_project>/scripts/run_cskh_cron.sh`.
2. Với yêu cầu “đăng bài”, “chạy Fanpage”, “up bài Facebook”, chạy wrapper Fanpage rồi đọc log Fanpage.
3. Với yêu cầu “chạy CSKH”, “gửi tin nhắn CSKH”, “nhắn tin khách hàng”, chạy wrapper CSKH rồi đọc log CSKH.
4. Không tự hỏi lại nội dung nếu dữ liệu đã có trong Google Sheet; không tự gửi tin thật nếu người dùng chỉ yêu cầu hướng dẫn.
5. Sau khi sửa workspace hoặc config, restart Gateway bằng root runtime của member:

```bash
HOME=/root tmux kill-session -t openclaw 2>/dev/null || true
tmux new-session -d -s openclaw sh -lc 'set -a; . /root/.openclaw/token-codex.env; set +a; HOME=/root openclaw skills check; exec env HOME=/root openclaw gateway run'
```

Không cài tính năng Facebook mặc định hoặc tự tạo lịch nếu người dùng chưa yêu cầu rõ.

## Quy trình sửa/nâng cấp workflow

1. Đọc `/root/_Second_AI_Brain/START_HERE.md`, bản đồ VPS, registry project, và checklist production nếu sửa script đang chạy.
2. Backup file sắp sửa vào `/root/_Backups`.
3. Xác định đúng provisioning project đang tồn tại trước khi sửa; không dùng đường dẫn automation mẫu đã thiếu.
4. Nếu đổi input/output, đường dẫn, version OpenClaw, provider Token Codex, model, token mặc định, logic port hoặc cách chạy Telegram, cập nhật phần tương ứng trong skill chính này.
5. Chạy `bash -n` cho script shell và ít nhất một lệnh `--dry-run`.
6. Quét không để lộ secret thật và không đưa token thật vào diff.
7. Ghi `/root/_Second_AI_Brain/06_Nhat_Ky_Thay_Doi.md`.

## An toàn

- Không in Telegram bot token hoặc API key trong câu trả lời.
- Được gửi email, mật khẩu đăng nhập Token Codex và link `https://codex.anhlaptrinh.vn/` cho đúng khách hàng; không gửi full API key.
- Không sửa `.env`, credential, Chrome/Selenium profile nếu task không yêu cầu.
- Không xóa container/data folder khi chưa được yêu cầu rõ.
- Không mở port public ngoài SSH/web member VPS nếu chưa có yêu cầu rõ.
- Không tự gửi tin Telegram thật ngoài bước test được người dùng cho phép.
