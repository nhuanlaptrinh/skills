# Supervisor And Watchdog Templates

Use these templates only after resolving the exact container, member HOME, host
data directory, and current process manager.

## Supervisor program

Add this block to both `/etc/supervisor/conf.d/member-vps.conf` and the matching
heredoc in `/usr/local/bin/member-vps-entrypoint.sh`:

```ini
[program:openclaw-gateway]
command=/usr/bin/openclaw gateway run
environment=HOME="<member-home>"
user=root
autorestart=true
startsecs=5
startretries=20
stopsignal=TERM
stopasgroup=true
killasgroup=true
stdout_logfile=/tmp/openclaw-supervisor.log
stderr_logfile=/tmp/openclaw-supervisor.log
stdout_logfile_maxbytes=10MB
stdout_logfile_backups=3
```

Use the existing data owner instead of `root` when the OpenClaw tree is not
root-owned. Confirm `/usr/bin/openclaw` with `command -v openclaw` before apply.

After staging:

```bash
bash -n member-vps-entrypoint.sh.staged
docker exec <container> kill -HUP 1
```

The HUP reloads Supervisor and may briefly restart its other managed programs.
Wait for `openclaw-gateway` to remain running for at least `startsecs`.

## Channel watchdog entry

```json
"member_<name>_zalouser": {
  "project_root": "/root/Automation/watchdog/shared_self_healing",
  "run_command": "CONTAINER='<container>' MEMBER_HOME='<member-home>' MEMBER_LABEL='<name>' PROJECT_KEY='member_<name>_zalouser' bash scripts/check_member_zalouser.sh",
  "script_to_fix": "scripts/check_member_zalouser.sh",
  "log_file": "/root/Automation/watchdog/shared_self_healing/logs/member_<name>_zalouser.log",
  "type": "openclaw_channel",
  "lock_file": "/tmp/member_<name>_zalouser.lock",
  "telegram_label": "OpenClaw Zalo Personal - <name>"
}
```

## Session maintenance entry

```json
"member_<name>_sessions": {
  "project_root": "/root/Automation/openclaw_member_assistant",
  "run_command": "MEMBER_HOME='<member-home>' SESSION_PATTERN='agent:main:zalouser:' TOKEN_THRESHOLD_64K=18000 TOKEN_THRESHOLD_128K=40000 SESSION_IDLE_SECONDS=600 MAX_COMPACTIONS_PER_RUN=1 COMPACTION_MODE='summary' bash scripts/audit_member_sessions.sh <container> --apply",
  "script_to_fix": "scripts/audit_member_sessions.sh",
  "log_file": "/root/Automation/watchdog/shared_self_healing/logs/member_<name>_sessions.log",
  "type": "openclaw_session",
  "lock_file": "/tmp/member_<name>_sessions.lock",
  "telegram_label": "OpenClaw Zalo Session Maintenance - <name>"
}
```

The broad Zalo pattern covers direct and group sessions without storing private
sender or group IDs in the registry.

## Cron markers

```cron
# BEGIN member_<name>_zalouser_watchdog
*/5 * * * * /root/Automation/watchdog/shared_self_healing/run_project.sh member_<name>_zalouser
# END member_<name>_zalouser_watchdog

# BEGIN member_<name>_session_maintenance
# Every 2 hours; summary-compact one idle Zalo session when over threshold.
35 */2 * * * /root/Automation/watchdog/shared_self_healing/run_project.sh member_<name>_sessions
# END member_<name>_session_maintenance
```

Offset the session-maintenance minute when another member already uses minute
35. Interval schedules do not require Vietnam-time conversion.

## Expected outputs

- Channel log: `/root/Automation/watchdog/shared_self_healing/logs/member_<name>_zalouser.log`
- Session log: `/root/Automation/watchdog/shared_self_healing/logs/member_<name>_sessions.log`
- Runtime state: `/root/Automation/watchdog/shared_self_healing/state/member_<name>_zalouser_runtime.json`
- Rollback backup: `/root/_Backups/openclaw-<name>-self-healing-<UTC timestamp>/`

## Manual runs

```bash
/root/Automation/watchdog/shared_self_healing/run_project.sh member_<name>_zalouser
/root/Automation/watchdog/shared_self_healing/run_project.sh member_<name>_sessions
```

The first command should report `HEALTHY` when the channel is working. The
second may use model tokens only when summary compaction is actually required.
