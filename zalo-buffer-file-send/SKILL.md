---
name: zalo-buffer-file-send
description: Send Zalo attachments from any OpenClaw member through the existing Gateway buffer and verify the destination receipt when the normal local-media route times out.
---

# Zalo buffer file send

Use this skill when a Zalo file reports `Timed out waiting for upload acknowledgement`, when logs show `media` with an empty `buffer`, or when a local attachment path is accepted but no media receipt is returned. A healthy Zalo channel probe and working text messages do not prove that file upload works.

## Files and deployment

- Reusable template: `/root/.agents/skills/zalo-buffer-file-send/`
- Member copy: `<member-data-dir>/.openclaw/workspace/skills/zalo-buffer-file-send/`
- Main helper: `scripts/send_buffer_attachment.py`
- The helper uses the member's already-running Gateway at `127.0.0.1:18789`; it does not create a second Zalo login or listener and does not require a Gateway restart.

Resolve the exact container name and member home from the member's project note before copying. A portable deployment is:

```bash
MEMBER_DATA_DIR=/root/Apps/member_vps/docker-users/data/<member>
CONTAINER=user-<member>
MEMBER_HOME=/home/<member>
docker exec "$CONTAINER" mkdir -p "$MEMBER_HOME/.openclaw/workspace/skills/zalo-buffer-file-send/scripts"
docker cp /root/.agents/skills/zalo-buffer-file-send/SKILL.md \
  "$CONTAINER:$MEMBER_HOME/.openclaw/workspace/skills/zalo-buffer-file-send/SKILL.md"
docker cp /root/.agents/skills/zalo-buffer-file-send/scripts/send_buffer_attachment.py \
  "$CONTAINER:$MEMBER_HOME/.openclaw/workspace/skills/zalo-buffer-file-send/scripts/send_buffer_attachment.py"
docker exec "$CONTAINER" chmod 0750 \
  "$MEMBER_HOME/.openclaw/workspace/skills/zalo-buffer-file-send/scripts/send_buffer_attachment.py"
```

Back up an existing member skill and AGENTS file under `/root/_Backups/<member>-zalo-buffer-file-send/<UTC-timestamp>/` before replacing them. Do not copy credentials, cookies, QR data, or a real target ID into this skill.

## Dry-run and send

Use an explicit destination prefix every time:

```bash
# Direct user
docker exec "$CONTAINER" python3 "$MEMBER_HOME/.openclaw/workspace/skills/zalo-buffer-file-send/scripts/send_buffer_attachment.py" \
  --target user:<user-id> --file "$MEMBER_HOME/.openclaw/workspace/output/<file>" --dry-run

# Group
docker exec "$CONTAINER" python3 "$MEMBER_HOME/.openclaw/workspace/skills/zalo-buffer-file-send/scripts/send_buffer_attachment.py" \
  --target group:<group-id> --file "$MEMBER_HOME/.openclaw/workspace/output/<file>" \
  --message 'Nội dung tùy chọn'
```

After the dry-run, run the same command without `--dry-run`. The helper reads the Gateway token in memory from the member's local OpenClaw config, base64 encodes the file as `buffer`, sends it through `/tools/invoke`, and prints only sanitized delivery metadata. Inputs are the target, readable non-empty file, and optional message. Output is JSON with `status`, platform `messageId`, receipt thread ID, filename, and byte count on dry-run.

The helper now derives an idempotency hash per target/file/message and records `in_flight`, `unknown`, or `sent` under `/tmp/openclaw-zalo-delivery/`. A prior `unknown` or `sent` request is refused until receipt/history reconciliation; use `--force-retry` only after proving that no successful delivery exists. This prevents a timeout or Gateway restart from blindly sending the same attachment again.

Accept a send only when `status` is `sent`, a platform message ID exists, and the receipt thread or conversation ID equals the numeric ID in the explicit target. For a `group:` target, the receipt thread/conversation and media part kind are authoritative; OpenClaw may label the transport `via: direct` even when the explicit group target and matching thread receipt prove group delivery. Reject only when the thread does not match or the media receipt is absent. If receipt data is missing or ambiguous, stop and inspect Gateway logs/history instead of retrying.

Do not use `openclaw message send --media <local-path>` for this failure mode, do not call standalone `zca-js`, and do not start another Zalo connection. The old route can pass a local `media` path while leaving `buffer` empty; `zca-js` then waits for a WebSocket `file_done` acknowledgement until timeout. The buffer route supplies the bytes before the upload starts and keeps the existing session as the single sender.

## Verification and rollback

Validate the helper before deployment and after copying it:

```bash
python3 -m py_compile /root/.agents/skills/zalo-buffer-file-send/scripts/send_buffer_attachment.py
docker exec "$CONTAINER" python3 "$MEMBER_HOME/.openclaw/workspace/skills/zalo-buffer-file-send/scripts/send_buffer_attachment.py" \
  --target user:<user-id> --file "$MEMBER_HOME/.openclaw/workspace/output/<file>" --dry-run
```

A failed or ambiguous live call is not proof of failure or success; check the receipt/history before one controlled retry. If the bounded `zca-js` acknowledgement guard is also being changed, use the `openclaw-zalo-reliability` guard procedure separately, with a bundle backup and syntax/probe checks. The buffer helper itself changes no package, config, session, or credential. Roll back by removing the member helper/skill or restoring the timestamped backup; no service restart is needed.

## Permanent core guard

The helper is the safe sender; the member can also install a narrow OpenClaw core guard so ordinary `message.send` calls with `media=<local path>` are hydrated into `buffer` automatically before Zalo dispatch. This is the fix for preventing recurrence, while the helper remains the fallback and verification path.

Run the patch script from the VPS host (where Docker and `/root/_Backups` are available), against the exact member container. Do not run this host patch script from inside the member container. It is dry-run by default and creates a timestamped bundle backup before applying:

```bash
/root/.agents/skills/zalo-buffer-file-send/scripts/patch_openclaw_buffer_hydration.sh \
  --container user-<member> --dry-run
/root/.agents/skills/zalo-buffer-file-send/scripts/patch_openclaw_buffer_hydration.sh \
  --container user-<member> --apply
docker exec user-<member> supervisorctl restart openclaw-gateway
docker exec user-<member> node --check /usr/lib/node_modules/openclaw/dist/message-action-normalization-*.mjs
```

The guard changes only `message-action-normalization-*`: when `send` has no buffer but has a media/file path, it loads the bytes using the existing media policy, stages them into the canonical outbound media store, and replaces the original path before the channel plugin runs. It also sets `buffer`, content type, and filename. Staging matters because the Zalo plugin otherwise may prefer the original local path even after a buffer was created. It fails explicitly on unreadable or disallowed media; it does not bypass media limits or credentials. After an OpenClaw upgrade, rerun the dry-run because the hashed bundle filename and anchors may change. Roll back by restoring the saved bundle from `/root/_Backups/<member>-zalo-buffer-hydration/<UTC-timestamp>/` and restarting only `openclaw-gateway`.

Verify the core fix with one owner-approved direct or group test using the ordinary `message` action and a local `media` path. Require `deliveryStatus: sent`, a media receipt, and a matching thread/conversation ID. Do not treat a text-only channel probe as attachment verification.
