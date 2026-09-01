---
name: sua-loi-telegram-offset-openclaw
description: Diagnose and safely repair OpenClaw Telegram bots that stop replying when a persisted polling offset is stale or higher than current Cloud Bot API updates; use for offset, polling, and Local-to-Cloud migration incidents, not general agent routing or video delivery.
---

# Sua Loi Telegram Offset Openclaw

Use this skill when a Telegram bot is configured and its agent/model appears healthy, but new DM or group messages do not reach OpenClaw after a polling restart or a Local Bot API to Cloud API migration.

## Core diagnosis

- Confirm the account, agent, workspace, `apiRoot`, webhook state, and bot identity without printing a token.
- Treat `https://api.telegram.org` with `getUpdates` as Cloud API polling. Polling mode is not the same as Local Bot API.
- Read the account's persisted row in the OpenClaw state database: namespace `telegram.update-offsets`, key equal to the Telegram account ID.
- Compare its `lastUpdateId` with update IDs returned by Cloud API. A stored offset greater than current Cloud update IDs causes Telegram to skip every new update.

## Safety rules

- Never call `getUpdates` while the Gateway is running. It can create a 409 conflict, consume/advance updates, or hide the real owner of the polling session.
- Stop the relevant Gateway before a direct Cloud API queue check or state-database mutation. Start it again even when a diagnostic command fails.
- Do not print bot tokens, full update payloads, message text, media IDs, or credential files.
- Default to dry-run. Apply only after the user explicitly authorizes the repair and the observed offset is passed as `--expected-offset`.
- Back up the SQLite database and its `-wal`/`-shm` companions before deleting anything.
- Delete only the target `telegram.update-offsets` row. Preserve sessions, message cache, workspace files, training data, routing, and configuration.

## Repair workflow

1. Check `openclaw channels status --channel telegram --probe --json`, the Gateway service, and the target account's effective routing. Record only redacted metadata.
2. Stop `openclaw-gateway.service` (or the actual service unit) and verify it is inactive.
3. Run the helper in dry-run mode with `--cloud-check`. It reports the stored offset, Cloud update ID range, bot ID, and whether a mismatch is proven.
4. If the stored offset is stale/high, rerun with `--apply --expected-offset <value>`. The helper refuses an active Gateway, an unexpected offset, or an unproven mismatch unless `--force` is explicitly supplied.
5. Start the Gateway and wait until the target account is connected. Send a fresh unique DM test and verify both `Inbound message` and outbound success in the log.
6. For a group, test with an explicit bot mention first. If unmentioned messages must trigger the bot, check BotFather Privacy Mode; OpenClaw `requireMention:false` cannot override Telegram privacy filtering.

## Helper

Resolve the helper relative to this skill directory. It is intentionally standard-library-only:

```bash
python3 scripts/repair_telegram_offset.py \
  --account-id <telegram-account-id> \
  --cloud-check
```

After reviewing the dry-run output while the Gateway is stopped:

```bash
python3 scripts/repair_telegram_offset.py \
  --account-id <telegram-account-id> \
  --cloud-check \
  --apply \
  --expected-offset <stored-lastUpdateId> \
  --backup-dir /root/_Backups
```

Use `--force` only when the mismatch was independently proven from logs or a known update ID but the Cloud queue is empty. Never use it to bypass an active-Gateway check or an unexpected offset.

<<<<<<< HEAD
## Prevention guard

OpenClaw update-offset state version 3 protects bot/token rotation, but a Local Bot API to Cloud API switch can keep the same bot/token while the update-ID sequence moves backward. A state migration can also preserve that high offset with the current bot identity. Install the bundled pre-start guard so this condition is repaired before polling resumes:

```bash
python3 scripts/guard_telegram_offsets.py
```

The dry-run is local-only and safe while the Gateway is active. It reports only account IDs, sanitized API roots, offset metadata, and repair reasons. It never prints bot tokens, message text, payloads, chat IDs, or media IDs.

Production apply must run while the Gateway is inactive:

```bash
python3 scripts/guard_telegram_offsets.py --apply
```

The guard deletes an account offset only when at least one fail-closed condition is proven:

- the effective Telegram `apiRoot` changed since the previous successful preflight;
- the configured bot ID changed;
- the stored high update ID exists in ingress history, but a lower update ID was received later for the same account.

Every mutation backs up the SQLite database plus WAL/SHM under `/root/_Backups/telegram-offset-guard-<UTC>/`. Guard state is secret-free and stored at `/root/.openclaw/state/telegram-offset-guard.json` with mode `0600`.

On the root VPS, install the systemd user drop-in at `/root/.config/systemd/user/openclaw-gateway.service.d/20-telegram-offset-guard.conf`, then run:

```bash
systemctl --user daemon-reload
systemctl --user restart openclaw-gateway.service
```

The drop-in runs the local guard as `ExecStartPre`, while the Gateway is still inactive. Do not add a cron job that calls Cloud `getUpdates` alongside the running Gateway.

Validation:

```bash
python3 -m py_compile scripts/repair_telegram_offset.py scripts/guard_telegram_offsets.py
python3 -m unittest discover -s tests -v
systemd-analyze --user verify openclaw-gateway.service
systemctl --user show openclaw-gateway.service -p ExecStartPre --no-pager
```

To roll back only the prevention guard, move the drop-in to the incident backup directory, run `systemctl --user daemon-reload`, and restart the same Gateway. Do not restore an old offset database unless the current database is corrupt; the guard state file can remain because it contains no credentials and is ignored without the drop-in.
=======
## Khac phuc tai dien

Tren VPS production, dung guard tai `/root/Automation/openclaw/telegram_offset_guard` de tu phuc hoi offset cho tat ca tai khoan Telegram. Guard chi sua khi mot tai khoan co update dang cho trong 3 chu ky lien tiep, moi chu ky cach nhau 5 phut; mot lan co the xu ly thanh cong se bi gioi han boi cooldown 30 phut.

- Khi Gateway dang chay, chi goi `getWebhookInfo` de doc `pending_update_count`. Tuyet doi khong goi `getUpdates` vi co the tranh chap poller, tieu thu update hoac lam sai chan doan.
- Khi du 3 chu ky, guard dung Gateway va xac minh service da inactive truoc khi doc Cloud queue hoac sua SQLite.
- Chi sua khi helper chung minh `stored_offset > max_update_id`. Truoc khi sua phai backup SQLite cung cac file `-wal` va `-shm`, sau do chi xoa dung row `telegram.update-offsets` cua account loi.
- Luon khoi dong lai Gateway trong cleanup/finally, ke ca khi kiem tra hoac sua loi. Dung `flock` de tranh hai lan chay chong nhau va cooldown de tranh restart lap.
- Ho tro token dang chuoi va environment SecretRef, nhung khong ghi token, payload Telegram hay noi dung tin nhan vao state/log.

Lich production de guard chay lech mot phut voi session maintenance:

```cron
1-56/5 * * * * /root/Automation/openclaw/telegram_offset_guard/run_telegram_offset_guard.sh >> /root/Automation/openclaw/telegram_offset_guard/logs/telegram_offset_guard.log 2>&1
```

Xoay session theo nguong `50000` token la lop bao ve context rieng, khong phai cach sua Telegram offset. Vi du cho agent `tester`:

```cron
2-57/5 * * * * /root/Automation/openclaw/session_maintenance/run_rotate_sessions.sh --agent tester --key-prefix 'agent:tester:telegram:' --threshold 50000 >> /root/Automation/openclaw/session_maintenance/logs/rotate_sessions_tester.log 2>&1
```

Sau khi cai lich, kiem tra state/log theo metadata da redacted, `openclaw config validate`, trang thai Gateway va `openclaw channels status --channel telegram --probe --json`. Khong gui tin Telegram thu that tu automation.
>>>>>>> a62b73f (nguyen van nhuannnn)

## If no mismatch is found

Investigate, in order: a duplicate poller or 409 conflict, webhook still configured, wrong bot token/account, DM or group allowlist, Telegram Privacy Mode, dispatch/session errors, and only then model/provider latency. Use `unify-openclaw-bot-workspace` for divergent routing and the relevant OpenClaw permission skill for owner policy; this skill does not change agent/workspace architecture.

If a token was printed to a terminal, history, or log, recommend rotating it with BotFather and updating the account after the offset repair. Do not copy the token into this skill or any diagnostic output.
