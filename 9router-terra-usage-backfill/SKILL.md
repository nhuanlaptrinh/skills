---
name: 9router-terra-usage-backfill
description: Preview, validate, apply, or reverse the explicitly authorized historical GPT-6.1 Terra cost correction in 9Router, including daily aggregates and customer billing verification.
---

# 9Router Terra Usage Backfill

## Status And Authorization

Prepared and tested on isolated copies on 2026-10-29. Production billing has NOT
been changed. The owner requested historical Terra billing, including customers,
but requires approval before any action that may interrupt the running app.
No maintenance window has been approved at the time this skill was created.

The running 9Router uses node:sqlite with read-then-write SAVEPOINT transactions.
A separate live writer can cause SQLITE_BUSY_SNAPSHOT and lose a usage save even
with busy_timeout=5000. This was reproduced on a synthetic database. Do not run a
live correction while 9Router is writing. Obtain approval for a short maintenance
window, then stop the user service, apply, and start it immediately with recovery
in a finally/trap path. Existing streams may need retry. Do not claim zero downtime.

## Paths And Inputs

- Script: `/root/Automation/9router/terra_usage_backfill/backfill.py`.
- Tests: `test_backfill.py` in the same directory.
- Snapshot validation: `verify_snapshot.py` in the same directory.
- Production router: `/root/.9router/db/data.sqlite`.
- Dashboard: `/root/Apps/9router_usage_dashboard`; its existing global skill is
  `/root/.agents/skills/9router-usage-dashboard/SKILL.md`.
- Router service: `XDG_RUNTIME_DIR=/run/user/0 systemctl --user ... 9router.service`.
- Snapshot and audit evidence:
  `/root/_Backups/9router_terra_backfill/20261029T030717Z/` (root-only).

Input is only provider `codex`, model `gpt-6.1-terra`, positive valid token counts,
and raw `cost=0`. Nonzero rows and other models are preserved. Rates per million
tokens: input 1, cache read 0.05, cache write 1.25, output 5, reasoning 5 USD.
Reasoning is added separately to match the installed 9Router formula. No added
long-context multiplier is used. Router daily buckets use UTC on this host.

## Dry Run And Validation

```bash
python3 -B /root/Automation/9router/terra_usage_backfill/backfill.py
cd /root/Automation/9router/terra_usage_backfill
python3 -B -m unittest -v test_backfill.py
```

Dry-run opens the source with `mode=ro` and `query_only=ON`, prints counts/rates and
the exact Decimal cost, and does not create files, send messages, or call APIs.

Before production work, use SQLite online backup to create fresh consistent
`router_before.sqlite` and `dashboard_before.sqlite` in a timestamped root-only
directory. Do not copy a live SQLite main file without its WAL. Duplicate those
offline snapshots as `router_test.sqlite` and `dashboard_test.sqlite`.

```bash
python3 -B /root/Automation/9router/terra_usage_backfill/backfill.py --database /root/_Backups/9router_terra_backfill/TIMESTAMP/router_test.sqlite --apply --receipt /root/_Backups/9router_terra_backfill/TIMESTAMP/test_apply_receipt.json
/root/Apps/9router_usage_dashboard/.venv/bin/python -B /root/Automation/9router/terra_usage_backfill/verify_snapshot.py /root/_Backups/9router_terra_backfill/TIMESTAMP
```

Replace TIMESTAMP with the prepared directory. Verification requires those exact
snapshot filenames, refuses production databases, reads only whitelisted pricing
variables from the dashboard process, rebuilds ONLY the copied Django summaries,
and writes `validation_report.json` (mode 600). Compare every customer's before,
delta, after and limit; check newly exceeded limits before applying. Production
credit enforcement runs each minute and may disable newly over-limit accounts or
send ordinary low-credit alerts; do not invoke it or send test messages manually.

## Real Run: Only After Maintenance Approval

After fresh backup and customer-impact verification, gracefully stop only
`9router.service` in the root user systemd manager. Confirm the service and its
children have exited. Dashboard and other services remain running. Ensure the
router is started again even if the following command fails:

```bash
python3 -B /root/Automation/9router/terra_usage_backfill/backfill.py --apply --allow-live-write --receipt /root/_Backups/9router_terra_backfill/TIMESTAMP/production_apply_receipt.json
```

The flag is a guard against accidental live execution, not proof of user approval.
The script uses a single BEGIN IMMEDIATE transaction with zero busy wait. It
revalidates each row fingerprint, updates only raw cost and matching daily cost
buckets (`byProvider`, `byModel`, `byAccount`, `byApiKey`, `byEndpoint`, total), and
rolls back completely on a conflict or missing bucket. Request/token counters,
keys, model configuration and user credit limits do not change.

Restart the stopped router immediately; verify its service, HTTP health and
ordinary new usage. Existing dashboard/customer billing reads the corrected raw
cost and applies the effective Codex multiplier (currently x2). Do not add the
same fee to credit limits, archives, or closed costs. `altcp-usage-summary.service`
detects the changed prefix and rebuilds automatically; verify direct and summary
totals agree after it publishes. No dashboard restart or schema migration is needed.

## Outputs, Rerun And Recovery

- Outputs: updated raw/daily router cost after approved apply, a receipt containing
  usage IDs, prices and irreversible row hashes, and the safe validation report.
- No Sheet writes, uploads, posting, payment calls, or customer messages.
- Rerun dry-run: changed rows no longer have cost=0, so they are not billed twice.
- Receipt is saved as `prepared` before the transaction and `committed` afterwards.
  If interrupted between commit and receipt finalization, inspect the affected
  costs before acting; do not infer failure from `prepared` alone.
- Rollback requires a new receipt and the same maintenance approval. It verifies
  that the corrected rows are unchanged, sets only those costs back to zero and
  subtracts their contributions from current daily totals, preserving newer usage.

```bash
python3 -B /root/Automation/9router/terra_usage_backfill/backfill.py --rollback /root/_Backups/9router_terra_backfill/TIMESTAMP/production_apply_receipt.json --allow-live-write --receipt /root/_Backups/9router_terra_backfill/TIMESTAMP/production_rollback_receipt.json
```

Never restore an old full database over live usage as routine rollback. Keep full
SQLite snapshots root-only because they contain credentials and request data.
Do not print or copy secrets into receipts, reports, skill files or chat. Missing
daily buckets or invalid token data require investigation, not estimated charges.

## Prepared Evidence

The 2026-10-29 snapshot has 9,162 zero-cost Terra rows from 2026-10-27 to
2026-10-29. Exact base correction: 145.2844666 USD; total x2 cost: 290.5689332.
Of this, 290.5587292 Credits belongs to 10 customers; 0.010204 belongs to two
requests on an API not assigned to any customer. None of the 10 crosses its limit.
179 other customer totals are unchanged. Six unit tests and full snapshot
validation passed. The isolated transaction took approximately 0.365 seconds;
this is not a guarantee of production downtime or startup duration.
