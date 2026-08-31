# Supervisor Guard And Shared Watchdog

Use the existing Shared Watchdog Center as the runtime. This reference defines
only the OpenClaw Zalo/Gateway entries; it does not replace the generic
`shared-watchdog-center` skill.

## Host-Side Gateway Guard

Source of truth:

- Script: `/root/Automation/watchdog/shared_self_healing/scripts/check_member_gateway_supervisor.py`
- Registry: `/root/Automation/watchdog/shared_self_healing/project_config.json`
- Launcher: `/root/Automation/watchdog/shared_self_healing/run_project.sh`
- Tests: `/root/Automation/watchdog/shared_self_healing/tests/test_member_gateway_supervisor_guard.py`

The guard must run on the main VPS, compare active and persistent Supervisor
blocks, repair only `[program:openclaw-gateway]`, back up both files, validate
staged content, and set `ai_on_failure=false`.

```json
"member_<name>_gateway_supervisor": {
  "project_root": "/root/Automation/watchdog/shared_self_healing",
  "run_command": "/usr/bin/python3 scripts/check_member_gateway_supervisor.py --container user-<name> --member-home <member-home> --member-label <name> --gateway-user <owner>",
  "script_to_fix": "scripts/check_member_gateway_supervisor.py",
  "log_file": "/root/Automation/watchdog/shared_self_healing/logs/member_<name>_gateway_supervisor.log",
  "type": "openclaw_gateway",
  "lock_file": "/tmp/member_<name>_gateway_supervisor.lock",
  "telegram_label": "OpenClaw Gateway Supervisor Guard - <name>",
  "ai_on_failure": false
}
```

Run the guard every minute through a unique cron marker and `run_project.sh`.

## Zalo Channel Watchdog

Configure `member_<name>_zalouser` as `openclaw_channel`. Pass `CONTAINER`,
`MEMBER_HOME`, `MEMBER_LABEL`, and `PROJECT_KEY` to
`scripts/check_member_zalouser.sh`. Schedule every five minutes. It may restart
only the Supervisor-managed Gateway and must keep a ten-minute cooldown.

## Session Maintenance

Configure `member_<name>_sessions` as `openclaw_session` and call
`/root/Automation/openclaw_member_assistant/scripts/audit_member_sessions.sh`
through the shared launcher. Schedule every two hours with an offset minute.
Use summary compaction, ten idle minutes, and at most one compaction per run.

Use a narrow `agent:main:zalouser:direct:<id>` pattern for one recurring DM.
Use `agent:main:zalouser:` only when member-wide Zalo maintenance is explicitly
intended. Do not store private IDs in shared documentation.

## Validation

```bash
python3 -m json.tool /root/Automation/watchdog/shared_self_healing/project_config.json >/dev/null
bash -n /root/Automation/watchdog/shared_self_healing/run_project.sh
python3 -m unittest discover -s /root/Automation/watchdog/shared_self_healing/tests -v
systemctl is-active cron
```

Preserve unrelated registry and cron entries. Healthy checks must not consume
AI tokens or restart services.
