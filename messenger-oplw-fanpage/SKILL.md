# messenger-oplw-fanpage

Use when operating, checking, starting, or updating the Facebook Messenger auto-reply bot for the OPLW course Fanpage.

## Project

- Project path: `/root/Automation/facebook/01_Mess_Fanpage/01_mes_op_oplw`
- App package: `app/`
- Local port: `8812`
- Local health check: `http://127.0.0.1:8812/health`
- Knowledge root: `/root/Data/second_brain/Second_Brain/01_chuong_trinh_dao_tao/03_domain_oplw`
- Course website: `https://oplw.anhlaptrinh.vn/`
- Done-for-you assistant service: `https://dvtl.anhlaptrinh.vn/`
- SQLite DB: `/root/Automation/facebook/01_Mess_Fanpage/01_mes_op_oplw/data/conversations.db`
- Primary AI backend: OpenClaw Chat Completions at `http://127.0.0.1:18789/v1/chat/completions`
- Secondary AI backend: DeepSeek Chat Completions from the OPLW website environment
- OpenClaw agent: `openclaw/messenger-oplw`
- OpenClaw model: `9r/GPT-5.6-luna`
- OpenClaw workspace: `/root/.openclaw/workspace_messenger_oplw`

## Safety Rules

- Do not print or commit real values from `.env`, Meta tokens, app secrets, admin keys, DeepSeek keys, cookies, or private credentials.
- Do not send real Messenger messages unless the user explicitly asks to test live sending.
- Before editing nginx, systemd, cron, or production config, back up the original file to `/root/_Backups`.
- Prefer checking `/health`, logs, and service status before making changes.
- Keep this skill updated if project path, port, webhook route, run command, or input/output logic changes.
- The bot auto-pauses a customer conversation after a human/Page reply echo; do not disable this safety unless explicitly requested.

## Dry Run / Local Checks

```bash
cd /root/Automation/facebook/01_Mess_Fanpage/01_mes_op_oplw
/usr/bin/python3 -m unittest discover -s tests
/usr/bin/python3 - <<'PY'
from app.knowledge import load_knowledge
print(len(load_knowledge()))
PY
```

## Manual Run

```bash
cd /root/Automation/facebook/01_Mess_Fanpage/01_mes_op_oplw
/usr/bin/python3 -m uvicorn app.main:app --host 127.0.0.1 --port 8812
```

Health check:

```bash
curl http://127.0.0.1:8812/health
```

## Systemd

Unit template:

```bash
/root/Automation/facebook/01_Mess_Fanpage/01_mes_op_oplw/deploy/01_mes_op_oplw.service
```

Install or update only after checking credentials and backing up an existing unit if present:

```bash
cp /root/Automation/facebook/01_Mess_Fanpage/01_mes_op_oplw/deploy/01_mes_op_oplw.service /etc/systemd/system/01_mes_op_oplw.service
systemctl daemon-reload
systemctl status 01_mes_op_oplw.service --no-pager
```

Start only when Meta credentials in project `.env` are real and approved:

```bash
systemctl start 01_mes_op_oplw.service
systemctl status 01_mes_op_oplw.service --no-pager -l
```

## Webhook / Nginx

Expected public route:

```text
https://synalt.anhlaptrinh.vn/messenger-oplw/webhook/facebook
```

Proxy target:

```text
http://127.0.0.1:8812/webhook/facebook
```

Nginx snippet template:

```bash
/root/Automation/facebook/01_Mess_Fanpage/01_mes_op_oplw/deploy/nginx-mess-op.conf.example
```

## Inputs

- Meta webhook events from the OPLW Fanpage.
- Meta `message_echoes` webhook events to detect human/Page replies and pause bot auto-replies for `HUMAN_PAUSE_MINUTES` minutes, default `60`.
- OPLW knowledge Markdown/TXT files under the knowledge root.
- DeepSeek configuration from `/root/Apps/course_websites/10Web_BH/03_domain_oplw/.env` if present.
- Meta credentials and admin key from the project `.env`.
- OpenClaw gateway token read locally from `/root/.openclaw/openclaw.json`; the project does not duplicate this token in `.env`.

## Outputs

- Messenger replies through Meta Send API.
- Conversation state and processed event IDs in SQLite.
- Timed manual takeover state in SQLite column `conversations.manual_pause_until`.
- Service logs in `journalctl -u 01_mes_op_oplw.service` after systemd install/start.

## Done-For-You Assistant Offer

- If a customer does not want to study, lacks time to study, or asks Anh Lập Trình to build a private assistant, state that the done-for-you service costs `5 triệu đồng` per assistant.
- State that the assistant can accept commands through Zalo or Telegram.
- Send `https://dvtl.anhlaptrinh.vn/` for service details.
- Do not confuse this full assistant price with small custom support or add-on implementation priced around `1 triệu đồng`.
- Source of truth: `01_du_lieu_website_chatbot_oplw_anhlaptrinh_vn/03_du_lieu_chatbot_tu_van.md` under the knowledge root and `app/chatbot.py`.

## Human Takeover Behavior

- Configure `META_APP_ID` when available so the webhook can ignore bot-origin echoes by app ID.
- Bot Send API messages include metadata `01_mes_op_oplw:auto_reply`; echoes with this metadata are ignored.
- Human/Page echo text is saved with role `human`, then that PSID is skipped until the pause window expires.
- No cron is required to resume; the next customer message after `manual_pause_until` is eligible for auto-reply.

## OpenClaw AI Behavior

- `app/chatbot.py` first calls model `openclaw/messenger-oplw`.
- Each Messenger PSID is SHA-256 hashed before being used as the OpenClaw `user` session key.
- OpenClaw agent `messenger-oplw` uses model `9r/GPT-5.6-luna`, workspace isolation, tool profile `minimal`, and denies runtime/filesystem/browser/messaging tools.
- If OpenClaw fails, times out, returns an HTTP/provider/JSON error, or returns an empty answer, the bot retries the same prompt through DeepSeek.
- Only if both OpenClaw and DeepSeek fail or are unavailable does the Messenger bot send the configured fallback message and wait for staff.
- Validate before production restart with `openclaw config validate --json`, `/usr/bin/python3 -m unittest discover -s tests`, and a direct `answer_question()` smoke test that does not call Meta Send API.

## Admin Actions

Pause one PSID:

```bash
curl -X POST -H "X-Admin-Key: ADMIN_API_KEY" \
  http://127.0.0.1:8812/admin/conversations/PSID/pause
```

Resume one PSID:

```bash
curl -X POST -H "X-Admin-Key: ADMIN_API_KEY" \
  http://127.0.0.1:8812/admin/conversations/PSID/resume
```

Reload knowledge:

```bash
curl -X POST -H "X-Admin-Key: ADMIN_API_KEY" \
  http://127.0.0.1:8812/admin/knowledge/reload
```
