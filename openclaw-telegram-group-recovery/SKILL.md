---
name: openclaw-telegram-group-recovery
description: Diagnose and repair OpenClaw Telegram groups that receive no reply or appear silent, including Telegram privacy/mention gating, wrong or migrated group IDs, sender allowlists, stale polling offsets, session locks, provider 503 errors, Docker-to-Telegram network failures, and sendDocument multipart failures. Use for root or Docker member VPS OpenClaw deployments when Telegram status looks connected but group responses are missing, delayed, or hidden after a file/report task.
---

# OpenClaw Telegram Group Recovery

Use this runbook to trace one Telegram message from Telegram inbound, through OpenClaw routing and the model, to the final text or media receipt. Apply only to the named VPS/member container; never mix accounts, agents, workspaces, offsets, or group IDs from another deployment.

## Safety and scope

- Read `/root/_Second_AI_Brain/START_HERE.md`, the VPS map, project registry, project note, and production checklist before changing anything.
- Resolve the actual container, OpenClaw root, agent ID, Telegram account ID, workspace, and group ID from configuration. Do not infer them from a bot username.
- Back up `openclaw.json` before editing. Back up SQLite plus matching `-wal` and `-shm` files before any state mutation. Store backups outside the live project with mode `0700`/`0600`.
- Never print, paste, or store bot tokens, API keys, cookies, passwords, private messages, full Telegram payloads, file contents, or private destination data.
- Do not recreate a member container. Do not delete sessions, workspaces, training data, media, or the whole SQLite database.
- Do not send a real Telegram message or call Cloud `getUpdates` while the Gateway is running. A real test needs explicit authorization; a normal user test is preferred.
- A `requireMention: false` OpenClaw setting cannot override Telegram BotFather Privacy Mode.

## Known layout and reusable helpers

For a Docker member, the usual values are:

```bash
export CONTAINER="user-<member>"
export DATA_DIR="/root/Apps/member_vps/docker-users/data/<member>"
export MEMBER_HOME="/home/<member>"
export OPENCLAW_ROOT="$DATA_DIR/.openclaw"
```

The Cát Minh incident used `CONTAINER=user-trolyketoancatminh` and `DATA_DIR=/root/Apps/member_vps/docker-users/data/trolyketoancatminh`. Treat those as an example, not defaults for another member.

Use these existing helpers only for the matching diagnosis. Their paths are host-side paths; when the Gateway runs inside a member container, run the helper from the host or copy only the required helper into a reviewed workspace location. Do not assume `/root/.agents` is mounted inside Docker:

- `/root/.agents/skills/openclaw-telegram-group-migrate/scripts/fix_group_migrate.py` for a suspected migrated group ID (dry-run first).
- `/root/.agents/skills/sua-loi-telegram-offset-openclaw/scripts/repair_telegram_offset.py` for a proven stale/high polling offset (Gateway must be stopped).
- `/root/.agents/skills/reliable-media-delivery/SKILL.md` for workspace media receipt and duplicate-suppression policy.
- `/root/.agents/skills/openclaw-telegram-task-delivery/SKILL.md` when a child/background task finishes internally but the requester receives no completion.

This skill has no bundled script; the commands below operate on the resolved member/container and are intended to be copied with placeholders replaced.

## Triage (read-only first)

Run narrow checks and redact output before reporting:

```bash
docker exec -e HOME="$MEMBER_HOME" "$CONTAINER" openclaw config validate
docker exec -e HOME="$MEMBER_HOME" "$CONTAINER" openclaw agents list --bindings
docker exec -e HOME="$MEMBER_HOME" "$CONTAINER" \
  openclaw channels status --channel telegram --probe --json
docker exec -e HOME="$MEMBER_HOME" "$CONTAINER" \
  openclaw models status --agent <AGENT_ID> --json
docker ps --filter "name=$CONTAINER" --format '{{.Names}} {{.Status}}'
```

For a Supervisor member Gateway, inspect the redacted log without reading message text:

```bash
docker exec "$CONTAINER" sh -lc \
  'grep -E "Inbound message telegram:group:|outbound send ok|sendDocument failed|block reply failed|409 Conflict|503|timeout|session file locked|Embedded agent failed" /tmp/openclaw-supervisor.log | tail -240'
```

Classify the incident before applying a fix:

1. **No inbound event:** Telegram is not delivering the tested message, the chat ID is wrong/migrated, privacy mode is filtering it, or sender/group admission is blocking it.
2. **Inbound but no outbound:** inspect routing, session locks, tool failures, provider errors, and Telegram send errors.
3. **Text outbound succeeds but media fails:** repair the Docker-to-Telegram multipart path and require a text fallback.
4. **All model calls fail or return 503:** preserve the primary model and add verified provider fallbacks.
5. **Only one historical session fails:** inspect lock/context state; do not reset unrelated sessions.

## Routing and Telegram admission

Inspect only safe fields from the live config:

```bash
jq '.channels.telegram.accounts | to_entries | map({accountId:.key,enabled:.value.enabled,groupPolicy:.value.groupPolicy,groups:(.value.groups // {}),proxy:.value.proxy,network:.value.network})' \
  "$OPENCLAW_ROOT/openclaw.json"
jq '.bindings' "$OPENCLAW_ROOT/openclaw.json"
```

For the tested group, verify all of the following:

- The account is enabled and the binding selects the intended agent.
- The exact group key exists under the account and has `enabled: true` and `requireMention: false` when unmentioned replies are required.
- A group-specific `allowFrom: ["*"]` is intentional; otherwise the effective account/group `groupAllowFrom` must contain the sender ID.
- The account is polling, has a successful probe, and has no recent `409 Conflict`.
- The group ID in the inbound log matches the group being tested. If not, run the migration helper in dry-run mode:

```bash
python3 /root/.agents/skills/openclaw-telegram-group-migrate/scripts/fix_group_migrate.py \
  --config "$OPENCLAW_ROOT/openclaw.json" --group-id '<GROUP_ID>'
```

Do not apply the helper merely because the bot is quiet. Add a new numeric group ID only when logs prove the migration and preserve the old entry.

If there is no inbound event for an unmentioned message, check BotFather Privacy Mode. A read-only `getMe`/probe result with `can_read_all_group_messages=false` means `/setprivacy -> Disable` must be performed manually for that bot. Also use a read-only `getChatMember` check to confirm the bot is still a member/administrator. Never put the token or API response payload in a report.

## Outbound text and media recovery

When logs show inbound plus model completion but `sendDocument failed` or `block reply failed`:

1. Confirm the local output exists and is readable; do not expose its contents.
2. Check the existing WARP/Telegram proxy listener and Docker bridge gateway:

```bash
ss -ltnp | grep -E '127\.0\.0\.1:40000|172\.[0-9.]+:40001' || true
echo "Docker gateways:"
docker inspect "$CONTAINER" --format '{{range .NetworkSettings.Networks}}{{.Gateway}} {{end}}'
```

3. If a local WARP proxy listens on `127.0.0.1:40000`, create a narrowly bound systemd relay for the member Docker bridge. Use the discovered bridge gateway, not a guessed public address. The known Cát Minh relay is:

```ini
[Unit]
Description=Relay Docker bridge traffic to local Cloudflare WARP proxy for Telegram uploads
After=network-online.target warp-svc.service docker.service
Wants=network-online.target

[Service]
Type=simple
ExecStart=/usr/bin/socat TCP-LISTEN:40001,bind=<DOCKER_BRIDGE_GATEWAY>,fork,reuseaddr TCP:127.0.0.1:40000
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

Back up any existing unit and UFW rules first. Allow only the member Docker bridge subnet to the relay; never publish it publicly. Then enable/start the unit, set the affected Telegram account's `proxy` to `http://<DOCKER_BRIDGE_GATEWAY>:40001`, and set `network.autoSelectFamily=false` plus `network.dnsResultOrder=ipv4first` when IPv6 selection is implicated.

4. Validate multipart transport without sending a real message: upload a harmless local test file to an invalid `chat_id=0` through the relay. A completed upload followed by Telegram `400 chat not found` proves the network path reached Telegram and did not send to a real group. Do not treat a timeout or partial upload as success.
5. Keep the text result independent from the attachment. If media delivery is unavailable, send text separately when the runtime supports it; never claim the file was delivered without a real `messageId` and matching destination receipt.

## Provider and session recovery

For provider 503/timeouts, back up the config and add only known-good fallbacks at the affected agent entry (and defaults when that is the authored policy):

```json
"model": {
  "primary": "9r/GPT-5.6-sol",
  "fallbacks": ["9r/GPT-5.6-terra", "9r/GPT-5.6-luna"]
}
```

Validate with `openclaw models status --agent <AGENT_ID> --json`; do not print provider keys. Preserve the original primary model and do not switch all agents because one route is unhealthy.

For session locks/context overflow:

- Inspect the lock path, owning PID, age, and whether the process is alive.
- If the process is active, wait or use the supported OpenClaw compact/rotation operation.
- If the process is dead and a stale lock is proven, back up the relevant session SQLite/WAL/SHM and use the documented session maintenance helper. Do not delete the transcript or whole database.
- For a polling offset, stop only the target Gateway, verify it is inactive, run `repair_telegram_offset.py --cloud-check` dry-run, and apply only when `stored_offset > max_update_id` is proven with the explicit expected value. Start the same Gateway in cleanup even after failure.

## Apply and reload

Before production writes:

```bash
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
BACKUP_DIR="/root/_Backups/openclaw-telegram-group-recovery/<member>/$STAMP"
install -d -m 700 "$BACKUP_DIR"
cp -a "$OPENCLAW_ROOT/openclaw.json" "$BACKUP_DIR/openclaw.json.before"
```

Also copy the relevant state SQLite file plus existing `-wal`/`-shm` companions when state changes are planned. Use `apply_patch` or an idempotent OpenClaw config operation; preserve authored fields and never edit token files.

After config or relay changes:

- Prefer OpenClaw hot reload. If reload does not happen, restart only the target Gateway process/service; never recreate the member container.
- Check Supervisor/systemd ownership so exactly one Gateway owns the Telegram pollers.
- If adding workspace policy, append managed `reliable-media-delivery` and `telegram-single-delivery` blocks to the exact agent `AGENTS.md` only when their markers are absent. Never duplicate blocks or alter unrelated workspace instructions.

## Validation and acceptance

Run all applicable checks:

```bash
docker exec -e HOME="$MEMBER_HOME" "$CONTAINER" openclaw config validate
docker exec -e HOME="$MEMBER_HOME" "$CONTAINER" openclaw channels status --channel telegram --probe --json
docker exec -e HOME="$MEMBER_HOME" "$CONTAINER" openclaw models status --agent <AGENT_ID> --json
systemctl is-active warp-proxy-relay-docker0.service 2>/dev/null || true
```

Confirm, without exposing payloads:

- Intended account and agent binding is unchanged.
- Target group has the expected `requireMention` and sender admission policy.
- Telegram account is `running`, `connected`, probe OK, with no `409` or reconnect loop.
- Event loop is not degraded and no active session lock remains for the target lane.
- Relay is active, bound only to the Docker bridge, and UFW is bridge-subnet-only.
- No new `sendDocument failed`, `block reply failed`, provider 503, timeout, or dispatch error appears after the reload timestamp.
- Model fallback status is effective for the affected agent.

Do not send a real Telegram test by default. Ask the authorized user to send one normal text message without mentioning the bot, then a small file/report request. If the user explicitly authorizes an automated test, use one unique harmless message and record the UTC receipt/message ID; do not run bot-to-bot tests because Telegram may reject them.

## Rollback and reporting

If validation fails, stop further changes and restore only files changed in this incident from the timestamped backup. Disable/remove only the new relay or firewall rule if it is the proven regression, reload the target Gateway, and re-run validation. Never restore an old offset/session database blindly.

Report:

- Scope: member/container, agent, account, group (redacted as needed), and workspace.
- Root cause: proven vs likely, separating no-inbound, model, session, and outbound/media causes.
- Changes: config fields, relay/firewall, workspace policy, and backup path; no secrets.
- Validation: config, Gateway, Telegram probe, model fallback, relay, and post-reload error scan.
- Remaining limitation: BotFather Privacy Mode, provider outage, or pending authorized user test.
