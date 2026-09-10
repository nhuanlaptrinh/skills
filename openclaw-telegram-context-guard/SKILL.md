---
name: openclaw-telegram-context-guard
description: Diagnose and harden OpenClaw Telegram group sessions that become silent or very slow after large Excel, report, or tool-heavy tasks cause context overflow, compaction timeouts, stalled runs, or queued inbound messages. Use across root and Docker member VPS deployments; do not use for ordinary Telegram routing or offset incidents unless those are the proven cause.
---

# OpenClaw Telegram Context Guard

Use this skill when a Telegram group receives an inbound update but the bot does not produce a timely reply, or logs show `Context overflow`, `compaction`, `stalled session`, `repeated_model_requests_without_progress`, or `Channel ingress ... stalled`.

## Scope and safety

- Resolve the actual container, `OPENCLAW_ROOT`, agent ID, Telegram account ID, workspace, and numeric group ID from configuration. Never infer them from a bot username or group title.
- Before production changes, read `/root/_Second_AI_Brain/START_HERE.md`, the VPS map, project registry, the applicable project note and `AGENTS.md`, plus the production checklist.
- Back up `openclaw.json` before editing. Before session/state mutation, back up the relevant SQLite file and matching `-wal`/`-shm` files under a `0700` directory; never print tokens, credentials, payloads, message text, or private destination data.
- Do not recreate a member container, delete a whole database, delete workspaces, or call Cloud Bot API `getUpdates` while a Gateway is running.
- A real Telegram test or outbound notice requires explicit authorization. A normal user message is preferred.

## Resolve and triage

For Docker members, discover rather than assume:

```bash
CONTAINER="user-<member>"
DATA_DIR="/root/Apps/member_vps/docker-users/data/<member>"
MEMBER_HOME="/home/<member>"
OPENCLAW_ROOT="$DATA_DIR/.openclaw"
docker exec -e HOME="$MEMBER_HOME" "$CONTAINER" openclaw config validate
docker exec -e HOME="$MEMBER_HOME" "$CONTAINER" openclaw agents list --bindings
docker exec -e HOME="$MEMBER_HOME" "$CONTAINER" openclaw channels status --channel telegram --probe --json
docker exec -e HOME="$MEMBER_HOME" "$CONTAINER" openclaw models status --agent <AGENT_ID> --json
```

Inspect only redacted metadata from the Gateway log:

```bash
docker exec "$CONTAINER" sh -lc \
  'grep -E "Inbound message telegram:group:|outbound send ok|Context overflow|compaction|stalled session|Channel ingress|409 Conflict|timeout|sessions_history failed" /tmp/openclaw-supervisor.log | tail -240'
```

Classify the path before changing anything: no inbound (privacy, ID/migration, allowlist, polling or offset); inbound without outbound (routing, active session, context, provider or send error); or media-only failure (use the media-delivery skill). Correlate by account, agent, workspace and group key.

`requireMention: false` cannot override Telegram BotFather Privacy Mode. If the account reports `can_read_all_group_messages=false`, either mention the bot for the test or have the owner run `/setprivacy -> Disable` for that bot.

## Immediate recovery for a proven context stall

Identify the exact session key (`agent:<agentId>:telegram:group:<groupId>`) and current run ID from redacted logs/session metadata. Preserve the state backup before mutation.

1. If a current run ID exists, abort only that run:

   ```bash
   docker exec "$CONTAINER" openclaw gateway call chat.abort \
     --params '{"sessionKey":"agent:<agentId>:telegram:group:<groupId>","runId":"<run-id>","preserveSideRuns":true}' --json
   ```

2. If the Gateway is draining or an active run cannot be aborted, restart only the target Gateway/Supervisor program after the backup. If graceful drain is proven stuck, terminate only that Gateway process and let its existing Supervisor respawn it; never recreate the member container.
3. Once the session is inactive, compact the affected transcript with bounded retention. Prefer 30–60 lines when tool results are large:

   ```bash
   docker exec -e HOME="$MEMBER_HOME" "$CONTAINER" \
     openclaw sessions compact "agent:<agentId>:telegram:group:<groupId>" \
     --max-lines 40 --json
   ```

   Do not delete the session. The transcript and SQLite backup are the rollback record.
4. Validate config, Gateway ownership, account probe and absence of new overflow/stall lines. Do not claim the business task completed until an authorized user sends a fresh test and a matching outbound receipt is observed.

## Apply the reusable long-term guard

Use the audited compaction helper when it exists, and keep the broader settings schema-gated. The helper owns only the compaction policy; it does not rewrite models, routing, tools or credentials:

```bash
GUARD=/root/.agents/skills/openclaw-compaction-recovery/scripts/audit_openclaw_compaction.py
python3 "$GUARD" --member <member> --audit --json
python3 "$GUARD" --member <member> --audit --validate-candidate --json
```

Apply only after reviewing the candidate and its expected checksum, using the helper's documented `--accept-defaults-scope --expect-sha256 ... --apply` flow. If the helper is unavailable, inspect `openclaw config schema --json`, create a timestamped config backup, and apply one reviewed field group at a time with an idempotent config operation. Never assume a field is supported or copy values from another VPS.

For a verified 128k model and finance/stateless agent, a useful candidate is an earlier model-visible cap around 96k, continuation-skip bootstrap limits around 4–6k per file/10–12k total, cache-TTL pruning around 5m, safeguard compaction with 2 recent turns, a bounded timeout, an active transcript byte guard, memory flush, group history around 30, and a daily reset plus a 180-minute idle group rotation. Preserve existing fallbacks, tools, routing and credentials; choose values from the target schema and workload. Validate with `openclaw config validate` and the model/channel probes. Prefer hot reload, and restart only the target Gateway when a session policy is not loaded by hot reload.

## Operational prevention

- Start large workbook/report work with `/new`; process bounded sheets/ranges and row limits.
- Save full intermediate results to a workspace file and send a short summary plus the file receipt; do not paste entire tool outputs into a shared group transcript.
- For `sessions_history`, pass either `offset` or `messageId`, never both.
- Monitor context-pressure diagnostics and alert before prompts approach the configured model budget.
- Keep one coordinator per request and require a real Telegram `messageId`/destination receipt before declaring delivery; retry at most once when delivery is ambiguous.

## Rollback and report

If validation fails, restore only the changed config from the timestamped backup, reload the same Gateway, and re-run validation. Report the resolved member/container, agent/account/group (redacted), proven path failure, backup path, exact guard settings, probe/reload result, and any remaining Privacy Mode or group-ID limitation.

## Bounded Excel/PDF/tool-output workflow

For spreadsheet, PDF, report, or web-tool work in a group:

1. Inspect metadata and headers first. Read sample data rows only when the user's requested processing scope requires them; do not scan the file just to count rows.
2. Run one coordinator script for the request using only the requested columns, ranges, and criteria. Do not spawn a second worker or paste the full workbook, table, JSON, HTML, or base64 into the conversation.
3. Process large inputs in bounded batches (for example 500–1,000 rows) with a checkpoint so a retry resumes from the last completed batch.
4. Save complete results and a compact machine-readable summary to the target workspace `output/` directory.
5. Return only counts, totals, errors, 3–5 representative rows, and the result file path to the group.
6. When estimated prompt usage reaches 70–80% of the model budget, stop reading, checkpoint, and continue in a fresh worker/session.

A group request should follow: identify target range -> sample -> filter/compute in worker -> save artifact -> send short summary. This policy applies to Telegram and Zalo groups.

## Group-light profile (optional, schema-gated)

For groups that repeatedly process spreadsheets/reports, apply only after validating the target model schema:

```text
model contextTokens: 64000 (provider model entry, while contextWindow may remain 128000)
compaction.keepRecentTokens: 4000
compaction.recentTurnsPreserve: 2
compaction.maxActiveTranscriptBytes: 1mb
session.resetByType.group.idleMinutes: 90
group history: 15–20 turns when the channel exposes a history-limit field
tool result: <=4,000 characters per call
```

Keep daily reset enabled. If a history-limit or tool-output field is not supported by the installed schema, enforce it in the workspace AGENTS/worker workflow instead of writing unknown config keys. Validate after every change and prefer hot reload.

## File intake: header-only first (Telegram and Zalo)

When a file arrives in a group, first inspect filename, size/type, available sheet names and headers. Use row/column counts only if cheap metadata already provides them; do not scan all rows for counts or sample data by default. Ask for scope only if the user's existing request does not specify it. Process requested ranges directly or a full analysis in a worker when authorized, returning a bounded summary and artifact path. Reading in a worker still consumes that worker's context if raw outputs are printed: require bounded output and prevent the parent from duplicating the same reads. Applies to Telegram and Zalo.

## Apply a new file policy to a running group

- Compare the active session's `systemPromptReport.generatedAt` and injected AGENTS character count with the current file. A run started before the edit can still hold the old prompt. Put the concise policy near the top of AGENTS and remove superseded duplicate instructions.
- For a healthy active run, prefer supported `chat.send` with `queueMode:"steer"`, exact `sessionKey` and current `sessionId`, `agentId`, short correction, `deliver:false`, and a unique `idempotencyKey`. Recheck activity and steer each still-running child that is reading the file, then the coordinator. Preserve produced artifacts; don't restart/reset a healthy Gateway just to load policy.
- The correction must explicitly stop unrequested deep reads, reuse existing metadata, save a short checkpoint and return only headers/status; do not request full transcript reconstruction. Do not send an additional public notice without existing authorization.
- A `started` acknowledgement is not enough: confirm the correction reached the target transcript and inspect subsequent actions/completion. Steering can become a follow-up if the run ends during admission. Report whether it was injected, queued, or completed.
- Back up state using SQLite online backup for a consistent live snapshot, or stop all writers before copying DB/WAL/SHM. For a separately authorized reset, this version can retain sessionId while changing lifecycleRevision and reset boundary; zero token counters alone do not prove the active transcript was cleared.

## New-session-first profile (opt-in, schema-gated)

When the owner chooses to avoid automatic compaction for a group, set `agents.defaults.compaction.enabled=false` after a config backup and validation. This disables threshold-driven embedded auto-compaction; OpenClaw may still use preflight/overflow recovery compaction or a manual `/compact` if a request already exceeds the provider budget. Therefore the operational rule is to start `/new` (or reset/rotate the exact group session) before pressure reaches the budget, at the 60–70% warning threshold. Never wait for overflow and assume disabled compaction can recover it. Preserve daily/idle session rotation, bounded file intake, worker checkpoints, and receipts. Report this limitation clearly.

## Member group new-session guard

For the member `lehuynhphong`, the reusable guard is `/root/Automation/openclaw/member_group_guard/group_guard.py`. It is scoped to exact Telegram/Zalo group-key prefixes, defaults to dry-run, reads numeric session metadata plus a bounded runtime pressure-log tail, protects progressing active runs, and calls the live Gateway `sessions.reset` RPC after the configured idle or unchanged-under-pressure observation. OpenClaw also applies its native tool-result truncation; this helper is the hard bound for workbook intake, not an interceptor for arbitrary user text or every tool. It verifies the lifecycle revision and zero token counters after reset. It never touches DM sessions or deletes transcripts.

```bash
/root/Automation/openclaw/member_group_guard/run_guard.sh --dry-run
/root/Automation/openclaw/member_group_guard/run_guard.sh --apply
```

The member's prior broad compaction cron is disabled; the guard is the only scheduled group rotation path. Review logs under `/root/Automation/openclaw/member_group_guard/logs/`.

## Mandatory runtime hard gate

For a member where group runs can loop on large files, deploy the fail-closed
plugin `runtime/context-hard-gate.mjs` (source is kept with this skill) and
load it through that member's `plugins.load.paths`. It blocks transcript/history
and arbitrary process/file tools in Telegram/Zalo groups; only the single
bounded coordinator scripts are executable, with at most two coordinator
calls per run. Keep provider/model/agent/exec timeouts bounded, set global
`messages.queue.mode` to `interrupt`, and keep group history small (8–20).

Pair the plugin with the metadata guard. The lehuynhphong profile trips at
52,000 fresh prompt tokens or 180 seconds of active runtime, calls
`chat.abort`, then `sessions.reset` under a shared Gateway lock, and verifies a
new lifecycle. Wrap its timer in a 50-second OS timeout. Validate the plugin
and config before restarting the owning Gateway; never rely on compaction to
recover an already oversized run. Copy the plugin and coordinator into each
member workspace and adjust only paths/thresholds after schema validation.

## Hard file-intake helper (lehuynhphong)

Use `/home/lehuynhphong/.openclaw/workspace/scripts/safe_excel_intake.py` for CSV/XLSX/XLSM intake. Default invocation is metadata/header-only:

```bash
python3 scripts/safe_excel_intake.py /path/to/file.xlsx
```

Targeted content reads require explicit scope:

```bash
python3 scripts/safe_excel_intake.py /path/to/file.xlsx --sheet Sheet1 --contains MaDon ABC123 --columns MaDon TrongLuong Tuyen --limit 5
```

The helper limits sample matches to 5 and emits one valid JSON record of at most 2,000 characters (including the newline). It uses only the standard library and performs no source writes.

For member `lehuynhphong` calculation tasks, use `/home/lehuynhphong/.openclaw/workspace/.venv-excel/bin/python` with `pandas` first (`read_excel` restricted by sheet/usecols/nrows); use `openpyxl` read-only streaming only when needed. The venv currently contains pandas 3.0.5 and openpyxl 3.1.5. Do not use the system interpreter for these imports or dump DataFrames. Other members must install/use their own venv; never assume this path exists. It does not compute business totals or write into source files. Do not use arbitrary `cat/head/sed/read_excel` output for group file intake, and do not spawn extra agents to inspect the same workbook. Preserve artifact outputs outside chat context. The member model budget is 96k with a 128k provider window; the 96k value is a preflight safety budget, not a guarantee that arbitrary output fits. A separate new-session guard must rotate pressure before overflow.

## 2026-09-09: lagging token counters and interrupted recovery

`totalTokens` alone is not a live prompt limit. In the lehuynhphong 10:44 VN incident it remained 38,381 while the mid-turn precheck estimated 95,367 against 76,000 available after reserve. The guard now compares fresh total/input counters and exact-session numeric pressure events from the last 1 MiB of the Supervisor log. Ignore events older than the current session/run start, and ignore pre-completion errors superseded by a finished turn. A running recovery node may have no writer ID: unchanged progress plus pressure for 90 seconds still qualifies; do not exempt it permanently. An unverified reset may retry after cooldown.

Header intake succeeding does not validate the calculation phase. Missing `openpyxl` caused this agent to inspect helper source and old `.out` files, producing 9–16k-character results repeatedly. Before relying on a calculation workflow, test its actual interpreter/dependencies, select the required rows/columns and keep all raw output in artifacts. The 2,000-character helper cap is not a global tool-output cap. Do not claim business completion from a probe, reset or guard test.

Reset RPC can finish after a CLI timeout: inspect lifecycle/token/active-window state before retrying. The 03:55 UTC reset returned to the client as a timeout but committed successfully after about 62 seconds.

## One-script Excel coordinator

Use the bundled `scripts/excel_task.py` as one coordinator for a CSV/XLSX/XLSM request. Copy it into `/home/<member>/.openclaw/workspace/scripts/excel_task.py`; its output root is derived from that location. Run with `/home/<member>/.openclaw/workspace/.venv-excel/bin/python` (pandas/openpyxl). The `lehuynhphong` copy is deployed. Do not run the global copy directly against member output paths.

Header-only dry run, no artifact writes:

```bash
/home/<member>/.openclaw/workspace/.venv-excel/bin/python \
  /home/<member>/.openclaw/workspace/scripts/excel_task.py FILE
```

One filtered request with optional numeric totals:

```bash
/home/<member>/.openclaw/workspace/.venv-excel/bin/python \
  /home/<member>/.openclaw/workspace/scripts/excel_task.py FILE \
  --sheet SHEET --contains COLUMN TEXT --columns COL1 COL2 \
  --limit 5 --max-scan-rows 10000 --output output/result.json --task-id REQUEST_ID
```

- `--contains` is literal, case-insensitive; no expression evaluation. `--header-row` is zero-based (0..20). Add `--sum NUMERIC_COLUMN` only when the user requests that total. Missing columns or nonnumeric sum data return a short error.
- Read only the requested sheet and up to 40 required columns. Default scan window is 10,000 rows, maximum 100,000; `--limit` controls summary samples (1..5), not artifact records. Save every match within that window in the JSON artifact. `scan_limit_reached=true` means the result may be partial; never call it a full-workbook result.
- One JSON on stdout, at most 2,000 UTF-8 bytes (stricter than characters); wide samples/headers are omitted with `output_truncated=true`. Full results remain in the artifact. No DataFrame or old `.out` dump into chat. Help is plain text; normal/error runs return JSON.
- Outputs must be `.json` under the member workspace `output/`. Source files and existing unrelated artifacts cannot be overwritten. There are no Sheet/API/channel writes.
- A per-output lock prevents overlapping runs. `<output>.state.json` tracks processing/completed and a fingerprint of task ID, input SHA-256 and parameters; completed results are reused only after artifact hash verification. A changed request requires a new output path.
- Checkpoint granularity is the bounded processing phase: an interrupted run with identical input/arguments reruns that phase safely; it does not resume at an individual row. The default whole-run timeout is 60 seconds (`--timeout-seconds` 5..90). Split oversized jobs into explicit windows/tasks; do not claim this is an unlimited batch engine.
- This coordinator provides header discovery, filtered export and optional sums. Freight rates, joins between workbooks and other business logic must be added and tested inside the same coordinator/workflow; no inferred pricing or placeholder answer. Use one final summary/artifact delivery after a real receipt; processing never sends messages itself.
- On a missing dependency, install into that member's Excel venv and rerun the same request. Never fall back to repeated script/source/output reads. Do not reset a healthy running session merely to load these instructions.

Validation: fixture XLSX verifies headers, filter and sum, complete bounded artifact with more than five matches, 2,000-byte Unicode stdout, source unchanged, idempotent rerun, different-request conflict, missing column and invalid-argument errors. After any edit, sync the workspace and global script copies, test with the real member interpreter, scan for secrets, and update the Second AI Brain.

## Structured file task runtime (lehuynhphong)

For group workbook work, the hard gate exposes one native `file_task` tool. It
runs `/home/<member>/.openclaw/workspace/scripts/file_task.py` with the member
Excel virtualenv, `shell=false`, one 45-second deadline and at most two input
files. Actions are `discover`, `inspect`, `process`, and `status`; request JSON
may be passed on stdin or `--request-json`. The coordinator returns exactly one
bounded JSON summary (<=2,000 UTF-8 bytes) and writes details under
`output/file-tasks/<task-id>/`. `process` uses only explicit customer/sheet/
column scope, preserves source files, reports `needs_input` for missing or
ambiguous gross/rate/booking data, and never invents freight values.

The runtime `before_prompt_build` hook exposes only `file_task` and
`progress_card` for Excel/file-intent group turns, so denied shell calls cannot
start a retry loop. Native coordinator errors return `terminate=true`; the
built-in repetitive-tool detector is enabled as a secondary stop. Do not
restore blanket `exec` access to groups; add a tested coordinator action when a
new bounded file workflow is required.

## Runtime hard gate update (lehuynhphong)

The canonical plugin `runtime/context-hard-gate.mjs` is deployed to the member policy path and applies to both Telegram and Zalo group session keys. Work tools (`exec`, `file_task`) are fail-closed until a native `message` tool call completes with a real `messageId`; the receipt expires after 120 seconds. The plugin also blocks subagents/history/raw reads and restricts Excel work to the bounded pandas coordinator. Verify deployment with:

```bash
/root/Automation/openclaw/member_group_guard/policy_drift_guard.py
```

Do not send test messages to production groups; validate with checksum, syntax, and config checks.
