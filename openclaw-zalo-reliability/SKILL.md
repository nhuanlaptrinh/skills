---
name: openclaw-zalo-reliability
description: Diagnose, recover, harden, and operate OpenClaw Zalo Personal on Docker member VPS systems. Use when Zalo receives no reply, inbound or outbound delivery fails, the listener exits, sessions become long-running or oversized, both Telegram and Zalo stop because the member Gateway is absent or unmanaged, Supervisor configuration drifts, recurring failures need Shared Watchdog prevention, files or heavy tasks are delivered unreliably, or Zalo QR login is required as a last resort.
---

# OpenClaw Zalo Reliability

Use this as the single entry point for Zalo Personal incidents and prevention on
OpenClaw member VPS containers. Diagnose the failure layer before changing
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

Cron must call
`/root/Automation/watchdog/shared_self_healing/run_project.sh`; do not call the
underlying scripts directly. Preserve unrelated registry and cron entries.

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
