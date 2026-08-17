---
name: openclaw-zalo-no-response
description: Diagnose, recover, and prevent recurring OpenClaw Zalo Personal cases where direct messages or group messages receive no reply, replies fail outbound, the listener silently exits, pairing appears valid but messages do not enter sessions, sessions become long-running or oversized, gateway probes show config-only status, or Zalo works temporarily after restart and then fails again. Use for member VPS Docker containers before deleting credentials or requiring QR login.
---

# OpenClaw Zalo No Response

Recover silent Zalo replies without losing pairing, credentials, or transcripts. Distinguish inbound, outbound, listener, session, plugin, and probe failures before changing production.

## Required preflight

1. Read the VPS Second AI Brain, the project `AGENTS.md`, the relevant project note, and the production checklist.
2. Resolve the exact Docker container, internal member HOME, host data directory, OpenClaw config, session store, and Supervisor gateway process.
3. Backup config, session index, affected plugin bundle, watchdog registry, and crontab before applying changes.
4. Do not print `.env`, gateway tokens, cookies, QR payloads, Zalo credentials, or message contents.

## Diagnose first

Run the bundled read-only diagnostic:

```bash
bash /root/.agents/skills/openclaw-zalo-no-response/scripts/diagnose.sh <container> <member-home> [zalo-id]
```

Examples of member HOME values are `/root` and `/home/<member>`. Never assume `/home/anhlaptrinh` for every container.

Then run the reusable dry-runs:

```bash
CONTAINER=<container> MEMBER_HOME=<member-home> MEMBER_LABEL=<label> PROJECT_KEY=<project-key> \
  bash /root/Automation/watchdog/shared_self_healing/scripts/check_member_zalouser.sh --dry-run

MEMBER_HOME=<member-home> SESSION_PATTERN='agent:main:zalouser:direct:<zalo-id>' COMPACTION_MODE=summary \
  bash /root/Automation/openclaw_member_assistant/scripts/audit_member_sessions.sh <container>

MEMBER_DATA_DIR=<host-member-home> \
  bash /root/Automation/openclaw_member_assistant/scripts/patch_zalouser_send_reliability.sh
```

`MEMBER_DATA_DIR` must point to the host directory that directly contains `.openclaw`; some members use `data/<member>`, while others use `data/<member>/root`.
The patch script checks compatible send bundles newest-first so an old patched plugin generation cannot hide an unpatched active generation. After a plugin update, confirm the dry-run target belongs to the source path reported by `openclaw plugins inspect zalouser`.

## Decision tree

### Message absent from log and session

1. Verify pairing/allowlist presence without printing the credential file.
2. Search recent logs for listener exit, cipher, disconnect, login, or channel-exited events.
3. Compare `openclaw --version` with `openclaw plugins inspect zalouser`; keep core and plugin on the same release line.
4. Restart only `openclaw-gateway` under Supervisor after backup. Do not restart the whole container unless the gateway cannot recover.
5. Require QR login only after version alignment and a clean gateway restart still fail.

### Message enters session but no reply reaches Zalo

1. Confirm `Zalouser final reply failed: OutboundDeliveryError` or retry failure in the log.
2. Apply the reusable send patch, which adds three attempts, backoff, and chunk delay:

```bash
MEMBER_DATA_DIR=<host-member-home> \
  bash /root/Automation/openclaw_member_assistant/scripts/patch_zalouser_send_reliability.sh --apply
```

3. Restart only the gateway to load the patched bundle.
4. Verify there is a new `out:` timestamp and no new outbound error after the restart.

### Session is oversized or long-running

Treat repeated `long-running session`, `queued_behind_active_work`, or `visible channel turn dispatched with no queued reply payloads` as a session problem when the target DM is present.

1. Backup `agents/main/sessions/sessions.json` and preserve all transcript files.
2. Enable preventive configuration when absent:

```bash
openclaw config set agents.defaults.contextPruning.mode cache-ttl
openclaw config set agents.defaults.contextPruning.ttl 5m
openclaw config set agents.defaults.compaction.mode safeguard
openclaw config set agents.defaults.compaction.reserveTokensFloor 40000
openclaw config set agents.defaults.compaction.maxHistoryShare 0.5
openclaw config validate
```

3. Summary-compact an idle oversized session:

```bash
openclaw sessions compact 'agent:main:zalouser:direct:<zalo-id>' --timeout 180000
```

4. If compaction reports no work and the session remains broken, remove only its key from the backed-up session index while the gateway is stopped so the next DM creates a fresh session. Never delete the old transcript.

### Probe reports config-only status

Source `$MEMBER_HOME/.openclaw/gateway.env` inside the container before `openclaw channels status --probe`. Do not restart based on a probe that says gateway auth is unavailable.

### Cipher or listener error

For `Invalid data length or missing cipher key`, align the plugin with core, restart the gateway, run `openclaw plugins doctor`, and probe again. Preserve credentials; QR login is the last resort.

## Prevent recurrence

Add two unique Shared Watchdog Center projects:

- `openclaw_channel`: health check every 5 minutes, detect listener exits and outbound delivery failures, source gateway auth, and restart with a 10-minute cooldown.
- `openclaw_session`: every 2 hours, target a narrow Zalo session pattern, require at least 10 idle minutes, and use `COMPACTION_MODE=summary` for large tool outputs.

Use the templates in [references/watchdog-config.md](references/watchdog-config.md). Preserve unrelated cron entries and use unique lock/state/log names per member.

## Verify

Run all checks before reporting completion:

```bash
bash -n /root/Automation/watchdog/shared_self_healing/scripts/check_member_zalouser.sh
bash -n /root/Automation/openclaw_member_assistant/scripts/audit_member_sessions.sh
bash -n /root/Automation/openclaw_member_assistant/scripts/patch_zalouser_send_reliability.sh
python3 -m json.tool /root/Automation/watchdog/shared_self_healing/project_config.json >/dev/null
openclaw config validate
openclaw plugins doctor
openclaw channels status --probe
```

Confirm the channel is `configured, running, works`, the target session is below its preventive threshold, cron is active, and no new listener/outbound error appears after restart. Do not send a real test message unless the user authorizes it; passive `in:` and `out:` activity is acceptable evidence.

## Safety

- Never delete or print Zalo credentials, pairing files, cookies, tokens, or transcripts.
- Never run a second gateway beside Supervisor or use `tmux` for these member containers.
- Never treat a healthy group channel as proof that DM inbound and outbound both work.
- Never assume restart alone is a durable fix; install the watchdog and session maintenance when the failure has recurred.
- Update `/root/_Second_AI_Brain/06_Nhat_Ky_Thay_Doi.md` after production changes.
