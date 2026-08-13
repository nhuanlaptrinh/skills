# Shared Watchdog Templates

Replace every placeholder and preserve valid JSON commas.

## Channel health project

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

## Session maintenance project

Use a narrow direct-session pattern when one owner DM is the recurring failure.

```json
"member_<name>_sessions": {
  "project_root": "/root/Automation/openclaw_member_assistant",
  "run_command": "MEMBER_HOME='<member-home>' SESSION_PATTERN='agent:main:zalouser:direct:<zalo-id>' TOKEN_THRESHOLD_64K=18000 TOKEN_THRESHOLD_128K=40000 SESSION_IDLE_SECONDS=600 MAX_COMPACTIONS_PER_RUN=1 COMPACTION_MODE='summary' bash scripts/audit_member_sessions.sh <container> --apply",
  "script_to_fix": "scripts/audit_member_sessions.sh",
  "log_file": "/root/Automation/watchdog/shared_self_healing/logs/member_<name>_sessions.log",
  "type": "openclaw_session",
  "lock_file": "/tmp/member_<name>_sessions.lock",
  "telegram_label": "OpenClaw Zalo Session Maintenance - <name>"
}
```

## Cron

The server uses UTC. These schedules are interval-based, so no Vietnam-time conversion is required.

```cron
# BEGIN member_<name>_zalouser_watchdog
*/5 * * * * /root/Automation/watchdog/shared_self_healing/run_project.sh member_<name>_zalouser
# END member_<name>_zalouser_watchdog

# BEGIN member_<name>_session_maintenance
# Offset the minute from other members to avoid simultaneous compaction.
35 */2 * * * /root/Automation/watchdog/shared_self_healing/run_project.sh member_<name>_sessions
# END member_<name>_session_maintenance
```

## Validation

```bash
python3 -m json.tool /root/Automation/watchdog/shared_self_healing/project_config.json >/dev/null
bash -n /root/Automation/watchdog/shared_self_healing/run_project.sh
/root/Automation/watchdog/shared_self_healing/run_project.sh member_<name>_zalouser
/root/Automation/watchdog/shared_self_healing/run_project.sh member_<name>_sessions
crontab -l
systemctl is-active cron
```

Do not send a real Zalo or Telegram test message unless authorized.
