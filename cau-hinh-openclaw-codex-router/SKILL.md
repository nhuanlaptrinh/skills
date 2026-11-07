---
name: cau-hinh-openclaw-codex-router
description: Apply a custom Codex-compatible API to OpenClaw on another machine, set GPT-6.1-sol as the default model, and verify it without storing or exposing API keys in the skill.
---

# OpenClaw Codex Router

Use this skill when a user wants to reuse the custom Codex API configuration on another OpenClaw installation. It configures OpenClaw only; use `cau-hinh-alt-codex_new` for Codex CLI or IDE extension files.

## Defaults

- Provider: `codex-router`
- Base URL: `https://codex.anhlaptrinh.vn/v1`
- API mode: `openai-completions`
- Model: `GPT-6.1-sol`
- Default reference: `codex-router/GPT-6.1-sol`

Do not name this provider `codex`: OpenClaw may route that reserved name through its Codex plugin and ignore the custom base URL. Keep the provider name `codex-router` unless the target installation has a documented non-conflicting provider name.

## Required Workflow

1. Resolve the target OpenClaw config. Prefer the active path reported by `openclaw config file`; otherwise use `~/.openclaw/openclaw.json`.
2. Ask the user for the API key if it is not already available. Put it in a temporary environment variable, never in this skill, a sample file, shell history, or the final response.
3. Run the helper in dry-run mode first:

   ```bash
   node scripts/apply_openclaw_codex.mjs
   ```

4. Apply only after reviewing the dry-run summary:

   ```bash
   node scripts/apply_openclaw_codex.mjs --apply
   ```

   The helper backs up `openclaw.json`, updates `models.providers`, sets `agents.defaults.model.primary`, adds the model to the allowlist, and synchronizes discovered `agents/*/agent/models.json` caches. It does not modify Telegram/Zalo credentials, sessions, workspaces, or channel bindings.
5. Validate the written configuration before restarting:

   ```bash
   openclaw config validate
   openclaw models status
   ```

   On Windows, use `openclaw.cmd` when the PowerShell shim is blocked by execution policy.
6. Restart the gateway only after validation, then run a live no-delivery probe:

   ```bash
   openclaw gateway restart
   openclaw gateway status
   openclaw models status --probe --probe-provider codex-router
   ```

   A successful probe must show `codex-router/GPT-6.1-sol`, status `ok`, and the custom gateway URL in the transport log. Never use a real Telegram/Zalo delivery as the smoke test.
7. Remove the temporary API-key environment variable after the run.

## Variants

Override only when the user asks for a different target:

```bash
node scripts/apply_openclaw_codex.mjs \
  --base-url https://example.invalid/v1 \
  --model GPT-6.1-sol \
  --provider codex-router \
  --apply
```

The key is read from `CODEX_API_KEY` by default. Use `--api-key-env OPENAI_API_KEY` when that is the approved environment variable. The helper rejects a missing key during `--apply` and never prints its value.

## Safety

- Do not print full OpenClaw config files or API keys; report only provider, base URL, model, and `present/missing` credential state.
- Keep the timestamped backup until validation, gateway status, and the live probe pass.
- If the probe targets `api.openai.com` instead of the configured base URL, stop and rename the provider away from reserved `codex` before retrying.
- If the gateway is managed by a service, restart only that gateway after validation; do not recreate containers or alter unrelated channels.
- Existing unrelated warnings may be reported, but do not fix them as part of this skill unless they block validation or the requested model.