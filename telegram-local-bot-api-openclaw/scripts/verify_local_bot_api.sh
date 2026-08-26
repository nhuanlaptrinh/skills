#!/usr/bin/env bash
set -euo pipefail

API_ROOT="http://127.0.0.1:8081"
COMPOSE_DIR="/root/_Infra/telegram-bot-api"
OPENCLAW_ROOT="/root/.openclaw"
CONTAINER="telegram-bot-api"
REQUIRE_OPENCLAW=1

usage() {
    cat <<'EOF'
Verify a local Telegram Bot API deployment without printing credentials.

Options:
  --api-root URL       Local Bot API root (default: http://127.0.0.1:8081)
  --compose-dir PATH   Compose directory (default: /root/_Infra/telegram-bot-api)
  --openclaw-root PATH OpenClaw state root (default: /root/.openclaw)
  --container NAME     Container name (default: telegram-bot-api)
  --skip-openclaw      Skip OpenClaw checks
  -h, --help           Show this help
EOF
}

while (($#)); do
    case "$1" in
        --api-root) API_ROOT="${2:?missing URL}"; shift 2 ;;
        --compose-dir) COMPOSE_DIR="${2:?missing path}"; shift 2 ;;
        --openclaw-root) OPENCLAW_ROOT="${2:?missing path}"; shift 2 ;;
        --container) CONTAINER="${2:?missing name}"; shift 2 ;;
        --skip-openclaw) REQUIRE_OPENCLAW=0; shift ;;
        -h|--help) usage; exit 0 ;;
        *) printf 'unknown option: %s\n' "$1" >&2; usage >&2; exit 2 ;;
    esac
done

failures=0
check() {
    local label="$1"
    shift
    if "$@"; then
        printf 'PASS %s\n' "$label"
    else
        printf 'FAIL %s\n' "$label"
        failures=$((failures + 1))
    fi
}

command -v curl >/dev/null || { echo "FAIL curl is required"; exit 2; }
command -v docker >/dev/null || { echo "FAIL docker is required"; exit 2; }

check "compose file exists" test -f "$COMPOSE_DIR/docker-compose.yml"
if [ -f "$COMPOSE_DIR/docker-compose.yml" ]; then
    check "compose config valid" docker compose -f "$COMPOSE_DIR/docker-compose.yml" config -q
fi

container_state="$(docker inspect --format '{{.State.Status}}' "$CONTAINER" 2>/dev/null || true)"
if [ "$container_state" = "running" ]; then
    printf 'PASS container running\n'
else
    printf 'FAIL container running (state=%s)\n' "${container_state:-missing}"
    failures=$((failures + 1))
fi

http_status="$(curl -sS --max-time 15 -o /dev/null -w '%{http_code}' "$API_ROOT/" 2>/dev/null || true)"
case "$http_status" in
    200|404) printf 'PASS local HTTP reachable (status=%s)\n' "$http_status" ;;
    *) printf 'FAIL local HTTP reachable (status=%s)\n' "${http_status:-unreachable}"; failures=$((failures + 1)) ;;
esac

port="${API_ROOT##*:}"
port="${port%%/*}"
listener="$(ss -H -ltn 2>/dev/null | awk -v p=":${port}" '$4 ~ p"$" {print $4}' | head -1 || true)"
case "$listener" in
    127.0.0.1:"$port"|\[::1\]:"$port") printf 'PASS loopback listener (%s)\n' "$listener" ;;
    *) printf 'FAIL loopback listener (found=%s)\n' "${listener:-none}"; failures=$((failures + 1)) ;;
esac

if [ -d "$COMPOSE_DIR/data" ]; then
    printf 'PASS data directory exists\n'
else
    printf 'FAIL data directory exists\n'
    failures=$((failures + 1))
fi

if [ "$REQUIRE_OPENCLAW" -eq 1 ]; then
    command -v openclaw >/dev/null || { echo "FAIL openclaw command is required"; exit 2; }
    cfg="$OPENCLAW_ROOT/openclaw.json"
    if [ -f "$cfg" ] && command -v jq >/dev/null; then
        check "OpenClaw config valid" openclaw config validate
        configured_root="$(jq -r '.channels.telegram.apiRoot // empty' "$cfg")"
        if [ "$configured_root" = "$API_ROOT" ]; then
            printf 'PASS OpenClaw apiRoot configured\n'
        else
            printf 'FAIL OpenClaw apiRoot configured (value=%s)\n' "${configured_root:-missing}"
            failures=$((failures + 1))
        fi
        media_limit="$(jq -r '.channels.telegram.mediaMaxMb // 0' "$cfg")"
        if awk -v value="$media_limit" 'BEGIN { exit !(value > 0) }'; then
            printf 'PASS OpenClaw mediaMaxMb configured (%s)\n' "$media_limit"
        else
            printf 'FAIL OpenClaw mediaMaxMb configured\n'
            failures=$((failures + 1))
        fi
        if jq -e --arg root "$COMPOSE_DIR/data" '(.channels.telegram.trustedLocalFileRoots // []) | index($root) != null' "$cfg" >/dev/null; then
            printf 'PASS trusted local file root configured\n'
        else
            printf 'FAIL trusted local file root configured\n'
            failures=$((failures + 1))
        fi
    else
        printf 'FAIL OpenClaw config or jq missing\n'
        failures=$((failures + 1))
    fi
    if openclaw channels status --probe --channel telegram >/tmp/telegram-local-bot-api-status.$$ 2>&1; then
        if rg -q 'connected|works' /tmp/telegram-local-bot-api-status.$$; then
            printf 'PASS OpenClaw Telegram channel probe\n'
        else
            printf 'FAIL OpenClaw Telegram channel probe\n'
            failures=$((failures + 1))
        fi
    else
        printf 'FAIL OpenClaw Telegram channel probe\n'
        failures=$((failures + 1))
    fi
    rm -f /tmp/telegram-local-bot-api-status.$$
fi

if [ "$failures" -eq 0 ]; then
    echo "verification=passed"
else
    printf 'verification=failed failures=%s\n' "$failures"
fi
exit "$failures"

