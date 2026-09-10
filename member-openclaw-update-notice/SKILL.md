---
name: member-openclaw-update-notice
description: Send an explicitly authorized OpenClaw upgrade notice to member Telegram allowlist users and configured or known permitted groups, with per-bot deduplication and platform receipts.
---

# Member OpenClaw Update Notice

Use only when the user authorizes sending the announcement. Upgrade authorization alone does not authorize notifications. Existing authorization in the conversation suffices; no second approval is needed.

Script: `/root/Automation/openclaw/member_update_notice/notice.py`.
Input: accepted upgrade manifest, UTF-8 notice text, target version and private job directory. The manifest narrows the scope to upgraded members; preparation verifies the installed version and each live Telegram account. Runtime HOME comes from the sole Gateway process.

Targets are numeric Telegram sender allowlist IDs plus enabled explicit groups. Known groups are read as metadata from the owning member's agent databases and admitted only by its group configuration. Wildcards are never destinations. The same bot/chat receives one notice, even if repeated in multiple configurations. Different bots may each notify a shared owner.

```bash
python3 /root/Automation/openclaw/member_update_notice/notice.py prepare \
  --manifest /root/_Backups/openclaw-members-2026.9.3/final-acceptance.json \
  --message-file <notice-text-file> --version 2026.9.3 --job <private-job-directory>
python3 /root/Automation/openclaw/member_update_notice/notice.py dry-run --job <private-job-directory>
python3 /root/Automation/openclaw/member_update_notice/notice.py apply --job <private-job-directory>
```

Review the dry-run counts, scope and exact text before apply. `--limit 1` allows validating the first authorized real receipt before continuing the same job. Apply uses the native `openclaw message send` command in each member and respects its existing Telegram token source and Local Bot API settings. It changes no member config, credentials, sessions, Sheet, cron or service.

Output: root-only `plan.json` and `receipts.json` in the supplied job directory. A send counts as successful only with a real message ID and matching destination. Never print tokens, config contents, private chat identifiers or raw API errors in documentation. Store sensitive targeting metadata only in the private job directory; report aggregate counts and member/account names.

Rerun apply with the SAME job directory: sent, failed, inflight and ambiguous entries are not replayed. An ambiguous timeout is not permission to retry; inspect receipts first. Blocked/deactivated users and groups where the bot is absent cannot receive the notice; report those failures without changing permissions or borrowing credentials. Do not create a new job to bypass duplicate protection. Append aggregate results and the private report path to the VPS change log.
