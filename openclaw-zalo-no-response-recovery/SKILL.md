---
name: openclaw-zalo-no-response-recovery
description: End-to-end diagnose, recover, and harden an OpenClaw Zalo Personal channel on a Docker member VPS when Zalo is silent, stopped, listener-closed, inbound-stalled, or unable to deliver replies. Use this single entrypoint before separate Zalo reliability, deploy, watchdog, or session actions.
---

# OpenClaw Zalo No-Response Recovery

Use this as the single operational entrypoint for a Docker member whose
OpenClaw Zalo Personal channel does not respond. It combines the maintained
Zalo reliability helpers, delivery guards, Shared Watchdog Center registration,
Supervisor recovery, Docker restart hardening, and idle-safe session
maintenance.

This skill is host-side and credential-free. Never print or copy real API keys,
tokens, cookies, passwords, QR payloads, pairing data, private sender/group
IDs, or message contents into output, skills, notes, or logs.

## When to use

Use when a member has one or more of these symptoms:

- Zalo is configured or linked but reports `stopped`, `not-running`, or
  `Zalo listener closed`.
- Zalo receives a message but no reply arrives, or inbound adoption stalls.
- Zalo attachment upload/outbound delivery hangs or has an ambiguous result.
- A large or stale Zalo session blocks new messages.
- The Gateway exists but Zalo does not recover after a normal listener close.

Do not use QR login, logout, session deletion, transcript deletion, or blind
queue replay as the first action.

## Required inputs and preflight

Resolve these values from the project note, container mounts, and live runtime;
never guess them:

```text
CONTAINER=user-<member>
MEMBER_LABEL=<member>
MEMBER_HOME=/home/<member>
MEMBER_DATA_DIR=/root/Apps/member_vps/docker-users/data/<member>
```

`MEMBER_DATA_DIR` must directly contain `.openclaw`. Read the VPS Second AI
Brain documents, nearest `AGENTS.md`, member project note if present, and the
production checklist before applying changes.

## Phase 1: read-only diagnosis

Run the maintained diagnostic first:

```bash
bash /root/.agents/skills/openclaw-zalo-reliability/scripts/diagnose.sh "$CONTAINER" "$MEMBER_HOME"
```

Then inspect only redacted metadata and bounded recent logs:

```bash
docker exec "$CONTAINER" supervisorctl status
docker exec -e HOME="$MEMBER_HOME" "$CONTAINER" openclaw config validate
docker exec -e HOME="$MEMBER_HOME" "$CONTAINER" openclaw plugins doctor
docker exec -e HOME="$MEMBER_HOME" "$CONTAINER" timeout 60s openclaw channels status --probe
docker exec -e HOME="$MEMBER_HOME" "$CONTAINER" openclaw health
```

Confirm the process manager and exactly one Gateway:

```bash
docker exec "$CONTAINER" sh -lc 'ps -eo pid,ppid,stat,etime,args | grep -E "[o]penclaw-gateway|[s]upervisord"'
```

Classify before changing anything:

1. **Gateway absent or both channels fail:** follow the Supervisor recovery
   reference and preserve exactly one Gateway.
2. **Telegram works but Zalo is stopped/listener-closed:** back up, apply the
   deployment guards, and restart only the existing Supervisor-owned Gateway.
3. **Core/plugin mismatch or cipher error:** align the active release line,
   validate, and restart; do not QR-login solely for a cipher error.
4. **Stalled or oversized session:** use the idle-safe maintenance phase below;
   never delete the whole session store.
5. **Attachment/outbound fault:** use the deploy dry-run and patch only the
   one active bundle; never replay an uncertain send blindly.
6. **Authentication still fails after alignment and clean restart:** stop and
   request explicit owner approval before QR login.

## Phase 2: backup before apply

Create a root-only timestamped backup before production changes. Include the
member `openclaw.json` with mode `0600`, main session SQLite plus existing
`-wal`/`-shm`, Shared Watchdog registry, root crontab, Docker restart-policy
metadata, and any active bundle backups produced by patch helpers. Keep the
backup path for rollback and do not put secret values in the report.

## Phase 3: maintained reliability deployment

Run the deployer dry-run first and stop on multiple active bundles, unsupported
`zca-js`, missing anchors, or an ambiguous target:

```bash
BASE=/root/.agents/skills/openclaw-zalo-reliability-deploy
"$BASE/scripts/install.sh" --container "$CONTAINER" --member-data-dir "$MEMBER_DATA_DIR" --member-home "$MEMBER_HOME" --member-label "$MEMBER_LABEL" --dry-run
```

After reviewing the dry-run, apply:

```bash
"$BASE/scripts/install.sh" --container "$CONTAINER" --member-data-dir "$MEMBER_DATA_DIR" --member-home "$MEMBER_HOME" --member-label "$MEMBER_LABEL" --apply
```

The maintained installer applies the scoped core group-target guard, active
`zca-js` ESM/CommonJS upload-completion guards, and delivery watchdog. It must
preserve unrelated registry entries and create timestamped backups. Never
broad-replace hashed bundles or patch an old generation when plugin inspection
reports another active source.

Run the offline acceptance test:

```bash
node /root/.agents/skills/openclaw-zalo-reliability/scripts/test_upload_completion_guard.mjs
```

## Phase 4: complete Shared Watchdog set

Use `/root/Automation/watchdog/shared_self_healing` as the only watchdog
center. Keep one unique registry key and cron marker per member:

- `member_<member>_zalouser`: channel/listener probe every 5 minutes.
- `member_<member>_zalo_delivery`: delivery guard every 5 minutes.
- `member_<member>_gateway_supervisor`: one-Gateway guard every minute.
- `member_<member>_resource_guard`: resource/OOM guard every 5 minutes.
- `member_<member>_sessions`: idle-safe Zalo session maintenance every 2 hours.

Every entry must run through the shared launcher:

```bash
/root/Automation/watchdog/shared_self_healing/run_project.sh member_<member>_<guard>
```

Preserve unrelated registry entries and cron jobs. Use unique lock files,
`ai_on_failure=false` for infrastructure guards, and no credentials in the
registry. Validate the center:

```bash
python3 -m json.tool /root/Automation/watchdog/shared_self_healing/project_config.json >/dev/null
bash -n /root/Automation/watchdog/shared_self_healing/run_project.sh
bash -n /root/Automation/watchdog/shared_self_healing/scripts/check_member_zalouser.sh
bash -n "$BASE/scripts/check_zalo_delivery_guard.sh"
```

The channel guard must combine probe status with recent listener events. The
delivery guard must keep active-delivery grace, cooldown, and multi-probe
recovery. A single ambiguous attachment result must not cause an immediate
restart.

## Phase 5: Docker and Gateway recovery

Inspect the existing policy before changing it:

```bash
docker inspect "$CONTAINER" --format 'restart_policy={{.HostConfig.RestartPolicy.Name}} status={{.State.Status}}'
```

For the standard member-VPS policy, use `always` only after confirming no
member-specific exception:

```bash
docker update --restart always "$CONTAINER"
```

Validate, then restart only the existing Supervisor-owned Gateway:

```bash
docker exec -e HOME="$MEMBER_HOME" "$CONTAINER" openclaw config validate
docker exec -e HOME="$MEMBER_HOME" "$CONTAINER" openclaw plugins doctor
docker exec "$CONTAINER" supervisorctl restart openclaw-gateway
```

Do not use `docker restart`, start a second `openclaw gateway run`, or create
a standalone Zalo listener.

## Phase 6: idle-safe session maintenance

Compact at most one idle Zalo session per run and preserve transcripts:

```bash
MEMBER_HOME="$MEMBER_HOME" SESSION_AGENT=main SESSION_PATTERN='agent:main:zalouser:' TOKEN_THRESHOLD_64K=18000 TOKEN_THRESHOLD_128K=40000 SESSION_IDLE_SECONDS=600 MAX_COMPACTIONS_PER_RUN=1 MAX_LINES=200 COMPACTION_MODE=summary bash /root/Automation/openclaw_member_assistant/scripts/audit_member_sessions.sh "$CONTAINER" --apply
```

If the script reports `skip recently active session`, keep the session intact.
The scheduled `openclaw_session` entry retries later; do not lower the idle
gate to force completion.

## Phase 7: verification

Require the following before reporting recovery complete:

```bash
docker exec -e HOME="$MEMBER_HOME" "$CONTAINER" timeout 60s openclaw channels status --probe
docker exec -e HOME="$MEMBER_HOME" "$CONTAINER" openclaw config validate
docker exec -e HOME="$MEMBER_HOME" "$CONTAINER" openclaw plugins doctor
docker exec "$CONTAINER" supervisorctl status
bash /root/.agents/skills/openclaw-zalo-reliability/scripts/diagnose.sh "$CONTAINER" "$MEMBER_HOME"
```

The Zalo line must show `configured`, `linked` when supported, `running`,
`connected`, and `works`. Confirm Telegram remains healthy when configured,
exactly one Gateway is Supervisor-managed, and the Docker policy is
intentional.

Run the member guards in dry-run mode and inspect only post-provider-start
markers. Require no new listener exit, cipher, outbound, or repeated
session-stall errors. Do not send a real Zalo message or attachment unless the
owner explicitly authorizes the destination and receipt check. Do not replay
old dead letters automatically.

## Stop and rollback

Stop and report on ambiguous bundles, changed patch anchors, unaligned
versions, unauthenticated probe after clean restart, multiple Gateways, or any
need for QR login, logout, credential replacement, session deletion, or live
message without explicit owner approval.

Rollback only files changed in the current transaction from the timestamped
backup, restore the prior Docker restart policy if changed, validate, and
restart the original Supervisor entry. Never delete credentials, pairing files,
the entire session store, or transcripts.

## Handoff

Report the failure layer and timestamps, member/container, Gateway manager,
guard/registry/cron changes, Docker policy, backup paths, validation results,
deferred session/queue work, and whether any real message was sent. After a
production change update the member project note and
`/root/_Second_AI_Brain/06_Nhat_Ky_Thay_Doi.md`.
