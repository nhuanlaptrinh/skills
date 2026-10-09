---
name: member-vps-install-new
description: Provision a new Docker OpenClaw member VPS from a clean template, configure its own Telegram/9Router identity, and verify group readiness without changing existing member VPSs.
---

# Member VPS Install New

Use this skill when creating a new member from a release under
`/root/Apps/member_vps/template-releases/`. The operation is scoped to one new
member container and its data directory. Never reuse another member's volume,
session database, workspace credentials, Telegram account, or API keys.

## Required preparation

Before changing anything, read:

- `/root/_Second_AI_Brain/START_HERE.md`
- `/root/_Second_AI_Brain/01_Ban_Do_VPS.md`
- `/root/_Second_AI_Brain/02_Danh_Sach_Project.md`
- `/root/_Second_AI_Brain/checklists/truoc_khi_sua_production.md`
- this project's `AGENTS.md`, when present

Use the clean release archive and confirm checksums. Resolve the requested
member name, SSH/web ports, owner Telegram IDs, group ID, assistant name, and
secret sources before applying. Do not put tokens or passwords in skill text,
argv, logs, chat output, or generated documentation.

## Isolation checks

Set shell-local values (never commit them):

```bash
MEMBER=<new_member>
RELEASE=/root/Apps/member_vps/template-releases/<release>
SSH_PORT=<unused_port>
WEB_PORT=<unused_port>
CONTAINER="user-${MEMBER}"
DATA="/root/Apps/member_vps/docker-users/data/${MEMBER}"
```

Before apply, verify:

- `docker ps -a` has no `$CONTAINER`.
- `$DATA` does not contain an existing member volume.
- `$SSH_PORT` and `$WEB_PORT` are unused.
- Existing member containers remain running and are not selected by commands.

Run checksum verification and a dry-run first. If the release wrapper refers to
a missing `docker/install.sh`, use the maintained installer at
`/root/Apps/member_vps/vps-template-v2/install.sh` with `--release-dir "$RELEASE"`;
do not modify existing containers to work around a packaging mismatch.

## Provisioning sequence

1. Create only the new container from the release archive, initially without
   secrets. Use unique SSH/web ports and the target member name.
2. Set the requested SSH password through a root-only temporary file piped to
   `chpasswd`; remove the file immediately. Never pass the password as a
   visible command argument or print it.
3. Keep the member's root/home mounts under `$DATA` and mode `700`.
4. Configure a fresh member-specific OpenClaw config. If the archive has no
   `openclaw.json`, create it from the installed schema or a sanitized schema
   template; never copy another member's credential-bearing config.
5. Store provider/Telegram secrets only in mode-`600` files owned by root. If
   a helper accepts only secret argv, prefer a reviewed post-install script
   that reads root-only files instead of exposing secrets in process listings.

The config must contain the following member-specific invariants:

- Telegram account ID is exactly `$MEMBER`; no stale account ID from a sample.
- `channels.telegram.defaultAccount` is `$MEMBER`.
- Every Telegram binding for the new agent has `match.accountId: $MEMBER`.
- `channels.telegram.accounts[$MEMBER]` has the new bot token, owner allowlist,
  group allowlist, and the requested group key.
- The target group uses `requireMention: false` only when unmentioned replies
  are explicitly wanted; configure sender allowlists with positive Telegram
  user IDs, never the negative group ID.
- Agent identity uses the requested assistant name and Full Exec settings only
  when explicitly requested.
- The provider key belongs to this member and is not copied from another
  member.

## Supervisor and state compatibility

The image must start Supervisor and have an `openclaw-gateway` program that
loads the member's env file. If the image entrypoint only runs `tail -f` or the
Supervisor config is missing, fix the template source and apply the reviewed
entrypoint/config to the new container; do not restart other members.

If the release contains SQLite state newer than the installed OpenClaw build,
back up the affected SQLite file plus matching `-wal`/`-shm` files under a
member-local backup directory, then move the stale template state aside so the
new member can initialize compatible state. Do not delete it, touch another
member's state, or reset a live production database blindly.

## Validation gate

Do not report completion until all applicable checks pass for the target only:

```bash
docker exec "$CONTAINER" openclaw config validate
docker exec "$CONTAINER" supervisorctl status
docker exec "$CONTAINER" openclaw agents list --bindings
docker exec "$CONTAINER" openclaw channels status --channel telegram --probe --json
docker ps --filter "name=$CONTAINER"
ss -ltnH | grep -E ":${SSH_PORT}$|:${WEB_PORT}$"
```

Redact tokens and message text from logs. Confirm the channel account is
`$MEMBER`, the binding matches it, the group audit resolves the intended group,
and no `409 Conflict`, provider timeout, session-lock, or send failure appears.
Do not send an automated Telegram test. Ask an authorized owner to send a new
group message; distinguish “channel connected” from “fresh group reply
confirmed”.

Telegram BotFather Privacy Mode is external to OpenClaw. If unmentioned group
messages are required and probe reports `can_read_all_group_messages=false`,
have the owner run `/setprivacy -> Disable` for this bot, then reload the target
gateway. A bot being administrator is useful evidence but does not remove the
need to report the privacy-mode limitation.

## Rollback and records

Before production edits, back up the new member config under
`/root/_Backups/openclaw-telegram-group-recovery/<member>/<UTC-stamp>/`. On
failure, restore only files changed for this member and restart only its
gateway. Never recreate or delete the container as a first response.

After a material change, append a secret-free entry to
`/root/_Second_AI_Brain/06_Nhat_Ky_Thay_Doi.md` describing the member, ports,
validation results, and any remaining BotFather/privacy limitation.
