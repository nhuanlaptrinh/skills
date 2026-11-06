---
name: Delegate VPS work to Codex CLI
description: >-
  Use when the user asks for server work prefixed with "codex:" (or asks to use
  Codex on a VPS) so the heavy reading/editing runs in the server's own Codex
  CLI instead of the assistant.
---
# Delegate VPS work to Codex CLI

Goal: the server's Codex CLI does the investigation and edits; the assistant only relays the request, checks the result, and reports back in the user's language.

## Steps
1. Acknowledge the request in one sentence.
2. Pick the mode:
   - Check / diagnose only: `codex exec --skip-git-repo-check -s read-only -C <project dir>`. Note: read-only sandbox can block systemd/DBus; if that matters, use the fix mode but tell Codex not to change anything.
   - Fix / change (user asked for a change): `codex exec --skip-git-repo-check --dangerously-bypass-approvals-and-sandbox -C <project dir>`.
3. Run it over SSH in one call, writing the final answer to a file: `-o /tmp/codex-last-<ts>.txt`, full log to `/tmp/codex-run-<ts>.log`. Use a timeout (5-12 min; long jobs in background with block_until_ms 0).
4. Always prepend these rules to the prompt given to Codex:
   - Answer in the user's language, short, with evidence (commands run, files changed, backups made).
   - Back up every file before editing (`<file>.bak-<timestamp>`).
   - Never delete data, never post/publish/send messages, never bypass human approval gates, never disable bots or timers, never restart services, never print secrets/tokens — unless the user explicitly asked for exactly that action in this request.
   - If a risky step is needed, stop and describe it instead of doing it.
5. Read only the final-answer file (and grep the log for errors). Don't re-do Codex's work yourself; spot-check one key claim if cheap.
6. Report to the user: result, what changed, backups, anything needing their decision. Ask before any risky follow-up.
7. If Codex fails (auth, quota, timeout), say so plainly and offer to do it directly instead.
