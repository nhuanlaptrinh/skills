---
name: facebook-messenger-human-pause
description: Apply or verify the 60-minute human takeover auto-pause pattern for Python/FastAPI Facebook Messenger Fanpage bots under `/root/Automation/facebook/01_Mess_Fanpage` or similarly structured projects. Use when Codex needs to add `message_echoes` handling, pause bot replies after staff manually responds, update Messenger bot tests/docs, restart/check related systemd services, or create new Messenger Fanpage bot projects with this safety behavior.
---

# Facebook Messenger Human Pause

## Goal

Make Messenger auto-reply bots stop replying to a customer for a configurable window after a Page staff member replies manually. The standard window is `HUMAN_PAUSE_MINUTES=60` and is counted from the latest human/Page echo.

## Standard Project Shape

Use this skill for projects like:

```text
/root/Automation/facebook/01_Mess_Fanpage/01_mes_op_<course>
├── app/main.py
├── app/database.py
├── app/facebook.py
├── app/settings.py
├── tests/test_core.py
├── README.md
├── .env.example
└── data/conversations.db
```

## Safety Rules

- Read `/root/Automation/facebook/01_Mess_Fanpage/AGENTS.md` if present.
- Do not print `.env` values, Meta tokens, app secrets, access tokens, admin keys, DeepSeek keys, cookies, or private credentials.
- Back up code files and `data/conversations.db` to `/root/_Backups` before editing production projects.
- Do not send live Messenger messages unless the user explicitly asks.
- Use local webhook simulation for verification; delete fake PSIDs/messages from SQLite after testing.
- Update `/root/_Second_AI_Brain/06_Nhat_Ky_Thay_Doi.md` after production changes.

## Apply Workflow

1. Identify target project(s):

```bash
find /root/Automation/facebook/01_Mess_Fanpage -maxdepth 1 -mindepth 1 -type d -name '01_mes_*'
```

2. Back up each target before editing:

```bash
TS=$(date -u +%Y%m%d_%H%M%S)
PROJECT=/root/Automation/facebook/01_Mess_Fanpage/01_mes_op_xxx
BACKUP=/root/_Backups/$(basename "$PROJECT")_manual_pause_$TS
mkdir -p "$BACKUP"
cp -a "$PROJECT"/app/main.py "$PROJECT"/app/database.py "$PROJECT"/app/settings.py \
  "$PROJECT"/app/facebook.py "$PROJECT"/tests/test_core.py "$PROJECT"/README.md \
  "$PROJECT"/.env.example "$BACKUP"/
cp -a "$PROJECT"/data/conversations.db "$BACKUP/conversations.db" 2>/dev/null || true
```

3. Run the bundled patcher:

```bash
python /root/.agents/skills/facebook-messenger-human-pause/scripts/apply_manual_pause.py \
  /root/Automation/facebook/01_Mess_Fanpage/01_mes_op_xxx
```

4. Run tests:

```bash
cd /root/Automation/facebook/01_Mess_Fanpage/01_mes_op_xxx
/usr/bin/python3 -m unittest discover -s tests
```

5. Start or restart the matching service only after tests pass:

```bash
systemctl restart 01_mes_op_xxx.service || systemctl start 01_mes_op_xxx.service
curl -sS --max-time 5 http://127.0.0.1:<PORT>/health
```

## Expected Code Behavior

- `app/settings.py` defines:
  - `BOT_REPLY_METADATA = f"{APP_NAME}:auto_reply"`
  - `META_APP_ID = os.getenv("META_APP_ID", "").strip()`
  - `HUMAN_PAUSE_MINUTES = int(os.getenv("HUMAN_PAUSE_MINUTES", "60"))`
- `app/facebook.py` sends bot replies with Messenger message metadata `BOT_REPLY_METADATA`.
- `app/database.py` has `conversations.manual_pause_until`, migration via `PRAGMA table_info`, and `set_manual_pause(psid, minutes)`.
- `app/main.py` handles `message.is_echo` before normal user messages:
  - Ignore bot echoes by metadata or `META_APP_ID`.
  - Treat human/Page echoes as role `human` and set `manual_pause_until = now + HUMAN_PAUSE_MINUTES`.
  - Keep permanent admin pause via existing `paused` column.
- The bot resumes automatically; no cron is needed. The next customer message after `manual_pause_until` can be answered.

## Local Echo Simulation

Use this pattern to verify without sending live Messenger messages. Replace `PORT` with the project port:

```bash
cd /root/Automation/facebook/01_Mess_Fanpage/01_mes_op_xxx
/usr/bin/python3 - <<'PY'
import hashlib, hmac, json, sqlite3, time
import requests
from app.settings import DATABASE_PATH, META_APP_SECRET
psid = f"codex-echo-test-{int(time.time())}"
mid = f"mid-codex-echo-test-{int(time.time())}"
payload = {"object":"page","entry":[{"messaging":[{"sender":{"id":"test-page"},"recipient":{"id":psid},"timestamp":int(time.time()*1000),"message":{"mid":mid,"is_echo":True,"text":"Codex local echo simulation"}}]}]}
raw = json.dumps(payload, separators=(",", ":")).encode()
sig = "sha256=" + hmac.new(META_APP_SECRET.encode(), raw, hashlib.sha256).hexdigest()
response = requests.post("http://127.0.0.1:PORT/webhook/facebook", data=raw, headers={"Content-Type":"application/json","X-Hub-Signature-256":sig}, timeout=10)
print(response.status_code, response.text)
with sqlite3.connect(DATABASE_PATH) as db:
    db.row_factory = sqlite3.Row
    row = db.execute("SELECT manual_pause_until FROM conversations WHERE psid=?", (psid,)).fetchone()
    msg = db.execute("SELECT role FROM messages WHERE psid=? ORDER BY id DESC LIMIT 1", (psid,)).fetchone()
    print("pause_saved", bool(row and row["manual_pause_until"]), "role", msg["role"] if msg else None)
    db.execute("DELETE FROM messages WHERE psid=?", (psid,))
    db.execute("DELETE FROM conversations WHERE psid=?", (psid,))
    db.execute("DELETE FROM processed_events WHERE event_id=?", (mid,))
PY
```

## Meta Requirement

In Meta Developer, subscribe the app/page webhook to `message_echoes`. Without this field, manual staff replies will not reach the bot, so auto-pause cannot trigger.
