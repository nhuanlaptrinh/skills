---
name: messenger-customer-history-daily-telegram-report
description: Run, verify, repair, or reschedule the separate daily Telegram reports that send only the current Vietnam-date Messenger customer conversation archive for ANVI at 13:00, ANCL at 13:10, and OPLW at 13:20 Asia/Ho_Chi_Minh.
---

# Messenger Customer History Daily Telegram Report

## When To Use

Use this skill when operating or changing the daily Telegram summary of Messenger histories for ANVI, ANCL, and OPLW, including schedule, source paths, Telegram delivery, report formatting, or reruns.

## Project

- Root: `/root/Automation/telegram/messenger_customer_history_daily_report`
- Main script: `report.py`
- Cron wrapper: `scripts/run_daily_report.sh`
- Logs: `logs/daily_report_anvi.log`, `logs/daily_report_ancl.log`, `logs/daily_report_oplw.log`
- Tests: `tests/test_report.py`

## Inputs

The script reads only the file matching today's date in `Asia/Ho_Chi_Minh`:

- ANVI: `/root/Data/second_brain/Second_Brain/01_chuong_trinh_dao_tao/31_domain_anvi/04_lich_su_cau_hoi_va_phan_hoi_khach_hang/YYYY/MM/YYYY-MM-DD.md`
- ANCL: `/root/Data/second_brain/Second_Brain/01_chuong_trinh_dao_tao/19_domain_ancl/04_lich_su_cau_hoi_va_phan_hoi_khach_hang/YYYY/MM/YYYY-MM-DD.md`
- OPLW: `/root/Data/second_brain/Second_Brain/01_chuong_trinh_dao_tao/03_domain_oplw/04_lich_su_cau_hoi_va_phan_hoi_khach_hang/YYYY/MM/YYYY-MM-DD.md`

Telegram credentials come from environment variables or the existing ANCL website environment file. Never print, copy into documentation, or commit the real token/chat ID.

## Output

- Telegram messages containing the three current-day archives.
- Missing archives are reported as having no questions or feedback that day.
- Long reports are split below Telegram's message limit.
- Runtime status is appended to `logs/daily_report.log`; credentials are never logged.

## Dry Run

This prints the report locally and does not call Telegram:

```bash
cd /root/Automation/telegram/messenger_customer_history_daily_report
/usr/bin/python3 report.py --course ANVI --dry-run
```

Run for a specific date without sending:

```bash
/usr/bin/python3 report.py --course ANVI --date YYYY-MM-DD --dry-run
```

## Tests

```bash
cd /root/Automation/telegram/messenger_customer_history_daily_report
/usr/bin/python3 -m unittest discover -s tests
bash -n scripts/run_daily_report.sh
```

## Run For Real

Only run when the user explicitly requests Telegram delivery:

```bash
/root/Automation/telegram/messenger_customer_history_daily_report/scripts/run_daily_report.sh ANVI
```

## Schedule

Server timezone is UTC. The daily schedule is:

```cron
# BEGIN MESSENGER_CUSTOMER_HISTORY_DAILY_TELEGRAM_REPORT
# ANVI: 13:00 Asia/Ho_Chi_Minh = 06:00 UTC
0 6 * * * /root/Automation/telegram/messenger_customer_history_daily_report/scripts/run_daily_report.sh ANVI
# ANCL: 13:10 Asia/Ho_Chi_Minh = 06:10 UTC
10 6 * * * /root/Automation/telegram/messenger_customer_history_daily_report/scripts/run_daily_report.sh ANCL
# OPLW: 13:20 Asia/Ho_Chi_Minh = 06:20 UTC
20 6 * * * /root/Automation/telegram/messenger_customer_history_daily_report/scripts/run_daily_report.sh OPLW
# END MESSENGER_CUSTOMER_HISTORY_DAILY_TELEGRAM_REPORT
```

Before changing cron, back up `crontab -l` to `/root/_Backups`. Never remove unrelated jobs.

## Rerun

Running the wrapper with one course argument sends that course's current Vietnam-date report again. Use `report.py --course COURSE --date YYYY-MM-DD --dry-run` to inspect an older day; normal scheduled jobs must remain current-day only.

## Safety

- Do not expose Telegram credentials, `.env` contents, real Messenger PSIDs, cookies, passwords, or API keys.
- Do not modify the three source archives when generating a report.
- Do not send a live test unless the user requested it.
- Keep Telegram failures isolated from Messenger bot services.
- Update `/root/_Second_AI_Brain/06_Nhat_Ky_Thay_Doi.md` after important changes.
