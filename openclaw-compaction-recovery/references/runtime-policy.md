# Runtime Policy

## Diagnosis

OpenClaw computes a pre-prompt budget from the configured context cap minus the effective compaction reserve. A typical member with `contextTokens=96000` and an effective reserve of `16000` has roughly `80000` tokens available before compaction. A log record such as `estimatedPromptTokens=93018 promptBudgetBeforeReserve=80000 overflowTokens=13018` is a local precheck failure, not proof that Telegram or the API key is invalid.

Common evidence of this incident:

- `context-overflow-midturn-precheck`
- `Auto-compaction failed`
- `Compaction timed out`
- `context-overflow-recovery ... Tool result truncation did not help`
- `livenessState=blocked suggestedAction=reset_or_new`

Large tool results, repeated `sessions_history`, recursive project reads, raw logs, image blocks, and media payloads are frequent causes. Count and summarize them; do not copy raw content into the report.

## Eligibility matrix

| Condition | Action |
| --- | --- |
| Configured context cap and every primary/fallback window give minimum budget `>= 80k`, existing safeguard | Eligible for candidate validation; apply only after authorization |
| Unknown model context window | Audit only; do not guess reserve or raise context cap |
| Any inheriting agent/fallback effective context `< 80k` | Audit only; derive an individual smaller-model policy |
| Custom compaction provider configured | Audit only unless provider is explicitly understood |
| Malformed config or duplicate Gateway | Stop and repair the narrower issue first |
| Provider latency repeatedly exceeds timeout | Raise compaction timeout only after checking upstream health and usage |
| Active session still above budget after config change | Semantic compact the specific session; do not reset all sessions |

## Baseline reasoning

For a `96k` agent cap, the 24k reserve moves the precheck threshold from about `80k` to `72k`. The helper sets both reserve and floor to at least `24000`, preserves larger existing values, and refuses a reserve consuming more than one third of the smallest known context budget. These are conservative helper-policy bounds, not universal provider guarantees. Runtime limits and estimates still need verification.

Reducing `keepRecentTokens`, `maxHistoryShare`, and `recentTurnsPreserve` makes the resulting summary smaller. Keeping the quality guard enabled protects summary integrity, while `maxRetries=1` prevents unbounded latency. `timeoutSeconds=600` accommodates a slow but responsive provider; it does not cure an unavailable provider.

Do not change `contextTokens`, model, provider, or token files as a first response. A larger context cap can increase the amount of history sent to a slow provider and make compaction more expensive.

## Session repair rules

1. Back up the config, agent registry and referenced transcripts before a production repair. The config helper does not do session backups. Check the runtime's supported backup command first. For a JSONL fallback, take a verified private snapshot only after active writes/runs are quiescent; for SQLite use the native backup facility or a consistent SQLite backup, not a lone copied database file with missing WAL.
2. Identify the exact session key from the log or `sessions.json`.
3. Use `openclaw sessions compact <key> --timeout 660000 --json` through the running Gateway.
4. With `truncateAfterCompaction` enabled, confirm the successor transcript and retained original. Other runtimes may append a compaction entry or store a checkpoint in SQLite instead; do not require a changed session ID or fake one manually. Verify reduced context and native checkpoint success rather than byte size alone.
5. Verify with a no-delivery smoke run and the channel probe.
6. Stop after an unchanged failure. At most one retry is justified by a concrete corrective change, not by wishful repeated resets.

Never manually truncate a JSONL transcript, delete reset archives, or run parallel compactions against the same Gateway.

## Version-dependent behavior

Check `openclaw --version`, `config schema`, `config validate`, `sessions --help` and installed docs before choosing operations. Do not trust `meta.lastTouchedVersion` as the running version. Newer upstream documentation can describe SQLite/context-engine or provider-specific behavior absent from a pinned installation.

Primary references to consult are the installed `docs/reference/session-management-compaction.md`, `docs/concepts/session-pruning.md`, and corresponding official OpenClaw documentation. Cache-TTL pruning eligibility is provider/version dependent; audit the actual implementation before adding it. Do not use generic pruning as an excuse to disable mid-turn safety checks.

The 2026-09-06 nv4 incident showed success after approximately 370 seconds for group compaction and 202 seconds for main, both beyond the old 180-second deadline. This explains that incident; other failures can be provider errors, model limits, corrupt state, or very large single-turn outputs and must be diagnosed separately.

## Safe report fields

Allowed: target label, container name, version marker, agent IDs, model/provider identifiers, numeric compaction settings, context estimates, file sizes, timestamps, hashes, health booleans, and error type/count.

Forbidden: bot tokens, API keys, authorization headers, cookies, raw approval data, private transcripts, full config dumps, media payloads, and credential file contents.
