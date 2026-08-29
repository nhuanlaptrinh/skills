---
name: messenger-bstuannk-fanpage
description: Operate, verify, repair, or update the Facebook Messenger auto-reply bot for the bstuannk member Fanpage and its nam khoa clinic knowledge base.
---

# Messenger bstuannk Fanpage

## Project

- Project: `/root/Apps/member_vps/docker-users/data/bstuannk/Apps/facebook_fanpage_auto_reply`
- App: `/root/Apps/member_vps/docker-users/data/bstuannk/Apps/facebook_fanpage_auto_reply/01_mes_op_anvi`
- Knowledge: `/root/Apps/member_vps/docker-users/data/bstuannk/Apps/facebook_fanpage_auto_reply/01_mes_op_anvi/data/knowledge`
- Runtime database: `01_mes_op_anvi/data/runtime/database/conversations.db`
- Local app port: `8811`
- Container: `user-bstuannk`
- Supervisor program: `facebook-fanpage-auto-reply`
- OpenClaw agent invocation: `openclaw agent --agent main`

## When To Use

Use this skill when checking the bot, updating nam khoa knowledge, repairing AI fallback, verifying Messenger webhook behavior, or restarting only this member's Messenger worker.

## Knowledge Behavior

- The app reads Markdown files under `01_mes_op_anvi/data/knowledge`.
- It scans all `.md` files inside directories beginning with `01_du_lieu_website_chatbot` and the priority paths listed in `app/knowledge.py`.
- The loader fingerprints file path, size, and modification time, so new or changed Markdown files are detected without relying on a process restart.
- Check `http://127.0.0.1:8811/health`; `knowledge_characters` must be greater than zero.
- Force a reload only when needed:

```bash
curl -X POST -H 'X-Admin-Key: ADMIN_API_KEY' \
  http://127.0.0.1:8811/admin/knowledge/reload
```

Never print the real admin key, customer PSID, or conversation contents.

## AI Integration

- The member OpenClaw Gateway at `127.0.0.1:18789` is a WebSocket Gateway and does not expose the REST `POST /v1/chat/completions` route in the current member configuration.
- `app/chatbot.py` therefore calls the local OpenClaw CLI with `--json`, `--message-file`, `--agent main`, and a hashed per-request session key. It does not copy a gateway token into the project.
- Messenger AI calls use a new OpenClaw session key per request. SQLite history remains the bounded conversation context; do not restore a permanent session key per customer because the knowledge bundle is included on every turn and can overflow the model context.
- DeepSeek is an optional fallback provider. If OpenClaw fails and `DEEPSEEK_API_KEY` is empty, the app sends the configured technical fallback message.
- The prompt and knowledge are for the nam khoa clinic Fanpage, not the ANVI course website.
- Treat the current loaded training data as the source of truth for information it explicitly contains, including clinic address, hours, service details, and contact fields. Answer those fields directly without asking for external verification; never invent fields that are absent, and preserve medical-safety limits.

## Dry Run

Run from the app directory:

```bash
cd /root/Apps/member_vps/docker-users/data/bstuannk/Apps/facebook_fanpage_auto_reply/01_mes_op_anvi
.venv/bin/python -m py_compile app/*.py
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -c 'from app.knowledge import load_knowledge; print(len(load_knowledge()))'
```

## AI Smoke Test Without Messenger Send

Use a synthetic prompt and do not call Meta Send API:

```bash
docker exec -e HOME=/home/bstuannk user-bstuannk sh -lc \
  'cd /home/bstuannk/Apps/facebook_fanpage_auto_reply/01_mes_op_anvi && \
   .venv/bin/python -c "from app.chatbot import answer_question; print(answer_question(\"Em tư vấn về gì vậy em?\", [], \"smoke-test-no-send\"))"'
```

Do not use `--deliver`, do not call `send_text`, and do not send a real customer message during testing.

## Health And Restart

```bash
docker exec user-bstuannk sh -lc 'curl -fsS http://127.0.0.1:8811/health'
docker ps --format '{{.Names}}\t{{.Status}}' | grep user-bstuannk
```

The worker is supervised inside `user-bstuannk`. Restart only the worker after backing up changed production files; do not restart the container or OpenClaw Gateway unless that is specifically required:

```bash
docker exec user-bstuannk sh -lc \
  'pid=$(ps -eo pid,args | awk '\''$0 ~ /facebook_fanpage_auto_reply\/01_mes_op_anvi\/\.venv\/bin\/python/ && $0 ~ /--port 8811/ {print $1; exit}'\''); \
   test -n "$pid" && kill -TERM "$pid"'
```

Confirm the new worker reports `knowledge_characters` greater than zero and inspect `/tmp/facebook-fanpage-auto-reply.log` for provider errors.

If an older customer session has already overflowed, preserve its session artifacts in a root-only backup and rename only the affected primary `.jsonl` transcript with a `.reset.<UTC timestamp>` suffix. Do not delete the SQLite conversation history or customer-history archive.

## Inputs And Outputs

- Inputs: Meta Messenger webhook events, approved Markdown knowledge, recent conversation context, member OpenClaw agent configuration, and optional DeepSeek configuration.
- Outputs: Messenger replies through Meta Send API, SQLite conversation state, Markdown customer-history archives, and worker logs.
- The app pauses a conversation after a human/Page echo; preserve this behavior.

## Safety

- Read the root VPS instructions, project `AGENTS.md`, and production checklist before changes.
- Back up `.env` and any production files before editing them; keep backups root-only.
- Never include API keys, gateway tokens, Page tokens, cookies, passwords, private keys, admin keys, or customer data in this skill or in responses.
- Do not change Meta webhook credentials, Nginx, Docker networking, or OpenClaw configuration without a targeted backup and validation.
- Do not send real Messenger messages unless the user explicitly requests a live test.
