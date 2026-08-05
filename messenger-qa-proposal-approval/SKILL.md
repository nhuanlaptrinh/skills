---
name: messenger-qa-proposal-approval
description: Phân tích lịch sử câu hỏi Messenger hằng ngày của ANVI, ANCL và OPLW, tạo đề xuất cập nhật chatbot để gửi Telegram duyệt, hoặc áp dụng một đề xuất đã được người dùng duyệt qua OpenClaw/Telegram. Use khi người dùng nói duyệt đề xuất Q&A, cập nhật câu trả lời từ lịch sử khách hàng, xem đề xuất chatbot hôm nay, hoặc vận hành cron đề xuất 13:30.
---

# Messenger Q&A Proposal Approval

## Project

- Root: `/root/Automation/telegram/messenger_qa_update_proposals`
- Manager: `proposal_manager.py`
- Cron: `scripts/run_daily_proposals.sh`
- Proposal files: `proposals/YYYY/MM/YYYY-MM-DD.json` and `.md`
- Logs: `logs/daily_proposals.log`

## Generate Daily Proposals

Read only the current Vietnam-date archives for ANVI, ANCL, and OPLW. Compare with each course's active chatbot, website, and Q&A Markdown. Never alter history archives.

Create JSON with this schema:

```json
{
  "date": "YYYY-MM-DD",
  "generated_at": "ISO-8601 Asia/Ho_Chi_Minh",
  "courses": {
    "ANVI": [],
    "ANCL": [
      {
        "id": "1",
        "question": "Câu hỏi gốc đã bỏ mã khách",
        "current_answer": "Câu bot đã trả lời hoặc trống",
        "assessment": "new_question|new_wording|incomplete|incorrect|needs_confirmation",
        "reason": "Lý do cần cập nhật",
        "proposed_answer": "Câu trả lời hoàn chỉnh để tư vấn",
        "targets": ["chatbot", "website", "qa"],
        "status": "pending"
      }
    ],
    "OPLW": []
  }
}
```

Create a matching Markdown review. Include a command example after each item:

`Duyệt đề xuất ANCL ngày YYYY-MM-DD mục 1`

Do not include customer IDs, secrets, tokens, cookies, credentials, private `.env` content, or unnecessary personal information.

## Review From Telegram/OpenClaw

When the user asks to view today's proposals, run:

```bash
python3 /root/Automation/telegram/messenger_qa_update_proposals/proposal_manager.py show
```

For another date:

```bash
python3 /root/Automation/telegram/messenger_qa_update_proposals/proposal_manager.py show --date YYYY-MM-DD
```

## Apply An Approved Item

Only apply after the user explicitly says to approve/update a specific course, date, and item. First dry-run:

```bash
python3 /root/Automation/telegram/messenger_qa_update_proposals/proposal_manager.py apply --date YYYY-MM-DD --course ANCL --item 1 --dry-run
```

Then apply:

```bash
python3 /root/Automation/telegram/messenger_qa_update_proposals/proposal_manager.py apply --date YYYY-MM-DD --course ANCL --item 1
```

The script backs up active targets under `/root/_Backups`, appends the approved Q&A to the correct course files, and marks the item `applied`. Never rewrite the historical conversation file.

Supported course codes: `ANVI`, `ANCL`, `OPLW`.

## Send Proposal Telegram

Dry-run:

```bash
python3 /root/Automation/telegram/messenger_qa_update_proposals/proposal_manager.py send --date YYYY-MM-DD --dry-run
```

Send for real only when scheduled or explicitly requested:

```bash
python3 /root/Automation/telegram/messenger_qa_update_proposals/proposal_manager.py send --date YYYY-MM-DD
```

## Schedule And Rerun

Server timezone is UTC. The scheduled run is 13:30 Asia/Ho_Chi_Minh:

```cron
30 6 * * * /root/Automation/telegram/messenger_qa_update_proposals/scripts/run_daily_proposals.sh
```

Rerun the full current-day analysis and Telegram delivery:

```bash
/root/Automation/telegram/messenger_qa_update_proposals/scripts/run_daily_proposals.sh
```

To resend an existing proposal without asking OpenClaw to analyze again:

```bash
python3 /root/Automation/telegram/messenger_qa_update_proposals/proposal_manager.py send --date YYYY-MM-DD
```

Inputs are the current Vietnam-date Messenger Markdown archives. Outputs are proposal JSON/Markdown files, Telegram review messages, approved Q&A appended to active course knowledge files, backup folders, and applied status in JSON. No Google Sheet or external database is used.

## Safety

- Require explicit approval before applying.
- Keep Messenger histories immutable.
- Do not edit archive folders.
- Back up active targets before applying.
- Never expose Telegram credentials or `.env` contents.
- Update `/root/_Second_AI_Brain/06_Nhat_Ky_Thay_Doi.md` after important changes.
