---
name: zalo-web-qr-login
description: Gắn trang web QR login cho các dự án Zalo/Chrome automation tương tự `https://9router.anhlaptrinh.vn/zalo-login/`, dùng Chrome profile hiện có, Xvfb, Nginx reverse proxy, systemd service, tự chụp màn hình QR ra web, refresh định kỳ, và tự nhả profile sau khi đăng nhập thành công để automation gửi tin tiếp tục chạy.
---

# Zalo Web QR Login

Use this skill when a project needs a public web URL like `https://domain/zalo-login/` to scan Zalo Web QR without RDP/Desktop launcher.

## Safety Rules

- Read the target project's `AGENTS.md` first if present.
- Use the existing Chrome/Zalo profile only; do not copy profile from another machine.
- Do not print cookies, profile data, tokens, credentials, or private sheet keys.
- Backup Nginx/systemd files before editing production config.
- Do not run message-sending automation while the QR worker is holding the profile.

## Required Inputs

Identify these values before installing:

- `PROJECT_ROOT`: automation project folder.
- `PROFILE_DIR`: Chrome/Zalo profile folder.
- `DOMAIN`: public Nginx domain, e.g. `9router.anhlaptrinh.vn`.
- `URL_PATH`: public path, default `/zalo-login/`.
- `UPSTREAM_PORT`: local QR server port, default a free `127.0.0.1` port.
- `DEBUG_PORT`: Chrome remote debugging port, often `9223`.
- `CHROME_BIN`: Chrome/Chromium binary; prefer project-pinned Chrome if available.

## Install Pattern

Use bundled script instead of hand-writing files:

```bash
/root/.agents/skills/zalo-web-qr-login/scripts/install_zalo_web_qr.sh \
  --project-root /path/to/project \
  --profile-dir /path/to/project/zalo-login-profile \
  --domain example.com \
  --path /zalo-login/ \
  --upstream-port 18790 \
  --debug-port 9223 \
  --chrome-bin /path/to/chrome
```

The script creates:

- `script/zalo_web_qr_server.py`: HTTP server on `127.0.0.1:<UPSTREAM_PORT>`.
- `script/start_zalo_web_qr_worker.sh`: Xvfb + Chrome worker that captures `screen.png` every `REFRESH_SECONDS`.
- `zalo_web_qr_link.txt`: public URL for the user.
- `/etc/systemd/system/<service>.service`: QR web service.
- Nginx `location <URL_PATH>` in the selected domain site file.

## Runtime Behavior

1. User opens `https://DOMAIN/URL_PATH`.
2. Web server starts the worker if needed.
3. Worker opens Chrome with the existing Zalo profile on an Xvfb display.
4. Worker writes screenshot to `/var/www/html/<safe-path>/screen.png`.
5. Page refreshes every `REFRESH_SECONDS`, default `5`.
6. When Chrome DevTools reports `https://chat.zalo.me`, worker closes Chrome, removes the manual-login flag, and exits so automation can use the profile.

## Validation

After install or repair:

```bash
nginx -t
systemctl is-active <service-name>
curl -fsS https://DOMAIN/URL_PATH | grep 'Zalo Automation QR'
curl -fsS https://DOMAIN/URL_PATH/screen.png -o /tmp/zalo_qr_test.png
file /tmp/zalo_qr_test.png
PROJECT_ROOT/script/check_zalo_profile_available.sh automation
```

Expected:

- URL returns `200 OK`.
- HTML contains `refresh content="5"` or configured refresh seconds.
- `screen.png` is a PNG image.
- After login succeeds, `check_zalo_profile_available.sh automation` returns exit `0`.

## Troubleshooting

- If automation does not send: check whether `.zalo_manual_login_active` exists or Chrome still holds `PROFILE_DIR`; stop QR worker and remove the flag only after login is confirmed.
- If page is blank: check `systemctl status <service>` and worker logs in `PROJECT_ROOT`.
- If Nginx serves the app instead of QR: ensure the `location /zalo-login/` block appears before `location /`.
- If screenshot is PostScript or wrong format: use ImageMagick `import` with `png:<tmp-file>.png`.
- If another project uses debug port `9223`, choose a different `DEBUG_PORT` and update the worker/server consistently.

## Existing Reference Implementation

Working example on this VPS:

- URL: `https://9router.anhlaptrinh.vn/zalo-login/`
- Project: `/root/Automation/zalo/01_zalo_lg_se`
- Service: `zalo-web-qr.service`
- Nginx site: `/etc/nginx/sites-available/9router.anhlaptrinh.vn`
