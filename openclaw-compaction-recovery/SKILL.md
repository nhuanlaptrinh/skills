---
name: openclaw-compaction-recovery
description: Chẩn đoán, phòng tái phát và sửa lỗi OpenClaw auto-compaction timeout, context overflow hoặc lịch sử tool quá lớn trên Linux host và member Docker. Dùng khi bot báo Auto-compaction could not recover this turn, Compaction timed out hoặc lỗi lặp lại sau /new; có audit, backup và rollback, không đổi credential/model/routing.
---

# OpenClaw Compaction Recovery

Use this skill when an OpenClaw agent reports `Auto-compaction could not recover this turn`, `Context overflow`, `Compaction timed out`, or repeatedly becomes blocked after `/new`.

## Scope

- The helper needs Linux, Python 3.9+ standard library, and access to the selected OpenClaw CLI or Docker container. No model usage occurs during config audit/validation; session recovery is a separate authorized operation.
- Treat the runtime configuration and gateway log as the source of truth. Do not infer a Telegram credential failure from a compaction error.
- Support the host runtime at `/root/AI_Runtime/openclaw/.openclaw` and Docker member data at `/root/Apps/member_vps/docker-users/data/<member>/.openclaw`.
- Audit only the requested targets. `--all-members` is read-only; an authorized fleet rollout applies targets sequentially, each with its own reviewed hash and backup.
- The helper changes installation-wide `agents.defaults.compaction`, not a per-agent override. Check every inheriting agent and fallback; a small/unknown model blocks the automatic baseline. It supports strict JSON on Linux; other layouts require native/manual handling.
- Do not change model/provider, API keys, Telegram tokens, owner/approval policy, bindings, workspace path, `.env`, media, or project files.
- Do not delete or manually rewrite JSONL transcripts. Preserve old sessions and use semantic compaction through the running Gateway.

## Required preflight

Before touching production, read:

1. `/root/_Second_AI_Brain/START_HERE.md`
2. `/root/_Second_AI_Brain/01_Ban_Do_VPS.md`
3. `/root/_Second_AI_Brain/02_Danh_Sach_Project.md`
4. The applicable project note under `/root/_Second_AI_Brain/projects/`
5. `/root/_Second_AI_Brain/checklists/truoc_khi_sua_production.md`
6. Any closer `AGENTS.md` that scopes the target config or workspace

## Workflow

### 1. Audit first

Run the bundled helper without mutation:

```bash
python3 scripts/audit_openclaw_compaction.py --all-members --audit
```

For one target:

```bash
python3 scripts/audit_openclaw_compaction.py \
  --member nv4_KhoVideoPNVGD --audit
```

The report must include only redacted/safe fields: target, OpenClaw version marker, model ID without credentials, context window, compaction settings, active transcript sizes, and counts of relevant log errors. Never print the full config or raw transcript.

### 2. Decide eligibility

Use [references/runtime-policy.md](references/runtime-policy.md). The automatic baseline requires a configured context cap and known model/fallback windows whose smallest effective budget is at least `80000`, existing safeguard mode, and no custom compaction override. The reference incident used a `96k` cap with a `128k` catalog window. Audit only when these conditions are unknown; do not silently invent a cap for the host main runtime.

For the standard `9rt/gpt-5.6-terra` member profile, the safe baseline is:

- `reserveTokens: 24000`
- `reserveTokensFloor: 24000` or higher
- `keepRecentTokens: 8000`
- `maxHistoryShare: 0.5`
- `recentTurnsPreserve: 2`
- `compaction.timeoutSeconds: 600`
- `qualityGuard.enabled: true`, `qualityGuard.maxRetries: 1`
- Preserve mode, mid-turn guard, memory flush, transcript rotation, and existing byte guards; the helper does not invent missing optional settings

The helper never reduces existing larger reserves/timeouts, increases a smaller history budget, or increases a smaller quality retry count. An excessive reserve is blocked for individual review. `eligible=true` in an offline audit is a capacity/policy check, not proof of version compatibility or gateway health.

The reserve is deliberate headroom, not an increase to the model context window. Do not raise `contextTokens` merely to hide an overflow until the upstream model limit is verified.

### 3. Apply with backup

Only after reviewing the audit:

```bash
python3 scripts/audit_openclaw_compaction.py \
  --member nhanvien1 --audit --validate-candidate \
  --container user-nhanvien1 \
  --runtime-root /home/nhanvien1/.openclaw --json

python3 scripts/audit_openclaw_compaction.py \
  --member nhanvien1 --apply --accept-defaults-scope \
  --expect-sha256 <CONFIG_SHA256_FROM_REVIEWED_AUDIT> \
  --container user-nhanvien1 \
  --runtime-root /home/nhanvien1/.openclaw
```

Inspect Docker mounts before choosing the container and runtime root. The helper verifies host/container config hashes, validates a private temporary candidate using the selected runtime, and only then backs up and writes. It preserves mode/owner, refuses a stale reviewed hash, and automatically restores the original if post-write validation fails and no concurrent writer intervened. A no-op does not rewrite config or create another backup.

`--validate-candidate` creates and removes a private temporary JSON file; ordinary audit creates none. Host/runtime version markers may differ: use `openclaw --version`, active process/service context, and the installed schema. A successful file validation does not prove hot reload; verify the running gateway separately. Never upgrade a package or restart/recreate a container just to make this baseline pass.

### 4. Repair affected sessions

For actual session recovery, read [references/runtime-policy.md](references/runtime-policy.md), identify the exact failed key through the native CLI/log, and back up the agent registry plus referenced transcripts. The helper backs up config only, not conversations. Run native semantic compact only if the installed `sessions compact --help` supports it:

```bash
docker exec -e HOME=/home/<user> <container> \
  openclaw sessions compact 'agent:main:telegram:group:<group-id>' \
  --timeout 660000 --json
```

- Run one compaction at a time per Gateway, after authorization for model usage and after checking no active run owns the session. Keep DM/group content isolated.
- Prefer semantic compaction. Never use `--max-lines` for a production recovery unless the owner explicitly accepts losing summarization quality.
- Do not send real Telegram messages for verification. The public `openclaw agent` CLI defaults to no delivery when `--deliver` is omitted; do not pass the unsupported `--deliver=false` syntax or backend-only `sessionEffects` controls. A smoke prompt should request one marker and forbid resuming work, tools, and external messages; it still appends a small test turn and consumes model usage.
- One repair attempt per session is the default. Retry once only after a diagnosed corrective change; do not repeat unchanged failures or treat three attempts as mandatory. Preserve the backup and report a provider outage/timeouts instead of resetting sessions silently.

### 5. Verify and document

Run `openclaw config validate`, `openclaw health --json`, and `openclaw channels status --probe`. Confirm hot reload/connectivity and no new relevant failures during a stated observation window; channel health fields vary by version. Check unchanged credentials, routing and unrelated sessions. The audit only scans the last 2 MiB of the configured log, filtered to 24 hours; old errors do not prove a current failure and zero matches do not prove health. Document changes in the local operations journal; on this VPS use `/root/_Second_AI_Brain/06_Nhat_Ky_Thay_Doi.md`.

## Recurrence prevention

- After reading scoped instructions and backing up the file, merge the short block in [references/prevention-workspace.md](references/prevention-workspace.md) into each authorized agent workspace. This is an agent instruction, not a hard runtime output limit; the config helper does not modify workspace policy automatically.
- Keep diagnostic tool output bounded; inspect excerpts instead of dumping logs, code trees, binary/media metadata, or session history into the model context.
- For video and media work, pass canonical file paths and small metadata summaries. Do not inline large media or repeated base64/image payloads into multiple turns.
- Split long work into checkpoints and independent sessions. Use `/compact` proactively before a large phase, not only after the runtime is already over budget.
- `contextPruning` is not a universal fix. The installed runtime may gate cache-TTL pruning by provider eligibility; do not enable it blindly for a custom OpenAI-compatible provider.
- An unrelated model catalog warning should be fixed separately and must not be conflated with compaction recovery.
- If a provisioning template recreates the old settings, report it and update it only within the authorized prevention scope, with backup and dry-run. Do not patch arbitrary custom-model templates with an unconditional 24k floor.
- This skill is an on-demand workflow, not a daemon or periodic monitoring service. Do not create cron, deploy to every workspace, change privilege policy, or promise zero recurrence merely because the skill exists.

## Rollback

Use the helper with the exact backup directory and one target:

```bash
python3 scripts/audit_openclaw_compaction.py \
  --member <member> --rollback \
  --container <verified-container> --runtime-root <verified-runtime-state-root> \
  --backup-dir /root/_Backups/openclaw-compaction-recovery/<target>/<timestamp>
```

Rollback validates the original candidate and checks target identity plus before/after checksums. It refuses when config changed after apply; review and merge deliberately rather than forcing old data over newer changes. Verify hot reload afterwards. Session backups are separate: never restore a whole live state directory over newer messages.

## Check the skill itself

```bash
PYTHONDONTWRITEBYTECODE=1 python3 scripts/test_compaction_recovery.py -v
```

These offline fixtures exercise apply/rollback, idempotence, stale-hash refusal, candidate-validation failure, multi-agent small-model blocking, and redacted diagnostics without touching production or calling a model.

## Supporting reference

Read [references/runtime-policy.md](references/runtime-policy.md) when selecting targets, interpreting precheck numbers, or diagnosing a provider/model that does not match the standard member profile.
