---
name: cai-dat-openclaw-windows-mac-linux
description: "Cài đặt hoặc sửa OpenClaw trên Windows, macOS và Linux với Python/pip, gateway local và Token Codex; chỉ chọn GPT-6.1-sol, GPT-6-terra, GPT-6-luna, GPT-6-astra, mặc định GPT-6.1-sol. Không tự cài/login Codex CLI hoặc bật DeepSeek."
---

# Cai Dat OpenClaw Windows, macOS, Linux

## Chính sách model — 2026-10-19

- Chỉ dùng đúng bốn model hội thoại/suy luận: `GPT-6.1-sol`, `GPT-6-terra`, `GPT-6-luna`, `GPT-6-astra`. Mặc định khi cài mới hoặc không chỉ định model là `GPT-6.1-sol`.
- Primary, fallback và lựa chọn trong wizard chỉ lấy từ danh sách này; không tự dùng alias/model cũ hoặc bật DeepSeek dù môi trường có key. Giữ provider hiện có và ghép `<provider>/<model-id>` đúng case.
- Trước khi apply, xác minh model đích trong `/v1/models` của provider thực tế; nếu không có thì dừng, không tự đổi tên hay chọn model ngoài danh sách. Chỉ cấu hình hiểu ảnh khi đã kiểm tra backend hỗ trợ.
- Đây là chính sách chọn model, không phải quyền tự đổi runtime đang chạy. Không đổi model STT/TTS/tạo ảnh thành model chat; các tính năng media chuyên dụng giữ workflow và kiểm tra riêng.

## Defaults

- Dashboard URL must always be `http://127.0.0.1:18789/`.
- OpenClaw CLI must always be installed as fixed `openclaw@2026.7.1-2`.
- Do not use `latest` or automatically change versions. Verify the Node engine with `npm view openclaw@2026.7.1-2 engines --json`, then confirm `openclaw --version` returns `2026.7.1-2`.
- Do not use a floating latest tag or any other OpenClaw version unless the user explicitly names that version in the current request.
- Gateway port must default to `18789`.
- Gateway bind must default to `loopback` so only the local computer can connect.
- Gateway auth mode must default to `token`.
- Gateway token must default to `chatbot` unless the user explicitly requests another value.
- Install or repair Python/pip by default because classroom machines often do not have pip.
- When setting an API-backed model in OpenClaw, always default to provider ID `token-codex`, Base URL `https://codex.anhlaptrinh.vn/v1`, exact case-sensitive model ID `GPT-6.1-sol`, and primary model `token-codex/GPT-6.1-sol`.
- The user may supply the API key through `TOKEN_CODEX_API_KEY`; also accept `CUSTOM_PROVIDER_API_KEY` as a compatibility fallback. Never invent a key, print it, or put a real key in the skill repository.
- If neither API-key variable exists, leave Token Codex unconfigured and clearly tell the user what variable to set before rerunning. Do not replace the missing key with a placeholder inside the live OpenClaw config.
- Although a user may write `GPT-6.1-SOL`, normalize the live configuration to `GPT-6.1-sol` because the API model ID is case-sensitive.
- Prepare Codex/OpenAI for ChatGPT/Codex account login, not OpenAI API key, unless the user explicitly asks for API billing.
- Do not install or run Codex login automatically. The teacher/student must install official Codex CLI and run login manually after OpenClaw install.
- Force Codex CLI to prefer ChatGPT account login by setting `forced_login_method = "chatgpt"` in `~/.codex/config.toml`.
- If the OpenClaw Codex plugin/provider is used later, clear `OPENAI_API_KEY` from the spawned Codex app-server environment so a machine-level API key does not skip account login.
- Never print API keys or store them inside the skill files.

## Workflow

1. Detect the operating system first.
2. Always use the fixed OpenClaw version `2026.7.1-2`.
3. On Windows, prefer `scripts/install_openclaw_windows.ps1`.
4. On macOS/MacBook, prefer `scripts/install_openclaw_macos.sh`.
5. On Linux, prefer `scripts/install_openclaw_linux.sh`.
6. If installing on a different machine, copy or reference the skill folder and run the matching script from that machine.
7. If `TOKEN_CODEX_API_KEY` or `CUSTOM_PROVIDER_API_KEY` is present, configure Token Codex and make `token-codex/GPT-6.1-sol` the OpenClaw primary model.
8. After install, tell the user to install/log in separately with official Codex CLI only when they also want ChatGPT/Codex account auth outside the Token Codex provider.

## Chọn model và kiểm tra trước khi chạy

- Linux/macOS: đặt `TOKEN_CODEX_MODEL_ID` thành một trong bốn ID được phép; nếu không đặt thì dùng `GPT-6.1-sol`.
- Windows: truyền `-Model GPT-6-terra`, `-Model GPT-6-luna` hoặc model được phép khác. Giá trị ngoài danh sách phải bị từ chối trước khi cài đặt.
- Installer đăng ký đúng bốn model vào provider `token-codex`; không tự bật provider khác từ key trong môi trường. Tham số Windows `-SkipDeepSeek` cũ chỉ còn được chấp nhận để tương thích, không bật DeepSeek khi bỏ tham số này.
- Các installer chưa có dry-run đầy đủ. Không chạy installer chỉ để xem kế hoạch: dùng `bash -n scripts/install_openclaw_linux.sh` hoặc `bash -n scripts/install_openclaw_macos.sh` để kiểm tra cú pháp. Trên Windows, kiểm tra script bằng PowerShell parser trước khi chạy thật.
- Trước khi chạy thật trên máy đã có config, backup các file liên quan, kiểm tra model đích trong `/v1/models` bằng key trong bộ nhớ và không in credential.
- Input: API key qua môi trường, model và hệ điều hành. Output: config local tại `~/.openclaw/openclaw.json`, tùy chọn đăng nhập Codex trong `~/.codex/config.toml`, và log trạng thái; không ghi Google Sheet, upload hoặc gửi tin nhắn.
- Rerun bằng cùng installer và model sau khi backup; nếu lỗi thì khôi phục đúng config đã backup rồi validate trước khi restart.

## Token Codex Default Provider

Use this live OpenClaw provider shape. Replace the placeholder only at execution time from the user's environment; never save a real key in this skill:

```json
{
  "agents": {
    "defaults": {
      "model": {"primary": "token-codex/GPT-6.1-sol"},
      "models": {
        "token-codex/GPT-6.1-sol": {},
        "token-codex/GPT-6-terra": {},
        "token-codex/GPT-6-luna": {},
        "token-codex/GPT-6-astra": {}
      }
    }
  },
  "models": {
    "mode": "merge",
    "providers": {
      "token-codex": {
        "baseUrl": "https://codex.anhlaptrinh.vn/v1",
        "apiKey": "YOUR_TOKEN_CODEX_API_KEY",
        "api": "openai-completions",
        "models": [
          {"id": "GPT-6.1-sol", "name": "GPT-6.1-sol"},
          {"id": "GPT-6-terra", "name": "GPT-6-terra"},
          {"id": "GPT-6-luna", "name": "GPT-6-luna"},
          {"id": "GPT-6-astra", "name": "GPT-6-astra"}
        ]
      }
    }
  }
}
```

After writing the provider, restrict the private config file to the current user where supported, run `openclaw config validate`, restart the gateway, and verify `openclaw models list` contains `token-codex/GPT-6.1-sol`.

### Windows

Run from PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File C:\Users\nhuan\.codex\skills\cai-dat-openclaw-windows-mac-linux\scripts\install_openclaw_windows.ps1
```

After install, install or open official Codex CLI manually only when the teacher/student is ready, then run:

```powershell
codex logout
codex login
```

If browser login is inconvenient, use the Codex CLI device flow, not OpenClaw's provider flag:

```powershell
codex login --device-auth
```

To make Token Codex the default OpenClaw model, set the user environment variable before running, then open a new PowerShell window:

```powershell
[Environment]::SetEnvironmentVariable("TOKEN_CODEX_API_KEY", "Nhap_API_Cua_Ban", "User")
```

Open a new PowerShell window after setting user environment variables.

If Windows shows a UAC/admin prompt while `winget` installs Node.js or Python, tell the user to approve it.

### macOS/MacBook

Run from Terminal:

```bash
chmod +x ~/.codex/skills/cai-dat-openclaw-windows-mac-linux/scripts/install_openclaw_macos.sh
~/.codex/skills/cai-dat-openclaw-windows-mac-linux/scripts/install_openclaw_macos.sh
```

After install, install or open official Codex CLI manually only when the teacher/student is ready, then run:

```bash
codex logout
codex login
```

To make Token Codex the default OpenClaw model, export:

```bash
export TOKEN_CODEX_API_KEY="Nhap_API_Cua_Ban"
```

If Homebrew is missing, the script installs it. If macOS asks for the login password during Homebrew setup, tell the user to enter the Mac login password.

### Linux

Run from Terminal:

```bash
chmod +x ~/.codex/skills/cai-dat-openclaw-windows-mac-linux/scripts/install_openclaw_linux.sh
~/.codex/skills/cai-dat-openclaw-windows-mac-linux/scripts/install_openclaw_linux.sh
```

After install, install or open official Codex CLI manually only when the teacher/student is ready, then run:

```bash
codex logout
codex login
```

If the machine is headless or browser callback is inconvenient, use:

```bash
codex login --device-auth
```

To make Token Codex the default OpenClaw model, export:

```bash
export TOKEN_CODEX_API_KEY="Nhap_API_Cua_Ban"
```

### Verify

After installation, verify:

```bash
node -v
npm -v
python3 --version
python3 -m pip --version
openclaw --version
openclaw gateway status
openclaw models auth list
openclaw models list
```

If official Codex CLI is already installed, verify it separately:

```bash
codex --version
codex login status
```

Report the final dashboard link exactly as `http://127.0.0.1:18789/`.
When Token Codex was configured, also report the Base URL `https://codex.anhlaptrinh.vn/v1` and primary model `token-codex/GPT-6.1-sol`, but never report any part of the API key.

## Manual Fallbacks

Use these Windows commands only when the bundled PowerShell script cannot run:

```powershell
winget install --id OpenJS.NodeJS.LTS --exact --accept-package-agreements --accept-source-agreements --disable-interactivity
winget install --id Python.Python.3.12 --exact --accept-package-agreements --accept-source-agreements --disable-interactivity
python -m ensurepip --upgrade
python -m pip install --upgrade pip
npm install -g openclaw@2026.7.1-2
openclaw onboard --non-interactive --accept-risk --mode local --auth-choice skip --skip-channels --skip-search --skip-skills --install-daemon --skip-health --gateway-bind loopback --gateway-auth token --gateway-port 18789 --gateway-token chatbot
openclaw config set gateway.auth.token chatbot
openclaw gateway restart
openclaw gateway status
```

Use these macOS commands only when the bundled shell script cannot run:

```bash
if ! command -v brew >/dev/null 2>&1; then
  NONINTERACTIVE=1 /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
fi
brew install node python
python3 -m ensurepip --upgrade || true
python3 -m pip install --upgrade pip --break-system-packages || python3 -m pip install --upgrade pip
npm install -g openclaw@2026.7.1-2
openclaw onboard --non-interactive --accept-risk --mode local --auth-choice skip --skip-channels --skip-search --skip-skills --install-daemon --skip-health --gateway-bind loopback --gateway-auth token --gateway-port 18789 --gateway-token chatbot
openclaw config set gateway.auth.token chatbot
openclaw gateway restart
openclaw gateway status
```

Use these Linux commands only when the bundled shell script cannot run:

```bash
sudo apt-get update
sudo apt-get install -y curl ca-certificates python3 python3-pip nodejs npm
sudo npm install -g openclaw@2026.7.1-2
openclaw onboard --non-interactive --accept-risk --mode local --auth-choice skip --skip-channels --skip-search --skip-skills --install-daemon --skip-health --gateway-bind loopback --gateway-auth token --gateway-port 18789 --gateway-token chatbot
openclaw config set gateway.auth.token chatbot
openclaw gateway restart
openclaw gateway status
```

## Weak Computer Guidance

For low-spec machines, keep OpenClaw as a local gateway and workflow coordinator only:

- Do not run local LLM/Ollama on weak machines.
- Use API-based models instead of local models.
- Enable only the channels needed for the lesson.
- Keep the gateway loopback-only unless the user understands LAN/public exposure.
- For 24/7 reliability, suggest a VPS or a small always-on mini PC instead of a student laptop.

## Security

Do not copy real API keys, bot tokens, OpenClaw generated tokens, logs, credentials, browser profiles, or `.openclaw` private state into the skill. Use placeholders such as `Nhap_API_Cua_Ban` for examples. The requested default token `chatbot` is allowed only for local loopback setups.

Codex/OpenAI account install and login must be done manually with official Codex CLI (`codex login` or `codex login --device-auth`) after OpenClaw installation. That login creates local auth cache such as `~/.codex/auth.json` or OS credential-store entries. Treat those as secrets and never copy them into Git, a skill folder, tickets, or chat.
