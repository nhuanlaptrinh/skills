---
name: openclaw-course-website-bridge
description: Operate, test, extend, or integrate the shared internal OpenClaw AI Bridge used by Docker course websites under /root/Apps/course_websites/10Web_BH. Use when replacing a website's direct DeepSeek chatbot call with an OpenClaw agent, adding another website project to the bridge allowlist, diagnosing bridge health, or rerunning an advisor request.
---

# OpenClaw Course Website Bridge

## Architecture

- Bridge project: `/root/AI_Runtime/openclaw_bridge`
- Service: `openclaw-ai-bridge.service`
- Internal endpoint: `http://172.18.0.1:18890/v1/chat/completions`
- Health endpoint: `http://172.18.0.1:18890/health`
- Project allowlist: `/root/AI_Runtime/openclaw_bridge/config/projects.json`
- Agent registration script: `/root/AI_Runtime/openclaw_bridge/scripts/register_course_websites.py`
- Legacy migration script: `/root/AI_Runtime/openclaw_bridge/scripts/migrate_deepseek_websites.py`
- OpenClaw gateway: `http://127.0.0.1:18789/v1/chat/completions`
- OpenClaw config: `/root/.openclaw/openclaw.json`
- Website agent primary model: `9r/GPT-5.6-luna`
- Model source of truth: `WEBSITE_MODEL` in `/root/AI_Runtime/openclaw_bridge/scripts/register_course_websites.py`
- Docker network: `root_traefik` (`172.18.0.0/16`)

Websites never receive or mount the OpenClaw gateway token. The host Bridge reads it locally and maps each allowed project to one restricted OpenClaw agent.

## Provider Fallback

- Priority is OpenClaw first, DeepSeek second, website fallback message last.
- DeepSeek credentials exist only in `/root/AI_Runtime/openclaw_bridge/.env` with mode `600`; never copy them into website projects or skill files.
- Every project may set `fallback_enabled`, `fallback_provider`, `fallback_model`, and `fallback_timeout_seconds` in `config/projects.json`.
- Fallback is allowed only for technical provider failures: connection error, timeout, provider HTTP error, invalid JSON, or empty answer.
- Do not fallback for invalid project, invalid request, invalid course code, missing course data, or security rejection.
- After `CIRCUIT_FAILURE_THRESHOLD` consecutive OpenClaw failures, the Bridge skips OpenClaw for `CIRCUIT_COOLDOWN_SECONDS`, uses DeepSeek, then automatically retries OpenClaw.
- Responses include internal metadata `provider_used` and `fallback_used`; websites should not display provider names to customers.
- Logs may contain project, provider, status, failure count, and circuit state only. Never log prompts, questions, answers, course knowledge, tokens, or API keys.

Fallback dry test without stopping production OpenClaw:

```bash
set -a
source /root/AI_Runtime/openclaw_bridge/.env
set +a
OPENCLAW_URL=http://127.0.0.1:1/v1/chat/completions python3 <isolated-test-script>
```

Always use a non-notifying synthetic prompt for fallback tests.

## Inputs And Outputs

Request:

```json
{
  "project": "dvtl",
  "session_id": "random-session-id",
  "messages": [
    {"role": "system", "content": "advisor rules"},
    {"role": "user", "content": "question and course knowledge"}
  ]
}
```

Output uses the OpenAI-compatible `choices[0].message.content` shape. The Bridge hashes `project + session_id` before sending the `user` value to OpenClaw.

## Dry Run

Run checks that do not call the AI model:

```bash
python3 -m py_compile /root/AI_Runtime/openclaw_bridge/app.py
python3 -m unittest discover -s /root/AI_Runtime/openclaw_bridge/tests -v
systemctl status openclaw-ai-bridge.service --no-pager
docker exec <website-container> python -c "from urllib.request import urlopen; print(urlopen('http://172.18.0.1:18890/health', timeout=5).read().decode())"
```

## Real Test

Use a non-notifying website advisor request:

```bash
curl -sS --max-time 60 \
  -H 'Content-Type: application/json' \
  -d '{"course_code":"35_domain_dvtl","question":"Dịch vụ này phù hợp với ai?","notify_telegram":false}' \
  http://127.0.0.1:8021/api/course-advisor/
```

## Add Another Website

1. Read VPS production checklist and the website project note.
2. Backup the website advisor file, `/root/.openclaw/openclaw.json`, Bridge config, service unit, and UFW rules if they will change.
3. Create a restricted workspace `/root/.openclaw/workspace_website_<code>`.
4. Add agent `website-<code>` to `/root/.openclaw/openclaw.json` using the script's `WEBSITE_MODEL`, with minimal tools and deny runtime, filesystem, browser, messaging, gateway, and web tools.
5. Add the project mapping to `config/projects.json`.
6. Configure the website with `OPENCLAW_BRIDGE_URL`, `OPENCLAW_BRIDGE_PROJECT`, and timeout only; do not add the gateway token.
7. Validate OpenClaw config, restart the gateway, restart the Bridge only if Bridge code/service changed, then test from inside the website container.
8. Test the website's local API with notifications disabled before testing the public domain.

All new course websites with chatbots must use this Bridge architecture by default. Do not introduce a direct DeepSeek, OpenAI, Gemini, or other provider call inside an individual website unless the user explicitly approves an architectural exception.

## Service Commands

```bash
systemctl restart openclaw-ai-bridge.service
journalctl -u openclaw-ai-bridge.service --since '-15 minutes' --no-pager
systemctl --user restart openclaw-gateway.service
openclaw config validate
openclaw gateway status
```

## Safety

- Never print, copy, document, or mount the OpenClaw gateway token into website containers.
- Keep the Bridge bound to `172.18.0.1`, never `0.0.0.0` or the public VPS IP.
- UFW must allow only `172.18.0.0/16` on interface `br-86c411492e8b` to destination `172.18.0.1:18890/tcp`.
- Do not log request messages, course knowledge, customer questions, or AI answers in the Bridge.
- Never print or document the real DeepSeek fallback key; keep `.env` ignored and mode `600`.
- Add projects explicitly to the allowlist; never accept an arbitrary agent/model from website input.
- Disable Telegram or other notifications during tests unless the user explicitly requests a real notification.
- Revert from the matching folder in `/root/_Backups` if production validation fails.
