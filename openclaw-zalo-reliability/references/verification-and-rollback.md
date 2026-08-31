# Verification And Rollback

Read this reference before reporting an incident complete.

## Validate Changed Artifacts

Run only the checks relevant to the branch used:

```bash
bash -n /root/.agents/skills/openclaw-zalo-reliability/scripts/diagnose.sh
node --check /root/.agents/skills/openclaw-zalo-reliability/scripts/send_zalo_qr_to_telegram_owner.mjs
bash -n /root/Automation/watchdog/shared_self_healing/scripts/check_member_zalouser.sh
bash -n /root/Automation/openclaw_member_assistant/scripts/audit_member_sessions.sh
bash -n /root/Automation/openclaw_member_assistant/scripts/patch_zalouser_send_reliability.sh
python3 -m json.tool /root/Automation/watchdog/shared_self_healing/project_config.json >/dev/null
```

Inside the affected member environment, validate config and plugins, then probe
channels with the correct HOME and Gateway env loaded.

## Completion Criteria

- Exactly one Gateway exists and its parent is the intended process manager.
- Telegram is `running, connected, works` when configured.
- Zalo Personal is `configured, running, works`.
- No new listener, outbound, cipher, or long-running error appears after the
  latest provider start.
- Target sessions are below the member's preventive threshold.
- Installed watchdog entries and cron markers are unique; cron is active.
- Passive `in:` and `out:` activity is sufficient. Do not send real test
  messages without explicit authorization.

## Rollback

Restore only files changed in the current transaction. If Supervisor loading
fails, restore both the active config and persistent entrypoint before reload.
Restore a session index only if the targeted reset caused a regression and
always preserve transcripts. Remove only the new member registry entries and
their cron marker blocks when uninstalling prevention.

Keep backups until the member confirms stability. Record backup paths,
schedules, validation results, and whether any real message was sent in the
member project note and `/root/_Second_AI_Brain/06_Nhat_Ky_Thay_Doi.md`. Never
record secrets or private sender/group IDs.
