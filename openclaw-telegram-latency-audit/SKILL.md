---
name: openclaw-telegram-latency-audit
description: Audit OpenClaw Telegram response latency across multiple bot accounts without mixing events that share a chat ID. Use when diagnosing slow Telegram bots, validating inbound/outbound timestamps, or correcting a cross-bot log correlation.
---

# OpenClaw Telegram Latency Audit

## When to use

Use this skill for a shared OpenClaw gateway serving multiple Telegram bots, especially when two bots message the same Telegram user or group. The audit must correlate by bot username/account ID and chat ID; a chat ID alone is never a valid latency key.

## Project and script

- Project: `/root/Automation/openclaw/telegram_latency_audit`
- Script: `/root/Automation/openclaw/telegram_latency_audit/telegram_latency_audit.py`
- Bot map: `/root/Automation/openclaw/telegram_latency_audit/bot_accounts.json`
- Default config: `/root/.openclaw/openclaw.json`
- Default journal: user unit `openclaw-gateway.service`

## Dry-run

```bash
python3 /root/Automation/openclaw/telegram_latency_audit/telegram_latency_audit.py \
  --since '1 hour ago'
```

Specific incident window:

```bash
python3 /root/Automation/openclaw/telegram_latency_audit/telegram_latency_audit.py \
  --since '2026-08-28 02:20:00 UTC' \
  --until '2026-08-28 02:31:00 UTC'
```

Machine-readable output:

```bash
python3 /root/Automation/openclaw/telegram_latency_audit/telegram_latency_audit.py \
  --since '1 hour ago' --json
```

To inspect only the expense bot, add `--account-id quanlychitieugd`. To inspect
only the Anh Lập Trình bot, add `--account-id trolyalt`. Repeat the option for
an explicit multi-account audit.

## Run and output

The command is read-only and is also the production audit command. It reads `journalctl --user -u openclaw-gateway.service -o cat`, validates each mapped account-level Telegram binding, parses inbound bot usernames and account-labeled outbound events, and reports:

- per-message latency pairs;
- canonical session keys derived from the configured agent and chat type;
- per-bot minimum, average, maximum, and threshold counts;
- unpaired events that were intentionally not guessed;
- legacy outbound lines without `accountId`, counted as unscoped rather than guessed;
- cross-account boundaries for the same chat, explicitly marked `is_latency=false`;
- account, agent, and workspace route checks.

Use `--input <journal-export.txt>` for a saved journal or unit-test fixture. Use `--journal-scope system` only when the gateway is a system service. Adjust `--threshold-seconds` and `--max-pair-seconds` when the incident requires different limits.

## Validation and rerun

```bash
openclaw config validate
python3 -m unittest discover -s /root/Automation/openclaw/telegram_latency_audit/tests -v
python3 /root/Automation/openclaw/telegram_latency_audit/telegram_latency_audit.py \
  --since '2026-08-28 02:20:00 UTC' --until '2026-08-28 02:31:00 UTC'
```

Rerun with a new time window; do not edit historical logs. Update only the public username mapping when a bot is renamed or replaced, then rerun `openclaw config validate` and the tests.

## Safety rules

- Never print, copy, or store bot tokens, API keys, cookies, passwords, or private data.
- Never pair events using only `chat ID`, journal proximity, or a timestamp gap.
- Never change `openclaw.json`, restart the gateway, stop a bot, or send Telegram messages as part of this audit.
- If an account or username is missing from the map, fail closed and report it as unpaired.
