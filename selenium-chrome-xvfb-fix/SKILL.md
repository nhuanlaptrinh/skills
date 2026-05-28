---
name: selenium-chrome-xvfb-fix
description: Fix Selenium Chrome errors on Linux servers, especially "session not created: Chrome instance exited", missing DISPLAY, Xvfb setup, Chrome profile locks, and ChromeDriver/Chrome startup failures for Zalo Web automation.
---

# Selenium Chrome Xvfb Fix

Use this skill when a Selenium/Chrome script on Linux fails with:

- `session not created: Chrome instance exited`
- `Chrome failed to start: exited normally`
- `DevToolsActivePort file doesn't exist`
- empty `DISPLAY`
- Zalo Web automation works on desktop but fails on VPS/server

## Quick Diagnosis

Run these first:

```bash
echo "DISPLAY=$DISPLAY"
which google-chrome || which chromium || which chromium-browser || true
google-chrome --version || chromium --version || true
which chromedriver || true
chromedriver --version || true
which xvfb-run || true
ps -ef | rg 'Xvfb|chrome|chromedriver' | rg -v rg || true
```

If `DISPLAY` is empty and the script uses `headless=False`, Chrome needs an X server.

## Standard Fix

Prefer starting Xvfb before running the script:

```bash
cd /root/SELENIUM_ZALO
if [ -z "${DISPLAY:-}" ]; then
  if ! pgrep -x Xvfb >/dev/null 2>&1; then
    Xvfb :12 -screen 0 1920x1080x24 >/dev/null 2>&1 &
    sleep 1
  fi
  export DISPLAY=:12
fi
source venv/bin/activate
python OpenZaloSendContact.py
```

Or run directly:

```bash
cd /root/SELENIUM_ZALO
xvfb-run -a venv/bin/python OpenZaloSendContact.py
```

## Python-Side Guard

For recurring scripts, add a small guard before creating the Chrome driver:

```python
def ensure_linux_display():
    import os, shutil, subprocess, sys, time
    if os.environ.get("DISPLAY"):
        return
    if sys.platform.startswith("linux") and shutil.which("Xvfb"):
        subprocess.Popen(
            ["Xvfb", ":12", "-screen", "0", "1920x1080x24"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        time.sleep(1)
        os.environ["DISPLAY"] = ":12"
```

Call `ensure_linux_display()` immediately before `webdriver.Chrome(...)` or `uc.Chrome(...)`.

## If It Still Fails

Check these causes in order:

1. Chrome profile lock: inspect `zalo-chrome-profile/Singleton*`. Only remove locks after confirming no Chrome process is using the profile.
2. Version mismatch: Chrome and ChromeDriver major versions should match.
3. Missing packages: install Chrome dependencies such as `libnss3`, `libatk-bridge2.0-0`, `libgbm1`, `libasound2`, `libxss1`.
4. Container/server flags: Chrome options should usually include `--no-sandbox`, `--disable-dev-shm-usage`, `--disable-gpu`, and a stable `--window-size`.

## Safety Notes

Do not store credentials, browser profiles, cookies, logs, QR screenshots, or service-account JSON in a skill. Use placeholders in examples.
