---
name: openclaw-9router-overload-recovery
description: Diagnose, install, verify, repair, or roll back the reliable local proxy used when OpenClaw Telegram bots receive HTTP 200/SSE responses whose assistant text says the AI servers are overloaded. Use for repeated 9Router/Codex overload replies, missing retry on successful HTTP responses, Codex account concentration, or model fallback hardening on the main VPS.
---

# OpenClaw 9Router Overload Recovery

Recover transient AI overloads without forwarding the raw overload sentence to Telegram. The proxy buffers chat-completion responses, recognizes the narrow known overload message, retries once, then changes model; 9Router rotates Codex accounts and its combo also has alternate models.

## Paths and services

- Project: `/root/Automation/9router/reliable_chat_proxy`
- Proxy service: `openclaw-9router-reliable-proxy.service`
- Upstream 9Router: `http://127.0.0.1:20128`
- Reliable proxy: `http://127.0.0.1:20129`
- OpenClaw config: `/root/.openclaw/openclaw.json`
- 9Router database: `/root/.9router/db/data.sqlite`
- Backups: `/root/_Backups/<timestamp>_openclaw_9router_overload_recovery`

## Safety

- Read the VPS Second AI Brain files and production checklist before changes.
- Obtain explicit authorization before production restart or configuration mutation.
- Never print provider credentials, Telegram tokens, prompts, private messages, or full request bodies.
- Back up `openclaw.json`, the 9Router SQLite database with the SQLite backup API, and affected systemd units.
- Do not call Telegram `getUpdates` while Gateway is running and do not send a real test message without authorization.
- Keep the proxy on loopback. Do not expose port `20129` publicly.

## Diagnose

Prove all of the following before applying this recovery:

- OpenClaw transcript contains the exact overload assistant text.
- Provider/model metadata points to the intended 9Router route.
- The transport returned HTTP `200` and `text/event-stream`, so ordinary error fallback did not run.
- Telegram polling, routing, Gateway, CPU, and RAM are healthy.
- Redacted 9Router usage data shows the downstream provider/model and account distribution.

The proxy intentionally matches only these normalized assistant responses: the known `Our servers are currently overloaded` sentence, a close server-overloaded variant, or `Service temporarily unavailable`. Do not broaden the match to arbitrary words such as `error`, because a legitimate assistant answer can contain them.

## Dry run

```bash
cd /root/Automation/9router/reliable_chat_proxy
npm test
python3 -m py_compile configure_9router_routing.py configure_openclaw.py
python3 configure_9router_routing.py
python3 configure_openclaw.py
systemd-analyze --user verify openclaw-9router-reliable-proxy.service
```

Dry-run output must show only provider strategy, combo model IDs, local proxy URL, target agent, and model aliases. It must not show API keys.

## Apply

Create a restrictive backup directory first, then run:

```bash
python3 configure_9router_routing.py \
  --apply \
  --backup-dir /root/_Backups/<incident-directory>

install -m 644 openclaw-9router-reliable-proxy.service \
  /root/.config/systemd/user/openclaw-9router-reliable-proxy.service
systemctl --user daemon-reload
systemctl --user restart 9router.service
systemctl --user enable --now openclaw-9router-reliable-proxy.service

python3 configure_openclaw.py \
  --apply \
  --backup-dir /root/_Backups/<incident-directory>
openclaw config validate
systemctl --user restart openclaw-gateway.service
```

The routing script sets Codex to round-robin with a sticky limit of one and changes combo `GPT-5.6-sol` to `sol -> terra -> luna`. The OpenClaw script creates provider alias `9rr` pointing to the loopback proxy and scopes the override to agent `taonhanvienao`.

## Validate

```bash
curl -fsS http://127.0.0.1:20128/api/health
curl -fsS http://127.0.0.1:20129/health
systemctl --user is-active \
  9router.service \
  openclaw-9router-reliable-proxy.service \
  openclaw-gateway.service
openclaw config validate
openclaw channels status --channel telegram --probe --json
journalctl --user -u openclaw-9router-reliable-proxy.service --since "15 minutes ago" -o cat --no-pager
```

Confirm one post-change request uses provider `9rr`, proxy logs `upstream_complete` or `upstream_retry`, Telegram sends successfully, and the exact overload sentence is absent from new transcript events. The proxy buffers each response before forwarding, so record the added buffering latency when reporting.

## Input and output

- Input: OpenAI-compatible `POST /v1/chat/completions`; all other paths are passed through.
- Output: the first successful non-overload upstream response.
- Retry order: requested model once, requested model retry once, then configured fallback models.
- Exhaustion: return a sanitized HTTP `503` JSON error; never forward raw overload assistant text.
- Logs: structured metadata only: timestamp, event, attempt, model, status, duration, retry reason. Never log prompt or credentials.

## Rollback

Restore only this incident's files and database backup:

```bash
systemctl --user stop openclaw-gateway.service
systemctl --user disable --now openclaw-9router-reliable-proxy.service
systemctl --user stop 9router.service
install -m 600 /root/_Backups/<incident-directory>/openclaw.json.before \
  /root/.openclaw/openclaw.json
install -m 600 /root/_Backups/<incident-directory>/9router-data.sqlite.before \
  /root/.9router/db/data.sqlite
systemctl --user start 9router.service
systemctl --user start openclaw-gateway.service
openclaw config validate
```

Restore SQLite only while 9Router is stopped. Preserve unrelated later configuration changes; if the incident is old, use a targeted reverse patch instead of copying the whole old config.

After an important change, update `/root/_Second_AI_Brain/06_Nhat_Ky_Thay_Doi.md`.
