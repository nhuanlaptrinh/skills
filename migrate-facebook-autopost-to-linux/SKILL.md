---
name: migrate-facebook-autopost-to-linux
description: Migrate a Windows Facebook personal auto-poster project to Linux/server execution. Use when Codex needs to move or repair projects like skill_post_facebook_personal, skill_post_facebook_personal_alt, Selenium Chrome-profile Facebook posters, Google Sheets driven auto-posters, Windows Task Scheduler projects being moved to Linux cron, or requests such as "chuyen tu Windows sang Linux", "set cron dang Facebook", "copy profile Chrome sang server", "xvfb-run", "dang moi 5 phut", or "fix Chrome session not created / chua dang nhap tren Linux".
---

# Migrate Facebook Auto Poster To Linux

Use this skill to convert a Windows-oriented Facebook personal auto-poster project into a Linux cron-safe project.

## Fast Path

1. Identify the project root, script path, Sheet config, image folder, Chrome profile folder, and existing schedule skill.
2. Read any local skill first, usually:
   - `.agents/skills/fb-auto-poster/SKILL.md`
   - `.agents/skills/skill_set_schedule_post_window/SKILL.md`
3. On Linux, prefer cron plus `xvfb-run` over Windows Task Scheduler.
4. Preserve existing user files, Chrome profiles, and cron jobs. Append only.
5. For Selenium/Chrome jobs, always run with:
   - absolute project paths
   - correct working directory
   - `xvfb-run -a`
   - a log file
   - `flock` to avoid overlapping posts
6. Verify by running one foreground posting command before adding cron, unless the user only asked to prepare files.

## Discovery Commands

Run from the project root:

```bash
pwd
find . -maxdepth 4 -type f | sort
sed -n '1,120p' .env
sed -n '1,220p' .agents/skills/fb-auto-poster/SKILL.md
sed -n '1,220p' .agents/skills/fb-auto-poster/scripts/OpenFBV2POST.py
crontab -l
which xvfb-run python3 flock google-chrome
google-chrome --version
```

If sandbox blocks network, Chrome, or cron, request escalated execution. Do not silently fall back to fake tests.

## Migration Checklist

Use this order.

1. **Confirm Linux runtime**
   - Check `DISPLAY`. If empty, direct Chrome windows will fail; use `xvfb-run -a`.
   - Check `/usr/bin/google-chrome` exists.
   - Check Python dependencies import with `/usr/bin/python3 -c "import selenium, gspread, dotenv"`.

2. **Fix Windows venv assumptions**
   - Do not assume `venv_linux/bin/python` is executable after copying from Windows.
   - If `Permission denied`, use `/usr/bin/python3` when dependencies are installed, or repair/create a Linux venv.
   - Do not chmod random copied binaries unless you know they are real Linux executables.

3. **Preserve project-relative behavior**
   - Run commands with `workdir`/`cd` set to project root.
   - The script often uses `os.getcwd()` for:
     - `facebook-chrome-profile/`
     - `images/`
     - `googlesheetcn.json`
     - `.env`

4. **Handle Chrome profile**
   - If copied from another project or previous run, remove stale lock symlinks before running:
     ```bash
     rm -f facebook-chrome-profile/SingletonCookie facebook-chrome-profile/SingletonLock facebook-chrome-profile/SingletonSocket
     ```
   - Never delete the whole profile unless the user explicitly asks; it contains login cookies.
   - If the script says "Chưa đăng nhập Facebook" under `xvfb-run`, the user cannot see that browser unless a real GUI or VNC is available. Ask user to copy a logged-in profile, run login on a GUI machine, or provide a visible remote display.

5. **Run one foreground validation**
   ```bash
   cd /absolute/project/root
   /usr/bin/xvfb-run -a /usr/bin/python3 -u /absolute/project/root/.agents/skills/fb-auto-poster/scripts/OpenFBV2POST.py
   ```
   Success signs:
   - "Đã nhận diện phiên đăng nhập cũ"
   - "Đã tải N bài viết từ Google Sheet"
   - "Đã cập nhật trạng thái 'POSTED'"
   - Browser closes cleanly

6. **Install cron**
   - Create a wrapper script. Prefer the bundled helper `scripts/create_cron_wrapper.py`.
   - Add cron using append-safe logic.
   - Start or verify cron daemon.

## Wrapper Pattern

Use this pattern for 5-minute personal posting. Adjust paths only.

```bash
#!/usr/bin/env bash
set -uo pipefail

PROJECT_ROOT="/absolute/project/root"
SCRIPT_PATH="$PROJECT_ROOT/.agents/skills/fb-auto-poster/scripts/OpenFBV2POST.py"
LOG_DIR="$PROJECT_ROOT/logs"
LOG_FILE="$LOG_DIR/personal_5min_post.log"
LOCK_FILE="/tmp/project_name_5min.lock"

mkdir -p "$LOG_DIR"
export TZ="Asia/Ho_Chi_Minh"

{
  echo "============================================================"
  echo "[$(date '+%Y-%m-%d %H:%M:%S %Z')] Start 5-minute personal post check"
  cd "$PROJECT_ROOT" || exit 1
  /usr/bin/flock -n "$LOCK_FILE" /usr/bin/xvfb-run -a /usr/bin/python3 "$SCRIPT_PATH"
  status=$?
  if [ "$status" -eq 1 ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S %Z')] Another run is already active; skipped."
  fi
  echo "[$(date '+%Y-%m-%d %H:%M:%S %Z')] Finished with exit code $status"
  exit "$status"
} >> "$LOG_FILE" 2>&1
```

## Cron Pattern

Append without replacing existing jobs:

```bash
tmpfile="/tmp/project_schedule.cron"
job="*/5 * * * * /absolute/project/root/.agents/skills/fb-auto-poster/scripts/run_5min_post.sh"
comment="# project_name: post 1 personal Facebook item every 5 minutes"
crontab -l > "$tmpfile" 2>/dev/null || true
if grep -Fq "$job" "$tmpfile"; then
  echo "Cron job already exists."
else
  printf '\n%s\n%s\n' "$comment" "$job" >> "$tmpfile"
  crontab "$tmpfile"
  echo "Cron job added."
fi
crontab -l
```

Verify cron:

```bash
pgrep -a cron || /usr/sbin/cron
pgrep -a cron
tail -n 80 /absolute/project/root/logs/personal_5min_post.log
```

If `/usr/sbin/cron` reports `can't lock /var/run/crond.pid`, cron is probably already running. Verify with `ps -p <pid> -f`.

## Common Failures

- **`Could not reach host. Are you offline?`**
  - Network sandbox blocked ChromeDriver download or Google/Facebook access. Rerun with approval.

- **`session not created: Chrome instance exited`**
  - Usually no GUI `DISPLAY`, stale profile locks, or broken Chrome profile. Use `xvfb-run -a`, remove `Singleton*`, and retry.

- **`Permission denied: ./venv_linux/bin/python`**
  - Copied venv files are not executable or not valid Linux binaries. Use `/usr/bin/python3` or rebuild the venv.

- **`Chưa đăng nhập Facebook`**
  - The profile is not logged in for this project root. Copy a logged-in `facebook-chrome-profile`, run `--login-only` on a visible GUI, or set up VNC.

- **Cron added but does not run**
  - Check daemon with `pgrep -a cron`.
  - Use absolute paths only.
  - Ensure wrapper is executable and `bash -n` passes.
  - Look at the wrapper log, not only terminal output.

## Safety Rules

- Never remove or overwrite an existing Chrome profile without explicit user permission.
- Never replace the whole crontab. Always append only the exact job needed.
- Use `flock` for schedules shorter than 15 minutes.
- Do not mark Google Sheet rows manually unless the post actually succeeded.
- Keep old personal/fanpage cron jobs unless the user asks to disable them.
