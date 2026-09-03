---
name: sync-openclaw-owner-training
description: Synchronize the policy that lets verified OpenClaw owners teach an assistant from Telegram or Zalo DM and group conversations, saving safe reusable summaries in that VPS's canonical workspace and memory. Use when deploying or updating an OpenClaw VPS, adding owner-training behavior, or auditing whether owner instructions are accepted without creating per-owner agents/workspaces.
---

# Sync OpenClaw Owner Training

Apply this as a workspace policy, not as a second agent or a second memory store. Each bot/account keeps its existing canonical agent and workspace; owner identities are permissions on that agent.

## Policy

Install the managed block in the canonical workspace `AGENTS.md`. It makes the assistant:

- accept clear, reusable operational guidance from verified owners in DM and in any group message already delivered by the current channel/group policy;
- summarize non-sensitive guidance in `memory/YYYY-MM-DD.md`, and promote durable rules to `MEMORY.md`, `AGENTS.md`, or a relevant skill only after review;
- keep owner-private information separate from shared workspace notes and never copy raw DM/group transcripts;
- refuse to store passwords, API keys, tokens, cookies, OTPs, payment data, session secrets, or unnecessary personal data;
- ask before applying conflicting, risky, ambiguous, or privilege-changing instructions, and follow the configured Skill Workshop approval policy.

The block does not grant channel access. Before applying it, synchronize exact owner identities through `cap-quyen-telegram-admin-openclaw` or `openclaw-zalouser-owner-access`. Read the target VPS's existing allowlist first; for another VPS, never copy IDs from this VPS. Never use a wildcard owner.

Preserve current routing and mention/reply behavior. “Group training enabled” means an owner can train when the group message reaches the canonical agent; it does not silently open unknown groups or remove mention requirements. If the owner explicitly requests no-mention group behavior, handle that as a separate group-policy change with its own backup and verification.

## Workflow

1. Identify the target VPS, runtime OpenClaw root, canonical agent, and workspace from its active config. Read the target project note, nearest `AGENTS.md`, and production checklist.
2. Inventory existing Telegram/Zalo owner allowlists and approvals. For a new VPS, use only owners verified for that VPS or supplied in the deployment request. Keep one canonical agent/workspace per bot/account.
3. Run the policy script in dry-run mode. It only edits the workspace `AGENTS.md`; it reports owner counts, does not print IDs, and does not change OpenClaw config.
4. Back up `AGENTS.md` under `/root/_Backups` and apply the managed block. Do not overwrite unrelated workspace instructions.
5. If owner permissions are incomplete, use the relevant owner-access skill separately. Review its dry-run before applying; do not change tokens, providers, sessions, or credentials.
6. Run config validation, `openclaw skills check`, and the policy script `--check`. Restart only the intended Gateway when a config change was actually made. Do not send automated test messages; ask an owner to test DM and group behavior.
7. Record the target workspace, backup, validation result, and any unresolved VPS targets in `/root/_Second_AI_Brain/06_Nhat_Ky_Thay_Doi.md` without IDs or secrets.

## Script

Resolve the canonical workspace from the active config:

```bash
python3 scripts/sync_owner_training_policy.py \
  --openclaw-root /root/.openclaw \
  --dry-run
```

Use an explicit workspace when the runtime is inside a member container or the config cannot be read from the host:

```bash
python3 scripts/sync_owner_training_policy.py \
  --workspace /root/Apps/member_vps/docker-users/data/<member>/root/.openclaw/workspace \
  --openclaw-root /root/Apps/member_vps/docker-users/data/<member>/root/.openclaw \
  --backup-dir /root/_Backups/sync-openclaw-owner-training/<member>/<timestamp> \
  --apply
```

Check without writing:

```bash
python3 scripts/sync_owner_training_policy.py \
  --openclaw-root /root/.openclaw \
  --check
```

The apply command is idempotent. It creates a root-owned private backup directory, preserves the file mode/owner, writes atomically, and refuses symlinked config or workspace files. It never edits `openclaw.json`, `exec-approvals.json`, credentials, sessions, or memory content.

## Verification and rollback

- Confirm the owner-access skill's exact identities are present at the target channel/account and approval layers; this skill only installs the behavioral policy.
- Confirm `openclaw config validate` and `openclaw skills check` pass for the target runtime.
- Confirm the canonical account-level binding still routes DM and groups to the intended agent/workspace.
- For rollback, stop/quiesce only the intended Gateway if needed, restore the backed-up `AGENTS.md` after checking it belongs to this transaction, validate again, and keep the backup until the owner confirms stability.
- Never claim another VPS was synchronized without evidence from that VPS.

## Related skills

- `member-workspace-training-knowledge`: retrieve approved training documents; it does not replace owner-message policy.
- `cap-quyen-telegram-admin-openclaw`: synchronize Telegram owner permissions.
- `openclaw-zalouser-owner-access`: synchronize Telegram/Zalo co-owner permissions and Zalo group access when explicitly requested.
- `unify-openclaw-bot-workspace`: repair one-account/one-agent/one-workspace routing before owner policy changes.
