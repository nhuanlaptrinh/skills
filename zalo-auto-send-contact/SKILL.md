---
name: zalo-auto-send-contact
description: Vận hành, sửa lỗi và tái sử dụng dự án /root/Automation/zalo/01_zalo_lg_se để gửi tin nhắn Zalo Web từ Google Sheet, sửa N8N/OpenClaw 401 hoặc exec bị blocked, đăng nhập bằng QR gửi tới Telegram private chat của chủ sở hữu không cần Remote Desktop, quản lý Chrome profile cố định, và Selenium attach qua debugger 127.0.0.1:9223.
---

# Zalo Auto Send Contact

Use this skill for project `/root/Automation/zalo/01_zalo_lg_se`.

## Core Rules

- Run the tool with Python directly:

```bash
cd /root/Automation/zalo/01_zalo_lg_se
/root/Automation/zalo/01_zalo_lg_se/venv/bin/python -u /root/Automation/zalo/01_zalo_lg_se/OpenZaloSendContact.py
```

- Use only one Zalo profile:

```bash
/root/Automation/zalo/01_zalo_lg_se/zalo-login-profile
```

- Do not create alternate profiles or copy profiles from another machine.
- Do not run standalone/headless Chrome for Zalo automation.
- The Python script opens Chrome for Testing, attaches Selenium through `127.0.0.1:9223`, sends messages, updates Google Sheet, and closes Chrome afterward.
- If Zalo is logged out, open the web QR page `http://187.127.177.163/zalo-login/<token>/`, scan QR, then rerun the Python command.
- For QR login, open Chrome as a normal browser window with `--new-window https://chat.zalo.me/`, not `--app=https://chat.zalo.me/`; app mode can open and then disappear on this VPS.
- Include `--password-store=basic` for the project Chrome launch so XFCE/GNOME Keyring cannot block the RDP login window with an unlock prompt.
- Before opening QR login, clear old Chrome session tabs under `zalo-login-profile/Default/Sessions/` to prevent many restored `chat.zalo.me` tabs. Multiple Zalo Web tabs cause Zalo to show "Bạn đang mở Zalo trên một Tab khác..." and block automation.
- Launch QR Chrome with `nohup setsid` or another detached method so the window survives after the desktop launcher exits.

## N8N OpenClaw 401 And Exec Repair

Use this when N8N reports `401 Unauthorized` for:

```text
POST http://172.18.0.1/openclaw/v1/chat/completions
```

The production workflow is `01_RegistrationNotification_Kết Nối Web`, ID `IQSLZpjfCa6AOcl9`. It has four HTTP Request nodes named `Openclaw3`, `Openclaw`, `Openclaw2`, and `Openclaw1`.

A successful Zalo QR login does not fix this error. The running gateway reads `/root/.openclaw/openclaw.json`; do not copy the legacy token from `/root/AI_Runtime/openclaw/.openclaw/openclaw.json`.

If the response is `[blocked] ... không có công cụ exec`, do not remove the wildcard deny from agent `main`. OpenAI-compatible HTTP sessions match the wildcard sender policy on this installed OpenClaw version, so `main.tools.toolsBySender["*"]` intentionally removes runtime tools for non-owner channel senders.

The workflow must target the dedicated runner:

```text
Agent: zalo-n8n-runner
Workspace: /root/.openclaw/workspace_zalo_n8n_runner
Wrapper: /root/Automation/zalo/01_zalo_lg_se/script/run_zalo_send_contact_from_n8n.sh
```

Runner security:

- Tool profile is `minimal` with only `exec` and `process` added through `alsoAllow`.
- Exec mode and approval security are `allowlist`; `ask=off`, `askFallback=deny`.
- The only approved executable is the fixed wrapper above.
- The wrapper rejects unexpected arguments, uses a non-blocking process lock, and supports `--check` without sending Zalo.
- Never set this runner to Full Exec and never point these four HTTP nodes back to agent `main`.

Dry-run:

```bash
/root/Automation/zalo/01_zalo_lg_se/venv/bin/python \
  /root/Automation/zalo/01_zalo_lg_se/script/sync_n8n_openclaw_token.py \
  --dry-run
```

Apply and run a harmless auth test from the N8N container:

```bash
/root/Automation/zalo/01_zalo_lg_se/venv/bin/python \
  /root/Automation/zalo/01_zalo_lg_se/script/sync_n8n_openclaw_token.py \
  --apply --test-auth
```

The helper:

- Reads the active gateway token and N8N owner API key at runtime without printing either value.
- Requires exactly four matching HTTP Request nodes and fails closed if the workflow shape changes.
- Creates a consistent SQLite backup under `/root/_Backups/n8n/` before any update.
- Synchronizes the bearer token, `x-openclaw-agent-id=zalo-n8n-runner`, and the fixed wrapper prompt in all four nodes.
- Uses the N8N public API, which creates a new version and automatically republishes an active workflow without restarting `n8nalt-app`.
- Prints only token fingerprints, node names, version state, and backup path.
- With `--test-auth`, runs only the wrapper `--check` path and expects `N8N_ZALO_RUNNER_CHECK_OK`; it never runs `OpenZaloSendContact.py`, sends Zalo messages, changes Sheet rows, or touches the Zalo browser profile.

Do not validate this repair by manually triggering the real webhook unless the owner explicitly wants to process current `UNAPPROVED` rows.

## Google Sheet Flow

Expected columns:

- `Phone`: phone number, saved account name, or group name.
- `Message`: text to send.
- `Status`: processing state.

Processing rules:

- Send only rows with `Status = UNAPPROVED`.
- On success, update `APPROVED`.
- If contact is not found, update `NOT_FOUND`.
- On other errors, update `FAILED`.

## Telegram Owner QR Flow

Use this flow when the user asks to send the Zalo Web login QR to the Telegram owner without opening Remote Desktop.

Configuration is read at runtime from the existing root-only project file:

```text
/root/Automation/zalo/01_zalo_lg_se/.env
TELEGRAM_BOT_TOKEN
TELEGRAM_CHAT_ID
```

Never print, copy into source, or document the actual values. `TELEGRAM_CHAT_ID` must resolve to a Telegram `private` chat, not a group or channel.

Dry-run:

```bash
/root/Automation/zalo/01_zalo_lg_se/venv/bin/python \
  /root/Automation/zalo/01_zalo_lg_se/script/send_zalo_qr_to_telegram_owner.py \
  --dry-run
```

Run for real with a five-minute wait:

```bash
/root/Automation/zalo/01_zalo_lg_se/venv/bin/python \
  /root/Automation/zalo/01_zalo_lg_se/script/send_zalo_qr_to_telegram_owner.py \
  --timeout 300
```

Inputs:

- Existing profile: `/root/Automation/zalo/01_zalo_lg_se/zalo-login-profile`.
- Existing Telegram credential names in `.env`.
- Optional `--timeout 30-900`; default `300` seconds.
- Optional `--keep-qr`; omit it normally so the sensitive QR photo is deleted after completion.

Outputs and behavior:

- Validates the Telegram bot and requires the target to be a private owner chat.
- Refuses to run if `OpenZaloSendContact.py`, project Chrome, another QR worker, or manual login is active; it never steals the shared profile.
- Starts the existing Xvfb/Chrome QR worker, sends the fresh screenshot with Telegram `protect_content=true`, and waits for `https://chat.zalo.me/`.
- On success, sends a confirmation, deletes the QR photo, closes Chrome, and releases the manual-login flag and profile locks.
- If Zalo is already logged in, sends a short owner notification and does not send a QR.
- On timeout, deletes the QR photo, closes Chrome, releases the profile, and tells the owner to rerun.
- Does not read or update Google Sheet rows and does not run the message-sending automation.

Runtime files:

```text
/root/Automation/zalo/01_zalo_lg_se/script/send_zalo_qr_to_telegram_owner.py
/root/Automation/zalo/01_zalo_lg_se/zalo_telegram_qr.lock
/root/Automation/zalo/01_zalo_lg_se/zalo_telegram_qr_worker.out
/root/Automation/zalo/01_zalo_lg_se/zalo_telegram_qr_worker.err
/var/www/html/zalo-login/screen.png
```

If the QR expires, rerun the same real command. Do not reuse or forward an old QR screenshot. The owner should open the Telegram image on another screen/device when the Zalo app cannot scan an image displayed on the same phone.

## Web QR Login Flow

Use the web QR page as a fallback when Telegram delivery is unavailable.

1. Read the token from `/root/Automation/zalo/01_zalo_lg_se/.zalo_web_qr_token`.
2. Open `http://187.127.177.163/zalo-login/<token>/` in a browser.
3. Wait 10-20 seconds for the page to auto-refresh and show the Zalo QR screenshot.
4. Scan the QR with the phone.
5. Wait until Zalo Web reaches the chat interface, then run the Python command again.

Open the web QR page on a computer or tablet, then scan it with the Zalo app on the phone. Do not open the Telegram screenshot and try to import/scan it on the same phone; Zalo computer-login QR is intended to be scanned from another screen.

The web page includes a `Lấy QR mới` button. QR must not refresh automatically while the user is scanning because changing the code during phone confirmation makes Zalo report it as invalid. Only click the refresh button after the current QR visibly expires. The worker considers login successful only when the active page has moved to `https://chat.zalo.me/` and is no longer titled `Đăng nhập tài khoản Zalo`.

Opening or auto-refreshing the QR web page must not start Chrome automatically. Use the explicit `Mở QR Login` button when login is required. This prevents an old browser tab from spawning the QR worker and stealing the shared profile while `OpenZaloSendContact.py` is sending messages.

Service/files:

- Systemd service: `zalo-web-qr.service`.
- Web QR server: `/root/Automation/zalo/01_zalo_lg_se/script/zalo_web_qr_server.py`.
- QR worker: `/root/Automation/zalo/01_zalo_lg_se/script/start_zalo_web_qr_worker.sh`.
- Public screenshot: `/var/www/html/zalo-login/screen.png`.

Do not close or replace `zalo-login-profile`.

### RDP Display Troubleshooting

This VPS may have several XRDP displays at the same time, commonly `:10`, `:11`, and `:12`. If the QR appears in screenshots but the user cannot see it in Remote Desktop Connection, it is probably open on a different display/session.

Check displays and windows:

```bash
for d in :10 :11 :12; do
  echo "===== DISPLAY $d ====="
  DISPLAY=$d wmctrl -d 2>&1 || true
  DISPLAY=$d wmctrl -lG 2>&1 || true
done
```

Open or move the QR window on the display the user is actually viewing. In the latest working case, the user saw the QR only after opening on `DISPLAY=:12`:

```bash
cd /root/Automation/zalo/01_zalo_lg_se
./script/check_zalo_profile_available.sh repair || true
rm -f .zalo_manual_login_active
DISPLAY=:12 ./open_zalo_login_rdp.sh
sleep 10
wid=$(DISPLAY=:12 wmctrl -lG | awk '/Đăng nhập tài khoản Zalo|Zalo|Chrome/ {print $1; exit}')
if [ -n "$wid" ]; then
  DISPLAY=:12 wmctrl -i -r "$wid" -t 2 || true
  DISPLAY=:12 wmctrl -s 2 || true
  DISPLAY=:12 wmctrl -i -r "$wid" -e 0,80,60,1280,900 || true
  DISPLAY=:12 wmctrl -i -a "$wid" || true
fi
```

Verify visually by taking a screenshot of that display:

```bash
DISPLAY=:12 import -window root /root/Automation/zalo/01_zalo_lg_se/rdp_zalo_qr_check.png
```

If a desktop launcher click shows a Thunar/XFCE `Attention` dialog instead of opening Chrome, mark the launcher executable/trusted and provide the shell fallback:

```bash
chmod +x "/root/Desktop/Zalo Automation Login.desktop" /root/Desktop/open_zalo_qr.sh
gio set "/root/Desktop/Zalo Automation Login.desktop" metadata::trusted true 2>/dev/null || true
```

### Kich Hoat Tab State

If the screenshot says "Bạn đang mở Zalo trên một Tab khác hoặc không sử dụng Zalo quá lâu" with a `Kích hoạt` button, this is not a QR login failure. It means Zalo sees another tab/session. First close/deduplicate old tabs and clear session restore files; then reopen exactly one Zalo window. Selenium/JS/xdotool clicks may not activate this button reliably.

## Safe Repair

When Chrome/profile is locked:

```bash
cd /root/Automation/zalo/01_zalo_lg_se
./script/check_zalo_profile_available.sh repair || true
```

When changing Zalo account or resetting a broken profile:

```bash
cd /root/Automation/zalo/01_zalo_lg_se
./script/reset_zalo_profile_for_login.sh
```

Then login again via RDP.

## Keep

Keep these:

```bash
OpenZaloSendContact.py
zalo-login-profile/
.chrome-for-testing/
.chromedriver_cache/
venv/
prn8n-457809-6f62365e4958.json
script/
tools/
skill/
```

## Can Clean

These are disposable:

```bash
rdp_*.png
*.log
*.out
*.err
*.pid
__pycache__/
build/
dist/
OpenZaloSendContact
OpenZaloSendContact.spec
zalo-cft-test-profile/
zalo-chromium-test-profile/
```
