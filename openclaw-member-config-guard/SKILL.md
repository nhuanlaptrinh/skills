---
name: openclaw-member-config-guard
description: Install, verify, repair, update, or remove the self-healing OpenClaw config guard for Docker member VPS containers when Telegram returns generic processing errors, tools.allow changes are cached, or group:messaging is accidentally reintroduced.
---

# OpenClaw Member Config Guard

## Source Of Truth

- Project: `/root/Automation/watchdog/openclaw_member_config_guard`
- Guard script: `/root/Automation/watchdog/openclaw_member_config_guard/openclaw_config_guard.py`
- Tests: `/root/Automation/watchdog/openclaw_member_config_guard/tests/test_openclaw_config_guard.py`
- Member config: `/root/Apps/member_vps/docker-users/data/<username>/.openclaw/openclaw.json`
- Deployed script: `/home/<username>/.openclaw/tools/openclaw_config_guard.py`
- Runtime state: `/home/<username>/.openclaw/state/openclaw-config-guard-state.json`
- Automatic backups: `/home/<username>/.openclaw/state/config-guard-backups/`
- Runtime log: `/tmp/openclaw-config-guard.log`

## Behavior

- Poll `openclaw.json` without logging credential values.
- Remove only `group:messaging` from `tools.allow`; preserve all other entries.
- Backup the config with mode `0600` before automatic repair.
- Run `openclaw config validate`; rollback when validation fails.
- Restart only `openclaw-gateway` when the tools allow policy changes because Telegram connectors can retain stale policy after hot reload.
- Leave invalid JSON untouched and retry later.

## Dry Run

Run from the host without changing production:

```bash
python3 /root/Automation/watchdog/openclaw_member_config_guard/openclaw_config_guard.py \
  --config /root/Apps/member_vps/docker-users/data/<username>/.openclaw/openclaw.json \
  --once \
  --dry-run
```

Run the deployed copy inside a member container:

```bash
docker exec user-<username> sh -lc 'HOME=/home/<username> python3 /home/<username>/.openclaw/tools/openclaw_config_guard.py --config /home/<username>/.openclaw/openclaw.json --once --dry-run'
```

## Supervisor Command

Add this program to the supervisor heredoc inside `/usr/local/bin/member-vps-entrypoint.sh`:

```ini
[program:openclaw-config-guard]
command=/usr/bin/python3 /home/<username>/.openclaw/tools/openclaw_config_guard.py --config /home/<username>/.openclaw/openclaw.json --home /home/<username> --poll-seconds 5 --restart-process-pattern ^openclaw-gateway$
environment=HOME="/home/<username>",PYTHONUNBUFFERED="1"
autorestart=true
startsecs=5
startretries=20
priority=10
stdout_logfile=/tmp/openclaw-config-guard.log
stderr_logfile=/tmp/openclaw-config-guard.log
```

Set `priority=20` on `openclaw-gateway`. Backup the entrypoint into `/root/_Backups`, run `bash -n`, then restart only the target container so the generated supervisor config includes the guard.

## Verification

```bash
python3 -m unittest discover -s /root/Automation/watchdog/openclaw_member_config_guard/tests -v
docker top user-<username> -eo pid,ppid,user,etimes,stat,args
docker exec user-<username> sh -lc 'tail -n 50 /tmp/openclaw-config-guard.log'
docker exec user-<username> sh -lc 'HOME=/home/<username> openclaw channels status --probe'
```

Confirm both `openclaw-config-guard` and `openclaw-gateway` are children of Supervisor, Telegram is `connected`, and the config has no `group:messaging` entry.

## Controlled Fault Test

Backup `openclaw.json` before production fault injection. Add only `group:messaging` temporarily, wait for the guard to create a backup, remove the invalid entry, validate the config, and signal Gateway. Confirm the Gateway PID changes and Telegram returns to `connected`. Do not send a real Telegram message during the test.

## Rollback

- Remove the `openclaw-config-guard` program from the container entrypoint.
- Restore the backed-up entrypoint with owner `root:root` and mode `0755`.
- Restart only the target container.
- Keep automatic config backups until the member confirms stable operation.

## Safety

- Never log token, API key, cookie, password, private key, `.env`, or full config content.
- Never auto-remove allow entries other than `group:messaging`.
- Never recreate the member container for this repair.
- Never change other member containers without an explicit request.
