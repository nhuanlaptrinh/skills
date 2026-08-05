---
name: meta-ads-daily-spend-report
description: Use when Codex needs to report daily Meta/Facebook Ads spend for the configured ad accounts, especially returning each ad account name, each account spend, and the combined total spend. Trigger for requests about daily ad spend, Meta Ads cost today/yesterday, or total spend across the two configured ad accounts.
---

# Meta Ads Daily Spend Report

## Project Location

- Canonical project path on this VPS: `/root/Automation/meta_ads/meta_ads_daily_spend_report`.
- Recommended project name: `meta_ads_daily_spend_report`.
- Previous names/paths: `/root/10MetaAdsMCP`, `/root/Automation/meta_ads/meta_ads_mcp`, and skill `meta-ads-mcp`.

## Core Rules

- This project is for reporting daily spend only: account name, account spend, and total spend across configured Meta Ads accounts.
- Always execute from the project root, the directory that contains `.env` and `.env.example`.
- Never print or reveal `.env` secret values. It is fine to report whether required keys are present.
- `META_AD_ACCOUNT_ID` may contain one account or multiple account IDs separated by commas. For this VPS, it is expected to contain 2 ad accounts.
- IDs may be stored with or without `act_`; scripts normalize before calling Meta API.
- Do not create, delete, activate, or pause campaigns unless the user explicitly asks for campaign management outside this daily-spend workflow.

## Main Command

Run today's report:

```bash
cd /root/Automation/meta_ads/meta_ads_daily_spend_report
.venv/bin/python daily_spend_report.py
```

Run a specific date:

```bash
cd /root/Automation/meta_ads/meta_ads_daily_spend_report
.venv/bin/python daily_spend_report.py --date YYYY-MM-DD
```

Expected output format:

```text
Meta Ads daily spend - YYYY-MM-DD
1. <Account name 1> (act_xxx): <spend> <currency>
2. <Account name 2> (act_yyy): <spend> <currency>
Total: <combined spend> <currency>
```

## Setup Checks

Expected local files:

- `daily_spend_report.py`
- `requirements.txt`
- `.env`
- `.env.example`
- `.venv/`

If dependencies are missing:

```bash
cd /root/Automation/meta_ads/meta_ads_daily_spend_report
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

## Legacy MCP Files

- `meta_ads_mcp.py` and `meta-ads-mcp/script/meta_ads_mcp.py` are legacy/general MCP files from the previous broader project.
- Prefer `daily_spend_report.py` for the current business need.
