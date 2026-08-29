---
name: recover-openclaw-member-gateway
description: Diagnose, recover, and harden Docker member-VPS OpenClaw gateways when the container is running but Telegram and Zalo both stop replying, `openclaw-gateway` or its tmux pane disappears after a container restart, the Gateway is not managed by Supervisor, or recurring channel/session failures need self-healing. Use for member data under `/root/Apps/member_vps/docker-users/data`, not for the root OpenClaw runtime.
---

# Recover OpenClaw Member Gateway

Restore exactly one Gateway, make it survive container restarts, and add channel
and session self-healing without changing tokens, pairing, or transcripts.

## Required preflight

1. Read the VPS Second AI Brain, production checklist, nearest `AGENTS.md`, and member project note.
2. Resolve these inputs exactly:
   - `CONTAINER`, such as `user-<member>`
   - `MEMBER_HOME` inside the container
   - `HOST_DATA_DIR` that directly contains `.openclaw`
   - `MEMBER_LABEL` and unique watchdog project names
3. Confirm whether the active Gateway parent is `supervisord`, `tmux`, or absent.
4. Never print `.env`, tokens, cookies, QR payloads, pairing files, sender IDs, or message contents.

## Diagnose first

Run the read-only channel diagnostic:

```bash
bash /root/.agents/skills/openclaw-zalo-no-response/scripts/diagnose.sh \
  "$CONTAINER" "$MEMBER_HOME"
```

Run the reusable dry-runs:

```bash
CONTAINER="$CONTAINER" MEMBER_HOME="$MEMBER_HOME" \
MEMBER_LABEL="$MEMBER_LABEL" PROJECT_KEY="member_${MEMBER_LABEL}_zalouser" \
  bash /root/Automation/watchdog/shared_self_healing/scripts/check_member_zalouser.sh --dry-run

MEMBER_HOME="$MEMBER_HOME" SESSION_PATTERN='agent:main:zalouser:' \
TOKEN_THRESHOLD_64K=18000 TOKEN_THRESHOLD_128K=40000 \
SESSION_IDLE_SECONDS=600 MAX_COMPACTIONS_PER_RUN=1 COMPACTION_MODE=summary \
  bash /root/Automation/openclaw_member_assistant/scripts/audit_member_sessions.sh "$CONTAINER"

MEMBER_DATA_DIR="$HOST_DATA_DIR" \
  bash /root/Automation/openclaw_member_assistant/scripts/patch_zalouser_send_reliability.sh
```

Interpret the result:

- Gateway absent and both channels config-only: restore the process manager.
- Gateway present but Zalo listener/outbound fails: use `$openclaw-zalo-no-response`.
- Gateway healthy but a session is oversized/long-running: compact or retire only the affected key.
- Credential/cipher/login failure persists after version alignment: require manual QR only as the last resort.

## Backup before apply

Create a root-only timestamped folder under `/root/_Backups` and preserve:

- `$HOST_DATA_DIR/.openclaw/openclaw.json`
- `$HOST_DATA_DIR/.openclaw/agents/main/sessions/sessions.json`
- the active Zalo send bundle reported by `openclaw plugins inspect zalouser`
- `/root/Automation/watchdog/shared_self_healing/project_config.json`
- root crontab
- container `/etc/supervisor/conf.d/member-vps.conf`
- container `/usr/local/bin/member-vps-entrypoint.sh`
- the member project note before editing it

Do not copy credentials into documentation or command output. A root-only backup
may contain the production config needed for rollback.

## Restore persistent Gateway management

Read [references/supervisor-and-watchdog.md](references/supervisor-and-watchdog.md)
before editing Supervisor or cron.

1. Add the same `openclaw-gateway` program block to the active Supervisor config and to the entrypoint heredoc that regenerates it.
2. Use the exact member HOME and the existing OpenClaw data owner. Legacy root-owned member data must run the Gateway as root.
3. Remove dependence on `tmux`; never start a second Gateway beside an existing live process.
4. Validate the staged entrypoint with `bash -n`.
5. Reload Supervisor once. This may restart SSH/Nginx/XRDP inside the container for a few seconds; do not recreate the container.
6. Confirm exactly one `openclaw-gateway` and that its parent command is `supervisord`.

Test process recovery by terminating only the Gateway PID. Require a different
PID to appear under Supervisor and both channels to reconnect. Do not restart the
whole container only to test this path.

## Install self-healing

When the incident involved a missing, commented, or drifted Supervisor Gateway
block, first install the host-side `$openclaw-member-gateway-supervisor-guard`:

- add `member_<name>_gateway_supervisor` to Shared Watchdog Center;
- set `ai_on_failure=false`;
- run it every minute from root cron;
- verify its dry-run reports `HEALTHY` before enabling cron.

For members using Zalo Personal, also add two unique Shared Watchdog Center
entries and preserve all unrelated entries:

- `member_<name>_zalouser`: every 5 minutes, probe the live Zalo listener and restart only the Supervisor-managed Gateway with a 10-minute cooldown.
- `member_<name>_sessions`: every 2 hours, target `agent:main:zalouser:`, require 10 idle minutes, summary-compact at most one session per run, and use 18k/64k or 40k/128k thresholds.

Install cron through marker blocks shown in the reference file. Use
`/root/Automation/watchdog/shared_self_healing/run_project.sh`; do not call the
underlying scripts directly from cron.

Enable preventive context handling when absent:

```bash
docker exec "$CONTAINER" sh -lc "export HOME='$MEMBER_HOME'; \
openclaw config set agents.defaults.contextPruning.mode cache-ttl; \
openclaw config set agents.defaults.contextPruning.ttl 5m; \
openclaw config set agents.defaults.compaction.mode safeguard; \
openclaw config set agents.defaults.compaction.reserveTokensFloor 40000; \
openclaw config set agents.defaults.compaction.maxHistoryShare 0.5; \
openclaw config validate"
```

## Recover stuck sessions

1. Run the session project once after the Gateway is healthy.
2. If summary compaction times out but the session drops below threshold, keep it.
3. If the same idle session remains oversized and produces long-running events:
   - backup the current session index and target transcript;
   - freeze only the Gateway so it cannot rewrite the index;
   - remove exactly one affected key from `sessions.json`;
   - preserve the transcript file;
   - terminate the frozen Gateway and let Supervisor create one fresh process.
4. Never delete all sessions or transcript files.

## Verify

Run all relevant checks before reporting completion:

```bash
python3 -m json.tool /root/Automation/watchdog/shared_self_healing/project_config.json >/dev/null
bash -n /root/Automation/watchdog/shared_self_healing/run_project.sh
bash -n /root/Automation/watchdog/shared_self_healing/scripts/check_member_zalouser.sh
bash -n /root/Automation/openclaw_member_assistant/scripts/audit_member_sessions.sh
systemctl is-active cron

docker exec "$CONTAINER" sh -lc "export HOME='$MEMBER_HOME'; \
openclaw config validate; openclaw plugins doctor; \
timeout 60s openclaw channels status --probe"
```

Confirm:

- exactly one Gateway exists and its parent is Supervisor;
- the host-side Gateway Supervisor guard is `HEALTHY` when installed;
- Telegram is `running, connected, works, audit ok`;
- Zalo Personal is `configured, running, works`;
- no new listener, outbound, cipher, or long-running event appears after the latest provider start;
- current Telegram/Zalo sessions are below the preventive threshold;
- both cron jobs exist and cron is active.

Do not send a real Telegram or Zalo message unless the user explicitly authorizes it. Passive `in:` and `out:` activity is sufficient evidence.

## Rollback and documentation

Restore only the files changed in the transaction. If Supervisor loading fails,
restore both its active config and the entrypoint generator before reloading.
Restore the session index only if the targeted reset caused a regression; keep
all transcripts.

After production changes, update the member project note and
`/root/_Second_AI_Brain/06_Nhat_Ky_Thay_Doi.md`. Record backup paths, schedules,
validation results, and whether a real message was sent. Never record secrets or
private sender/group IDs.
