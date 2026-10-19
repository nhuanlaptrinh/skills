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
- The Python script reuses an existing Chrome with the exact project profile through `127.0.0.1:9223`; it opens pinned Chrome for Testing only if the profile is idle. Existing RDP Chrome stays open after Selenium detaches. Only Chrome started by that run is closed gracefully afterward.
- If Zalo is logged out, open the web QR page `http://187.127.177.163/zalo-login/<token>/`, scan QR, then rerun the Python command.
- QR success is not inferred from the URL alone. The worker checks the visible contact-search UI through `/root/Automation/zalo/01_zalo_lg_se/script/zalo_cdp_state.py`, reopens Chrome with the same profile, and only releases the profile after the chat UI remains ready again.
- Read-only state check: `cd /root/Automation/zalo/01_zalo_lg_se && ./venv/bin/python script/zalo_cdp_state.py` while the project Chrome debugger is active. It never sends a message.
- For QR login, open Chrome as a normal browser window with `--new-window https://chat.zalo.me/`, not `--app=https://chat.zalo.me/`; app mode can open and then disappear on this VPS.
- Include `--password-store=basic` for the project Chrome launch so XFCE/GNOME Keyring cannot block the RDP login window with an unlock prompt.
- Do not delete or copy profile session files to repair automation. The sender deduplicates Zalo tabs in its newly opened browser through CDP, without a session backup or another profile. Never steal a busy browser or remove its locks.
- Launch QR Chrome with `nohup setsid` or another detached method so the window survives after the desktop launcher exits.

## Chrome Startup And Safe Browser Preflight

Use this section for exit 22, a missing debugger, stale XRDP displays, or exit 23 incorrectly reported for a browser-startup error. Source: `/root/Automation/zalo/01_zalo_lg_se/OpenZaloSendContact.py`; N8N entrypoint: `script/run_zalo_send_contact_from_n8n.sh` in that project.

Safe checks, repeatable without messages or Sheet access:

```bash
cd /root/Automation/zalo/01_zalo_lg_se
./venv/bin/python -m py_compile OpenZaloSendContact.py
bash -n script/run_zalo_send_contact_from_n8n.sh
./script/run_zalo_send_contact_from_n8n.sh --check
./script/run_zalo_send_contact_from_n8n.sh --check-browser
```

`--check` validates dependencies only. `--check-browser` uses the shared non-blocking N8N/QR lock and verifies the visible contact-search UI. It reuses the current project browser, or opens the same profile if idle and closes only its own browser afterward. It never reads or writes Google Sheet, sends Zalo/Telegram, or changes the saved account. No additional input or credentials are accepted on the command line.

- Success output: `N8N_ZALO_BROWSER_READY`, exit 0. Exit 1 means the chat UI is not ready, not necessarily logged out.
- Exit 22 means Chrome/display/debugger startup failed. The sender never sends a QR for this failure. Review `zalo_automation_chrome.log` and `zalo_automation_display.log` in the project; these are root-only operational logs, not public files.
- Exit 23 means an actual Zalo login page was observed. The sending flow captures a fresh root-only `zalo_qr.png` from that page; it never reuses an old QR image. Preflight itself does not send the image. For sustained QR login, use the owner QR helper described below after releasing the profile.
- Exit 21 means manual QR login is active; exit 75 means the shared profile lock is busy. Wait; never kill the owner browser or reset the account to bypass these conditions.
- Display discovery probes each candidate using `xdpyinfo`. Stale/unreachable sockets and stale `DISPLAY` values are skipped. If none is accessible, Xvfb chooses a free display through `-displayfd`, and readiness is verified before Chrome starts. No hardcoded `:12` fallback is used.
- The sender checks that the debugger belongs to the project profile. It refuses to steal a busy profile, preserves borrowed RDP Chrome, and closes only its own Chrome through `Browser.close`, without `kill -9`.

Real sending, only with explicit authorization to process current `UNAPPROVED` Sheet rows:

```bash
cd /root/Automation/zalo/01_zalo_lg_se
./script/run_zalo_send_contact_from_n8n.sh
```

Input/output columns and message/status updates remain as documented in Google Sheet Flow. Rerun `--check-browser` after repair; do not automatically rerun a real send or overwrite Sheet statuses. N8N HTTP 200 or an execution marked `success` does not prove that the subprocess exited 0: check its returned exit status. A future workflow health branch should treat 22/23/21/75 separately and avoid automatic retries of real sends to prevent duplicates. No cron, workflow version, Gateway secret, or member config is changed by these checks.

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
- The wrapper rejects unexpected arguments, uses a non-blocking process lock, and supports `--check` and `--check-browser` without sending Zalo.
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

### Provider auth failure despite a correct Gateway token

If the response contains `Provider 9rt has auth issue` and `MODEL_FALLBACK_SKIPPED`, distinguish Gateway authentication from OpenClaw's provider credential. Correct N8N headers do not repair the OpenClaw-to-9Router key.

On OpenClaw 2026.9.4, auth profiles take precedence over the inline provider key. Shared credentials reside in `/root/.openclaw/state/openclaw.sqlite`; agent-local overrides reside in `/root/.openclaw/agents/zalo-n8n-runner/agent/openclaw-agent.sqlite`. Retired `auth-profiles.json` files are not the active store.

Read-only diagnosis:

```bash
timeout 90s openclaw models auth list --agent zalo-n8n-runner --provider 9rt --json
```

Compare the effective `9rt:default` key against the configured provider key and the live 9Router key registry without printing their values. A disabled key can return `API key required for remote API access`; this message does not prove that the Authorization header was absent. Use authenticated `GET /v1/models` to check the candidate key before applying it; do not call a real Zalo workflow.

After explicit repair authorization, create a consistent SQLite backup and copy the current Gateway config under a root-only directory in `/root/_Backups/openclaw-9router-auth-repair/`. Include the agent database if it already contains local credentials. Never copy only the main SQLite file while WAL writes are active.

Apply the configured, verified-active key to the runner's existing profile using stdin, not a command-line secret:

```bash
python3 -c 'import json; print(json.load(open("/root/.openclaw/openclaw.json"))["models"]["providers"]["9rt"]["apiKey"], end="")' | \
  openclaw models auth paste-api-key \
    --agent zalo-n8n-runner --provider 9rt --profile-id 9rt:default
```

This command writes an agent-local override and config auth metadata; it does not replace the shared profile or credentials for other agents. Input is the existing active provider key; output is redacted CLI status and the updated runner auth store. Preserve the Gateway token, workflow version, model, and runner allowlist.

Verify without changing N8N or sending Zalo:

```bash
/root/Automation/zalo/01_zalo_lg_se/venv/bin/python \
  /root/Automation/zalo/01_zalo_lg_se/script/sync_n8n_openclaw_token.py \
  --dry-run --test-auth
```

Success requires HTTP 200 and `N8N_ZALO_RUNNER_CHECK_OK` from the N8N container. This only executes the wrapper's `--check` branch; it does not send messages, update Sheet rows, or open Chrome. Rerunning this check is safe.

The auth CLI attempts a live refresh. A refresh warning alone is not evidence that the running Gateway still uses the old key: run the harmless test first. If it passes, do not restart just because of the warning. If a restart is genuinely required, drain active work, restart only the host user's `openclaw-gateway.service`, and poll readiness for up to 120 seconds before retesting. Do not restart N8N/9Router or edit member containers to repair this route. Do not restore a full live state database as a casual rollback.

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
5. Wait for the page status to say the session survived reopening Chrome; only then run the Python command again.

Open the web QR page on a computer or tablet, then scan it with the Zalo app on the phone. Do not open the Telegram screenshot and try to import/scan it on the same phone; Zalo computer-login QR is intended to be scanned from another screen.

The web page includes a `Lấy QR mới` button. QR must not refresh automatically while the user is scanning because changing the code during phone confirmation makes Zalo report it as invalid. Only click the refresh button after the current QR visibly expires. The worker considers login successful only when the visible contact-search UI is ready, no login/activation state is present, and the same profile remains ready after reopening Chrome.

Opening or auto-refreshing the QR web page must not start Chrome automatically. Use the explicit `Mở QR Login` button when login is required. This prevents an old browser tab from spawning the QR worker and stealing the shared profile while `OpenZaloSendContact.py` is sending messages.

Service/files:

- Systemd service: `zalo-web-qr.service`.
- Web QR server: `/root/Automation/zalo/01_zalo_lg_se/script/zalo_web_qr_server.py`.
- QR worker: `/root/Automation/zalo/01_zalo_lg_se/script/start_zalo_web_qr_worker.sh`.
- Read-only CDP state probe: `/root/Automation/zalo/01_zalo_lg_se/script/zalo_cdp_state.py`.
- Public screenshot: `/var/www/html/zalo-login/screen.png`.

Do not close or replace `zalo-login-profile`.

### Verified Login And Safe Reruns

- Dry-run: `bash -n script/start_zalo_web_qr_worker.sh` and `./venv/bin/python script/zalo_cdp_state.py`; the latter only observes DOM state and fails closed when Chrome is offline.
- Start explicitly: `curl -fsS -o /dev/null http://127.0.0.1:18790/zalo-login/start`; use `https://9router.anhlaptrinh.vn/zalo-login/` on another screen to scan with the phone.
- Initial chat UI must stay ready for 30 seconds; the worker then requests graceful `Browser.close`, reopens the same profile, and requires another 15 stable seconds. A URL redirect or activation modal never counts as success.
- Only `zalo_login_verified.json` with `state=verified`, `reopened=true`, no manual-login flag and a finished worker confirms completion. The root-only receipt contains no account details, cookies or tokens. Public progress is `/var/www/html/zalo-login/status.txt`.
- The worker holds `/run/lock/zalo-send-contact-from-n8n.lock`; N8N sends stop with exit 75 while QR verification is running. Do not rerun sends until verification finishes. `--check` checks dependencies only, not authentication.
- Restored duplicate Zalo tabs are closed in the owned browser only; no alternate profile or session backup is created. Chat contents are never copied to the public QR screenshot.
- If persistence fails, no success receipt is written. The worker keeps the login flow available; refresh the QR only after it expires, never during phone confirmation. The flow does not send Zalo messages or update Google Sheet/API rows.
- The Telegram QR helper uses the fresh verified receipt too; it must not confirm success from URL/title or an old status file.
- If the same-profile reopen shows the official `Kích hoạt` modal, the worker uses `./venv/bin/python script/zalo_cdp_state.py --activate` to click only that visible modal button with a trusted DevTools mouse event. It does not send any message. Both worker validation and the normal sender wait for the chat UI again after activation; this is not a reason to ask the user to rescan QR.

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
