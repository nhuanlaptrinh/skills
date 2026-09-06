---
name: openclaw-zalo-reliability
description: Diagnose, recover, harden, and operate OpenClaw Zalo Personal on Docker member VPS systems. Use when Zalo receives no reply, inbound or outbound delivery fails, the listener exits, sessions become long-running or oversized, both Telegram and Zalo stop because the member Gateway is absent or unmanaged, Supervisor configuration drifts, recurring failures need Shared Watchdog prevention, files or heavy tasks are delivered unreliably, or Zalo QR login is required as a last resort.
---

# OpenClaw Zalo Reliability

Use this as the single entry point for Zalo Personal incidents and prevention on
OpenClaw member VPS containers. For a new connection or a new member, first
run `openclaw-zalouser-onboarding-standard`; use this skill for the channel
diagnosis and recovery layers. Diagnose the failure layer before changing
production, preserve pairing and transcripts, and use QR login only after safer
recovery paths fail.

## Boundaries

- Keep `/root/Automation/watchdog/shared_self_healing` as the shared runtime and
  registry for all projects. Do not copy or merge that center into this skill.
- Use `/root/.agents/skills/shared-watchdog-center/SKILL.md` only when changing
  the generic center architecture or adding non-OpenClaw projects.
- Do not modify `/root/.agents/skills/self-healing-watchdog` as part of a Zalo
  incident.
- Use this skill for member data under
  `/root/Apps/member_vps/docker-users/data`, not automatically for the root
  OpenClaw runtime.

## Required Preflight

1. Read the VPS Second AI Brain, production checklist, nearest `AGENTS.md`, and
   the affected member project note.
2. Resolve the exact `CONTAINER`, internal `MEMBER_HOME`, host directory that
   directly contains `.openclaw`, member label, and unique watchdog keys.
3. Confirm whether the Gateway parent is Supervisor, tmux, systemd, or absent.
4. Back up every file that may change, the session index, affected plugin
   bundle, watchdog registry, cron, and relevant project note.
5. Never print `.env`, tokens, cookies, passwords, QR payloads, pairing data,
   private sender/group IDs, or message contents.

## Start With Read-Only Diagnosis

```bash
bash /root/.agents/skills/openclaw-zalo-reliability/scripts/diagnose.sh \
  <container> <member-home> [zalo-id]
```

The diagnostic loads Gateway auth internally, redacts common secrets, checks
core/plugin versions, probes Zalo, inspects only recent provider logs, detects
listener/outbound/cipher/session symptoms, and does not change production.

## Route The Incident

- **Telegram works, Zalo is silent or outbound fails:** read
  [references/zalo-no-response.md](references/zalo-no-response.md).
- **Both Telegram and Zalo stop, port 18789 is absent, or proxy returns 502:**
  read [references/gateway-recovery.md](references/gateway-recovery.md), then
  [references/supervisor-watchdog.md](references/supervisor-watchdog.md) when
  process-manager drift caused the incident.
- **Sessions, long tool output, files, voice, or heavy tasks cause delayed or
  missing replies:** read
  [references/delivery-and-session.md](references/delivery-and-session.md).
- **Credential/cipher/login still fails after version alignment and a clean
  Gateway restart:** read
  [references/zalo-qr-login.md](references/zalo-qr-login.md). Applying QR login
  requires an explicit owner request because it replaces the active Zalo
  session.
- **Before declaring completion or rolling back:** read
  [references/verification-and-rollback.md](references/verification-and-rollback.md).

Read only the references required for the current failure path. For incidents
that cross layers, follow this order: Gateway process, plugin/listener, inbound
and outbound, session, then authentication.

## Durable Prevention

After a recurring incident, use the existing Shared Watchdog Center rather than
creating another watchdog implementation:

- `openclaw_gateway`: host-side Supervisor guard; set `ai_on_failure=false`.
- `openclaw_channel`: Zalo listener/outbound probe with restart cooldown.
- `openclaw_session`: scheduled audit/summary compaction with an explicit
  session pattern.
- `host_resource`: RAM, swap, memory PSI, OOM and member cgroup guard through
  `member-vps-resource-oom-guard`.

The Zalo probe status may include fields such as `linked` between
`configured` and `running`. Health matching must therefore allow intermediate
fields (`configured.*running.*works`) instead of requiring those words to be
adjacent; otherwise a healthy linked account can trigger a false restart and
Telegram warning.

Treat `dm:pairing` as the configured DM access policy, not as an authentication
result. Do not claim that a Zalo session expired from this field, a stale
delivery error, or a retry warning alone; confirm authentication with the live
channel probe/plugin result before recommending QR login.

Cron must call
`/root/Automation/watchdog/shared_self_healing/run_project.sh`; do not call the
underlying scripts directly. Preserve unrelated registry and cron entries.

## Recovery procedure for an oversized or stalled group session

Use this sequence when logs contain `claim→adoption stalled`,
`reply_operation_aborted`, `skipped:duplicate`, `finalization_stalled`, or
`OutboundDeliveryError` while the live Zalo probe still works:

1. Resolve the exact group session key from the live session list. Do not use a
   broad pattern when applying a repair.
2. Back up `openclaw.json`, the agent SQLite store and matching `-wal`/`-shm`,
   the shared state SQLite files, the active Zalo send bundle, watchdog JSON,
   and crontab under `/root/_Backups`.
3. Wait until the target session has been idle for at least 600 seconds. Run a
   dry-run first:

   ```bash
   MEMBER_HOME=/home/<member> \
   SESSION_PATTERN='agent:main:zalouser:group:<group-id>' \
   TOKEN_THRESHOLD_64K=18000 TOKEN_THRESHOLD_128K=40000 \
   SESSION_IDLE_SECONDS=600 MAX_COMPACTIONS_PER_RUN=1 \
   COMPACTION_MODE=summary \
   bash /root/Automation/openclaw_member_assistant/scripts/audit_member_sessions.sh \
   user-<member>
   ```

   Apply only after the target is idle and the backups exist, using the same
   command with `--apply`. This preserves the transcript and compacts one
   session at a time; never delete the whole session store.
4. For OpenClaw 2026.8.2, enable only schema-supported prevention settings:

   ```bash
   openclaw config set agents.defaults.contextPruning.mode cache-ttl
   openclaw config set agents.defaults.contextPruning.ttl 5m
   openclaw config set agents.defaults.compaction.mode safeguard
   openclaw config set agents.defaults.compaction.midTurnPrecheck.enabled true
   openclaw config set agents.defaults.compaction.maxActiveTranscriptBytes 2mb
   openclaw config set agents.defaults.compaction.keepRecentTokens 12000
   openclaw config validate
   ```

   `reserveTokensFloor` and `maxHistoryShare` are not valid keys on this
   release; do not leave unsupported keys in production config.
5. If the active bundle is unpatched, run
   `patch_zalouser_send_reliability.sh --apply`, validate with `node --check`
   and `openclaw plugins doctor`, then restart only the existing
   Supervisor-owned `openclaw-gateway`.
6. Add two Shared Watchdog entries for the member: an `openclaw_channel` probe
   every five minutes and an `openclaw_session` audit every two hours with
   `SESSION_PATTERN='agent:main:zalouser:'`, `MAX_COMPACTIONS_PER_RUN=1`,
   `COMPACTION_MODE=summary`, and the 600-second idle gate. Register both in
   `project_config.json` and call them through `run_project.sh` from cron.

After reload, require `config validate`, `plugins doctor`, Zalo probe
`configured/linked/running/connected/works`, one live Gateway under Supervisor,
zero pending delivery-queue entries, and a post-reload log scan with no new
stall/abort/outbound errors. Ask the authorized owner to send the real group
test; do not send a bot-generated test message.

## Safety Rules

- Prefer dry-run, passive probes, syntax validation, and unit tests.
- Never delete credentials, all sessions, or transcripts.
- Never run a second Gateway beside Supervisor or keep a member Gateway in
  tmux after migration.
- Never recreate a container for a Gateway-only repair.
- Do not fault-inject production or send real Telegram/Zalo test messages
  without explicit authorization.
- After production changes, update the affected member note and
  `/root/_Second_AI_Brain/06_Nhat_Ky_Thay_Doi.md` without recording secrets.

## Member maintenance update (2026-09-05)

For member bundles on OpenClaw 2026.8.2, use
`/root/Automation/openclaw_member_assistant/scripts/patch_zalouser_send_reliability.sh`
to add bounded three-attempt Zalo text-send retries and a 600 ms delay between
split chunks. The helper accepts both the older bundle with
`DEFAULT_TEXT_CHUNK_MODE` and the current bundle that begins directly at
`ZALO_TEXT_LIMIT`; it backs up the active `send-*.js` bundle before applying.
After patching, run `node --check` on the active bundle, `openclaw plugins doctor`,
then restart only the Supervisor-owned member Gateway.

### Watchdog matcher correction (2026-09-05)

The shared Zalo watchdog must recognize the stable status sequence
`configured, ... , running, ... works` while allowing optional fields such as
`linked` or `dm:pairing`. Require punctuation or whitespace before the
`running` token so `health:not-running` cannot count as healthy. Do not use an
alternation containing `^` after `.*` in the `grep -E` expression; that pattern
falsely classified healthy members as `channel_not_running` and caused repeated
Gateway restarts. Validate the matcher with both healthy and
`not authenticated/stopped` status fixtures, then run the member watchdog in
`--dry-run` mode before relying on cron.

The member channel watchdog also uses a bounded reconnect grace window after a
Gateway restart. Keep several probe attempts across roughly 60 seconds before
raising a QR/login warning; a single failed probe during listener startup is
not evidence that the saved Zalo session is gone.

When a Zalo send returns an unknown error, distinguish the outbound delivery
failure from authentication: preserve the delivery record, use the bounded
send retry patch, and do not blind-replay a `send_attempt_started` item. Check
Gateway/event-loop and host I/O or swap pressure because those stalls can make
both Zalo and Telegram appear disconnected. Keep a member `host_resource` guard
enabled for early warning, and align or pin the Zalo plugin with the core
release during the next controlled maintenance window.
