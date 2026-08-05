# messenger-anvi-fanpage

Use when operating, checking, starting, or updating the Facebook Messenger auto-reply bot for the ANVI course Fanpage.

## Project

- Project path: `/root/Automation/facebook/01_Mess_Fanpage/01_mes_op_anvi`
- App package: `app/`
- Local port: `8811`
- Local health check: `http://127.0.0.1:8811/health`
- Knowledge root: `/root/Data/second_brain/Second_Brain/01_chuong_trinh_dao_tao/31_domain_anvi`
- Course website: `https://anvi.anhlaptrinh.vn/`
- SQLite DB: `/root/Automation/facebook/01_Mess_Fanpage/01_mes_op_anvi/data/conversations.db`
- Primary AI backend: OpenClaw Chat Completions at `http://127.0.0.1:18789/v1/chat/completions`
- Secondary AI backend: DeepSeek Chat Completions from the ANVI website environment
- OpenClaw agent: `openclaw/messenger-anvi`
- OpenClaw model: `9r/GPT-5.6-luna`
- OpenClaw workspace: `/root/.openclaw/workspace_messenger_anvi`

## Safety Rules

- Do not print or commit real values from `.env`, Meta tokens, app secrets, admin keys, DeepSeek keys, cookies, or private credentials.
- Do not send real Messenger messages unless the user explicitly asks to test live sending.
- Before editing nginx, systemd, cron, or production config, back up the original file to `/root/_Backups`.
- Start the service only after `META_PAGE_ID` and `META_PAGE_ACCESS_TOKEN` are confirmed to belong to the ANVI Fanpage.
- Keep this skill updated if project path, port, webhook route, run command, or input/output logic changes.
- The bot auto-pauses a customer conversation after a human/Page reply echo; do not disable this safety unless explicitly requested.

## Dry Run / Local Checks

```bash
cd /root/Automation/facebook/01_Mess_Fanpage/01_mes_op_anvi
/usr/bin/python3 -m unittest discover -s tests
/usr/bin/python3 - <<'PY'
from app.knowledge import load_knowledge
print(len(load_knowledge()))
PY
```

## Manual Run

```bash
cd /root/Automation/facebook/01_Mess_Fanpage/01_mes_op_anvi
/usr/bin/python3 -m uvicorn app.main:app --host 127.0.0.1 --port 8811
```

Health check:

```bash
curl http://127.0.0.1:8811/health
```

## Systemd

Unit path:

```bash
/etc/systemd/system/01_mes_op_anvi.service
```

Start only after ANVI Fanpage credentials are set and approved:

```bash
systemctl start 01_mes_op_anvi.service
systemctl status 01_mes_op_anvi.service --no-pager -l
```

Enable auto-start only after production verification:

```bash
systemctl enable 01_mes_op_anvi.service
```

## Webhook / Nginx

Expected public route:

```text
https://mess-op.anhlaptrinh.vn/webhook/facebook
```

Proxy target:

```text
http://127.0.0.1:8811/webhook/facebook
```

## Inputs

- Meta webhook events from the ANVI Fanpage.
- Meta `message_echoes` webhook events to detect human/Page replies and pause bot auto-replies for `HUMAN_PAUSE_MINUTES` minutes, default `60`.
- ANVI knowledge Markdown/TXT files under the knowledge root.
- DeepSeek configuration from `/root/Apps/course_websites/10Web_BH/31_domain_anvi/.env` if present.
- Meta credentials and admin key from the project `.env`.
- OpenClaw gateway token read locally from `/root/.openclaw/openclaw.json`; the project does not duplicate this token in `.env`.

## Outputs

- Messenger replies through Meta Send API.
- Conversation state and processed event IDs in SQLite.
- Timed manual takeover state in SQLite column `conversations.manual_pause_until`.
- Service logs in `journalctl -u 01_mes_op_anvi.service` after systemd start.

## Human Takeover Behavior

- Configure `META_APP_ID` when available so the webhook can ignore bot-origin echoes by app ID.
- Bot Send API messages include metadata `01_mes_op_anvi:auto_reply`; echoes with this metadata are ignored.
- Human/Page echo text is saved with role `human`, then that PSID is skipped until the pause window expires.
- No cron is required to resume; the next customer message after `manual_pause_until` is eligible for auto-reply.

## OpenClaw AI Behavior

- `app/chatbot.py` first calls model `openclaw/messenger-anvi`.
- Each Messenger PSID is SHA-256 hashed before being used as the OpenClaw `user` session key.
- OpenClaw agent `messenger-anvi` uses model `9r/GPT-5.6-luna`, workspace isolation, tool profile `minimal`, and denies runtime/filesystem/browser/messaging tools.
- If OpenClaw fails, times out, returns an HTTP/provider/JSON error, or returns an empty answer, the bot retries the same prompt through DeepSeek.
- Only if both OpenClaw and DeepSeek fail or are unavailable does the Messenger bot send the configured fallback message and wait for staff.
- Validate before production restart with `openclaw config validate --json`, `/usr/bin/python3 -m unittest discover -s tests`, and a direct `answer_question()` smoke test that does not call Meta Send API.
