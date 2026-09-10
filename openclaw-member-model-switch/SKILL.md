---
name: openclaw-member-model-switch
description: Change the default chat model and image input model for OpenClaw agents in a Docker member VPS, with a dry run, exact backups, validation, and a controlled Gateway reload.
---

# OpenClaw Member Model Switch

Use this skill when a member VPS should use a different 9Router model by default across all configured OpenClaw agents. It operates on the host-side persistent member directory and never recreates a member container.

The reusable updater is:

```text
/root/.agents/skills/openclaw-member-model-switch/scripts/update_member_models.py
```

The defaults requested for the current fleet are:

- Chat: `9r/ds-v4-flash`
- Image input: `9r/ds-v4-flash-vision-exp`

These are exact model IDs exposed by the 9Router `/v1/models` endpoint. Keep the `9r/` provider prefix in OpenClaw references.

## Required workflow

1. Identify the persistent directory:

   ```text
   /root/Apps/member_vps/docker-users/data/<member>
   ```

   Confirm `.openclaw/openclaw.json` exists and inspect the configured agent IDs. Do not edit `.env`, Telegram credentials, browser profiles, sessions, or workspaces.

2. Run the updater in dry-run mode first:

   ```bash
   python3 /root/.agents/skills/openclaw-member-model-switch/scripts/update_member_models.py \
     --member-dir /root/Apps/member_vps/docker-users/data/<member>
   ```

   The dry run reports only model-related paths and never writes files. Use `--default-model` and `--vision-model` to select different exact IDs when needed.

3. Apply only after reviewing the dry-run output:

   ```bash
   python3 /root/.agents/skills/openclaw-member-model-switch/scripts/update_member_models.py \
     --member-dir /root/Apps/member_vps/docker-users/data/<member> \
     --apply
   ```

   The script backs up `openclaw.json` and each changed `agents/<id>/agent/models.json` under `/root/_Backups/openclaw-model-switch/<member>/<UTC timestamp>/`. It updates the default chat model, image model, model allowlist, provider model metadata, each agent's explicit primary model, and matching per-agent model caches.

   Existing fallback arrays are preserved for recovery if the new model is unavailable. Historical session transcripts and session databases are preserved.

4. Validate before reloading:

   ```bash
   docker exec user-<member> sh -lc \
     'HOME=/home/<member> openclaw config validate'
   docker exec user-<member> sh -lc \
     'HOME=/home/<member> openclaw agents list --bindings'
   ```

5. Reload only the target Gateway. Do not recreate the container:

   ```bash
   docker kill --signal HUP user-<member>
   sleep 5
   docker exec user-<member> sh -lc \
     'HOME=/home/<member> openclaw channels status --probe'
   ```

   A brief `ECONNREFUSED` immediately after HUP can occur while Supervisor respawns the Gateway; probe again after the process is present. Confirm configured Telegram/Zalo channels return `running` and `connected` before finishing.

6. Run one isolated no-delivery smoke test per configured agent. Use a unique session key and do not pass `--deliver`:

   ```bash
   docker exec user-<member> sh -lc \
     'HOME=/home/<member> openclaw agent --agent <agent_id> \
       --session-key agent:<agent_id>:model-switch-check \
       --message "Reply exactly MODEL_SWITCH_OK. Do not call tools." \
       --thinking off --timeout 120 --json'
   ```

   Inspect only the returned `provider` and `model` metadata. For an image-model routing check, repeat with `--model 9r/<vision-model>` and no delivery. Never send a real Telegram/Zalo test message as part of this skill.

## Safety and rollback

- Never print, copy into this skill, or record API keys, bot tokens, cookies, passwords, or full config contents.
- Stop if the provider `9r` is absent, the config is invalid, or the requested model IDs are not returned by the router's `/v1/models` endpoint.
- Keep the generated backup until channel probes and smoke tests pass.
- To roll back, restore only the backed-up configuration/cache files, run `openclaw config validate`, and HUP the same Gateway. Do not restore sessions or recreate the member container.

## Outputs

- Updated member OpenClaw model configuration in the persistent member directory.
- A timestamped backup under `/root/_Backups/openclaw-model-switch/`.
- Validation and no-delivery smoke-test evidence in the operator log.
