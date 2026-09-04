---
name: telegram-local-bot-api-openclaw
description: Install, configure, migrate, verify, troubleshoot, and roll back Telegram Local Bot API for OpenClaw on a standalone Linux VPS or Docker member VPS. Use when Telegram bots need files beyond cloud Bot API limits (especially uploads over 50 MB or downloads over 20 MB), when setting channels.telegram.apiRoot/trustedLocalFileRoots/mediaMaxMb, or when cloning this setup to another VPS/member.
---

# Telegram Local Bot API for OpenClaw

Use this skill to run Telegram's official Local Bot API server beside OpenClaw. The local server removes the cloud Bot API download/upload limits, while OpenClaw still needs a matching local API root, trusted file root, and media limit.

## Security and Credential Rules

- Require a Telegram api_id (integer) and api_hash (hex string) from my.telegram.org. Never guess them and never substitute an RSA public key or a bot token.
- Keep api_hash, bot tokens, cookies, and private keys out of this skill, logs, chat replies, shell history, and git. Store them in a dedicated mode-600 env/secret file.
- One Telegram app credential pair can technically be reused by multiple Local Bot API VPS instances. Prefer separate app credentials per trust boundary (for example production and staging): a compromise or rate-limit event on one VPS then does not affect every instance.
- Reuse is acceptable only when the VPSes are under the same administrative trust boundary. Shared credentials also share Telegram app identity, quotas, and any suspension impact.
- Do not run the same bot token in polling mode on two VPSes at once. Each bot token needs one active update consumer; duplicate consumers cause 409 Conflict, missed updates, or duplicate processing. Use different bot tokens for parallel VPSes, or perform a logout handover before moving one bot.
- Read references/security-and-reuse.md when deciding whether to reuse credentials.

## Preconditions

Before changing an existing VPS, read:

1. /root/_Second_AI_Brain/START_HERE.md
2. /root/_Second_AI_Brain/01_Ban_Do_VPS.md
3. /root/_Second_AI_Brain/02_Danh_Sach_Project.md
4. The relevant project note under /root/_Second_AI_Brain/projects/
5. /root/_Second_AI_Brain/checklists/truoc_khi_sua_production.md for production changes
6. Any nearer AGENTS.md in the OpenClaw project/workspace

Inspect the current gateway, Telegram accounts, Docker, disk, and ports before stopping anything:

~~~bash
openclaw --version
openclaw gateway status
openclaw config validate
openclaw channels status --channel telegram
docker --version
docker ps -a --filter name=telegram-bot-api
ss -ltnp | rg ':8081\b|:18789\b' || true
free -h
df -h /
~~~

Do not expose the Local Bot API port publicly. Bind it to loopback on a standalone VPS, or publish no host port at all for a Docker member sidecar.

## Variables

Choose paths that match the target VPS. The following layout matches the ALT VPS standard:

~~~bash
OC_ROOT=/root/.openclaw
INFRA_ROOT=/root/_Infra/telegram-bot-api
API_ROOT=http://127.0.0.1:8081
MEDIA_MAX_MB=2000
~~~

Use a narrower data directory if the deployment has a different service user. Do not use / as a trusted media root.

For a Docker member, use member-specific values instead of the standalone defaults:

```bash
MEMBER=thanhhuy
MEMBER_CONTAINER=user-${MEMBER}
MEMBER_HOME=/home/${MEMBER}
MEMBER_DATA_HOST=/root/Apps/member_vps/docker-users/data/${MEMBER}/.openclaw/telegram-bot-api/data
MEMBER_DATA_PATH=${MEMBER_HOME}/.openclaw/telegram-bot-api/data
MEMBER_TRUSTED_ROOT=${MEMBER_HOME}/.openclaw/telegram-bot-api
MEMBER_NETWORK=telegram-local-${MEMBER}
API_CONTAINER=telegram-bot-api-${MEMBER}
API_ROOT=http://${API_CONTAINER}:8081
```

The member's `apiRoot` must use the Docker DNS name, not `127.0.0.1`: inside the member, loopback is the member container itself. The sidecar work directory and the member trusted root must resolve to the same absolute path so Local Bot API `file_path` values are readable by OpenClaw.

## Choose the deployment topology

- **Standalone VPS/root OpenClaw:** run the Local Bot API container with `127.0.0.1:8081:8081`; set `apiRoot` to `http://127.0.0.1:8081` and trusted root to the host data directory.
- **Docker member VPS:** run one sidecar container on a dedicated user-defined Docker network, attach only the target member to that network, publish no host port, and set `apiRoot` to `http://telegram-bot-api-<member>:8081`.
- **One bot, one poller:** a bot token must not be polled by the Cloud API and Local API at the same time. Stop the actual member Gateway before `logOut`, offset checks, or configuration changes.

## Installation Workflow

### 1. Prepare credentials and files

Obtain the api_id and api_hash from my.telegram.org -> API development tools. Create the env file through a secure editor or secret manager; do not put real values in a command that will be saved in shell history:

~~~bash
install -d -m 700 "$INFRA_ROOT"
install -m 600 /dev/null "$INFRA_ROOT/.env"
install -d -m 700 "$INFRA_ROOT/data"
~~~

The file must contain only:

~~~dotenv
TELEGRAM_API_ID=<integer>
TELEGRAM_API_HASH=<hex-string>
~~~

Check permissions without printing contents:

~~~bash
stat -c '%A %U:%G %n' "$INFRA_ROOT/.env" "$INFRA_ROOT/data"
~~~

### 2. Deploy the Local Bot API container

Use a pinned image digest after pulling and inspecting the image. The following example uses the maintained aiogram/telegram-bot-api image that packages the official tdlib/telegram-bot-api server:

~~~yaml
services:
  telegram-bot-api:
    image: aiogram/telegram-bot-api@sha256:<verified-digest>
    container_name: telegram-bot-api
    restart: unless-stopped
    env_file:
      - .env
    environment:
      TELEGRAM_LOCAL: "1"
      TELEGRAM_HTTP_IP_ADDRESS: "0.0.0.0"
      TELEGRAM_HTTP_PORT: "8081"
    ports:
      - "127.0.0.1:8081:8081"
    volumes:
      - ./data:/var/lib/telegram-bot-api
~~~

Create this as $INFRA_ROOT/docker-compose.yml, then run:

~~~bash
cd "$INFRA_ROOT"
docker pull aiogram/telegram-bot-api:latest
docker image inspect aiogram/telegram-bot-api:latest --format '{{index .RepoDigests 0}}'
docker compose config -q
docker compose up -d
docker compose ps
~~~

The container must listen on 0.0.0.0 internally because Docker publishes it on the host loopback. Never change the host binding to 0.0.0.0 unless an explicit, reviewed reverse-proxy design requires it.

Check the HTTP listener. A 404 JSON response at / is expected; it proves the server is reachable:

~~~bash
curl -sS -o /tmp/telegram-local-root.json -w 'http=%{http_code}\n' "$API_ROOT/"
~~~

Before switching OpenClaw, check every bot token through the local API without printing tokens. Use the bundled verifier when available:

~~~bash
"$SKILL_DIR/scripts/verify_local_bot_api.sh" --api-root "$API_ROOT" --compose-dir "$INFRA_ROOT"
~~~

If the verifier cannot resolve a SecretRef-backed token, use openclaw channels status --probe --channel telegram after the OpenClaw switch.

### 3. Back up and hand over bot polling

Create a timestamped, mode-600 backup before changing OpenClaw:

~~~bash
BACKUP_DIR=/root/_Backups/openclaw
install -d -m 700 "$BACKUP_DIR"
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
cp -a "$OC_ROOT/openclaw.json" "$BACKUP_DIR/openclaw-before-telegram-local-bot-api-$STAMP.json"
chmod 600 "$BACKUP_DIR/openclaw-before-telegram-local-bot-api-$STAMP.json"
~~~

Stop the gateway before logging bots out of the public API. This prevents a second polling client during the handover:

~~~bash
systemctl --user stop openclaw-gateway.service
systemctl --user is-active openclaw-gateway.service || true
~~~

Call logOut on https://api.telegram.org for every configured bot. Resolve tokens internally from the existing OpenClaw config/secret provider and print only account labels and ok status. Abort if any bot cannot be logged out; do not paste tokens into output.

### 4. Point OpenClaw at the local server

Set the global Telegram values so account-specific configs inherit them. Preserve any existing trusted roots when merging the list:

~~~bash
openclaw config patch --stdin <<'JSON'
{"channels":{"telegram":{"apiRoot":"http://127.0.0.1:8081","trustedLocalFileRoots":["/root/_Infra/telegram-bot-api/data"],"mediaMaxMb":2000}}}
JSON
~~~

If the target VPS already has trusted roots, include them in the array instead of replacing them. Use a lower positive mediaMaxMb only when disk, memory, or policy requires it; 2000 MB matches the Local Bot API upload ceiling. This OpenClaw setting controls its own media read limit and is separate from Telegram's server limit.

Validate before starting the gateway:

~~~bash
openclaw config validate
openclaw config get channels.telegram.apiRoot
openclaw config get channels.telegram.mediaMaxMb
openclaw config get channels.telegram.trustedLocalFileRoots --json
~~~

### 5. Restart and verify

~~~bash
systemctl --user start openclaw-gateway.service
systemctl --user is-active openclaw-gateway.service
openclaw gateway status
openclaw channels status --probe --channel telegram
ss -ltnp | rg ':8081\b|:18789\b'
docker compose -f "$INFRA_ROOT/docker-compose.yml" ps
~~~

Require every Telegram account to report running, connected, and works. Confirm 8081 is bound only to 127.0.0.1. Check recent logs for startup errors, 409 Conflict, 413 Request Entity Too Large, or media path errors:

~~~bash
journalctl --user -u openclaw-gateway.service --since '5 minutes ago' --no-pager -o cat | rg -i 'telegram|error|failed|conflict|too large|413' || true
docker logs --since 5m telegram-bot-api 2>&1 | tail -100
~~~

Do not send a test message to a real chat unless the user explicitly requests it. The safe verification is local getMe, channel probe, listener scope, and healthy polling connections. A real user can then send a video over 50 MB to the bot and ask it to send a video over 20 MB.

## Mandatory slow-reply recovery gate before handoff

Installing Local Bot API is not complete until the companion skill
`/root/.agents/skills/openclaw-telegram-slow-reply-recovery/SKILL.md` has been used
for the same VPS, Gateway, agent, and Telegram account. This gate is mandatory
before declaring the Cloud -> Local handover healthy or handing the bot back to
the user. Do not treat `getMe` or `connected` alone as proof that replies will
dispatch promptly.

Run the companion skill's account-scoped diagnostics after the Local API is
reachable and the Gateway has restarted. At minimum, collect redacted results
for config validation, Telegram probe JSON, effective agent/binding, active
sessions and token counts, Gateway/Supervisor state, recent Telegram/dispatch/
provider logs, and one-owner/polling checks. If the latency audit is available,
run it for the target account; otherwise correlate only account-labeled inbound
and outbound events and mark unpaired measurements as unverified.

For a Docker member, use `docker exec` equivalents and the Supervisor program
`openclaw-gateway`; never use the host systemd unit as a substitute. If the
diagnostics show a stale/high offset, duplicate update spooling, `409 Conflict`,
wrong routing, session lock/bloat, dispatch failure, provider timeout, or an
event-loop stall, stop the affected Gateway, back up config/state, and follow
`openclaw-telegram-slow-reply-recovery` plus
`sua-loi-telegram-offset-openclaw` before handoff. For `tokenFile` members,
resolve the token only into a mode-600 ephemeral config; for Local API offset
checks use the sidecar Docker IP and never call `getUpdates` while the Gateway
is running.

The handoff gate passes only when all of these are true:

- the target account reports `running`, `connected`, and `works`, with no active
  reconnect loop or duplicate poller;
- the effective account, agent, workspace, DM/group policy, and Local API root
  are the intended ones;
- no unaddressed offset mismatch, repeated update ID, `409 Conflict`, dispatch
  error, provider timeout, or outbound Telegram error appears in the verification
  window;
- event-loop health and CPU are stable enough for the member's workload, and any
  provider latency is recorded separately from Telegram transport latency;
- config validation succeeds, the sidecar is healthy, the listener scope is
  correct, and the backup path plus any remaining media/provider limitation are
  recorded without secrets.

Do not send a real Telegram test during this gate unless the user explicitly
authorizes it. If any pass criterion is unknown or fails, stop the handoff,
report the exact blocked check, and keep the previous known-good polling path
until a verified repair is complete.

## Docker member workflow

Use this workflow when OpenClaw runs in a member container under Supervisor (for example `user-<member>`). It leaves the main VPS OpenClaw and all other members unchanged.

### 1. Preflight and backup

Resolve the real container, persistent home, OpenClaw account, and Supervisor process before changing anything:

```bash
docker inspect "$MEMBER_CONTAINER" --format 'status={{.State.Status}} mounts={{json .Mounts}} networks={{json .NetworkSettings.Networks}}'
docker exec "$MEMBER_CONTAINER" supervisorctl status
docker exec -e HOME="$MEMBER_HOME" "$MEMBER_CONTAINER" sh -lc \
  'openclaw config validate && openclaw channels status --probe --channel telegram'
```

Back up the member config and SQLite state, including WAL/SHM companions, outside live data:

```bash
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
BACKUP_DIR=/root/_Backups/member_vps/${MEMBER}/telegram-local-api-${STAMP}
install -d -m 700 "$BACKUP_DIR"
cp -a /root/Apps/member_vps/docker-users/data/${MEMBER}/.openclaw/openclaw.json \
  "$BACKUP_DIR/openclaw.json.before"
for file in \
  /root/Apps/member_vps/docker-users/data/${MEMBER}/.openclaw/state/openclaw.sqlite \
  /root/Apps/member_vps/docker-users/data/${MEMBER}/.openclaw/state/openclaw.sqlite-wal \
  /root/Apps/member_vps/docker-users/data/${MEMBER}/.openclaw/state/openclaw.sqlite-shm; do
  [ -f "$file" ] && cp -a "$file" "$BACKUP_DIR/"
done
chmod 600 "$BACKUP_DIR"/*
```

Do not copy token files into the backup unless a rollback explicitly requires it.

### 2. Stop the member poller and check offset

Supervisor is not a systemd user unit. Stop only the member Gateway and verify its process/listener is gone:

```bash
docker exec "$MEMBER_CONTAINER" supervisorctl stop openclaw-gateway
docker exec "$MEMBER_CONTAINER" supervisorctl status openclaw-gateway
docker exec "$MEMBER_CONTAINER" sh -lc \
  'ss -ltnp 2>/dev/null | grep ":18789\\b" && exit 1 || true'
```

Run `sua-loi-telegram-offset-openclaw` in dry-run mode before changing offset. Member configs commonly use `tokenFile`, while the helper accepts `botToken` or an environment SecretRef; resolve the token internally into a short-lived mode-600 config in `/tmp`, never print it, and delete it in cleanup. Because the real poller is Supervisor-managed, pass a deliberately nonexistent `--gateway-unit` only after the member process is proven stopped:

```bash
python3 /root/.agents/skills/sua-loi-telegram-offset-openclaw/scripts/repair_telegram_offset.py \
  --account-id <account-id> \
  --config /tmp/<ephemeral-config>.json \
  --state-db /root/Apps/member_vps/docker-users/data/<member>/.openclaw/state/openclaw.sqlite \
  --gateway-unit member-<member>-gateway.service \
  --api-root https://api.telegram.org \
  --cloud-check
```

If the result proves `stored_offset > max_update_id`, apply only with the exact observed `--expected-offset` and a backup directory. If `offset_mismatch=false`, do not delete the row. Never call Cloud `getUpdates` while the member Gateway is running.

### 3. Create the sidecar network and media path

Create a dedicated network and attach only the target member. A Docker restart preserves this attachment; a container recreate does not, so recovery automation must reconnect the network before starting the Gateway:

```bash
docker network inspect "$MEMBER_NETWORK" >/dev/null 2>&1 || \
  docker network create --driver bridge --label com.alt.scope=member-${MEMBER} "$MEMBER_NETWORK"
docker network inspect "$MEMBER_NETWORK" --format '{{range .Containers}}{{.Name}}{{"\\n"}}{{end}}' \
  | grep -Fxq "$MEMBER_CONTAINER" || \
  docker network connect --alias openclaw-${MEMBER} "$MEMBER_NETWORK" "$MEMBER_CONTAINER"
install -d -m 700 "$MEMBER_DATA_HOST" "$MEMBER_DATA_HOST/tmp"
```

The current `aiogram/telegram-bot-api` image runs as UID/GID `101:101`; verify this for a changed image digest and make the mounted work directory writable:

```bash
docker run --rm --entrypoint sh aiogram/telegram-bot-api@sha256:<verified-digest> \
  -lc 'id telegram-bot-api'
chown -R 101:101 "$MEMBER_DATA_HOST"
chmod 700 "$MEMBER_DATA_HOST" "$MEMBER_DATA_HOST/tmp"
```

### 4. Deploy the member sidecar

Create `/root/_Infra/telegram-bot-api-<member>/docker-compose.yml` and `.env` with mode `0600`. Keep real `TELEGRAM_API_ID` and `TELEGRAM_API_HASH` only in `.env`; never put them in this skill, compose YAML, shell history, logs, or chat replies.

```yaml
services:
  telegram-bot-api:
    image: aiogram/telegram-bot-api@sha256:<verified-digest>
    container_name: telegram-bot-api-<member>
    restart: unless-stopped
    env_file:
      - .env
    environment:
      TELEGRAM_WORK_DIR: /home/<member>/.openclaw/telegram-bot-api/data
      TELEGRAM_TEMP_DIR: /home/<member>/.openclaw/telegram-bot-api/data/tmp
      TELEGRAM_LOCAL: "1"
      TELEGRAM_HTTP_IP_ADDRESS: "0.0.0.0"
      TELEGRAM_HTTP_PORT: "8081"
    volumes:
      - /root/Apps/member_vps/docker-users/data/<member>/.openclaw/telegram-bot-api/data:/home/<member>/.openclaw/telegram-bot-api/data
    networks:
      - member-local-api

networks:
  member-local-api:
    name: telegram-local-<member>
    external: true
```

The two `.env` keys are:

```dotenv
TELEGRAM_API_ID=<integer>
TELEGRAM_API_HASH=<hex-string>
```

Validate and start:

```bash
cd /root/_Infra/telegram-bot-api-<member>
chmod 600 .env docker-compose.yml
docker compose config -q
docker compose up -d
docker compose ps
docker inspect telegram-bot-api-<member> --format 'status={{.State.Status}} ports={{json .NetworkSettings.Ports}} mounts={{json .Mounts}}'
```

There must be no published host port (`ports` values are `null`). From the member, HTTP `404` at `/` is expected and proves reachability:

```bash
docker exec <member-container> sh -lc \
  'getent hosts telegram-bot-api-<member>; curl -sS -o /dev/null -w "http=%{http_code}\\n" http://telegram-bot-api-<member>:8081/'
```

### 5. Handover Cloud -> Local and configure OpenClaw

With the member Gateway still stopped, call Cloud `logOut` for only the target bot, resolving its token internally and printing only `cloud_logout_ok=true|false`. Check local `getMe` before switching.

Patch only the target member config. The trusted root is the member-visible path, not the host source path:

```bash
docker exec <member-container> sh -lc \
  'openclaw config patch --stdin <<JSON
{"channels":{"telegram":{"apiRoot":"http://telegram-bot-api-<member>:8081","trustedLocalFileRoots":["/home/<member>/.openclaw/telegram-bot-api"],"mediaMaxMb":2000}}}
JSON'
docker exec -e HOME=/home/<member> <member-container> sh -lc \
  'openclaw config validate && openclaw config get channels.telegram.apiRoot && \
   openclaw config get channels.telegram.mediaMaxMb && \
   openclaw config get channels.telegram.trustedLocalFileRoots --json'
```

Start the member Gateway only after sidecar, local `getMe`, and config validation pass:

```bash
docker exec <member-container> supervisorctl start openclaw-gateway
sleep 8
docker exec <member-container> supervisorctl status openclaw-gateway
docker exec -e HOME=/home/<member> <member-container> sh -lc \
  'openclaw channels status --probe --channel telegram'
```

Require the target account to report `running, connected, works`. Do not send a real Telegram message unless explicitly requested.

### 6. Verify member and media path

The bundled `verify_local_bot_api.sh` assumes a host-loopback listener and host OpenClaw root, so it is not a complete member check. Use equivalent checks:

```bash
docker exec <member-container> sh -lc 'python3 - <<"PY"
import json, urllib.request
from pathlib import Path
token = Path("/home/<member>/.openclaw/telegram_bot_token").read_text().strip()
base = "http://telegram-bot-api-<member>:8081/bot" + token
for method in ("getMe", "getWebhookInfo"):
    with urllib.request.urlopen(base + "/" + method, timeout=15) as response:
        payload = json.load(response)
    result = payload.get("result") or {}
    if method == "getMe":
        print({"method": method, "ok": payload.get("ok"), "bot_id": result.get("id"), "username": result.get("username")})
    else:
        print({"method": method, "ok": payload.get("ok"), "has_url": bool(result.get("url")), "pending_update_count": result.get("pending_update_count")})
PY'
docker inspect telegram-bot-api-<member> --format 'status={{.State.Status}} restart={{.HostConfig.RestartPolicy.Name}} published={{json .NetworkSettings.Ports}}'
docker network inspect telegram-local-<member> --format '{{range .Containers}}{{.Name}} {{.IPv4Address}}{{"\\n"}}{{end}}'
ss -ltnp | grep ':8081\\b' || true
```

The safe result is local `getMe ok=true`, webhook URL absent, member channel `connected/works`, sidecar `running`, no host `8081` listener, and the network containing only the target member plus its sidecar. For a final offset check, stop the Gateway and call the helper with the sidecar Docker IP as `--api-root http://<sidecar-ip>:8081`; never use `getUpdates` against a running poller.

After these member checks, run the **Mandatory slow-reply recovery gate before
handoff** above with the member's Supervisor/Gateway and account-specific paths.
The member is not ready for handoff until that companion-skill gate passes.

## Troubleshooting

- error: expected TELEGRAM_API_ID...: the env file is absent, empty, or unreadable. Stop; obtain real credentials instead of guessing.
- 409 Conflict: an old gateway/container is still polling. Stop duplicate gateways, log out the bot from the currently active API server, then start only one poller.
- 413 Request Entity Too Large: confirm OpenClaw loaded the local apiRoot, the Local Bot API is in --local mode, and mediaMaxMb is not below the file size.
- Absolute local file_path cannot be read: mount the same host data directory into the exact absolute path used by the member-visible `TELEGRAM_WORK_DIR` and list its parent in `trustedLocalFileRoots`. For a standalone VPS, the host data path and trusted root must likewise match the path returned by Local Bot API.
- Local media path is not under an allowed directory: this is OpenClaw's own outbound filesystem allowlist, not a Telegram size limit. Put the media under an approved workspace/media root or adjust that separate policy.
- Member sidecar resolves but OpenClaw cannot connect after recreate: reconnect `telegram-local-<member>` to `user-<member>` before starting the Supervisor Gateway. A normal `docker restart` preserves the network attachment; `docker rm/create` does not.
- getMe works but media fails: inspect free disk space, container logs, the trusted root mapping, and the exact file_path returned by local getFile.
- Public API access is blocked: the Local Bot API still needs outbound connectivity to Telegram DCs. A local endpoint does not remove VPS firewall/DNS/proxy requirements.

## Rollback

Keep the Local Bot API data; do not delete it during rollback. Stop OpenClaw, call local logOut for every bot, restore the timestamped openclaw.json backup, and start the gateway against the public API. Only after the public polling path is healthy may the local container be stopped with docker compose stop; use down only when removal is explicitly requested.

For a Docker member, stop only `openclaw-gateway` through Supervisor, call the sidecar's local `logOut` for the target bot, restore the member `openclaw.json` backup, and start the same Supervisor program against `https://api.telegram.org`. After Cloud polling is healthy, run `docker compose stop` in the member sidecar directory. Keep the Docker network and data directory unless removal is explicitly requested; do not recreate the member container as part of rollback.

After a production change, append a redacted entry to /root/_Second_AI_Brain/06_Nhat_Ky_Thay_Doi.md with the backup path, endpoint, limits, verification results, and any remaining caveat. Never include api_hash, bot tokens, or other secrets.

## Bundled Resource

- scripts/verify_local_bot_api.sh: read-only container, loopback listener, and OpenClaw configuration checks; it never prints credentials.
- references/security-and-reuse.md: credential reuse decision guidance and threat model.
