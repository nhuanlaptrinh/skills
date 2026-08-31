# Zalo No-Response Diagnosis And Recovery

Use this branch when the Gateway is present and Telegram still works, but Zalo
inbound, outbound, listener, probe, or session behavior is unhealthy.

## Reusable Dry-Runs

```bash
CONTAINER=<container> MEMBER_HOME=<member-home> \
MEMBER_LABEL=<label> PROJECT_KEY=member_<label>_zalouser \
  bash /root/Automation/watchdog/shared_self_healing/scripts/check_member_zalouser.sh --dry-run

MEMBER_DATA_DIR=<host-dir-containing-.openclaw> \
  bash /root/Automation/openclaw_member_assistant/scripts/patch_zalouser_send_reliability.sh
```

## Message Absent From Logs And Sessions

1. Confirm pairing/allowlist presence without printing credential files.
2. Inspect recent logs for listener exit, cipher, disconnect, login, and
   channel-exited events.
3. Compare `openclaw --version` with `openclaw plugins inspect zalouser` and
   keep core and plugin on the same release line.
4. Restart only the Supervisor-managed Gateway after backup.
5. Require QR login only if version alignment and a clean restart still fail.

## Message Enters A Session But No Reply Reaches Zalo

Confirm `Zalouser final reply failed: OutboundDeliveryError` or send retry
failure, then apply the reusable patch:

```bash
MEMBER_DATA_DIR=<host-dir-containing-.openclaw> \
  bash /root/Automation/openclaw_member_assistant/scripts/patch_zalouser_send_reliability.sh --apply
```

Restart only the Gateway to load the active patched bundle. After plugin
updates, rerun dry-run and confirm the target matches the source reported by
`openclaw plugins inspect zalouser`; an older patched generation must not hide
an unpatched active generation.

## Probe Reports Config-Only

Source `$MEMBER_HOME/.openclaw/gateway.env` inside the container before
`openclaw channels status --probe`. Do not restart based only on a probe that
reports unavailable Gateway auth.

## Cipher Or Listener Error

For `Invalid data length or missing cipher key`, align the Zalo plugin with the
OpenClaw core, restart the Gateway, run `openclaw plugins doctor`, and probe
again. Preserve credentials. Move to QR login only when the error persists.

## Session Symptoms

Repeated `long-running session`, `queued_behind_active_work`, or
`visible channel turn dispatched with no queued reply payloads` indicates a
session branch when the target DM/group is present. Follow
[delivery-and-session.md](delivery-and-session.md); never delete transcripts.
