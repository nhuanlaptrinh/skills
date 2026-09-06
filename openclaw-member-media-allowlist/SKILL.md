---
name: openclaw-member-media-allowlist
description: Diagnose, repair, verify, and roll back OpenClaw media attachment path and allowlist problems on Docker member VPS containers. Use when a member reports LocalMediaAccessError, a DOCX/PDF/image/audio/video is created but cannot be sent, Telegram Local Bot API paths are confused with outbound paths, or host paths are being passed into a member container.
---

# OpenClaw Member Media Allowlist

Use this skill for one named member at a time. Separate OpenClaw outbound media reads, Telegram Local Bot API inbound file roots, and host-to-container path mapping. Prefer the narrow managed outbound directory; widen filesystem policy only after explicit owner approval.

## Safety Rules

- Read the VPS preflight documents, member project note, nearest `AGENTS.md`, and production checklist before changing a live member.
- Never print or copy tokens, API keys, cookies, passwords, private keys, `.env` contents, or full configs into logs, skills, or replies.
- Never use `/` as a trusted root. `/root` is a broad high-risk exception and requires explicit owner approval.
- Do not assume a host path exists inside a Docker member. Convert host paths to member-visible paths before sending media.
- Back up `openclaw.json` before changing it; restart only `openclaw-gateway` unless the member container itself must be recreated.
- Do not send a real test attachment unless the owner explicitly requests it and the exact target is known.

## Path Model

Resolve values from the running member instead of hardcoding one member's layout:

```bash
MEMBER=<username>
CONTAINER="user-${MEMBER}"
docker inspect "$CONTAINER" --format '{{range .Mounts}}{{println .Source " -> " .Destination}}{{end}}'
docker exec "$CONTAINER" sh -lc 'printf "HOME=%s\n" "$HOME"; openclaw config get agents.defaults.workspace; openclaw config get tools.fs --json'
```

Typical member-visible paths are:

```text
<HOME>/.openclaw/workspace
<HOME>/.openclaw/media/outbound
<HOME>/.openclaw/media/inbound
```

For Minh Vuong, `<HOME>` is `/root`. Other members may use `/home/<member>`. A host source such as `/root/Apps/member_vps/docker-users/data/<member>/root/...` is not automatically visible inside the member; it normally maps to `/root/...` or `/home/<member>/...`.

## Boundary Decision

1. **Outbound send failure:** stage a validated file under `<state-dir>/media/outbound/` and pass the member-visible path to `message`.
2. **Workspace send failure:** check sender/tool policy. `tools.fs.workspaceOnly=false` permits host-local media only when the agent is allowed to read it; it does not itself create a literal `/root` allowlist.
3. **Inbound Local Bot API failure:** configure `channels.telegram.trustedLocalFileRoots` with the member-visible Local Bot API data root, not the host source path.
4. **Never conflate the two:** `trustedLocalFileRoots` does not fix every outbound `LocalMediaAccessError`.

## Read-Only Diagnosis

Run without changing production:

```bash
docker exec "$CONTAINER" sh -lc 'openclaw config validate'
docker exec "$CONTAINER" sh -lc 'openclaw config get agents.defaults.workspace; openclaw config get tools.fs --json; openclaw config get channels.telegram.trustedLocalFileRoots --json'
docker exec "$CONTAINER" sh -lc 'supervisorctl status openclaw-gateway'
docker exec "$CONTAINER" sh -lc 'set -a; . /root/.openclaw/gateway.env 2>/dev/null || true; set +a; openclaw channels status --probe --channel telegram'
```

For a candidate file, inspect only metadata and structure:

```bash
docker exec "$CONTAINER" sh -lc 'test -r /root/.openclaw/media/outbound/report.docx && unzip -tqq /root/.openclaw/media/outbound/report.docx'
```

Do not treat `message send --dry-run` as a media-read test; it can print a payload without opening the file.

## Standard Repair

1. Create a timestamped backup under `/root/_Backups/openclaw-member-assistant/<member>/`.
2. Confirm the active config path and current values. Preserve unrelated settings.
3. Prefer the narrow fix: copy the artifact into `<state-dir>/media/outbound/` and use that container path.
4. If the owner explicitly authorizes broad outbound reads, set `tools.fs.workspaceOnly=false`. Document the risk; do not edit OpenClaw source or use `localRoots: "any"`.
5. If the owner explicitly requests broad Telegram Local Bot API roots, add the member-visible `/root` or `/home/<member>` path only after confirming the risk. A host path may be recorded for audit, but it does not make that path visible inside the container.
6. Run `openclaw config validate`; if invalid, restore the backup and stop.
7. Restart only the Supervisor program `openclaw-gateway` and wait for it to be `RUNNING`.
8. Run the Telegram probe and confirm `running, connected, works`.

Example values for a member whose HOME is `/root`:

```json
{
  "tools": { "fs": { "workspaceOnly": false } },
  "channels": {
    "telegram": {
      "trustedLocalFileRoots": [
        "/home/<member>/telegram-bot-api",
        "/root"
      ]
    }
  }
}
```

Do not copy this example blindly. Resolve the member's actual Local Bot API path and preserve existing roots. The host path `/root/Apps/member_vps/docker-users/data/<member>/...` is not a substitute for a member-visible path.

## Verification

Confirm all of the following:

- The file exists, is readable, has the expected MIME/extension, and passes format validation.
- The member-visible outbound path is accepted.
- The host source path is not incorrectly passed to the container.
- `openclaw config validate` passes.
- `openclaw-gateway` is `RUNNING` and Telegram reports `connected/works`.
- The Local Bot API sidecar is running and has no published host port.

For an owner-approved real delivery, use one exact target and verify the returned `messageId` plus destination metadata. Record the receipt without recording any secret. Retry at most once after inspecting an ambiguous result.

## Rollback

Restore the timestamped `openclaw.json` backup, validate it, and restart only `openclaw-gateway`. Keep generated media and Local Bot API data unless removal is explicitly requested. Re-run the Telegram probe and report the rollback result.

## Related Skills

- `openclaw-python-docx-telegram`: create/validate DOCX and stage it under `media/outbound`.
- `telegram-local-bot-api-openclaw`: install or verify the Local Bot API sidecar and inbound trusted roots.
- `reliable-media-delivery`: enforce receipt verification and duplicate-send protection.
- `openclaw-member-config-guard`: use only for its config-guard scope; do not make it auto-open media roots.

## Required Handoff

Report the member/container, changed config keys, backup path, validation result, Gateway/Telegram status, test path, receipt if sent, and remaining security caveats. Never report secrets.
