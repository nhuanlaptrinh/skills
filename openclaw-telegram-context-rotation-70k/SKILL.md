---
name: openclaw-telegram-context-rotation-70k
description: Install, inspect, or update automatic 70000-token rotation for idle OpenClaw Telegram sessions in one Docker member without mixing accounts or resetting active turns.
---

# OpenClaw Telegram Context Rotation 70k

Use the existing host-side runner to reset only idle `agent:<agent>:telegram:` sessions whose fresh `totalTokens` reaches `70000`. The official `sessions.reset` RPC creates a new context without deleting conversation history. OpenClaw 2026.9.9 can retain the same session ID and preserve transcript events behind a reset boundary rather than creating a separate transcript archive. The next prompt does not contain the full old conversation.

## Scope

- Runner: `/root/Automation/watchdog/shared_self_healing/scripts/rotate_member_sessions_70k.py`
- Registry: `/root/Automation/watchdog/shared_self_healing/project_config.json`
- Launcher: `/root/Automation/watchdog/shared_self_healing/run_project.sh`
- Root cron: `* * * * *` for the registered `member_<label>_sessions` project
- Default member HOME: resolve from the project note; do not infer it from the host data path.

The runner is fail-closed: it requires fresh numeric token metadata, a terminal/idle session, no active run, a session ID, a complete session listing, and a matching `expectedSessionId`. It resets at most one session per invocation by default. It never edits SQLite rows, deletes transcripts, changes credentials, or sends Telegram messages.

Receipt checking defaults to `new-session-id` for backward compatibility. For the verified 2026.9.9 runtime use `--reset-receipt-mode reset-boundary`: require official `ok=true`, the exact session key, a nonempty session ID and lifecycle revision, fresh zero input/output/total tokens, and matching reset timestamps at or after the RPC start. A preserved session ID alone is not a failure. Do not enable the compatibility mode on other members without checking their runtime contract. Re-listing and session-ID checks reduce, but cannot eliminate, the inbound-message race between the last check and reset.

## Dry-run

```bash
python3 /root/Automation/watchdog/shared_self_healing/scripts/rotate_member_sessions_70k.py \
  --container user-<member> \
  --member-home /home/<member> \
  --agent main \
  --key-prefix 'agent:main:telegram:' \
  --threshold 70000 \
  --active-window-seconds 180 \
  --state-dir /root/Automation/watchdog/shared_self_healing/state \
  --max-resets-per-run 1 \
  --reset-receipt-mode reset-boundary \
  --dry-run
```

## Deploy or update

Before production changes, read the member note and applicable `AGENTS.md`; backup the member config, state SQLite plus matching `-wal`/`-shm`, registry, root crontab, and relevant notes under `/root/_Backups`. Add one registry entry with `key-prefix agent:main:telegram:` and a matching root-cron block. Preserve unrelated registry and cron entries. Do not restart the container or Gateway for this scheduler change.

The first cron tick may reset an already eligible idle session. Treat that as an authorized production state mutation; report the count and redacted session labels. Do not run the non-dry command manually unless the customer explicitly authorizes an immediate reset.

## Verify

```bash
python3 -m py_compile /root/Automation/watchdog/shared_self_healing/scripts/rotate_member_sessions_70k.py
python3 -m unittest discover -s /root/Automation/watchdog/shared_self_healing/tests -p 'test_rotate_member_sessions_70k.py' -v
crontab -l | grep -A2 -B1 'member_<member>_sessions_70k'
tail -n 50 /root/Automation/watchdog/shared_self_healing/logs/member_<member>_sessions.log
docker exec -e HOME=/home/<member> user-<member> openclaw channels status --channel telegram --probe --json
```

Confirm the Gateway remains running, Telegram remains connected, and reset receipts satisfy the selected mode. For a same-ID reset boundary, read-only SQLite metadata can confirm a new reset event, changed lifecycle revision and zero tokens while prior transcript-event identities remain intact. Never perform a production reset merely to test receipt parsing. Do not use this policy to diagnose provider or Telegram transport latency; run the Telegram latency audit separately.

## Deployed member: nguyentienvinh

- Container: `user-nguyentienvinh`; HOME: `/home/nguyentienvinh`; agent: `main`.
- Authorized scope: Telegram DM/group sessions only, never other members or Zalo.
- Input: official Gateway session metadata; output: redacted candidate/reset receipts in the member log, plus official OpenClaw reset boundaries retaining prior transcript history.
- Log: `/root/Automation/watchdog/shared_self_healing/logs/member_nguyentienvinh_sessions.log`; locks: `/root/Automation/watchdog/shared_self_healing/state/`.
- Backup: `/root/_Backups/nguyentienvinh-telegram-context-rotation-70k/20261015T130757Z/` contains config, consistent state/agent SQLite snapshots, WAL/SHM copies, registry, crontab, and notes. Raw live database copies alone are not a consistent restore image.
- No Sheet, upload, publishing, or external notification is used. This scheduler performs no inference requests.

Read-only scan or rerun verification:

```bash
python3 /root/Automation/watchdog/shared_self_healing/scripts/rotate_member_sessions_70k.py \
  --container user-nguyentienvinh --member-home /home/nguyentienvinh \
  --agent main --key-prefix 'agent:main:telegram:' --threshold 70000 \
  --active-window-seconds 180 \
  --state-dir /root/Automation/watchdog/shared_self_healing/state \
  --max-resets-per-run 1 --reset-receipt-mode reset-boundary --dry-run
```

Real run, already scheduled every minute; an explicitly requested manual rerun uses the same launcher and locks:

```bash
/root/Automation/watchdog/shared_self_healing/run_project.sh member_nguyentienvinh_sessions
```

No rerender is applicable. To change threshold, scope, HOME or schedule, back up again, preserve unrelated entries, dry-run the new arguments, validate the registry/cron, and update this skill and the member note.

## Rollback and safety

- Remove only the target registry entry and matching cron block, then restore from the timestamped backup if a rollback is required.
- Never restore an entire stale shared registry/crontab over later unrelated changes. Leave the shared runner compatibility flag in place unless its other callers have been checked; their default receipt mode remains unchanged.
- Never reset active/queued sessions, lower the idle guard below 180 seconds, or use a chat ID alone as a session identity.
- Never print bot tokens, API keys, cookies, passwords, private keys, message text, peer IDs, or full session IDs.
