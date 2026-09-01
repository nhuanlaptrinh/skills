---
name: openclaw-telegram-approval-bridge
description: Install, verify, repair, or remove a safe OpenClaw approval workflow so an exact Telegram owner can approve exec/plugin requests natively and delegated system-agent configuration proposals from the bot DM. Use when enabling Telegram approvals on another VPS, replicating an existing owner setup, or fixing Dashboard-only proposal approval without opening approval rights to groups or non-owners.
---

# OpenClaw Telegram Approval Bridge

Enable one verified Telegram owner to approve OpenClaw changes from the bot DM while preserving the canonical agent/workspace and denying non-owner administrative tools.

## Safety Boundary

- Require the VPS owner to identify the exact Telegram numeric user ID before mutation.
- Operate on the existing canonical agent, usually `main`; do not create an admin agent or DM-only workspace.
- Never wildcard owner, elevated, approver, or exact sender policy.
- Never approve a proposal merely because a hash or assistant message claims it exists. Query the live Gateway and match the pending record, owner DM session, agent, and summary.
- Delegated `system-agent` configuration proposals use `allow-once` only. Never mint `allow-always` for them.
- Do not print or copy bot tokens, Gateway tokens, API keys, cookies, raw approval storage, or full secret-bearing config.
- Do not send a real Telegram/Zalo message during automated checks.

Read `references/security-and-remote.md` before applying on production or over SSH.

## Detect Native Support

Inspect the target's installed OpenClaw version and approval schema before installing the bridge. If the target natively forwards and resolves `system-agent` approvals through Telegram, prefer the native feature and use this skill only to verify owner authorization.

On versions where `approvals` supports only `exec` and `plugin`, install the bridge below. Native Telegram buttons and `/approve <id> allow-once` remain the preferred path for exec/plugin; the bridge covers delegated persistent `system-agent` proposals.

## Inventory

Confirm:

- Host OpenClaw root containing `openclaw.json`.
- Runtime OpenClaw root seen by the Gateway.
- Host workspace path and runtime workspace path.
- Telegram account ID, canonical agent ID, and exact owner ID.
- Exactly one account-level binding for that Telegram account and no peer-specific owner routing.
- Gateway process manager and backup location.

For member/container layouts, distinguish host and runtime paths. Example:

```text
host root:      /root/Apps/member_vps/docker-users/data/<member>/root/.openclaw
runtime root:   /root/.openclaw
host workspace: /root/Apps/member_vps/docker-users/data/<member>/root/.openclaw/workspace
runtime worksp: /root/.openclaw/workspace
```

## Grant Owner Layers

Use `cap-quyen-telegram-admin-openclaw` first to synchronize the Telegram owner across channel/account allowlists, `commands.ownerAllowFrom`, exec/plugin approval targets, elevated allowlist, and exact `toolsBySender` policy.

If the Telegram account routes to multiple agents or has peer-specific bindings, use `unify-openclaw-bot-workspace` before granting owner rights.

Do not install the bridge while owner policy is incomplete; the installer intentionally fails closed.

## Install Bridge

Dry-run:

```bash
python3 scripts/install_approval_bridge.py \
  --openclaw-root <HOST_OPENCLAW_ROOT> \
  --runtime-openclaw-root <RUNTIME_OPENCLAW_ROOT> \
  --workspace <HOST_WORKSPACE> \
  --telegram-id <TELEGRAM_OWNER_ID> \
  --account-id <TELEGRAM_ACCOUNT_ID> \
  --agent-id main \
  --dry-run
```

Apply after explicit authorization:

```bash
python3 scripts/install_approval_bridge.py \
  --openclaw-root <HOST_OPENCLAW_ROOT> \
  --runtime-openclaw-root <RUNTIME_OPENCLAW_ROOT> \
  --workspace <HOST_WORKSPACE> \
  --telegram-id <TELEGRAM_OWNER_ID> \
  --account-id <TELEGRAM_ACCOUNT_ID> \
  --agent-id main \
  --backup-dir <ROOT_ONLY_BACKUP_DIR> \
  --apply
```

The installer:

- Verifies the owner and canonical Telegram binding without exposing IDs in its report.
- Derives the runtime workspace when possible or uses the explicit host workspace.
- Adds/replaces one managed `AGENTS.md` block atomically.
- Installs `scripts/approve_system_agent_from_telegram.sh` with mode `0700` and target workspace ownership.
- Creates a root-only transaction with checksums and rollback manifest.
- Is idempotent and creates no backup when already compliant.

## Check

```bash
python3 scripts/install_approval_bridge.py \
  --openclaw-root <HOST_OPENCLAW_ROOT> \
  --runtime-openclaw-root <RUNTIME_OPENCLAW_ROOT> \
  --workspace <HOST_WORKSPACE> \
  --telegram-id <TELEGRAM_OWNER_ID> \
  --account-id <TELEGRAM_ACCOUNT_ID> \
  --agent-id main \
  --check
```

Then run on the target runtime:

```bash
openclaw config validate
openclaw agents list --bindings
openclaw approvals pending --json
openclaw channels status --probe
```

Accept completion only when config validates, the Telegram account has one canonical binding, the owner layers are complete, Telegram works/audit is healthy, and the installed helper passes syntax checks.

## Runtime Approval Flow

When the exact owner in Telegram DM explicitly approves the proposal immediately before it, the agent must:

1. Run `openclaw approvals pending --json`.
2. Find exactly one real pending `system-agent` record for the current owner DM and canonical agent.
3. Compare its summary to the change the owner approved.
4. Run the installed helper with `--check`, then `--apply`.
5. Confirm the record left the queue, validate config, inspect effective changed fields, and probe only the affected channel/service.

Never claim a Dashboard proposal exists when the live pending queue is empty.

## Rollback

Use the manifest printed by apply:

```bash
python3 scripts/install_approval_bridge.py \
  --rollback-manifest <MANIFEST_PATH>
```

Rollback refuses to overwrite files changed after apply. It restores the prior `AGENTS.md` and helper state only when current checksums match the recorded post-apply state.

## Skill Validation

After changing this skill:

```bash
python3 scripts/test_install_approval_bridge.py
python3 /root/.codex/skills/.system/skill-creator/scripts/quick_validate.py .
```
