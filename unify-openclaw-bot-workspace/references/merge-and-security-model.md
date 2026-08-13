# Merge And Security Model

## Invariant

- Route one Telegram `accountId` to exactly one OpenClaw agent.
- Give that agent exactly one workspace and one agent state directory.
- Route both direct messages and groups through the account-level binding.
- Treat owners as full-permission senders on that same agent; never model an owner as an agent or workspace.
- Give a second bot/account its own agent, workspace, and agent state directory.
- Keep DM and group session keys separate. Shared workspace means shared approved files and memory, not a shared raw transcript.

## Workspace Merge

- Keep the target workspace canonical.
- Copy source-only files at the same relative path.
- Skip byte-identical files.
- Put same-path, different-content files under `_merged_from/<source>/<timestamp>/`.
- Put conflicting Markdown memory files in `memory/merged-from-...md` so they remain searchable without overwriting the target note.
- Import root control files under `_merged_from/<source>/<timestamp>/control/` instead of replacing `AGENTS.md`, `IDENTITY.md`, `USER.md`, `SOUL.md`, `TOOLS.md`, `HEARTBEAT.md`, `BOOTSTRAP.md`, or `openclaw-workspace-state.json`.
- Never merge agent SQLite, auth profiles, `models.json`, `sessions.json`, raw JSONL transcripts, WAL, or SHM files. Retire the entire source agent state into the root-only transaction backup.
- Reject source symlinks and path escapes. Keep existing target symlinks untouched.

## Owner Model

Use numeric Telegram entries in `commands.ownerAllowFrom` as the canonical owner set. Synchronize all owners into channel/account `allowFrom`, Telegram exec approvers, plugin approval targets, elevated allowlists, and exact per-sender policy keys.

Keep the target agent at `tools.profile: full`, but configure guarded exec and sender policy:

```json
{
  "exec": {
    "host": "gateway",
    "mode": "auto",
    "strictInlineEval": true
  },
  "toolsBySender": {
    "channel:telegram:<OWNER_ID>": {},
    "*": {
      "deny": [
        "group:runtime",
        "group:fs",
        "group:memory",
        "group:ui",
        "group:automation",
        "group:messaging",
        "group:nodes",
        "group:agents",
        "group:plugins",
        "sessions_list",
        "sessions_history",
        "sessions_send",
        "sessions_spawn",
        "sessions_yield",
        "subagents",
        "skill_workshop"
      ]
    }
  }
}
```

Exact sender matches take precedence over the wildcard. An empty exact policy leaves the owner's full profile intact; the wildcard removes administrative and host-changing tools for everyone else.

Also set `tools.fs.workspaceOnly: true`. This keeps normal filesystem tools inside the shared workspace. It does not make `exec` read-only, which is why non-owners must lose `group:runtime`.

## Exec Approvals

- Use host approval policy `security=allowlist`, `ask=on-miss`, `askFallback=deny`.
- Do not automatically transfer source-agent `allow-always` entries to the shared target agent. Archive them and let owners approve commands again.
- Never print the approval socket token or secret-bearing config.

## Transaction And Rollback

Apply only while the Gateway is stopped or quiesced. Store the transaction outside member persistent data, normally under `/root/_Backups/openclaw-bot-workspace/<account>/<timestamp>/`.

The transaction contains pre-change config/approvals, retired source workspace and state, and a checksum manifest. Rollback deletes an imported file only when its checksum still matches; otherwise it moves the changed file to `rollback-conflicts`.

Validate the transformed config against the installed OpenClaw schema before apply. Do not write undocumented channel fields such as `channels.telegram.commands.enforceOwnerForCommands`; owner command authorization derives from `commands.ownerAllowFrom` on current OpenClaw versions.

Rollback must accept only a root-owned private manifest inside its own transaction, constrain all paths to the recorded OpenClaw root/transaction/workspace, verify before/after checksums, and refuse to overwrite config changed after migration.

## Validation

1. Run the script `--check`.
2. Source provider environment privately and run `openclaw config validate`.
3. Confirm `openclaw agents list --bindings` shows one account-level binding for the bot.
4. Restart only the Gateway process manager, then run `openclaw channels status --probe`.
5. Inspect `openclaw approvals get` and confirm target exec is allowlist/on-miss/deny.
6. Run `openclaw security audit --json`; its multi-user heuristic may not understand per-sender policy.
7. Test an owner in DM and group with read-only commands. Test a non-owner group sender and confirm administrative tools are absent.
8. Do not send real messages during automated validation.

## Privacy Boundary

A shared workspace cannot provide the same file isolation as two workspaces. Preserve group privacy instructions in `AGENTS.md`, do not import raw DM transcripts, and keep infrastructure/private operator memory out of group-visible daily notes.
