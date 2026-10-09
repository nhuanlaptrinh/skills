---
name: member-vps-to-local-migration
description: Migrate one OpenClaw Telegram member from its Docker VPS to the owner’s Windows, macOS, or Linux computer, preserving selected workspace/config data while preventing duplicate polling and protecting secrets.
---

# Member VPS → Local Migration

Use this skill when an existing member bot must move from
`user-<member>` on the VPS to the member’s own computer. This is a one-member
operation. Do not touch other member containers, the primary VPS runtime, or
another Telegram bot account.

Read the VPS operating instructions and production checklist before changes:

- `/root/_Second_AI_Brain/START_HERE.md`
- `/root/_Second_AI_Brain/01_Ban_Do_VPS.md`
- `/root/_Second_AI_Brain/02_Danh_Sach_Project.md`
- `/root/_Second_AI_Brain/checklists/truoc_khi_sua_production.md`
- this skill’s [request template](references/request-template.md)

## Non-negotiable safety rules

- One Telegram bot token may have only one active polling Gateway. Stop the VPS
  Gateway before starting local polling; otherwise expect `409 Conflict`.
- Keep the old VPS container and data stopped for rollback. Do not delete them
  during the first migration.
- Never print, commit, paste, or put bot tokens, provider keys, passwords,
  cookies, or private keys in the export prompt, shell history, logs, or chat.
- Use a root-only export and encrypted/secure transfer when the bundle contains
  `openclaw.json` or token env files.
- Preserve the member’s own account ID, group IDs, bindings, owners, and
  assistant identity. Never inherit these from another member.
- Do not claim migration complete until a fresh authorized Telegram test is
  received by the local Gateway and a matching reply is observed.

## Decide what to migrate

Ask whether the member wants:

1. **Operational migration:** config, Telegram/provider secrets, identity,
   workspace skills/rules, and selected memory. Exclude old chat/session DBs,
   caches, temporary media, and stale lock files. This is the recommended mode
   for a new local machine.
2. **Full state migration:** also preserve sessions/state databases. Use only
   when the local OpenClaw version exactly matches the VPS version and the owner
   explicitly needs old conversations. Back up SQLite with its matching
   `-wal`/`-shm`; never copy a live database while Gateway writers are active.

If the choice is unclear, stop before exporting and recommend operational
migration.

## Resolve the source member

On the VPS, resolve exact values; do not infer them from a bot username:

```bash
MEMBER=<member>
CONTAINER="user-${MEMBER}"
DATA="/root/Apps/member_vps/docker-users/data/${MEMBER}"
docker inspect "$CONTAINER" --format '{{json .Mounts}}'
docker ps --filter "name=^/${CONTAINER}$" --format '{{.Names}} {{.Status}}'
```

Confirm the persistent root is `$DATA/root`, the OpenClaw root is
`$DATA/root/.openclaw`, and the target account/binding in `openclaw.json` is
`$MEMBER`. Back up the source config and any state selected for migration under
`/root/_Backups/member-vps-to-local/<member>/<UTC-stamp>/`.

## Source freeze and export

Stop only the target member Gateway and confirm it is stopped:

```bash
docker exec "$CONTAINER" supervisorctl stop openclaw-gateway
docker exec "$CONTAINER" supervisorctl status
```

Stage an export in the member’s home, owned by the member and mode `600`, so it
can be downloaded through the member’s SSH port. Include only the selected
paths. For operational migration, include at minimum:

- `.openclaw/openclaw.json`
- `.openclaw/token-codex.env` (protect this file; it contains secrets)
- `.openclaw/workspace/` and its skills/rules
- explicitly requested identity/memory files

Exclude `sessions/`, runtime SQLite files, `*.sqlite-wal`, `*.sqlite-shm`,
`cache/`, `tmp/`, lock files, uploads, and generated media unless the owner
explicitly selected full-state migration. Use `tar` only after checking the
paths and never archive another member’s directory.

Transfer the bundle with `scp`/SFTP over the member SSH port. Verify checksum
and archive contents without printing file contents. Remove the staged archive
from the VPS only after local verification; retain the VPS data and a rollback
backup.

## Prepare the local computer

Identify the local OS before installing:

- Windows: PowerShell as Administrator; use the owner’s local OpenClaw root.
- macOS: use the owner’s local account and its OpenClaw root.
- Linux: use the owner’s local account, not an unrelated root runtime.

Install the same OpenClaw major/minor version as the VPS when possible, plus
Node.js and any required Python/FFmpeg tools. Initialize a local Gateway bound
to loopback. Do not expose the dashboard publicly or reuse a VPS gateway token.

Extract into the local OpenClaw root, restore ownership to the local user, and
set secret files to user-only permissions. Review and adjust only local paths;
preserve the Telegram account ID and binding as `$MEMBER`. If the local version
differs, do not restore old SQLite state; use operational migration.

Run:

```text
openclaw config validate
openclaw skills check
openclaw agents list --bindings
openclaw channels status --channel telegram --probe --json
```

The binding must select the member account, the group key must resolve, and no
old sample account may remain. If unmentioned group messages are required,
report Telegram BotFather Privacy Mode and have the owner disable it for this
bot when appropriate.

## Cutover and rollback

Start the local Gateway only after the VPS Gateway is confirmed stopped. Ask an
authorized owner to send one fresh DM and one fresh group message. Check the
local log for the matching inbound/outbound event without exposing message
text.

If local validation fails, stop the local Gateway and start only the original
VPS Gateway. Do not change other members. Keep the backup until the owner has
accepted local operation for an agreed period.

After acceptance, the owner may remove the local transfer archive and revoke or
rotate credentials according to policy. Do not automatically delete the VPS
member; leave it stopped unless the owner explicitly requests decommissioning.

## Completion report

Report source member/container, local OS, migration mode, validation results,
cutover time, rollback location, and any remaining privacy/proxy limitation.
Never report secrets or private message contents. Append a secret-free change
entry to `/root/_Second_AI_Brain/06_Nhat_Ky_Thay_Doi.md` for VPS-side work.
