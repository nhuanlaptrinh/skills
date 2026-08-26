---
name: telegram-local-bot-api-openclaw
description: Install, configure, migrate, verify, troubleshoot, and roll back Telegram Local Bot API for OpenClaw on a Linux VPS. Use when Telegram bots need files beyond cloud Bot API limits (especially uploads over 50 MB or downloads over 20 MB), when setting channels.telegram.apiRoot/trustedLocalFileRoots/mediaMaxMb, or when cloning this setup to another VPS.
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

Do not expose the Local Bot API port publicly. Bind it to loopback only.

## Variables

Choose paths that match the target VPS. The following layout matches the ALT VPS standard:

~~~bash
OC_ROOT=/root/.openclaw
INFRA_ROOT=/root/_Infra/telegram-bot-api
API_ROOT=http://127.0.0.1:8081
MEDIA_MAX_MB=2000
~~~

Use a narrower data directory if the deployment has a different service user. Do not use / as a trusted media root.

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

## Troubleshooting

- error: expected TELEGRAM_API_ID...: the env file is absent, empty, or unreadable. Stop; obtain real credentials instead of guessing.
- 409 Conflict: an old gateway/container is still polling. Stop duplicate gateways, log out the bot from the currently active API server, then start only one poller.
- 413 Request Entity Too Large: confirm OpenClaw loaded the local apiRoot, the Local Bot API is in --local mode, and mediaMaxMb is not below the file size.
- Absolute local file_path cannot be read: mount the same host data directory into /var/lib/telegram-bot-api and list that host directory in trustedLocalFileRoots.
- Local media path is not under an allowed directory: this is OpenClaw's own outbound filesystem allowlist, not a Telegram size limit. Put the media under an approved workspace/media root or adjust that separate policy.
- getMe works but media fails: inspect free disk space, container logs, the trusted root mapping, and the exact file_path returned by local getFile.
- Public API access is blocked: the Local Bot API still needs outbound connectivity to Telegram DCs. A local endpoint does not remove VPS firewall/DNS/proxy requirements.

## Rollback

Keep the Local Bot API data; do not delete it during rollback. Stop OpenClaw, call local logOut for every bot, restore the timestamped openclaw.json backup, and start the gateway against the public API. Only after the public polling path is healthy may the local container be stopped with docker compose stop; use down only when removal is explicitly requested.

After a production change, append a redacted entry to /root/_Second_AI_Brain/06_Nhat_Ky_Thay_Doi.md with the backup path, endpoint, limits, verification results, and any remaining caveat. Never include api_hash, bot tokens, or other secrets.

## Bundled Resource

- scripts/verify_local_bot_api.sh: read-only container, loopback listener, and OpenClaw configuration checks; it never prints credentials.
- references/security-and-reuse.md: credential reuse decision guidance and threat model.
