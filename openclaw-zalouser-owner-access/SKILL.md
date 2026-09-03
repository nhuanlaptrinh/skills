---
name: openclaw-zalouser-owner-access
description: Synchronize verified Telegram and Zalo Personal co-owner access for an existing OpenClaw member bot, including DM allowlists, owner commands, elevated tools, default approval authority for Skill Workshop and system-agent proposals, Telegram exec/plugin approvals, exact sender policies, and open Zalo groups without mention. Use when connecting OpenClaw to a Zalo user, adding a cross-channel owner, granting approval authority, or repairing incomplete owner permissions while preserving existing owners and safeguards.
---

# OpenClaw Zalo User Owner Access

Use this skill when a member OpenClaw bot must recognize verified identities on
Telegram and/or Zalo Personal as co-owners. It updates only owner/policy fields;
it does not change tokens, providers, models, credentials, sessions, or QR data.

## Required owner layers

- Telegram: channel and account `allowFrom`, `commands.ownerAllowFrom` as
  `telegram:<id>`, `tools.elevated.allowFrom.telegram`, both top-level and
  account-level `channels.telegram.execApprovals.approvers`, the account-specific
  `approvals.exec.targets` and `approvals.plugin.targets` entries, enable plugin
  approval forwarding with `mode=targets`, and
  `toolsBySender["channel:telegram:<id>"] = {}`.
- Zalo Personal: channel `allowFrom`, `commands.ownerAllowFrom` as
  `zalouser:<id>`, `tools.elevated.allowFrom.zalouser`, and
  `toolsBySender["channel:zalouser:<id>"] = {}`. If the plugin has account-level
  Zalo allowlists, synchronize that account too.
- When an existing Telegram/Zalo account or group has an explicit sender
  allowlist, add the verified owner to that existing list; never create a new
  group entry or replace `*`.
- Keep the canonical `main` agent on `tools.profile: full` and its existing full
  Gateway Exec policy. Keep the wildcard non-owner deny safeguards, at least
  `group:runtime`, `group:fs`, and `group:messaging`.
- Preserve the existing Zalo group policy by default. Only when the request
  explicitly asks to open all Zalo groups without mention, set `groupPolicy:
  open`, retain `groupAllowFrom: ["*"]`, enable `groups["*"]`, and set
  `requireMention: false` with `--open-zalo-groups`.

Every verified exact owner synchronized into these layers is approval-authorized
by default for Skill Workshop lifecycle proposals and persistent `system-agent`
configuration proposals on the canonical agent. This authority requires explicit
approval of each live proposal; it does not set Skill Workshop to auto-apply and
does not bypass queue, source, agent, summary, expiry, or `allow-once` checks.

There is no separate training-approval identity field in the member policy
found so far. Owner command authorization plus the Telegram exec/plugin targets
and the native/bridge `system-agent` route provide the approval authority;
inspect workspace-specific training rules before adding any additional policy.
For memory/workspace behavior, also install `sync-openclaw-owner-training`; do
not treat owner access alone as permission to copy raw conversations into
memory.

When a configuration proposal originates in a Zalo group, the approval bridge
accepts it only if that exact group is explicitly enabled in
`channels.zalouser.groups`; for the current non-native route, approval must
still be sent by an exact Telegram owner in a direct DM. This transport rule
does not remove the default approval authority of verified owners; it prevents
Zalo group participants or non-owner senders from approving.

## Preconditions and safety

1. Read the Second AI Brain runbook, the member project note, nearest
   `AGENTS.md`, and the production checklist.
2. Resolve the host OpenClaw root, container, runtime HOME, Telegram account,
   Zalo account, and canonical `main` agent. Never guess an account when more
   than one is enabled.
3. Back up `openclaw.json` (and `exec-approvals.json` when Telegram owner
   tooling is changed) under `/root/_Backups` with mode `0700/0600`.
4. Quiesce only the existing Gateway process before applying production policy;
   preserve its Supervisor/tmux manager and respawn the same process entry.
5. Never put real IDs, tokens, cookies, QR payloads, passwords, or private IDs
   in this skill or operational notes. Do not send test messages.

## Workflow

Use the bundled deterministic updater. It validates a candidate with the
installed OpenClaw CLI (use `--container` for a Docker member), writes atomically,
and does not restart the Gateway itself.

Dry-run:

```bash
python3 scripts/update_owner_access.py \
  --openclaw-root /root/Apps/member_vps/docker-users/data/<member>/.openclaw \
  --telegram-account-id <telegram_account> \
  --telegram-id <telegram_user_id> \
  --zalo-id <zalo_user_id> \
  --container user-<member> \
  --runtime-home /home/<member> \
  --runtime-openclaw-root /home/<member>/.openclaw \
  --dry-run
```

The dry-run preserves existing Zalo group/mention behavior. Add
`--open-zalo-groups` only for an explicit request to open all Zalo groups and
disable mention requirements; this is a separate policy decision.

Apply only after reviewing the dry-run and quiescing the Gateway:

```bash
python3 scripts/update_owner_access.py \
  --openclaw-root /root/Apps/member_vps/docker-users/data/<member>/.openclaw \
  --telegram-account-id <telegram_account> \
  --telegram-id <telegram_user_id> \
  --zalo-id <zalo_user_id> \
  --container user-<member> \
  --runtime-home /home/<member> \
  --runtime-openclaw-root /home/<member>/.openclaw \
  --backup-dir /root/_Backups/openclaw-zalouser-owner-access/<member>/<timestamp> \
  --apply
```

Append `--open-zalo-groups` only when the request explicitly asks to open all
Zalo groups without mention.

Run `--check` with the same identity/account arguments after the Gateway is
running. Rerunning `--apply` is idempotent and preserves unrelated owners,
groups, plugin targets, and deny rules. The updater reports counts and generic
change names only; it never prints the supplied IDs.

## Verification

Run all relevant checks with the member runtime HOME:

```bash
docker exec -e HOME=/home/<member> user-<member> openclaw config validate
docker exec -e HOME=/home/<member> user-<member> openclaw plugins doctor
docker exec -e HOME=/home/<member> user-<member> openclaw channels status --probe
python3 scripts/update_owner_access.py ... --check
```

Confirm one account-level binding to `main`, Telegram and Zalo are
`configured/running/connected/works`, and the Gateway has exactly one live
process under its intended manager. Inspect owner/elevated/approval counts and
exact sender keys without printing credential-bearing config. Ask the owner to
perform any real command test; do not send messages automatically.

## Rollback

Stop/quiesce the same Gateway, verify the backup belongs to this operation and
that the live config has not changed unexpectedly, then restore only the backed
up `openclaw.json` with mode/owner preserved. Validate the restored candidate,
respawn the original Gateway entry, and rerun the checks. Keep the backup until
the member confirms stability; never delete credentials or session data.

## Resource

- `scripts/update_owner_access.py`: dry-run/apply/check updater for Telegram and
  Zalo owner policy.
