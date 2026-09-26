---
name: openclaw-group-full-exec
description: Grant full exec/process runtime access to every sender in one explicitly named OpenClaw Telegram group, with backup, validation, reload, and rollback guidance. Use only when the user explicitly requests group-wide command execution for a specific group ID.
---

# OpenClaw Group Full Exec

Use this skill only for a specific Telegram group ID supplied by the user. The permission change is high risk: it allows every sender admitted by that group policy to run host commands and manage processes through the agent.

## Required workflow

1. Identify the exact OpenClaw config and Telegram account. Do not infer a group ID from a name when multiple groups exist. For a Member VPS, the usual config is `/root/Apps/member_vps/docker-users/data/<member>/root/.openclaw/openclaw.json` (or `<member>/.openclaw/openclaw.json` for legacy homes).
2. Run the helper in dry-run mode first:

```bash
bash scripts/set_group_full_exec.sh \
  --config /path/to/.openclaw/openclaw.json \
  --group-id <telegram-group-id> \
  --account workspace_videofactory \
  --scope account \
  --dry-run
```

3. Only after explicit user authorization, apply it:

```bash
bash scripts/set_group_full_exec.sh \
  --config /path/to/.openclaw/openclaw.json \
  --group-id <telegram-group-id> \
  --account workspace_videofactory \
  --scope account \
  --apply
```

4. Verify with `--check`. The helper creates a timestamped config backup, validates JSON through `openclaw config validate`, and reloads the Gateway after a successful apply unless `--no-restart` is supplied.

## Member VPS recipe

For a member named `nguyenvantieng` and group `-5215984188`:

```bash
CFG=/root/Apps/member_vps/docker-users/data/nguyenvantieng/root/.openclaw/openclaw.json
bash scripts/set_group_full_exec.sh --config "$CFG" --group-id -5215984188 --account default --scope global --dry-run
bash scripts/set_group_full_exec.sh --config "$CFG" --group-id -5215984188 --account default --scope global --apply
bash scripts/set_group_full_exec.sh --config "$CFG" --group-id -5215984188 --account default --scope global --check
```

Group full-exec only grants the tools. To stop Telegram approval prompts for the whole member runtime, also run the auto-approval skill:

```bash
python3 /root/.agents/skills/set-phe-duyet-tu-dong-openclaw/scripts/set_auto_approval.py --member <member> --dry-run
python3 /root/.agents/skills/set-phe-duyet-tu-dong-openclaw/scripts/set_auto_approval.py --member <member> --apply
python3 /root/.agents/skills/set-phe-duyet-tu-dong-openclaw/scripts/set_auto_approval.py --member <member> --check
```

Use `--scope global` when the group is under `channels.telegram.groups`; use `--scope account` when it is under `channels.telegram.accounts.<account>.groups`. Always pass `--config` for a non-default VPS/member; otherwise the helper reads the current shell user's `~/.openclaw/openclaw.json`.

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
