---
name: openclaw-member-model-switch
description: Change the default chat model and image input model for OpenClaw agents in a Docker member VPS, with a dry run, exact backups, validation, and a controlled Gateway reload.
---

# OpenClaw Member Model Switch

## Chính sách model — 2026-10-29

- Chỉ dùng đúng ba model hội thoại/suy luận: `GPT-6.1-sol`, `GPT-6.1-terra`, `GPT-6-astra`. Mặc định khi cài mới hoặc không chỉ định model là `GPT-6.1-sol`.
- Primary, fallback và lựa chọn trong wizard chỉ lấy từ danh sách này; không tự dùng alias/model cũ hoặc bật DeepSeek dù môi trường có key. Giữ provider hiện có và ghép `<provider>/<model-id>` đúng case.
- Trước khi apply, xác minh model đích trong `/v1/models` của provider thực tế; nếu không có thì dừng, không tự đổi tên hay chọn model ngoài danh sách. Chỉ cấu hình hiểu ảnh khi đã kiểm tra backend hỗ trợ.
- Đây là chính sách chọn model, không phải quyền tự đổi runtime đang chạy. Không đổi model STT/TTS/tạo ảnh thành model chat; các tính năng media chuyên dụng giữ workflow và kiểm tra riêng.

Use this skill when a member VPS should use a different 9Router model by default across all configured OpenClaw agents. It operates on the host-side persistent member directory and never recreates a member container.

The reusable updater is:

```text
/root/.agents/skills/openclaw-member-model-switch/scripts/update_member_models.py
```

The defaults requested for the current fleet are:

- Chat: `9r/GPT-6.1-sol`
- Image input: `9r/GPT-6.1-sol`, only after confirming image input on this route.

The supported IDs are `GPT-6.1-sol`, `GPT-6.1-terra`, and `GPT-6-astra`. Verify availability through the target provider's `/v1/models` endpoint before applying. Keep the existing provider prefix in OpenClaw references. Image understanding is not image generation: the updater does not change `agents.defaults.mediaModels.image`.

## Required workflow

1. Identify the persistent directory:

   ```text
   /root/Apps/member_vps/docker-users/data/<member>
   ```

   The script discovers both common layouts: `<member>/.openclaw` and `<member>/root/.openclaw`. If more than one config exists below a member directory, pass the exact intended root with `--openclaw-root <member>/.../.openclaw`; never guess between production and auxiliary configs.

   Confirm `.openclaw/openclaw.json` exists and inspect the configured agent IDs. Do not edit `.env`, Telegram credentials, browser profiles, sessions, or workspaces.

2. Run the updater in dry-run mode first:

   ```bash
   python3 /root/.agents/skills/openclaw-member-model-switch/scripts/update_member_models.py \
     --member-dir /root/Apps/member_vps/docker-users/data/<member>
   ```

   The dry run reports only model-related paths and never writes files. By default it uses provider `9r`; pass the provider already configured by that member when it differs, for example `--provider 9rt` or `--provider token-codex`. Use `--default-model` and `--vision-model` to select different exact IDs when needed.
   For a member with multiple OpenClaw roots, include the exact root in both dry-run and apply commands:

   ```bash
   python3 /root/.agents/skills/openclaw-member-model-switch/scripts/update_member_models.py \
     --member-dir /root/Apps/member_vps/docker-users/data/<member> \
     --openclaw-root /root/Apps/member_vps/docker-users/data/<member>/root/.openclaw \
     --provider <existing-provider-id>
   ```

3. Apply only after reviewing the dry-run output:

   ```bash
   python3 /root/.agents/skills/openclaw-member-model-switch/scripts/update_member_models.py \
     --member-dir /root/Apps/member_vps/docker-users/data/<member> \
     --provider <existing-provider-id> \
     --apply
   ```

   The script backs up `openclaw.json` and each changed `agents/<id>/agent/models.json` under `/root/_Backups/openclaw-model-switch/<member>/<UTC timestamp>/`. It updates the default chat model, image model, model allowlist, provider model metadata, each agent's explicit primary model, and matching per-agent model caches.

   Existing fallback arrays are preserved for recovery if the new model is unavailable. Historical session transcripts and session databases are preserved.

4. Validate before reloading:

   ```bash
   docker exec user-<member> sh -lc \
     'HOME=<member-home> openclaw config validate'
   docker exec user-<member> sh -lc \
     'HOME=<member-home> openclaw agents list --bindings'
   ```

5. Reload only the target Gateway. Use the member's actual HOME (`/home/<member>` for standard members; `/root` for legacy root-home members). Do not recreate the container:

   ```bash
   docker kill --signal HUP user-<member>
   sleep 5
   docker exec user-<member> sh -lc \
     'HOME=<member-home> openclaw channels status --probe'
   ```

   A brief `ECONNREFUSED` immediately after HUP can occur while Supervisor respawns the Gateway; probe again after the process is present. Confirm configured Telegram/Zalo channels return `running` and `connected` before finishing.

6. Run one isolated no-delivery smoke test per configured agent. Use a unique session key and do not pass `--deliver`:

   ```bash
   docker exec user-<member> sh -lc \
     'HOME=<member-home> openclaw agent --agent <agent_id> \
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
