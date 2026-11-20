---
name: 9router
description: Entry point for 9Router — local/remote AI gateway with OpenAI-compatible REST for chat, image, TTS, embeddings, web search, web fetch. Use when the user mentions 9Router, NINEROUTER_URL, or wants AI without writing provider boilerplate. This skill covers setup + indexes capability skills; fetch the relevant capability SKILL.md from the URLs below when needed.
---

# 9Router

Local/remote AI gateway exposing OpenAI-compatible REST. One key, many providers, auto-fallback.

## Setup

```bash
export NINEROUTER_URL="http://localhost:20128"      # or VPS / tunnel URL
export NINEROUTER_KEY="sk-..."                      # from Dashboard → Keys (only if requireApiKey=true)
```

All requests: `${NINEROUTER_URL}/v1/...` with header `Authorization: Bearer ${NINEROUTER_KEY}` (omit if auth disabled).

Verify: `curl $NINEROUTER_URL/api/health` → `{"ok":true}`

## Discover models

For the local Token Codex service at `https://codex.anhlaptrinh.vn/v1`, the current chat-model choices are `gpt-6.2-sol` (default), `GPT-6.1-terra`, and `gpt-6.2-astra`. Keep these exact case-sensitive IDs in new instructions and configurations, and verify the selected model through `/v1/models`. This list applies to Token Codex; other providers and media capabilities use their own discovered catalogs. Updating this skill does not change existing runtime configuration. The website uses the exact API IDs for display names and copyable examples alike. Label `gpt-6.2-sol` as the default for new installations.

```bash
curl $NINEROUTER_URL/v1/models                  # chat/LLM (default)
curl $NINEROUTER_URL/v1/models/image            # image-gen
curl $NINEROUTER_URL/v1/models/tts              # text-to-speech
curl $NINEROUTER_URL/v1/models/embedding        # embeddings
curl $NINEROUTER_URL/v1/models/web              # web search + fetch (entries have `kind` field)
curl $NINEROUTER_URL/v1/models/stt              # speech-to-text
curl $NINEROUTER_URL/v1/models/image-to-text    # vision
```

Use `data[].id` as `model` field in requests. Combos appear with `owned_by:"combo"`.

Response shape:
```json
{ "object": "list", "data": [
  { "id": "openai/gpt-5", "object": "model", "owned_by": "openai", "created": 1735000000 },
  { "id": "tavily/search", "object": "model", "kind": "webSearch", "owned_by": "tavily", "created": 1735000000 }
]}
```

## Capability skills

When the user needs a specific capability, fetch that skill's `SKILL.md` from its raw URL:

| Capability | Raw URL |
|---|---|
| Chat / code-gen | https://raw.githubusercontent.com/decolua/9router/refs/heads/master/skills/9router-chat/SKILL.md |
| Image generation | https://raw.githubusercontent.com/decolua/9router/refs/heads/master/skills/9router-image/SKILL.md |
| Text-to-speech | https://raw.githubusercontent.com/decolua/9router/refs/heads/master/skills/9router-tts/SKILL.md |
| Speech-to-text | https://raw.githubusercontent.com/decolua/9router/refs/heads/master/skills/9router-stt/SKILL.md |
| Embeddings | https://raw.githubusercontent.com/decolua/9router/refs/heads/master/skills/9router-embeddings/SKILL.md |
| Web search | https://raw.githubusercontent.com/decolua/9router/refs/heads/master/skills/9router-web-search/SKILL.md |
| Web fetch (URL → markdown) | https://raw.githubusercontent.com/decolua/9router/refs/heads/master/skills/9router-web-fetch/SKILL.md |

## Errors

- 401 → set/refresh `NINEROUTER_KEY` (Dashboard → Keys)
- 400 `Invalid model format` → check `model` exists in `/v1/models/<kind>`
- 503 `All accounts unavailable` → wait `retry-after` or add another provider account

## GPT-6.2 pricing on this VPS (2026-11-18)

Native Standard overrides: codex/openai GPT-6.2 Astra and Sol plus openai/text-embedding-3-small. Source: https://developers.openai.com/api/docs/pricing. See /root/_Backups/9router_pricing_20261118T095104Z/README.md for 0.5.119's non-duplicating reasoning override. Native long-context correction installed on disk in /usr/lib/node_modules/9router/app/.next-cli-build/server/chunks/9100.js after checking the vendor hash and isolated raw/daily writes. It takes effect on the next normal process start; no restart is required or scheduled for the billing portals. A package upgrade may replace this file: verify against the new version rather than reapplying an old bundle. Historical native raw/daily costs were left unchanged. The ALT and partner portals already account for successful zero-cost rows and short-priced calls above 272,000 input tokens; do not bill customers twice. For dry-run/verification, maintenance and rollback evidence see /root/_Backups/9router62_billing_20261118T095846Z/README.md. No Fast/Ultrafast or 12h write surcharges without actual usage evidence.
