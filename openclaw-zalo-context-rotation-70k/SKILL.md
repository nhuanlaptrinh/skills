---
name: openclaw-zalo-context-rotation-70k
description: Install, inspect or update automatic Zalo context rotation at 70000 tokens for one OpenClaw Docker member. Use when a customer wants long Zalo DM/group sessions reset to reduce context growth while preserving transcript archives and skipping active turns. Includes dry-run, backups, minute cron, threshold overrides and rollback; does not change Telegram, login or message routing.
---

# OpenClaw Zalo Context Rotation 70k

Reset **only the selected agent's Zalo sessions** when reported `totalTokens`
reaches 70,000. A reset starts a fresh conversational context; the previous
transcript remains archived by OpenClaw. It is not semantic compaction and
does not preserve the entire old conversation in the next prompt. Explain
this tradeoff when installing it. It can reduce context growth, not guarantee
fast replies or repair Zalo connectivity.

## Scope and prerequisites

- Linux Docker host, Python 3.10+, `docker`, root `crontab`, and a running cron service.
- OpenClaw Gateway with `sessions.list` and `sessions.reset` RPCs; reset must
  support `expectedSessionId`. Verified against OpenClaw 2026.9.7; check other
  releases rather than patching bundles or bypassing schema validation.
- Existing member data must directly contain `.openclaw/openclaw.json` and
  `.openclaw/state/openclaw.sqlite` for consistent pre-install backup.
- This package is **host-side**. Do not blindly run it inside a member, on the
  root user's unrelated OpenClaw, or on Windows/macOS/native installations.
  Those targets require a separately reviewed transport/scheduler adaptation.
- Read applicable AGENTS and VPS/project production notes. Resolve container,
  HOME, data mount and agent first. HOME may be `/root` even when the member's
  visible login directory is `/home/<member>`.

## Install for one customer

Set `BASE` to the installed skill folder. Substitute verified member values;
the example member below is synthetic. `--member-data-dir` is the directory
directly containing `.openclaw`, not necessarily the member's top-level folder.

```bash
BASE=/root/.agents/skills/openclaw-zalo-context-rotation-70k
python3 "$BASE/scripts/install.py" \
  --container user-khachmau --member-label khachmau \
  --member-home /root \
  --member-data-dir /root/Apps/member_vps/docker-users/data/khachmau/root \
  --dry-run
```

Review the dry-run, then rerun **the same command with `--apply` instead of
`--dry-run`** only when that customer's rotation is authorized. Creation of
this skill alone does not authorize installation on other customers.

Defaults: `--threshold 70000`, `--idle-seconds 180`, `--agent main`, cron every
minute, at most one reset per run. All are runtime arguments, not customer
values hardcoded in source. Optional `--center-dir` and `--backup-root` allow
another Linux host layout. State/logs are kept outside the shareable skill.

The installer verifies the data/HOME mount and performs a read-only Gateway
scan. Dry-run creates no backup, file, lock, registry or cron entry. Apply:

1. Creates root-only timestamped backups of config, consistent SQLite state,
   registry and root crontab before scheduling.
2. Installs the reusable runner under the Shared Watchdog Center, using
   `member_<label>_sessions` and marker `member_<label>_sessions_70k`.
3. Preserves unrelated registry/cron entries and reuses an existing matching
   job. Rejects duplicate scopes, ambiguous markers and shared runtime drift.
4. Keeps an existing `run_project.sh`; creates a minimal bundled launcher only
   when absent. Infrastructure jobs do not call AI or consume inference tokens.
5. Enables cron but does not intentionally reset a session inside the installer.
   Once enabled, eligible sessions can reset on the next cron tick.

## Rotation safeguards

- Prefix is exactly `agent:<selected-agent>:zalouser:`: includes Zalo DM and
  group sessions, excludes Telegram and other agents.
- Requires fresh numeric token usage, known terminal/idle status,
  `hasActiveRun=false`, empty `activeRunIds`, an existing session ID, no archive
  or incognito flag, and at least three minutes since the latest activity.
- Locks overlapping runs, re-lists immediately before mutation, and passes
  `expectedSessionId`. Verify a new session ID in the receipt; stop on errors.
- Missing metadata, unknown status, partial/paginated listings, active turns,
  stale usage or changed identity fail closed. Do not lower the idle guard or
  clear active state to force a reset.
- Never delete transcripts, edit SQLite/session rows, replay messages, change
  credentials/QR login, or send test messages. Only the official reset RPC
  mutates a session. Session IDs and peer IDs are not printed in logs.
- The idle/recheck gates reduce race risk; they are not an atomic promise that
  a new inbound message cannot arrive between the final check and the RPC.

## Verify and handoff

```bash
python3 "$BASE/scripts/test_rotation.py"
python3 "$BASE/scripts/test_installer.py"
python3 "$BASE/scripts/rotate_zalo_sessions.py" \
  --container user-khachmau --member-home /root --threshold 70000 --dry-run
```

After an authorized install, inspect root cron and
`<center>/logs/member_<label>_sessions.log`; verify the cron service is active.
Check channel health without sending real messages. No candidates is a valid
result, not a reason to force a production reset. Offline fixture tests do not
constitute a real delivery/production reset test.

Report scope, threshold, idle gate, schedule, backup path, candidates/resets,
and whether the installer created or reused the launcher. Update the member
note and change journal where available. Read
[references/rollback.md](references/rollback.md) before removing/changing an
installed policy or recovering a partial installation.
