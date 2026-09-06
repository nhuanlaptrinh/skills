---
name: openclaw-zalouser-onboarding-standard
description: Chuẩn hóa việc kết nối OpenClaw với Zalo Personal cho member VPS, root VPS hoặc agent khác. Use when onboarding a new Zalo account, binding Zalo to an OpenClaw agent, creating a new member Zalo runtime, migrating an existing Zalo runtime to managed supervision, or applying the required Gateway, channel watchdog, session, resource/OOM, backup, and verification safeguards.
---

# OpenClaw Zalo User Onboarding Standard

Use this skill as the orchestration layer for every new or migrated OpenClaw
Zalo Personal connection. It delegates incident details to
`openclaw-zalo-reliability`, shared scheduling to `shared-watchdog-center`, and
host pressure monitoring to `member-vps-resource-oom-guard`.

## Required Inputs

Resolve these values without printing secrets:

```text
RUNTIME_KIND=docker-member|root-service|systemd-service
CONTAINER=user-<member>                 # Docker member only
MEMBER_HOME=/home/<member>              # or the service OpenClaw HOME
MEMBER_LABEL=<member>
OPENCLAW_ROOT=<MEMBER_HOME>/.openclaw
AGENT_ID=<agent-id>
ZALO_ACCOUNT_ID=<account-id>
DATA_DIR=<host directory containing OPENCLAW_ROOT>
```

For a member VPS, also resolve the container PID, Gateway parent process,
persistent entrypoint, Supervisor config, shared watchdog project key, and the
healthy notification account. Never copy an owner ID, credential, QR payload,
or token from another member.

## Mandatory Order

1. Read the VPS Second AI Brain, production checklist, nearest `AGENTS.md`, and
   the affected project note.
2. Run read-only preflight and back up all files that may change.
3. Ensure exactly one Gateway is managed by Supervisor/systemd; do not leave a
   member Gateway only in tmux.
4. Align OpenClaw core and `@openclaw/zalouser` release lines.
5. Configure the Zalo account binding, DM policy, group policy, and mention
   policy explicitly.
6. Complete QR login only through `openclaw-zalo-qr-login` after owner consent.
7. Validate config, plugin, Gateway, Telegram fallback, and Zalo channel.
8. Register Gateway, Zalo channel, and resource/OOM watchdog entries.
9. Install cron through the shared launcher, then run dry-runs again.
10. Record sanitized backups, outputs, and the final state in the project note
    and Second AI Brain change log.

## Preflight Dry Run

For a Docker member, run the following from the main VPS:

```bash
bash /root/.agents/skills/openclaw-zalo-reliability/scripts/diagnose.sh \
  "$CONTAINER" "$MEMBER_HOME"

python3 /root/Automation/watchdog/shared_self_healing/scripts/check_member_gateway_supervisor.py \
  --container "$CONTAINER" --member-home "$MEMBER_HOME" \
  --member-label "$MEMBER_LABEL" --gateway-user root --dry-run

CONTAINER="$CONTAINER" MEMBER_HOME="$MEMBER_HOME" \
MEMBER_LABEL="$MEMBER_LABEL" PROJECT_KEY="member_${MEMBER_LABEL}_zalouser" \
bash /root/Automation/watchdog/shared_self_healing/scripts/check_member_zalouser.sh --dry-run

python3 /root/Automation/watchdog/shared_self_healing/scripts/check_member_resource_guard.py \
  --container "$CONTAINER" --member-home "$MEMBER_HOME" \
  --member-label "$MEMBER_LABEL" --account "$TELEGRAM_ACCOUNT_ID" --dry-run
```

For a root or systemd service, use the same logical checks with the service
manager's process/status commands and do not pass Docker-only arguments.

## Apply Procedure

Before the first write, back up the active Supervisor config, persistent
entrypoint, OpenClaw config, session index/database companions, plugin bundle,
watchdog registry, crontab, project note, and affected skill. Store backups
root-only under `/root/_Backups/<incident>/<UTC timestamp>`.

For a Docker member with an unmanaged Gateway, quiesce only the existing
Gateway, then use the Supervisor guard. Never start a second Gateway:

```bash
python3 /root/Automation/watchdog/shared_self_healing/scripts/check_member_gateway_supervisor.py \
  --container "$CONTAINER" --member-home "$MEMBER_HOME" \
  --member-label "$MEMBER_LABEL" --gateway-user root \
  --backup-root "/root/_Backups/openclaw-member-gateway-supervisor-guard"
```

Configure the Zalo account with the Zalo Reliability procedure, preserve the
existing credential/session, and use QR login only when version alignment and a
clean Gateway restart do not recover authentication. Do not send a real Zalo
test message as part of onboarding.

## Shared Watchdog Contract

Every Zalo runtime must have these unique registry keys in
`/root/Automation/watchdog/shared_self_healing/project_config.json`:

```json
"member_<label>_gateway_supervisor": {
  "project_root": "/root/Automation/watchdog/shared_self_healing",
  "run_command": "/usr/bin/python3 scripts/check_member_gateway_supervisor.py --container user-<label> --member-home <member-home> --member-label <label> --gateway-user root",
  "script_to_fix": "scripts/check_member_gateway_supervisor.py",
  "log_file": "/root/Automation/watchdog/shared_self_healing/logs/member_<label>_gateway_supervisor.log",
  "type": "openclaw_gateway",
  "lock_file": "/tmp/member_<label>_gateway_supervisor.lock",
  "telegram_label": "OpenClaw Gateway Supervisor Guard - <label>",
  "ai_on_failure": false
},
"member_<label>_zalouser": {
  "project_root": "/root/Automation/watchdog/shared_self_healing",
  "run_command": "WATCHDOG_TELEGRAM_ACCOUNT='<telegram-account>' CONTAINER='user-<label>' MEMBER_HOME='<member-home>' MEMBER_LABEL='<label>' PROJECT_KEY='member_<label>_zalouser' bash scripts/check_member_zalouser.sh",
  "script_to_fix": "scripts/check_member_zalouser.sh",
  "log_file": "/root/Automation/watchdog/shared_self_healing/logs/member_<label>_zalouser.log",
  "type": "openclaw_channel",
  "lock_file": "/tmp/member_<label>_zalouser.lock",
  "telegram_label": "OpenClaw Zalo Personal - <label>"
},
"member_<label>_resource_guard": {
  "project_root": "/root/Automation/watchdog/shared_self_healing",
  "run_command": "/usr/bin/python3 scripts/check_member_resource_guard.py --container user-<label> --member-home <member-home> --member-label <label> --account <telegram-account>",
  "script_to_fix": "scripts/check_member_resource_guard.py",
  "log_file": "/root/Automation/watchdog/shared_self_healing/logs/member_<label>_resource_guard.log",
  "type": "host_resource",
  "lock_file": "/tmp/member_<label>_resource_guard.lock",
  "telegram_label": "OpenClaw Resource/OOM Guard - <label>",
  "ai_on_failure": false
}
```

Install cron only through `run_project.sh`:

```cron
* * * * * /root/Automation/watchdog/shared_self_healing/run_project.sh member_<label>_gateway_supervisor
*/5 * * * * /root/Automation/watchdog/shared_self_healing/run_project.sh member_<label>_zalouser
*/5 * * * * /root/Automation/watchdog/shared_self_healing/run_project.sh member_<label>_resource_guard
```

Use unique marker blocks and preserve unrelated cron entries. Add session
maintenance separately only when evidence shows idle session growth.

## Health And Resource Rules

- Treat Zalo as healthy only when `configured`, `running`, and `works` are
  separate status tokens; `health:not-running` is unhealthy.
- Allow intermediate fields such as `linked` and `connected`.
- Treat `dm:pairing` as access policy, not authentication proof.
- Do not restart the whole container for a Gateway-only or Zalo-only failure.
- Keep a restart cooldown and notify through a different healthy channel.
- Monitor host `MemAvailable`, `SwapFree`, memory PSI, recent OOM events, and
  the target cgroup; never kill unrelated processes automatically.
- If host OOM repeats, investigate high-memory workloads or host capacity; do
  not delete sessions, credentials, browser profiles, or SQLite state.

## Final Acceptance

Do not report completion until all applicable checks pass:

```bash
openclaw config validate
openclaw plugins doctor
openclaw channels status --probe
openclaw skills check
```

Also verify one Gateway, Supervisor/systemd parent, healthy fallback channel,
Zalo `configured/linked/running/connected/works`, three watchdog keys, cron
markers, sanitized state/log files, restrictive backup permissions, and a
change-log entry. Record whether any real notification was sent; do not use a
real Zalo message as a health test without explicit authorization.

## Recovery Routing

- Listener, inbound, outbound, cipher, or Zalo session incident: read
  `openclaw-zalo-reliability` and only the required reference.
- Missing or drifted Supervisor Gateway: read its `gateway-recovery` and
  `supervisor-watchdog` references.
- Host RAM, swap, PSI, or OOM pressure: read
  `member-vps-resource-oom-guard`.
- Generic Shared Watchdog architecture or new project type: read
  `shared-watchdog-center`.

Never use this onboarding standard to bypass owner consent, reveal secrets,
force QR login, or create duplicate Gateway processes.
