---
name: openclaw-telegram-group-migrate
description: Diagnose and fix OpenClaw Telegram group chats that suddenly require mentioning the bot, especially after Telegram migrates a normal group to a supergroup and changes the chat ID. Use when a user says OpenClaw/Telegram bot only replies when mentioned, asks why requireMention stopped working, provides a Telegram group ID, or needs channels.telegram.groups repaired in /root/.openclaw/openclaw.json.
---

# OpenClaw Telegram Group Migrate

## Purpose
Fix the common OpenClaw Telegram issue where a group was configured with `requireMention: false`, but the bot later replies only when mentioned because Telegram migrated the chat to a new group ID.

## Safety Rules
- Read VPS instructions and OpenClaw project notes before editing production config.
- Do not print bot tokens, API keys, `.env` contents, cookies, or private credentials.
- Backup `/root/.openclaw/openclaw.json` to `/root/_Backups/openclaw/` before applying changes.
- Keep `"*": { "requireMention": true }` so unknown groups still require mention.
- Keep the old migrated group ID in config; add the new ID instead of deleting old entries.
- After important changes, update `/root/_Second_AI_Brain/06_Nhat_Ky_Thay_Doi.md`.

## Fast Diagnosis
Given a group ID, first run dry-run mode:

```bash
/root/.agents/skills/openclaw-telegram-group-migrate/scripts/fix_group_migrate.py --group-id '<GROUP_ID>'
```

The script checks recent `openclaw-gateway.service` logs for:
- `Group migrated: <old_id> → <new_id>`
- recent `telegram:group:<id>` inbound IDs
- missing `channels.telegram.groups[<id>].requireMention=false`

## Apply Fix
If dry-run shows `MISSING_REQUIRE_MENTION_FALSE`, apply the config update:

```bash
/root/.agents/skills/openclaw-telegram-group-migrate/scripts/fix_group_migrate.py --group-id '<GROUP_ID>' --apply
```

Then verify hot reload:

```bash
journalctl --user -u openclaw-gateway.service --since '5 minutes ago' --no-pager -o cat | rg -i 'config hot reload applied|channels.telegram.groups|Group migrated|telegram:group|outbound send ok'
```

Ask the user to send a normal group message without mentioning the bot.

## Manual Fallback
If the script cannot find a migration but the bot only replies when mentioned:
1. Ask the user to mention the bot once in the affected group.
2. Find the true inbound ID:
   ```bash
   journalctl --user -u openclaw-gateway.service --since '10 minutes ago' --no-pager -o cat | rg 'telegram:group|Group migrated'
   ```
3. Add the actual inbound group ID to `/root/.openclaw/openclaw.json`:
   ```json
   "groups": {
     "*": { "requireMention": true },
     "<ACTUAL_GROUP_ID>": { "requireMention": false }
   }
   ```
4. Validate JSON:
   ```bash
   python3 -m json.tool /root/.openclaw/openclaw.json >/dev/null
   ```
5. Confirm hot reload or restart the user service only if reload does not occur.

## When It Is Not a Config ID Issue
If the correct group ID already has `requireMention: false` and there is no inbound log for normal messages, explain that Telegram is not delivering normal group messages to the bot. Check:
- Bot is still in the correct group.
- Bot has enough permissions or is admin if required.
- BotFather `Group Privacy` is turned off, then remove/add bot or promote it.
- The user is testing in the migrated/current group, not the old group.

## Report Format
Report concisely:
- Old group ID and new group ID if migration was detected.
- Whether config was changed or already correct.
- Backup path if changed.
- Hot reload result.
- Exact next test for the user: send a normal message without mention.
