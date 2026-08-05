---
name: meta-ads-campaign-guard
description: Use when Codex needs to run, audit, repair, or update the Meta Ads campaign guard that pauses inefficient campaigns in the configured two Meta ad accounts after the 2 AM to 3 AM campaign start window.
---

# Meta Ads Campaign Guard

## Project Location

- Canonical path: `/root/Automation/meta_ads/meta_ads_campaign_guard`
- Main script: `/root/Automation/meta_ads/meta_ads_campaign_guard/campaign_guard.py`
- Scheduled activation script: `/root/Automation/meta_ads/meta_ads_campaign_guard/activate_scheduled_campaigns.py`
- Telegram notify script: `/root/Automation/meta_ads/meta_ads_campaign_guard/telegram_notify.py`
- Cron wrapper: `/root/Automation/meta_ads/meta_ads_campaign_guard/scripts/run_campaign_guard.sh`
- Start-window notify wrapper: `/root/Automation/meta_ads/meta_ads_campaign_guard/scripts/run_start_window_notify.sh`
- Shared Watchdog projects: `meta_ads_campaign_guard`, `meta_ads_activate_scheduled_campaigns`
- Timezone: `Asia/Ho_Chi_Minh`
- Log file: `/root/Automation/meta_ads/meta_ads_campaign_guard/logs/campaign_guard_cron.log`

## When To Use

Use this skill when the user asks to:

- Check or run the Meta Ads auto-pause app.
- Change spend/result thresholds.
- Repair the Meta Ads campaign guard cron that starts after 3 AM Vietnam time.
- Audit why a campaign was or was not paused.

## Configuration

- The app reads Meta credentials and ad account IDs from `/root/Automation/meta_ads/meta_ads_daily_spend_report/.env`.
- Telegram bot token and chat ID are stored in the project-local `.env` and must never be printed.
- Do not print or copy real secrets from that file.
- `META_AD_ACCOUNT_ID` can contain one or more account IDs separated by commas; this VPS is expected to have two.
- Campaigns are expected to start during `02:00–03:00` Vietnam time.
- The guard must not auto-pause campaigns during that start window.
- At `02:00`, activate scheduled campaigns/adsets through Shared Watchdog Center.
- Send a Telegram notification whenever the guard pauses a campaign.
- Activation script only activates `campaign` and `adset`; it does not force activate individual ads with invalid Page posts.
- Activation script uses batch delay and retry for Meta API rate limits, then sends Telegram summary.
- Default thresholds:
  - `META_NO_RESULT_SPEND_LIMIT=8000`
  - `META_MAX_COST_PER_RESULT=13000`
- Result metric: only `messaging_conversation_started_7d` is counted as a result.
- Result action types are defined in code and can be overridden with `META_RESULT_ACTION_TYPES` if needed.

## Dry Run

```bash
cd /root/Automation/meta_ads/meta_ads_campaign_guard
.venv/bin/python campaign_guard.py
```

Dry-run output is JSON. Matching campaigns show `action: "would_pause"`.

## Run For Real

```bash
cd /root/Automation/meta_ads/meta_ads_campaign_guard
.venv/bin/python campaign_guard.py --apply
```

Real-run output is JSON. Matching campaigns show `action: "paused"` after the API update succeeds.

## Scheduled Run

Cron should call:

```bash
/root/Automation/watchdog/shared_self_healing/run_project.sh meta_ads_campaign_guard
```

Recommended schedule, using Vietnam timezone. This starts after the `02:00–03:00` campaign start window:

```cron
CRON_TZ=Asia/Ho_Chi_Minh
5-50/15 3-23 * * * /root/Automation/watchdog/shared_self_healing/run_project.sh meta_ads_campaign_guard
```

Start-window notification schedule:

```cron
CRON_TZ=Asia/Ho_Chi_Minh
0 2 * * * /root/Automation/watchdog/shared_self_healing/run_project.sh meta_ads_activate_scheduled_campaigns
```

## Input / Output

- Input: Meta Ads account IDs and API token from the existing daily spend `.env`.
- Output: JSON printed to stdout and cron log.
- The script only pauses active campaigns; it does not create, delete, or edit budgets.

## Safety Rules

- Always use dry-run first when changing logic or thresholds.
- Back up crontab before changing the schedule.
- Never write real API keys, access tokens, cookies, passwords, private keys, or `.env` contents into this skill.
- If changing paths, thresholds, schedule, or output format, update this skill and `/root/_Second_AI_Brain/06_Nhat_Ky_Thay_Doi.md`.
