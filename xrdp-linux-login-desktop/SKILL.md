---
name: xrdp-linux-login-desktop
description: Set up or repair Linux VPS Remote Desktop access with xrdp/XFCE so a user can log in through Windows Remote Desktop Connection and interactively authenticate Chrome/Selenium browser profiles. Use when a crawler, Facebook automation, Google Sheet Selenium bot, Chrome profile, or Linux server task runs headless and the user needs a visible Linux desktop like Windows to log in, solve checkpoints, unlock sessions, or open the exact project Chrome profile.
---

# XRDP Linux Login Desktop

Use this skill when a Selenium/Chrome automation project on Linux needs a visible desktop login path. Prefer xrdp/RDP over noVNC when the user says they want "Remote Desktop Connection", "giao dien nhu Windows", "dang nhap truc tiep tren Linux", or wants to log in manually on the VPS.

## Fast Path

1. Identify the project root, Chrome profile directory, and browser command used by the automation.
2. Check xrdp, XFCE, port 3389, and firewall.
3. Stop any headless/VNC/Chrome process that is using the same profile before opening it interactively.
4. Configure `/root/.xsession` or the target user's `.xsession` to start `xfce4-session`.
5. Create a desktop shortcut and launcher script that opens Chrome with the exact project profile.
6. Tell the user how to connect with Windows Remote Desktop Connection, which account to use, and which shortcut to click.

## Discovery Commands

Run from the project root when possible:

```bash
pwd
find . -maxdepth 3 -type f | sort
sed -n '1,160p' .env
which google-chrome-stable google-chrome chromium xrdp startxfce4
systemctl status xrdp --no-pager
systemctl status xrdp-sesman --no-pager
ss -ltnp
ufw status
pgrep -a chrome
pgrep -a chromedriver
```

For Python/Selenium projects, inspect config files for `HEADLESS`, `CHROME_PROFILE_DIR`, `CHROME_USER_DATA_DIR`, `user-data-dir`, and `profile-directory`.

## Setup Or Repair

If xrdp or XFCE is missing on Ubuntu/Debian, install:

```bash
apt-get update
apt-get install -y xrdp xfce4 xfce4-terminal dbus-x11
```

Enable services:

```bash
systemctl enable --now xrdp xrdp-sesman
```

Ensure the RDP user starts XFCE:

```bash
printf 'xfce4-session\n' > /root/.xsession
```

If `ufw` is active, allow RDP:

```bash
ufw allow 3389/tcp
```

Verify:

```bash
systemctl is-active xrdp
systemctl is-active xrdp-sesman
ss -ltnp | grep ':3389'
```

## Chrome Profile Rules

- Never delete the whole Chrome profile unless the user explicitly asks.
- Remove only stale lock files before opening a profile interactively:

```bash
rm -f "$PROFILE_DIR"/SingletonCookie "$PROFILE_DIR"/SingletonLock "$PROFILE_DIR"/SingletonSocket
```

- Stop any Chrome process using the same profile before running the crawler, otherwise Selenium may fail with profile lock errors.
- If the automation runs with `HEADLESS=true`, manual login will not be visible. Use RDP to open the same `--user-data-dir` profile, log in, close Chrome, then run headless automation again.

## Reusable Script

Use `scripts/setup_xrdp_chrome_profile.sh` for common cases. It creates a launcher script in the project and a desktop shortcut for the RDP user.

```bash
/root/.agents/skills/xrdp-linux-login-desktop/scripts/setup_xrdp_chrome_profile.sh \
  --project-root /absolute/project/root \
  --profile-dir /absolute/project/root/facebook-chrome-profile \
  --shortcut-name "Facebook Login Profile"
```

Optional flags:

```bash
--user root
--url https://www.facebook.com/
--install-missing
```

Use `--install-missing` only when apt installs are acceptable. Without it, report missing packages and what to install.

## User Instructions To Provide

After setup, give concise instructions:

```text
Open Windows Remote Desktop Connection:
Computer: <host-or-ip>:3389
Username: root
Password: <your VPS root password>
Session: Xorg

After login, click the desktop shortcut: <shortcut name>.
Log in to Facebook/target site, then close Chrome before running the crawler.
```

Do not ask the user to use noVNC unless xrdp is unavailable or blocked.

## Common Fixes

- **RDP connects but black screen**: ensure `.xsession` contains `xfce4-session`, install `dbus-x11`, restart `xrdp` and `xrdp-sesman`.
- **Cannot connect**: check `ss -ltnp` for `3389`, `ufw status`, provider firewall, and `systemctl status xrdp`.
- **Crawler still says not logged in**: user likely logged into Chrome's default profile, not the project profile. Create or fix the desktop shortcut to use the exact `--user-data-dir`.
- **Chrome profile locked**: close Chrome in RDP, stop stray Chrome/Selenium processes for that profile, remove only `Singleton*` lock files.
- **Facebook checkpoint returns**: open the profile through RDP, complete checkpoint, close Chrome, then rerun automation.
