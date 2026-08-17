---
name: unify-openclaw-bot-workspace
description: Normalize or merge OpenClaw Telegram routing so each bot account uses exactly one agent, one workspace, and one agent state directory for both DMs and groups, while preserving training data and granting every configured owner full guarded access. Use for a clean new member that needs canonical main/account-level routing, or when a legacy bot has separate main/admin agents, peer bindings, divergent workspaces, or owner routing that needs backup, dry-run, validation, and rollback.
---

# Unify OpenClaw Bot Workspace

Enforce `one Telegram account -> one agent -> one workspace`. Keep sessions separate by conversation for privacy while sharing approved workspace files, training data, persona, and memory.

Owners are permissions on that canonical agent, not separate agents. For the existing bot, route owners, normal DMs, and groups to `main` at `/root/.openclaw/workspace`. Create another agent/workspace only for another bot/account.

## Safety Model

- Read the VPS runbook, project `AGENTS.md`, production checklist, and related project note first.
- Read `references/merge-and-security-model.md` before applying or changing owner/tool policy.
- Never merge raw session stores, agent SQLite, auth profiles, provider files, or `models.json`.
- Never print bot tokens, approval socket tokens, API keys, cookies, passwords, or full secret-bearing config.
- Stop or quiesce only the OpenClaw Gateway during apply/rollback. Do not recreate the member container.
- Store transactions in `/root/_Backups`, outside member persistent data.
- Validate the transformed candidate with the installed `openclaw config validate` before writing production.

## Inventory

Confirm the live OpenClaw root, runtime root, Telegram account, target agent, source agents, workspaces, agent directories, bindings, owner count, Gateway process manager, and disk headroom.

Dry-run:

```bash
python3 /root/.agents/skills/unify-openclaw-bot-workspace/scripts/unify_bot_workspace.py \
  --openclaw-root <HOST_OPENCLAW_ROOT> \
  --runtime-openclaw-root /root/.openclaw \
  --account-id <TELEGRAM_ACCOUNT_ID> \
  --target-agent main \
  --source-agent owner-admin
```

Dry-run reports sanitized counts only and performs no writes.

For a clean new member with only `main`, omit `--source-agent`. This normalize-only mode rewrites account routing and guarded owner policy without merging or retiring another workspace:

```bash
python3 /root/.agents/skills/unify-openclaw-bot-workspace/scripts/unify_bot_workspace.py \
  --openclaw-root <HOST_OPENCLAW_ROOT> \
  --runtime-openclaw-root /root/.openclaw \
  --account-id <TELEGRAM_ACCOUNT_ID> \
  --target-agent main
```

## Apply

1. Stop or quiesce only the Gateway and confirm it cannot write config/session state.
2. Run:

```bash
python3 /root/.agents/skills/unify-openclaw-bot-workspace/scripts/unify_bot_workspace.py \
  --openclaw-root <HOST_OPENCLAW_ROOT> \
  --runtime-openclaw-root /root/.openclaw \
  --account-id <TELEGRAM_ACCOUNT_ID> \
  --target-agent main \
  --source-agent owner-admin \
  --backup-dir /root/_Backups/openclaw-bot-workspace \
  --apply --gateway-stopped
```

3. Preserve the returned `manifest` path. It is the rollback source of truth.
4. Merge useful source control-file rules into the canonical workspace manually only after review. Do not replace the canonical persona or group privacy rules.
5. Validate config while the Gateway remains stopped, then restart only the Gateway.

For normalize-only on a clean member, use the same apply command without `--source-agent`. The transaction still backs up config and approvals, but has zero moved source workspaces.

The script copies source-only files, skips identical files, namespaces conflicts, retires source workspace/agent state into the transaction, routes the whole account to the target, synchronizes all configured Telegram owners, protects non-owner tools, resets source `allow-always` rules, and writes atomically.

## Check

```bash
python3 /root/.agents/skills/unify-openclaw-bot-workspace/scripts/unify_bot_workspace.py \
  --openclaw-root <HOST_OPENCLAW_ROOT> \
  --runtime-openclaw-root /root/.openclaw \
  --account-id <TELEGRAM_ACCOUNT_ID> \
  --target-agent main \
  --source-agent owner-admin \
  --check
```

Then run runtime validation, binding inspection, Gateway/channel probe, exec-policy inspection, security audit, and owner/non-owner tool tests from the reference checklist.

## Rollback

Stop or quiesce only the Gateway, then run:

```bash
python3 /root/.agents/skills/unify-openclaw-bot-workspace/scripts/unify_bot_workspace.py \
  --rollback-manifest <TRANSACTION_MANIFEST> \
  --gateway-stopped
```

Validate and restart the Gateway. Rollback never deletes an imported file that changed after apply; it moves that file to `rollback-conflicts`.
Rollback also refuses to overwrite `openclaw.json` or `exec-approvals.json` if either changed after the migration.

## New Bots

Create a new agent/workspace only when adding a distinct bot/account. For a new member with one bot and only `main`, run normalize-only without `--source-agent`, bind the whole account at account level, and verify with `--check`. Never create an extra agent/workspace merely to grant another owner access to an existing bot.

## Completion

- Sync this global skill into the target OpenClaw skills root and run the sync checker.
- Update `cap-quyen-telegram-admin-openclaw` so it grants owners on the bot's canonical agent.
- Run a secret scan over the skill and sanitized transaction metadata.
- Update the project note and `/root/_Second_AI_Brain/06_Nhat_Ky_Thay_Doi.md` without IDs or secrets.
