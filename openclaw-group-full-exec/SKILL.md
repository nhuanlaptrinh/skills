---
name: openclaw-group-full-exec
description: Grant full exec/process runtime access to every sender in one explicitly named OpenClaw Telegram group, with backup, validation, reload, and rollback guidance. Use only when the user explicitly requests group-wide command execution for a specific group ID.
---

# OpenClaw Group Full Exec

Use this skill only for a specific Telegram group ID supplied by the user. The permission change is high risk: it allows every sender admitted by that group policy to run host commands and manage processes through the agent.

## Required workflow

1. Identify the exact OpenClaw config and Telegram account. Do not infer a group ID from a name when multiple groups exist.
2. Run the helper in dry-run mode first:

```bash
bash scripts/set_group_full_exec.sh \
  --group-id <telegram-group-id> \
  --account workspace_videofactory \
  --scope account \
  --dry-run
```

3. Only after explicit user authorization, apply it:

```bash
bash scripts/set_group_full_exec.sh \
  --group-id <telegram-group-id> \
  --account workspace_videofactory \
  --scope account \
  --apply
```

4. Verify with `--check`. The helper creates a timestamped config backup, validates JSON through `openclaw config validate`, and reloads the Gateway after a successful apply unless `--no-restart` is supplied.

## Policy shape

For the selected group only, set:

```json
"toolsBySender": {
  "*": {
    "alsoAllow": ["exec", "process"]
  }
}
```

Remove only a group-local `deny` entry for `exec` or `process`; preserve every other deny, allowlist, group setting, account, token, model, workspace, and agent policy. Do not grant group-wide access by changing the agent wildcard or global defaults.

The default account is `workspace_videofactory`, but always pass it explicitly when operating production configuration. Use `--scope global` only when the group is intentionally configured under `.channels.telegram.groups` rather than an account-specific group map.

Do not send a Telegram test message automatically. After reload, ask the user to retry the task in the target group. If the bot still reports missing tools, inspect routing and the active session before changing broader policy.
