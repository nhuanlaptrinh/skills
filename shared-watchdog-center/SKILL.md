---
name: shared-watchdog-center
description: Thiết kế, tạo, mở rộng, kiểm tra hoặc sửa Shared Watchdog Center cho nhiều dự án tự động chạy cron trên Linux, dùng project_config.json, run_project.sh, self_healing_runner.py, logs/state tập trung, phân loại lỗi, gọi OpenClaw self-healing chỉ khi cần, set cron hằng ngày theo giờ Việt Nam, và mở rộng cho Facebook, Zalo, Django, n8n, crawler, Selenium, Graph API hoặc Python automation.
---

# Shared Watchdog Center

Use this skill when the user wants a reusable self-healing watchdog architecture for many projects instead of one watchdog per project. The goal is to run projects through a central wrapper, write logs consistently, detect failures by exit code, classify errors, call OpenClaw only when code repair is useful, and keep cron schedules easy to manage.

## Core Model

Create one shared center outside individual projects:

```text
shared_self_healing/
├── project_config.json
├── run_project.sh
├── self_healing_runner.py
├── logs/
├── state/
└── README.md
```

Each project is only a config entry. Do not duplicate watchdog logic into every project unless the user explicitly asks for per-project isolation.

## What Each File Does

- `project_config.json`: registry of project names and safe execution details.
- `run_project.sh`: cron-safe launcher; reads config, runs the selected project, writes logs, calls runner on non-zero exit.
- `self_healing_runner.py`: reads latest log, classifies error, prevents duplicate OpenClaw calls, optionally notifies Telegram, calls `openclaw agent`.
- `logs/`: central log files, one per project.
- `state/`: JSON files storing last error hash/type per project to avoid infinite AI loops.
- `README.md`: short user-facing command and maintenance guide.

## Non-Token Rule

Clarify to users when relevant: reading config, running shell/Python scripts, writing logs, and checking exit codes do not consume AI tokens. Tokens are used only when `openclaw agent --message ...` is actually invoked after a failure.

## Recommended Workflow

1. Identify projects to manage.
2. For each project, identify:
   - `project_root`
   - `run_command`
   - `script_to_fix`
   - `log_file`
   - `type`
   - `lock_file`
   - optional `telegram_label`
3. Ensure each main script returns non-zero on real failure.
4. Create or update `shared_self_healing/` using bundled templates or existing center style.
5. Validate JSON, shell syntax, Python syntax.
6. Test wrapper with a safe command if possible.
7. Install cron with marker comments, preserving unrelated cron entries.
8. Report exact paths, cron lines, and how to run manually.

## Project Types

Use these labels in config:

- `selenium`: browser/UI automation, Chrome profile, Xvfb, selectors, login/checkpoint risks.
- `graph_api`: API-based Facebook fanpage posting, token/media/Sheet risks.
- `zalo`: Zalo Web/Selenium automation, Chrome profile and session risks.
- `django`: web app, Docker, migrations, API or healthcheck command.
- `n8n`: workflow/webhook jobs, Docker/API health checks.
- `crawler`: scraper/crawler jobs.
- `python`: generic Python automation.
- `openclaw_channel`: health/recovery check for an OpenClaw channel such as Zalo Personal.
- `openclaw_session`: scheduled OpenClaw session audit/compaction with an explicit channel-key filter.

For OpenClaw session maintenance, set the token threshold comfortably below the effective context limit. For a member configured with `contextTokens=64000` and `reserveTokensFloor=40000`, use a preventive threshold around `45000`, not `60000`. Enable `agents.defaults.contextPruning` separately when large tool results are the main source of context growth, because line-count compaction may not shrink a short transcript containing one very large tool result.

For OpenClaw channel watchdogs, do not rely only on a healthy gateway process. Combine `openclaw channels status --probe` with the latest channel listener events, use a restart cooldown, and notify through a different healthy channel only when an incident or recovery occurs.

The `type` is used to create better OpenClaw prompts and classify errors.

## Config Schema

Each project config should look like:

```json
{
  "fanpage_alt": {
    "project_root": "/absolute/path/to/project",
    "run_command": "/absolute/python -u relative/or/absolute/script.py",
    "script_to_fix": "relative/path/to/main_script.py",
    "log_file": "/absolute/path/to/shared_self_healing/logs/fanpage_alt.log",
    "type": "graph_api",
    "lock_file": "/tmp/fanpage_alt.lock",
    "telegram_label": "Fanpage ALT"
  }
}
```

Rules:

- Use absolute paths for `project_root`, `log_file`, and external Python binaries.
- `script_to_fix` should usually be relative to `project_root`.
- `run_command` runs after `cd project_root`; relative script paths are acceptable.
- Use unique `lock_file` per project.
- Keep project names short, lowercase, stable, and cron-friendly.
- Do not store secrets in `project_config.json`.

## Wrapper Behavior

`run_project.sh <project_name>` must:

1. Read the project entry from `project_config.json`.
2. Create log/state directories.
3. Append a start banner with timestamp.
4. `cd` to `project_root`.
5. Optionally perform pre-run cleanup for known project types, such as removing Chrome lock files for Selenium.
6. Run `run_command` under `flock -n lock_file`.
7. Append finish banner and exit code.
8. If exit code is non-zero, call `self_healing_runner.py <project_name>`.
9. Exit with the original command's status.

Important: Do not call OpenClaw from the wrapper directly. Keep classification and token-saving logic in `self_healing_runner.py`.

## Runner Behavior

`self_healing_runner.py <project_name>` must:

1. Load config.
2. Read only the last 80–160 log lines.
3. Classify error:
   - no-code/manual issue: token expired, missing media, missing `.env`, missing credentials, login checkpoint
   - code-fix issue: traceback, selector failures, ChromeDriver mismatch, request exceptions, API response parsing bugs
4. Hash the error type + log excerpt.
5. If same hash as previous state, skip OpenClaw and notify only.
6. If manual issue, notify only and do not call OpenClaw.
7. If code-fix issue, build a narrow prompt and call `openclaw agent --message`.
8. Notify Telegram if project `.env` contains Telegram settings.

## Error Classification

Do not call OpenClaw for these unless user explicitly asks:

- Facebook token expired or invalid.
- Missing media file.
- Missing `.env` values.
- Missing `googlesheetcn.json` or Google Sheet permission denied.
- Facebook/Zalo checkpoint or login required.
- Payment/API secrets need manual replacement.

Call OpenClaw for these:

- Python traceback due to code bug.
- Selenium selector/DOM changed.
- ChromeDriver/session creation mismatch.
- API response handling changed.
- Upload logic bug.
- Sheet column changed and code can be adapted safely.

## OpenClaw Prompt Rules

The prompt must be narrow and safe. Include:

```text
Project name/type/root
Log excerpt
Allowed file(s) to edit
Exact test command
Safety rules
Expected report
```

Always include these safety rules:

```text
1. Do not edit or print .env, credentials, cookies, Chrome profile, or tokens.
2. Prefer editing only script_to_fix.
3. Create a .bak.timestamp backup before modifying files.
4. If the issue is token/login/media/permission, do not fake a code fix; report the manual action required.
5. Run the exact test command after changes.
6. Report changed files and test result.
```

## Exit Code Requirements

A project is watchdog-ready only if the main command exits correctly:

- success/post completed/no pending work: exit `0`
- real failure: exit non-zero, usually `1`

For Python scripts that currently catch exceptions but return `0`, patch them to call `sys.exit(1)` on real failures.

For Selenium scripts, close the browser in `finally` before `sys.exit(1)`.

For Graph API posting scripts, consider no `PD` row as success (`0`), not a failure.

## Telegram Proxy Pattern

If the VPS cannot reach Telegram directly but WARP proxy is available, add this to project `.env`:

```env
TELEGRAM_PROXY_URL=http://127.0.0.1:40000
```

In Python:

```python
proxy_url = os.getenv("TELEGRAM_PROXY_URL", "").strip()
proxies = {"http": proxy_url, "https": proxy_url} if proxy_url else None
requests.post(url, data=data, proxies=proxies, timeout=10).raise_for_status()
```

If a project sends Telegram notifications, ensure it validates response or calls `raise_for_status()` so failed notifications are visible in logs.

## Cron Rules

When setting cron:

- Preserve unrelated cron entries.
- Wrap managed entries in marker comments:

```cron
# BEGIN ALT_SHARED_WATCHDOG
...
# END ALT_SHARED_WATCHDOG
```

- Know the server timezone. If server timezone is UTC and the user asks for Vietnam time, subtract 7 hours.
- Put project names in comments.
- Use the wrapper, not direct scripts:

```cron
0 1 * * * /root/path/shared_self_healing/run_project.sh personal_alt
```

## Vietnam Time Conversion

If server timezone is UTC:

- 08:00 Vietnam = 01:00 UTC
- 13:00 Vietnam = 06:00 UTC
- 15:00 Vietnam = 08:00 UTC
- 19:00 Vietnam = 12:00 UTC

Always state the conversion in the final report.

## Validation Commands

Run these after creating/updating a center:

```bash
python3 -m json.tool /path/shared_self_healing/project_config.json >/dev/null
python3 -m py_compile /path/shared_self_healing/self_healing_runner.py
bash -n /path/shared_self_healing/run_project.sh
```

Validate referenced files:

```bash
python3 - <<'PY'
import json
from pathlib import Path
cfg=json.loads(Path('/path/shared_self_healing/project_config.json').read_text())
for name,item in cfg.items():
    assert Path(item['project_root']).is_dir(), name
    assert (Path(item['project_root']) / item['script_to_fix']).is_file(), name
    assert item['run_command'], name
print('ok')
PY
```

Check cron:

```bash
crontab -l
systemctl is-active cron 2>/dev/null || systemctl is-active crond 2>/dev/null || service cron status
```

## Manual Run Commands

After setup, users should run projects through the center:

```bash
/path/shared_self_healing/run_project.sh fanpage_alt
```

Check logs:

```bash
tail -120 /path/shared_self_healing/logs/fanpage_alt.log
```

## OpenClaw Zalo Personal Health Check

Với member VPS `user-anhlaptrinhthu` (giữ home nội bộ `/home/anhlaptrinh`), dùng project `member_anhlaptrinh_zalouser` và script:

```bash
bash /root/Automation/watchdog/shared_self_healing/scripts/check_member_zalouser.sh --dry-run
/root/Automation/watchdog/shared_self_healing/run_project.sh member_anhlaptrinh_zalouser
```

Script kiểm tra container, giữ `proxy.enabled=false` để Zalo chạy direct-first, probe `openclaw channels status --probe`, và chỉ restart tmux gateway khi channel không ở trạng thái `configured, running, works`. Cooldown restart là 10 phút. Nếu restart không khôi phục được phiên, script ghi `MANUAL_REQUIRED`; không tự logout, không tự tạo QR và không gọi AI lặp lại.

Log và state:

```text
/root/Automation/watchdog/shared_self_healing/logs/member_anhlaptrinh_zalouser.log
/root/Automation/watchdog/shared_self_healing/state/member_anhlaptrinh_zalouser_runtime.json
```

Reset duplicate-error protection for one project:

```bash
rm -f /path/shared_self_healing/state/fanpage_alt.json
```

## Implementation Shortcuts

Prefer copying bundled templates from `scripts/` and editing config, rather than rewriting boilerplate from memory.

Use:

- `scripts/run_project.sh.template`
- `scripts/self_healing_runner.py.template`
- `scripts/project_config.example.json`

## Final Report Checklist

When finished, report:

- Center path.
- Project names configured.
- Cron schedule in user timezone and server timezone.
- Validation commands run.
- Whether Telegram test was sent.
- How to manually run a project.
- Where logs and state files live.
