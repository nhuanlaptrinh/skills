# Zalo QR Login

Use QR login only when the owner explicitly asks to replace the Zalo session or
when credential/cipher/login failure persists after core/plugin alignment and a
clean Gateway restart.

## Required Telegram Owner Permissions

Every QR recipient must be present in all applicable owner layers:

- `channels.telegram.allowFrom`
- `commands.ownerAllowFrom` as `telegram:<user_id>` or the existing equivalent
- `tools.elevated.allowFrom.telegram`
- `channels.telegram.execApprovals.approvers`
- `approvals.plugin.targets` when plugin approval routing is enabled

Never add wildcard owner/elevated/approver access and never send QR images to a
group or an unverified forwarded ID.

## Preferred Owner Workflow

Run dry-run first:

```bash
node /root/.agents/skills/openclaw-zalo-reliability/scripts/send_zalo_qr_to_telegram_owner.mjs \
  --target <telegram-user-id> --dry-run
```

Apply only after explicit authorization:

```bash
node /root/.agents/skills/openclaw-zalo-reliability/scripts/send_zalo_qr_to_telegram_owner.mjs \
  --target <telegram-user-id> --apply
```

Repeat `--target` for multiple approved owners and use `--telegram-account`
when multiple Telegram accounts are enabled. The helper backs up private state,
stops only the Zalo channel when needed, creates one QR, sends it independently
to approved owners, waits for confirmation, restarts Zalo, and removes the
temporary image.

`--apply` replaces the active Zalo session. Do not run it merely to inspect
status. If Telegram cannot initiate a DM, the owner must open the bot DM first.

## Headless Web Fallback

When the owner workflow cannot be used, publish only the generated PNG through
a no-cache Nginx location, run QR sync only during login, and stop the sync
after success. Keep the existing model, provider, channel policies, hooks,
skills, and unrelated config unchanged during `openclaw onboard`.

Never print or store the raw QR payload in documentation, logs, or chat.
