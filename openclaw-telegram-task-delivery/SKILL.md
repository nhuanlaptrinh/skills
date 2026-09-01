---
name: openclaw-telegram-task-delivery
description: Install, audit, repair, or reuse reliable same-origin completion delivery for OpenClaw Telegram agents on Docker member VPS systems. Use when background tasks or subagents finish internally but the user must remind the bot, completion alerts go to the wrong DM/group, files are created but not attached, heartbeat owner routing is ambiguous, or a reusable post-completion watchdog is required.
---

# OpenClaw Telegram Task Delivery

Make the parent/coordinator deliver a completed task to the exact Telegram conversation that requested it. Do not use heartbeat owner routing as the primary task handoff.

## Inputs

Resolve these values from Docker metadata and the active OpenClaw config; do not guess them:

```bash
export CONTAINER="user-<member>"
export DATA_DIR="/root/Apps/member_vps/docker-users/data/<member>"
export MEMBER_HOME="/home/<member>"
export AGENT_ID="main"
export ACCOUNT_ID="<telegram-account-id>"
export OWNER_ID="<existing-authorized-telegram-user-id>"
```

The owner must already exist in the Telegram account allowlist or be separately authorized by the user. Never copy a private destination from another member.

## What the installer changes

The bundled installer:

- Backs up `openclaw.json`, workspace `AGENTS.md`, optional `HEARTBEAT.md`, and the prior cron file under `/root/_Backups/openclaw-telegram-task-delivery/<member>/<timestamp>/`.
- Adds the selected Telegram owner as the primary `commands.ownerAllowFrom` entry while preserving other authored owners.
- Keeps the existing tool profile and adds `message`, which is not included in the `coding` profile.
- Authors heartbeat routing to the selected owner/account for administrative alerts; task results still return through the requester session.
- Appends idempotent same-origin task handoff, reliable media, and Telegram duplicate-suppression blocks to the exact agent workspace `AGENTS.md`.
- Adds a heartbeat rule that forbids using ambient heartbeat as a substitute for requester-session completion delivery.
- Copies this skill into `<workspace>/skills/openclaw-telegram-task-delivery`.
- Optionally installs the reusable watchdog at `/root/Automation/watchdog/openclaw_telegram_task_delivery` and a member-specific `/etc/cron.d/` entry.

## Dry-run

Run the installer without `--apply`. It validates all proposed OpenClaw config writes and prints only redacted metadata:

```bash
python3 /root/.agents/skills/openclaw-telegram-task-delivery/scripts/install_member.py \
  --container "$CONTAINER" \
  --data-dir "$DATA_DIR" \
  --member-home "$MEMBER_HOME" \
  --agent-id "$AGENT_ID" \
  --account-id "$ACCOUNT_ID" \
  --owner-id "$OWNER_ID" \
  --install-cron
```

Run the watchdog in read-only mode:

```bash
python3 /root/Automation/watchdog/openclaw_telegram_task_delivery/watch_delivery.py \
  --container "$CONTAINER" \
  --data-dir "$DATA_DIR" \
  --member-home "$MEMBER_HOME" \
  --agent-id "$AGENT_ID" \
  --account-id "$ACCOUNT_ID" \
  --state-file "/root/Automation/watchdog/openclaw_telegram_task_delivery/state/<member>.json"
```

## Apply

After reviewing the dry-run, apply the production changes:

```bash
python3 /root/.agents/skills/openclaw-telegram-task-delivery/scripts/install_member.py \
  --container "$CONTAINER" \
  --data-dir "$DATA_DIR" \
  --member-home "$MEMBER_HOME" \
  --agent-id "$AGENT_ID" \
  --account-id "$ACCOUNT_ID" \
  --owner-id "$OWNER_ID" \
  --install-cron \
  --apply
```

The installer uses official `openclaw config set` dry-runs before writes, validates the final config, and does not send a Telegram test message.

## Required runtime behavior

For a task that needs a child session:

1. Keep one parent/coordinator responsible for external delivery.
2. Spawn the child with `sessions_spawn`.
3. If the result is required for the user's request, call `sessions_yield`; do not end the parent turn with only a promise.
4. When completion arrives, inspect the retained child result. Do not return `NO_REPLY` while the requester still lacks the result.
5. Verify files locally before sending. For office documents, inspect structure/content and render or preview when practical; suspiciously tiny files are not completion evidence.
6. Send through `message` to the explicit channel, account, group/DM, and topic derived from the requester session.
7. Treat delivery as complete only after a real platform `messageId` and matching destination receipt.
8. Return `NO_REPLY` after a verified `message` send to prevent a duplicate normal assistant reply.

## Watchdog behavior

The watchdog monitors only tasks that finish after its installation cutoff. It never replays older tasks automatically.

- It reads the shared task ledger and the target container's recent OpenClaw logs.
- It accepts a completion only when a Telegram outbound success appears after task completion for the exact account and requester chat.
- After the grace period, it starts one recovery turn against the exact requester session and exact Telegram target.
- It checks again immediately before recovery, records attempts in a root-only state file, and limits retries.
- It never logs message content, task output, credentials, or destination identifiers.

## Validation

Run after installation:

```bash
docker exec -e HOME="$MEMBER_HOME" "$CONTAINER" openclaw config validate
docker exec -e HOME="$MEMBER_HOME" "$CONTAINER" openclaw agents list --bindings
docker exec -e HOME="$MEMBER_HOME" "$CONTAINER" \
  openclaw channels status --channel telegram --probe --json
docker exec -e HOME="$MEMBER_HOME" "$CONTAINER" openclaw tasks audit --json
python3 /root/.codex/skills/.system/skill-creator/scripts/quick_validate.py \
  /root/.agents/skills/openclaw-telegram-task-delivery
```

Check that `message` is present in the effective tool policy, the workspace markers occur exactly once, the cron command has no private destination, and the watchdog dry-run reports no unhandled post-install task.

For a real acceptance test, obtain authorization, then create one harmless background task from a Telegram group and one from a DM. Confirm child completion, verified outbound to the same origin, no cross-chat delivery, and no duplicate message.

## Rerun and rollback

- The installer is idempotent: rerun dry-run or apply after config drift without duplicating managed blocks.
- The watchdog is safe to rerun; without `--apply` it never starts a recovery turn.
- To roll back, stop or remove only the member-specific cron file, restore `openclaw.json` and workspace files from the timestamped backup, validate config, and reload/restart only the target Gateway if required.
- Never delete sessions, task records, Telegram offsets, or state SQLite files for this delivery problem.

## Safety

- Do not print or copy tokens, API keys, cookies, passwords, private keys, `.env` contents, full private messages, or destination identifiers into documentation.
- Do not use `heartbeat.target=last` as a generic multi-chat fix; another recent DM/group can become the destination.
- Do not mark a task complete merely because `task_runs.delivery_status=delivered`; that status can mean the child result reached the parent internally, not that Telegram received it.
- Back up before changing config or cron and update the VPS change log after production changes.
