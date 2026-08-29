---
name: openclaw-telegram-slow-reply-recovery
description: Diagnose and safely recover OpenClaw Telegram bots that reply slowly, stop replying, or appear connected but do not dispatch messages. Use for account-scoped latency analysis, stale Telegram polling offsets, duplicate pollers, wrong routing, oversized bootstrap/context/tool results, session bloat, provider latency, and Local-versus-Cloud Bot API incidents on a main or member VPS.
---

# OpenClaw Telegram Slow-Reply Recovery

Diagnose the full path from Telegram inbound update to OpenClaw outbound reply, then apply the smallest verified repair. Keep the procedure portable: discover the VPS layout, service manager, OpenClaw root, agent, account, workspace, state database, and session store instead of assuming paths or identities.

## Scope and safety

- Confirm whether the request targets the main VPS or a member VPS; do not cross that boundary.
- Obtain explicit authorization before restarting a production Gateway, changing OpenClaw configuration, mutating SQLite state, or sending a real Telegram test.
- Treat a Telegram bot username as an identifier only; use the internal OpenClaw `agent-id` and Telegram `account-id` for routing and state operations.
- Never print, copy, store, or paste bot tokens, API keys, cookies, passwords, private keys, `.env` contents, full Telegram payloads, message text, or private chat data.
- Back up every production file before editing it. Store backups outside the live project, with restrictive permissions.
- Prefer read-only diagnosis and dry-run commands. Never call Cloud Bot API `getUpdates` while the Gateway is running.
- Do not delete sessions, workspace files, training data, or the whole SQLite database to fix a Telegram polling problem.

## Required inputs

Resolve these values from local configuration and service metadata without exposing secrets:

```bash
export OPENCLAW_ROOT="${OPENCLAW_ROOT:-$HOME/.openclaw}"
export AGENT_ID="<agent-id>"
export ACCOUNT_ID="<telegram-account-id>"
export SESSION_PREFIX="agent:${AGENT_ID}:telegram:"
export GATEWAY_UNIT="openclaw-gateway.service"
export SKILL_ROOT="${SKILL_ROOT:-$HOME/.agents/skills/openclaw-telegram-slow-reply-recovery}"
```

Also record, in redacted notes, the actual:

- Gateway service or container name.
- OpenClaw config path and state database path.
- Agent workspace and session directory.
- Telegram account binding, bot username, API root, and webhook/polling mode.
- Provider/model route and whether the request is DM or group traffic.

## Triage order

Classify the incident before changing anything:

1. **No inbound event:** inspect Gateway state, Telegram account status, polling ownership, webhook state, update offset, and allowlists.
2. **Inbound but no outbound:** inspect dispatch, session lock, tool execution, provider errors, and outbound Telegram failures.
3. **Outbound is late:** correlate inbound and outbound events by bot account plus chat/session key, then split the duration into Telegram, Gateway, tool, and provider time.
4. **Only long finance or tool-heavy requests are slow:** inspect bootstrap/context size, memory search, tool-result size, session tokens, and model reasoning level.
5. **All requests are slow:** run a provider/model health or dry-run benchmark without delivery and compare route latency with Gateway latency.

Do not infer latency from a chat ID alone. The same user or group can be served by multiple bots.

## Read-only diagnosis

Run the narrowest applicable checks and redact identifiers from the final report:

```bash
openclaw config validate
openclaw channels status --channel telegram --probe --json
openclaw agents list --bindings
openclaw sessions --agent "$AGENT_ID" --json --limit all
systemctl --user is-active "$GATEWAY_UNIT"
journalctl --user -u "$GATEWAY_UNIT" --since "15 minutes ago" -o cat --no-pager
```

For a Docker or Supervisor deployment, identify the exact Gateway process and run the equivalent status and log commands. Do not restart a container merely because a diagnostic command is inconvenient.

If the account-scoped latency audit exists, use it instead of guessing from mixed logs:

```bash
python3 /root/Automation/openclaw/telegram_latency_audit/telegram_latency_audit.py \
  --since "15 minutes ago" --account-id "$ACCOUNT_ID" --json
```

The audit must report paired inbound/outbound events, minimum/average/maximum latency, unpaired events, account/agent/workspace route checks, and any cross-account events that were intentionally excluded. If that path does not exist, use the Gateway journal but label unscoped pairs as unverified.

Inspect only redacted metadata from the following layers:

- **Telegram:** account connected state, probe result, Cloud/Local API root, webhook presence, rate-limit or `409 Conflict` errors, and update IDs without payload text.
- **Gateway:** one active owner process, event-loop stalls, dispatch/session errors, outbound request failures, and restart loops.
- **Routing:** exactly the intended agent, workspace, account binding, DM/group policy, allowlist, and group mention/privacy requirements.
- **Context:** bootstrap character counts, context-pruning mode/TTL, memory-search status, tool-result limits, thinking level, and current session token counts.
- **Provider:** model/route name, request start/end or time-to-first-byte, timeout/retry count, status code, and response size; never log prompt or credential content.

## Repair no-response incidents

Use the existing offset helper when the evidence points to a stale or too-high persisted Telegram polling offset:

```bash
export OFFSET_HELPER="${OFFSET_HELPER:-$HOME/.agents/skills/sua-loi-telegram-offset-openclaw/scripts/repair_telegram_offset.py}"
python3 "$OFFSET_HELPER" --account-id "$ACCOUNT_ID" --cloud-check
```

Follow this exact sequence:

1. Confirm the correct Gateway unit and stop only that Gateway.
2. Verify that it is inactive before querying the Cloud update queue.
3. Back up the OpenClaw state SQLite file and any matching `-wal` and `-shm` files.
4. Run the helper in dry-run mode with `--cloud-check` and record only redacted offset metadata.
5. Apply only when a mismatch is proven and the observed value is passed explicitly:

   ```bash
   python3 "$OFFSET_HELPER" \
     --account-id "$ACCOUNT_ID" \
     --cloud-check \
     --apply \
     --expected-offset "<stored-lastUpdateId>" \
     --backup-dir "/root/_Backups"
   ```

6. Start the same Gateway and verify the target account becomes connected.
7. With explicit authorization, send one fresh unique DM test from a real user and verify both inbound and outbound events. Record the measured latency.

The repair must delete only the target `telegram.update-offsets` row. Preserve sessions, message cache, routing, workspace data, and configuration. Use `--force` only when the mismatch is independently proven but the Cloud queue is empty; never use it to bypass an active-Gateway check or an unexpected offset.

If no offset mismatch is proven, investigate duplicate pollers, `409 Conflict`, a lingering webhook, wrong account/token mapping, DM/group allowlists, Telegram Privacy Mode, dispatch/session errors, and only then model/provider latency. Use `unify-openclaw-bot-workspace` for divergent routing; do not change agent architecture in this skill.

## Repair slow responses

Before changing production, back up `openclaw.json`, the relevant session-rotation script/cron, and any project-specific configuration. Keep the change scoped to the affected agent.

For a finance or stateless reporting agent, use this baseline after confirming the configuration schema supports each field:

- Set `thinkingDefault: off` unless the user explicitly needs reasoning.
- Set `contextInjection: continuation-skip` for independent Telegram turns.
- Bound per-file bootstrap input around `4k–6k` characters and total bootstrap around `10k–12k` characters.
- Keep context pruning in `cache-ttl` mode with a short verified TTL, such as `5m`.
- Bound tool results around `12k` characters or lower when the task permits.
- Keep `memorySearch.enabled: false` for a stateless finance agent when its data source is explicit and current.
- Use a narrow allowlist for the needed file/report operations; deny browser, web search/fetch, image, subagents, sessions, and unrelated workshop tools.
- Rotate idle Telegram sessions before context growth reaches the unsafe range. Use `50_000` tokens as the current baseline for the finance-bot rotation job, and make the threshold configurable per agent.

Do not apply the finance baseline blindly to coding, research, or media agents. Preserve tools and memory that are required by the agent's contract, and validate the config before restarting the Gateway.

For provider or route latency:

- Run a non-delivery health or dry-run benchmark with a short fixed prompt.
- Record model, route, time-to-first-byte, total duration, timeout/retry count, and payload size.
- Compare several samples; one slow request is not enough to re-route production.
- Prefer a faster model/route only after confirming the provider is the dominant segment.
- Never use `--deliver` or send a Telegram message during a benchmark.

## Validation after changes

Run targeted checks first, then broader checks:

```bash
openclaw config validate
python3 -m py_compile <changed-python-script>.py
/path/to/session-rotation-wrapper --threshold 50000 --dry-run
openclaw channels status --channel telegram --probe --json
systemctl --user is-active "$GATEWAY_UNIT"
```

Confirm that:

- The Gateway has one active owner and the target account is connected.
- The agent/workspace/account binding is unchanged unless routing repair was requested.
- The configured thinking level, pruning, bootstrap, tool-result limit, tool allowlist, and rotation threshold are effective.
- No new `409 Conflict`, `UND_ERR_CONNECT_TIMEOUT`, offset mismatch, dispatch error, or provider timeout appears.
- A real-user test is performed only with authorization and is reported with exact UTC timestamps and measured latency.

Telegram may reject a bot-to-bot test with `USER_BOT_TO_BOT_DISABLED`; treat that as a test limitation, not proof that the target bot is broken. A group test may also require an explicit mention because Telegram Privacy Mode is upstream of OpenClaw.

## Rollback

If validation fails, stop further changes and restore only the files changed in this incident from the timestamped backup. Restore the previous crontab as a complete crontab snapshot only after confirming it belongs to the same host. Restart the affected Gateway once, re-run `openclaw config validate`, and verify the account status. Do not delete reset transcript archives or SQLite backups.

## Report format

Return a short redacted report containing:

- Scope: VPS, Gateway unit/container, agent, account, and workspace identifiers.
- Root cause: proven, likely, or not found; separate no-response from latency causes.
- Evidence: status, paired latency measurements, session token range, and relevant error counts.
- Changes: exact non-secret files, settings, threshold, and backup directory.
- Validation: config, service, Telegram account, offset, and test result.
- Remaining limits: provider latency, Telegram outage/rate limit, privacy mode, or an unverified hypothesis.
