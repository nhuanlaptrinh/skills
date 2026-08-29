---
name: openclaw-member-gateway-supervisor-guard
description: Install, verify, operate, test, update, or remove the host-side self-healing guard that prevents a Docker member OpenClaw Gateway from disappearing when the Supervisor program block is commented, deleted, drifted, or fails to start. Use for member containers under `/root/Apps/member_vps/docker-users/data` when the container remains Up but Telegram stops replying, port 18789 disappears, or Nginx returns 502.
---

# OpenClaw Member Gateway Supervisor Guard

Protect the Gateway from outside the member container so recovery still works
when the in-container Gateway process or Supervisor program block is gone.

## Source Of Truth

- Shared center: `/root/Automation/watchdog/shared_self_healing`
- Guard script: `/root/Automation/watchdog/shared_self_healing/scripts/check_member_gateway_supervisor.py`
- Tests: `/root/Automation/watchdog/shared_self_healing/tests/test_member_gateway_supervisor_guard.py`
- Registry: `/root/Automation/watchdog/shared_self_healing/project_config.json`
- Launcher: `/root/Automation/watchdog/shared_self_healing/run_project.sh`
- Logs: `/root/Automation/watchdog/shared_self_healing/logs/member_<name>_gateway_supervisor.log`
- State: `/root/Automation/watchdog/shared_self_healing/state/member_<name>_gateway_supervisor_runtime.json`
- Automatic backups: `/root/_Backups/openclaw-member-gateway-supervisor-guard/<name>/<UTC timestamp>/`

## When To Use

- Container is running but `openclaw-gateway` is absent.
- Port `127.0.0.1:18789` is not listening or the member web proxy returns `502`.
- `[program:openclaw-gateway]` was commented, removed, or changed in the active Supervisor config.
- The entrypoint heredoc and active Supervisor config no longer contain the same Gateway block.
- A member needs automatic prevention after a manual Gateway recovery.

This guard is different from `openclaw-member-config-guard`, which protects
specific `openclaw.json` tool policy. Use this skill for process-manager drift.

## Behavior

1. Run from the main VPS, not under the Supervisor being protected.
2. Read only the active Supervisor config and persistent entrypoint from the target container.
3. Use the valid entrypoint Gateway block as the preferred canonical source, then the active block, then the standard generated block.
4. Repair only `[program:openclaw-gateway]`; preserve SSH, Nginx, XRDP, video bots, and unrelated programs.
5. Backup both files into a root-only timestamped directory before an automatic repair.
6. Validate the staged entrypoint with `bash -n` and the Supervisor config with Python before applying.
7. Reload Supervisor, require exactly one Gateway under PID 1, and require Telegram `running, connected, works`.
8. Set `ai_on_failure=false` so infrastructure failures do not invoke an AI repair agent or consume tokens.

## Dry Run

```bash
/usr/bin/python3 \
  /root/Automation/watchdog/shared_self_healing/scripts/check_member_gateway_supervisor.py \
  --container user-<name> \
  --member-home /home/<name> \
  --member-label <name> \
  --gateway-user root \
  --dry-run
```

Dry-run reports `HEALTHY` or the exact repair action without modifying files or state,
reloading Supervisor, restarting Gateway, or sending messages.

## Shared Watchdog Entry

Add a unique registry entry:

```json
"member_<name>_gateway_supervisor": {
  "project_root": "/root/Automation/watchdog/shared_self_healing",
  "run_command": "/usr/bin/python3 scripts/check_member_gateway_supervisor.py --container user-<name> --member-home /home/<name> --member-label <name> --gateway-user root",
  "script_to_fix": "scripts/check_member_gateway_supervisor.py",
  "log_file": "/root/Automation/watchdog/shared_self_healing/logs/member_<name>_gateway_supervisor.log",
  "type": "openclaw_gateway",
  "lock_file": "/tmp/member_<name>_gateway_supervisor.lock",
  "telegram_label": "OpenClaw Gateway Supervisor Guard - <name>",
  "ai_on_failure": false
}
```

Install cron with marker comments and preserve unrelated entries:

```cron
# BEGIN member_<name>_gateway_supervisor_guard
* * * * * /root/Automation/watchdog/shared_self_healing/run_project.sh member_<name>_gateway_supervisor
# END member_<name>_gateway_supervisor_guard
```

## Manual Run

```bash
/root/Automation/watchdog/shared_self_healing/run_project.sh member_<name>_gateway_supervisor
```

Healthy checks do not restart services and do not consume AI tokens. A real
repair briefly reloads Supervisor and may restart its managed programs.

## Verification

```bash
python3 -m unittest discover \
  -s /root/Automation/watchdog/shared_self_healing/tests -v
python3 -m json.tool \
  /root/Automation/watchdog/shared_self_healing/project_config.json >/dev/null
bash -n /root/Automation/watchdog/shared_self_healing/run_project.sh
systemctl is-active cron
docker exec user-<name> sh -lc 'pgrep -af "^openclaw-gateway"'
docker exec user-<name> sh -lc \
  'HOME=/home/<name> openclaw channels status --channel telegram --probe'
```

Confirm the log reports `HEALTHY` or `RECOVERED`, exactly one Gateway has parent
PID 1, active and entrypoint blocks match, and Telegram is connected.

## Rollback

1. Remove only the member registry entry and its cron marker block.
2. Restore `project_config.json`, `run_project.sh`, skill, and cron from the transaction backup when needed.
3. If an automatic repair changed container files, restore only the matching timestamped `member-vps.conf.before` and `member-vps-entrypoint.sh.before`, validate, then reload Supervisor.
4. Keep logs and backups until the member confirms stable operation.

## Safety

- Never print or copy token, API key, cookie, password, private key, `.env`, message content, sender ID, or pairing data.
- Never recreate the container for this repair.
- Never overwrite unrelated Supervisor program blocks.
- Never auto-delete Telegram groups, sessions, or transcripts.
- Do not fault-inject production unless the owner explicitly authorizes it; unit tests and dry-run are the default verification.
