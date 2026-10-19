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
- Legacy scaffold default: `WEBSITE_MODEL=9r/GPT-5.6-luna` in `/root/AI_Runtime/openclaw_bridge/scripts/register_course_websites.py`; this is not a guarantee of the live route.
- Live model source of truth: `agents.entries.<agent>.model` in `/root/.openclaw/openclaw.json`, verified with `openclaw models status --agent <agent> --check --json`.
- Docker network: `root_traefik` (`172.18.0.0/16`)
- AIA mapping: project `aia` -> agent `website-aia` -> website folder `36_domain_aia`

Deployment note: `website-oplw` currently routes through `9rr/GPT-5.6-sol` with `9rr/GPT-5.6-terra` and `9rr/GPT-5.6-luna` fallbacks via the local reliable proxy. Keep this route when maintaining OPLW unless the direct provider profile is revalidated first.

Deployment note: `website-alt` currently routes through `9rr/GPT-5.6-luna` with `9rr/GPT-5.6-terra` and `9rr/GPT-5.6-sol` fallbacks via the local reliable proxy. The direct `openai/gpt-5.6-luna` route is not usable while its subscription authentication is expired. `luna` is preferred for shorter advisor responses; keep the fallback order unless the provider is revalidated.

For ALT, keep the Bridge project timeout at 60 seconds and the website advisor timeout at 90 seconds. The reliable proxy can take longer than the legacy 35/40-second defaults during provider recovery.

## OPLW Incident Recovery

- On 2026-10-15, the direct `openai/gpt-5.6-luna` route failed with `Explicit auth order for openai has no usable profiles`; Gateway returned HTTP 500. DeepSeek simultaneously returned HTTP 402 `Insufficient Balance`, so Bridge returned HTTP 502 and the website showed its generic retry message.
- Routing only `website-oplw` through the existing `9rr` provider restored local and public advisor responses. No website code, `.env`, credentials, shared provider settings or other agents were changed. Backup: `/root/_Backups/oplw_chatbot_fix_20261015T105324Z`.
- `/health` checks configuration/connectivity, not model authentication or provider balance. Always verify a synthetic advisor request with `notify_telegram: false`, a non-empty answer and `configured: true`.
- Diagnose model/auth status before changing anything. Do not stop Gateway merely to run an optional provider probe; the CLI may refuse live probes while Gateway is active. Prefer the non-notifying Bridge/website request.
- The legacy registration script writes all managed agents and uses `agents.list`; inspect the current `agents.entries` schema and preserve live model overrides before any bulk apply. Do not use it for a single-agent repair.
- DeepSeek remains unavailable until the account is funded or an authorized working fallback is configured. Do not top up, replace secrets or change other websites without authorization.

Websites never receive or mount the OpenClaw gateway token. The host Bridge reads it locally and maps each allowed project to one restricted OpenClaw agent.

## Provider Fallback

### ALT Recovery Notes

- ALT portal: `/root/Apps/course_websites/10Web_BH/28_domain_alt`, container `alt-sub-django`, public domain `https://anhlaptrinh.vn`, loopback `127.0.0.1:8006`, Bridge project `alt`, agent `website-alt`.
- On 2026-10-15, direct OpenAI subscription authentication was unavailable and DeepSeek returned HTTP 402. Switching only the ALT model restored AI access, but a stale inherited `9rr:default` profile caused HTTP 401 followed by provider-wide auth cooldown. A single successful response did not establish recovery.
- The verified provider key already configured in `models.providers.9rr.apiKey` was saved as an agent-local override. Effective auth now comes from `/root/.openclaw/agents/website-alt/agent/openclaw-agent.sqlite`, not the inherited profile. Do not replace shared profiles or change another agent to repair ALT.
- Back up configuration and take consistent SQLite snapshots of the shared state and existing target agent database before updating auth. Never copy a live SQLite main file without its WAL and never restore the full shared database as a routine rollback. Incident backup: `/root/_Backups/alt_chatbot_fix_20261015T123919Z`.
- An authenticated `/v1/models` HTTP 200 alone is insufficient: verify a non-delivering synthetic chat completion with the candidate key before copying it. Do not print keys, auth headers, or provider configuration.
- If the candidate is verified and repair is authorized, use the existing key through stdin, not a command-line argument or a manual credential-file edit:

```bash
jq -jr '.models.providers["9rr"].apiKey' /root/.openclaw/openclaw.json | \
  openclaw models auth paste-api-key \
    --agent website-alt --provider 9rr --profile-id 9rr:default
```

- The CLI also updates the non-secret `auth.profiles.9rr:default` metadata in `openclaw.json`. Confirm that all other agent/provider/channel configuration remains unchanged. Never store the key in this skill or a website `.env`.
- A CLI live-refresh warning does not by itself justify a restart: test the safe advisor request first. If required, restart only the host user's Gateway once, let active work drain, and wait for `/healthz` plus an actual advisor response. A `/readyz` failure naming an unrelated Telegram account does not imply that the website endpoint is unavailable; record it separately and do not change Telegram tokens in this task.
- Keep ALT's Bridge OpenClaw timeout at 60 seconds, DeepSeek fallback at 25 seconds, and website `OPENCLAW_TIMEOUT_SECONDS` default at 90 seconds. The outer deadline must cover both provider budgets plus overhead. Update `website/views.py` and `.env.example` together; preserve an explicit production environment override unless authorized.
- Bridge reads project settings per request; no Bridge restart is needed for only its ALT timeout entry. The current ALT container bind-mounts source and uses Django autoreload; verify that the server reloaded before testing.
- Confirm multiple consecutive advisor responses and browser selection/submission on desktop and mobile. All synthetic browser requests must rewrite `notify_telegram` to `false` before reaching the server. Check that a non-empty AI answer is rendered and the retry notice is absent.
- For browser smoke tests, an in-memory wrapper around `requestDeepSeekAdvisor` can force its third argument to `false` without network interception or changing production JavaScript. The 2026-10-15 acceptance run verified real frontend submission on desktop 1440x1000 and mobile 390x844, HTTP 200, rendered answers, no retry notice and no JavaScript errors; screenshots are in the incident backup. A separate final public API check took 2.89 seconds. These timings are observations, not a latency guarantee.

```bash
curl -sS --max-time 100 \
  -H 'Content-Type: application/json' \
  -H 'User-Agent: ALT-chatbot-healthcheck' \
  -d '{"course_code":"37_domain_opas","question":"Chuong trinh nay phu hop voi ai?","notify_telegram":false}' \
  https://anhlaptrinh.vn/api/course-advisor/
```

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
