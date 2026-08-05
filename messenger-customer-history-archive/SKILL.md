---
name: messenger-customer-history-archive
description: Add, verify, repair, or operate automatic Markdown archiving of complete Facebook Messenger text conversations for Fanpage bots under /root/Automation/facebook/01_Mess_Fanpage, including ANVI, ANCL, and OPLW histories stored in Second Brain. Use when customer messages, bot replies, and staff replies must be saved together without Telegram or real Facebook PSIDs.
---

# Messenger Customer History Archive

## Paths

- ANVI project: `/root/Automation/facebook/01_Mess_Fanpage/01_mes_op_anvi`
- ANCL project: `/root/Automation/facebook/01_Mess_Fanpage/01_mes_op_ancl`
- OPLW project: `/root/Automation/facebook/01_Mess_Fanpage/01_mes_op_oplw`
- Archive module: `app/customer_history.py`
- ANVI destination: `/root/Data/second_brain/Second_Brain/01_chuong_trinh_dao_tao/31_domain_anvi/04_lich_su_cau_hoi_va_phan_hoi_khach_hang`
- ANCL destination: `/root/Data/second_brain/Second_Brain/01_chuong_trinh_dao_tao/19_domain_ancl/04_lich_su_cau_hoi_va_phan_hoi_khach_hang`
- OPLW destination: `/root/Data/second_brain/Second_Brain/01_chuong_trinh_dao_tao/03_domain_oplw/04_lich_su_cau_hoi_va_phan_hoi_khach_hang`
- Services: `01_mes_op_anvi.service`, `01_mes_op_ancl.service`, `01_mes_op_oplw.service`

## Behavior

- Archive inbound customer text after signature validation and `claim_event()` deduplication.
- Archive customer text before `is_paused()` handling so messages remain recorded during human takeover pauses.
- Archive bot text only after the Messenger Send API succeeds.
- Archive staff text from non-bot `message.is_echo` events while preserving human takeover pause behavior.
- Ignore bot echoes identified by metadata or Meta app ID to avoid duplicate bot entries.
- Store files as `YYYY/MM/YYYY-MM-DD.md` in Vietnam time.
- Store only a SHA-256-derived short customer code; never store the real PSID in Markdown.
- Keep archive failures isolated so Messenger replies continue operating.

## Safe Workflow

1. Read VPS instructions, project `AGENTS.md`, and the production checklist.
2. Back up `app`, `tests`, `README.md`, `.env.example`, and `data/conversations.db` into `/root/_Backups`.
3. Do not read or print `.env` values.
4. Run focused tests without sending live Messenger messages:

```bash
cd /root/Automation/facebook/01_Mess_Fanpage/01_mes_op_<course>
/usr/bin/python3 -m unittest tests.test_core.CoreTests.test_conversation_roles_are_archived_without_real_psid
```

5. Run the complete test suite:

```bash
/usr/bin/python3 -m unittest discover -s tests
```

6. Restart only after tests pass, then check health:

```bash
systemctl restart 01_mes_op_<course>.service
curl -sS --max-time 5 http://127.0.0.1:<PORT>/health
```

## Input And Output

- Input: validated customer webhook messages, successful bot responses, and non-bot staff echoes.
- Output: appended Markdown entries labeled `Khách hàng`, `Bot tư vấn`, or `Nhân viên Fanpage` in the daily history file.
- No Telegram, Sheet, API upload, cron, or separate worker is used.

Use port `8811` for ANVI, `8812` for OPLW, and `8813` for ANCL.

## Verification

- Confirm the service is active and `/health` returns `ok: true`.
- Confirm new real customer messages create or append the correct daily file.
- Confirm Markdown contains no access token, API key, cookie, password, `.env` content, or real PSID.
- Update `/root/_Second_AI_Brain/06_Nhat_Ky_Thay_Doi.md` after production changes.
