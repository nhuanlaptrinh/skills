---
name: openclaw-member-upgrade-telegram-recovery
description: Safely upgrade OpenClaw inside a Docker member VPS and recover Telegram bots that stop replying during or after the upgrade. Use for version upgrades, partial or corrupted global npm installs, missing Gateway autorestart under Supervisor, post-upgrade doctor/session SQLite migrations, malformed Telegram allowlists, stale polling offsets, duplicate pollers, or SessionRestartRecoveryTombstoneError incidents.
---

# OpenClaw Member Upgrade Telegram Recovery

Upgrade one member container without crossing into other members, then verify the complete Telegram inbound-to-outbound path. Prefer the official updater; use a forced npm reinstall only when package integrity is proven broken.

## Inputs and outputs

Resolve these values from Docker metadata and OpenClaw config. Do not guess them:

```bash
export MEMBER="<member>"
export CONTAINER="user-${MEMBER}"
export MEMBER_HOME="/home/${MEMBER}"
export ACCOUNT_ID="<telegram-account-id>"
export AGENT_ID="<agent-id>"
export DATA_DIR="/root/Apps/member_vps/docker-users/data/${MEMBER}"
export BACKUP_ROOT="/root/_Backups/openclaw-member-upgrade-telegram-recovery/${MEMBER}"
```

Expected outputs:

- OpenClaw at the latest requested stable version inside the target container.
- Legacy sessions and workspace state migrated to the current format when required.
- Exactly one Gateway owned by Supervisor and configured to autorestart.
- The target Telegram account `running`, `connected`, and able to complete a real reply.
- Timestamped backups under `$BACKUP_ROOT` and a sanitized VPS change-log entry.

## Safety rules

- Read the VPS operating docs, production checklist, project note, and nearest `AGENTS.md` before changing production.
- Obtain authorization before package changes, Gateway/container restarts, session deletion, SQLite mutation, or a real Telegram delivery test.
- Never print or copy bot tokens, API keys, cookies, passwords, private keys, `.env` contents, full Telegram payloads, or private message text.
- Keep token material in an existing `tokenFile`; report only `tokenSource`, `tokenStatus`, probe status, and bot username.
- Back up current production state before the first write. Copy SQLite database, WAL, and SHM companions together.
- Stop only the target Gateway for package or state changes. Restart the whole container only when Supervisor configuration cannot be safely reloaded.
- Never call Telegram Cloud `getUpdates` while the Gateway is running. Use `sua-loi-telegram-offset-openclaw` for proven offset incidents.
- Never delete all sessions or the whole state database to repair one failed chat. Use the official exact-session lifecycle command.
- Do not change model/provider, routing, workspace, permission architecture, or credentials unless evidence shows they are part of the incident.

## 1. Read-only preflight

Confirm the exact container, bind mount, process owner, service manager, version, update source, config, agent/account binding, and Telegram state:

```bash
docker ps --filter "name=^/${CONTAINER}$" \
  --format 'table {{.Names}}\t{{.Status}}\t{{.Image}}\t{{.Ports}}'
docker inspect "$CONTAINER" --format '{{json .Mounts}}'
docker exec "$CONTAINER" supervisorctl status
docker exec -e HOME="$MEMBER_HOME" "$CONTAINER" openclaw --version
docker exec -e HOME="$MEMBER_HOME" "$CONTAINER" \
  openclaw update status --json
docker exec -e HOME="$MEMBER_HOME" "$CONTAINER" \
  openclaw config validate
docker exec -e HOME="$MEMBER_HOME" "$CONTAINER" \
  openclaw agents list --bindings
docker exec -e HOME="$MEMBER_HOME" "$CONTAINER" \
  openclaw channels status --channel telegram --probe --json
```

Record only redacted metadata. Check the recent Gateway log for package load errors, `SIGTERM`, missing `dist` modules, `409 Conflict`, polling activity, dispatch errors, tombstones, and outbound success.

Preview the official update without restart:

```bash
docker exec -e HOME="$MEMBER_HOME" "$CONTAINER" \
  openclaw update --dry-run --no-restart --json
```

If the registry cannot be queried, do not assume the installed version is latest. Retry when network/DNS is available or report the unverified version explicitly.

## 2. Back up production state

Create one root-only incident directory:

```bash
export BACKUP_DIR="${BACKUP_ROOT}/$(date -u +%Y%m%dT%H%M%SZ)"
install -d -m 700 "$BACKUP_DIR/openclaw" "$BACKUP_DIR/container"
```

Back up, when present:

- `$DATA_DIR/.openclaw/openclaw.json`, `.last-good`, and `.pre-update`.
- `$DATA_DIR/.openclaw/openclaw.sqlite` plus `-wal` and `-shm`.
- `$DATA_DIR/.openclaw/agents/*/agent/openclaw-agent.sqlite` plus companions.
- The persistent member entrypoint under `$DATA_DIR` if present.
- `/usr/local/bin/member-vps-entrypoint.sh` and `/etc/supervisor/conf.d/member-vps.conf` from the container.
- Legacy session indexes or migration metadata that doctor reports.

Do not copy token files or credentials into documentation or skill folders. Restrict all backup files to root.

## 3. Upgrade OpenClaw

Stop and verify only the Gateway:

```bash
docker exec "$CONTAINER" supervisorctl stop openclaw-gateway
docker exec "$CONTAINER" supervisorctl status openclaw-gateway
```

Use the official updater first:

```bash
docker exec -e HOME="$MEMBER_HOME" "$CONTAINER" \
  openclaw update --tag latest --no-restart --yes --json
```

If the updater reports an unknown package manager but leaves the existing package intact, inspect the global package root before choosing the package manager. If OpenClaw is already partially replaced, has dependency mismatches, or cannot load required `dist` modules, reinstall the same target atomically through the detected package manager. For npm-based global installs:

```bash
docker exec "$CONTAINER" npm root -g
docker exec "$CONTAINER" npm install -g openclaw@latest
docker exec "$CONTAINER" npm ls -g openclaw --depth=0
docker exec -e HOME="$MEMBER_HOME" "$CONTAINER" openclaw --version
```

Use `npm install -g openclaw@latest --force` only when a normal reinstall fails and package corruption is proven. Preserve the previous version string for rollback.

## 4. Run post-upgrade migrations

Run repair and doctor with the Gateway still stopped:

```bash
docker exec -e HOME="$MEMBER_HOME" "$CONTAINER" \
  openclaw update repair --no-restart --yes --json
docker exec -e HOME="$MEMBER_HOME" "$CONTAINER" \
  openclaw doctor --post-upgrade --json
docker exec -e HOME="$MEMBER_HOME" "$CONTAINER" \
  openclaw doctor --session-sqlite dry-run \
  --session-sqlite-all-agents --json
```

If the dry-run reports legacy entries, import them with the official migration and validate afterward:

```bash
docker exec -e HOME="$MEMBER_HOME" "$CONTAINER" \
  openclaw doctor --session-sqlite import \
  --session-sqlite-all-agents --yes --json
docker exec -e HOME="$MEMBER_HOME" "$CONTAINER" \
  openclaw doctor --session-sqlite validate \
  --session-sqlite-all-agents --json
```

Keep doctor-created archives. Do not manually remove legacy files merely because migration succeeded.

## 5. Make Gateway startup persistent

Member containers commonly run Supervisor as PID 1. Ensure the canonical entrypoint that generates `member-vps.conf` contains Supervisor RPC sections and exactly one Gateway program:

```ini
[program:openclaw-gateway]
command=/usr/bin/openclaw gateway run
directory=<member-home>
user=root
environment=HOME="<member-home>"
autostart=true
autorestart=true
startsecs=10
startretries=5
stopasgroup=true
killasgroup=true
stopwaitsecs=60
stdout_logfile=/tmp/openclaw-supervisor.log
stderr_logfile=/tmp/openclaw-supervisor.log
```

Preserve SSH, Nginx, XRDP, and member-specific programs. Patch both the live container entrypoint and the persistent host-side source when one exists. Validate before reload:

```bash
bash -n "$DATA_DIR/member-vps-entrypoint.sh"
docker exec "$CONTAINER" bash -n /usr/local/bin/member-vps-entrypoint.sh
docker exec "$CONTAINER" python3 -c \
  'import configparser; p="/etc/supervisor/conf.d/member-vps.conf"; c=configparser.ConfigParser(); assert c.read(p)==[p]; assert c.has_section("program:openclaw-gateway")'
```

Use `supervisorctl reread` and `supervisorctl update` when the active Supervisor RPC interface is available. Otherwise restart the target container once, then verify the new Gateway has parent PID 1. Do not launch a second standalone Supervisor or Gateway for testing.

## 6. Start and classify Telegram failures

Start the Gateway and wait through `startsecs`:

```bash
docker exec "$CONTAINER" supervisorctl start openclaw-gateway
docker exec "$CONTAINER" supervisorctl status openclaw-gateway
docker exec -e HOME="$MEMBER_HOME" "$CONTAINER" \
  openclaw gateway status
docker exec -e HOME="$MEMBER_HOME" "$CONTAINER" \
  openclaw channels status --channel telegram --probe --json
```

Classify before repairing:

1. No inbound update: inspect polling ownership, webhook/API mode, offset, account binding, and allowlists.
2. Inbound but no outbound: inspect dispatch/session state, provider/tool errors, and Telegram send errors.
3. Inbound and outbound but slow: correlate events by account and session key before changing model or context settings.

### Malformed allowlist

OpenClaw expects one numeric Telegram sender ID per array item. Back up `openclaw.json`, remove only malformed comma-joined or nonnumeric entries, preserve valid IDs, validate config, and restart only the Gateway. Do not place group IDs in sender allowlists; configure negative group chat IDs under `channels.telegram.groups`.

### Tombstoned direct session

When logs prove `SessionRestartRecoveryTombstoneError`, inspect the exact failed key:

```bash
export SESSION_KEY="agent:${AGENT_ID}:telegram:direct:<telegram-user-id>"
docker exec -e HOME="$MEMBER_HOME" "$CONTAINER" \
  openclaw sessions --all-agents --limit all --json
docker exec -e HOME="$MEMBER_HOME" "$CONTAINER" \
  openclaw sessions delete "$SESSION_KEY" --dry-run --json
```

After authorization, delete only that failed session through the Gateway lifecycle API. The command archives its transcript and live artifacts:

```bash
docker exec -e HOME="$MEMBER_HOME" "$CONTAINER" \
  openclaw sessions delete "$SESSION_KEY" --yes --json
```

Let the next real inbound DM create a replacement session, or use `/new` or `/reset`. A non-delivery internal health turn may create the replacement session when a user test is not immediately available; never add `--deliver` without authorization.

### Polling offset or duplicate poller

If no inbound event arrives and evidence points to a stale/high offset, invoke `sua-loi-telegram-offset-openclaw` and follow its stop-backup-dry-run-apply-start sequence. If logs show `409 Conflict`, find and stop the duplicate poller; never reset offsets to hide two active owners.

## 7. Acceptance checks

Require all applicable checks to pass:

```bash
docker exec "$CONTAINER" supervisorctl status
docker exec -e HOME="$MEMBER_HOME" "$CONTAINER" openclaw --version
docker exec -e HOME="$MEMBER_HOME" "$CONTAINER" \
  openclaw update status --json
docker exec -e HOME="$MEMBER_HOME" "$CONTAINER" \
  openclaw config validate
docker exec -e HOME="$MEMBER_HOME" "$CONTAINER" \
  openclaw gateway status
docker exec -e HOME="$MEMBER_HOME" "$CONTAINER" \
  openclaw channels status --channel telegram --probe --json
docker exec -e HOME="$MEMBER_HOME" "$CONTAINER" \
  openclaw sessions --all-agents --limit all --json
```

Confirm:

- Installed version matches the requested/latest registry version.
- Exactly one Gateway is `RUNNING`, listens on the intended loopback port, and survives a controlled restart.
- Telegram account is configured, running, connected, polling, and has no current error.
- No new malformed allowlist warning, `409 Conflict`, tombstone, package import error, or dispatch failure appears after the repair timestamp.
- A fresh user DM produces one inbound event, one successful outbound event, and a non-failed replacement session. Record UTC timestamps and latency without message content.

## Rollback

Stop the Gateway before rollback. Restore only files changed in the incident from the timestamped backup. If the package itself regressed, reinstall the recorded previous version with the same package manager. Restore a state or session SQLite database only when migration corruption is proven; restore its database, WAL, and SHM as one stopped-Gateway set to avoid losing or mixing writes.

Restore the previous entrypoint and Supervisor config, validate them, then start one Gateway and rerun config, Gateway, and Telegram probes. Do not restore token files from documentation backups and do not delete doctor/session archives.

## Rerun and reporting

The preflight, update dry-run, doctor dry-run, session-delete dry-run, and acceptance probes are safe to rerun. Before rerunning a real update, create a new timestamped backup.

Report only:

- Target member/container, agent/account identifiers, old/new version, and backup directory.
- Proven root cause and exact non-secret files changed.
- Migration counts, Supervisor/Gateway status, Telegram probe, and real reply result.
- Any residual warning or rollback limitation.

Append a sanitized entry to `/root/_Second_AI_Brain/06_Nhat_Ky_Thay_Doi.md` after material production changes.
