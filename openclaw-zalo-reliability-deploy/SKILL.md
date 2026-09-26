---
name: openclaw-zalo-reliability-deploy
description: Deploy the reusable OpenClaw Zalo Personal delivery guards and watchdog to Docker member VPS instances.
---

# OpenClaw Zalo reliability deployment

Use this skill when installing the repeatable Zalo Personal reliability layer on another Docker member VPS. It covers wrong group routing and attachment uploads that wait forever for a callback, plus a conservative delivery watchdog for stale send/session failures.

The package is host-side and credential-free. It never edits `.env`, Zalo cookies, QR data, pairing files, or message content.

## Files

- `scripts/install.sh`: dry-run by default; applies the core target guard, ESM/CommonJS `zca-js` upload guards, the shared watchdog registry entry, and a five-minute cron marker with `--apply`.
- `scripts/check_zalo_delivery_guard.sh`: host watchdog. It checks the live Gateway/Zalo probe and recent redacted delivery fault markers. It observes the first fault, and only restarts the existing Gateway after a repeated fault and a 10-minute cooldown.
- `scripts/scan_delivery_faults.py`: bounded, hash-only log scanner.

## Install on a member VPS

Run from the host as root. The member data directory must directly contain `.openclaw` and the container must already be running:

```bash
BASE=/root/.agents/skills/openclaw-zalo-reliability-deploy
$BASE/scripts/install.sh \
  --container user-<member> \
  --member-data-dir /root/Apps/member_vps/docker-users/data/<member> \
  --member-home /home/<member> \
  --member-label <member> --dry-run

$BASE/scripts/install.sh \
  --container user-<member> \
  --member-data-dir /root/Apps/member_vps/docker-users/data/<member> \
  --member-home /home/<member> \
  --member-label <member> --apply
```

The installer creates timestamped backups under `/root/_Backups/`, validates modified JavaScript with `node --check`, runs the offline upload guard test, validates the member config/plugin bundle, and probes Zalo after applying. It does not send a live test message.

The installer refuses ambiguous bundles, unsupported `zca-js` versions, missing member paths, or changed patch anchors. Re-run the dry-run after every OpenClaw/plugin upgrade; if an anchor changed, stop and review the bundle rather than broad-replacing text.

## Watchdog behavior

The installed registry entry runs through the shared launcher:

```bash
/root/Automation/watchdog/shared_self_healing/run_project.sh member_<member>_zalo_delivery
```

The watchdog keeps only counts, timestamps, and a category hash. It does not write queue SQLite files and never blindly replays a `send_attempt_started` attachment. On a repeated `blocked_tool_call`, `stalled session`, upload or outbound failure, it first applies a 120-second active-delivery grace gate (upload, `file_done`, `send_attempt_started`, or an in-flight tool turn). If the Zalo probe is still healthy, delivery faults remain ambiguous and the watchdog never restarts the Gateway; this prevents turning an attachment stall into HTTP 503 and restart recovery loops. A restart is allowed only after the channel probe is unhealthy and the fault repeats, then it waits for the normal multi-probe recovery window and logs `MANUAL_REQUIRED` if recovery fails.

The reusable activity detector is `scripts/scan_active_delivery.py`. It reads only bounded, recent log markers and emits category/age without IDs or message text. Validate it with `python3 -m unittest discover -s tests -q` before changing the watchdog.

For the OpenClaw 2026.9.5 member bundle, restart recovery notices are suppressed for `zalouser` deliveries. A Zalo attachment can remain ambiguous while the Gateway restarts; emitting the English recovery notice into the group makes the same interrupted request look duplicated. The recovery run still resumes internally, but only the final verified delivery should be user-facing. Reapply this narrow bundle guard after an OpenClaw upgrade.

## Verification and rollback

After apply, require:

```bash
node /root/.agents/skills/openclaw-zalo-reliability/scripts/test_upload_completion_guard.mjs
bash /root/.agents/skills/openclaw-zalo-reliability-deploy/scripts/check_zalo_delivery_guard.sh --dry-run
```

Then confirm `openclaw config validate`, `openclaw plugins doctor`, a probed Zalo status showing configured/linked/running/connected/works, one Gateway under its existing process manager, and zero pending delivery entries. Rollback is file-level from the timestamped backup recorded by the installer; never delete credentials or the whole session store.

## Safety

- Keep group targets explicitly scoped as `group:<numeric-id>`; never use a bare numeric target.
- A send is successful only with a real platform `messageId` and matching group receipt metadata.
- On an uncertain attachment result, inspect receipts and queue state before one safe retry; never auto-replay a timed-out upload.
- Do not QR-login automatically. Authentication recovery is a separate, owner-approved operation.
