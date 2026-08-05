---
name: zalo-auto-send-contact
description: Vận hành, sửa lỗi và tái sử dụng dự án /root/Automation/zalo/01_zalo_lg_se để tự động gửi tin nhắn Zalo Web từ Google Sheet bằng Python trực tiếp, Chrome profile cố định, RDP login thủ công khi cần, và Selenium attach qua debugger 127.0.0.1:9223.
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

## Login Flow

Preferred flow: use the web QR page instead of Remote Desktop.

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
