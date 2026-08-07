#!/usr/bin/env bash
set -euo pipefail

usage() {
    cat <<'EOF'
Usage:
  setup_django_domain.sh --project-dir PATH --domain FQDN --port PORT --ip IPV4 --dry-run
  setup_django_domain.sh --project-dir PATH --domain FQDN --port PORT --ip IPV4 [--certbot-email EMAIL] [--skip-dns] [--skip-ssl] --apply
EOF
}

fail() {
    echo "ERROR: $*" >&2
    exit 1
}

PROJECT_DIR=""
DOMAIN=""
PORT=""
IP_ADDRESS=""
CERTBOT_EMAIL=""
MODE=""
SKIP_DNS=0
SKIP_SSL=0

while [[ $# -gt 0 ]]; do
    case "$1" in
        --project-dir)
            PROJECT_DIR="${2:-}"
            shift 2
            ;;
        --domain)
            DOMAIN="${2:-}"
            shift 2
            ;;
        --port)
            PORT="${2:-}"
            shift 2
            ;;
        --ip)
            IP_ADDRESS="${2:-}"
            shift 2
            ;;
        --certbot-email)
            CERTBOT_EMAIL="${2:-}"
            shift 2
            ;;
        --skip-dns)
            SKIP_DNS=1
            shift
            ;;
        --skip-ssl)
            SKIP_SSL=1
            shift
            ;;
        --dry-run)
            MODE="dry-run"
            shift
            ;;
        --apply)
            MODE="apply"
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            fail "unknown argument: $1"
            ;;
    esac
done

[[ -n "$PROJECT_DIR" ]] || fail "--project-dir is required"
[[ -n "$DOMAIN" ]] || fail "--domain is required"
[[ -n "$PORT" ]] || fail "--port is required"
[[ -n "$IP_ADDRESS" ]] || fail "--ip is required"
[[ "$MODE" == "dry-run" || "$MODE" == "apply" ]] || fail "choose --dry-run or --apply"
[[ "$DOMAIN" =~ ^([a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$ ]] || fail "invalid domain"
[[ "$PORT" =~ ^[0-9]+$ ]] || fail "invalid port"
(( PORT >= 1024 && PORT <= 65535 )) || fail "port must be between 1024 and 65535"

python3 - "$IP_ADDRESS" <<'PY' || fail "invalid IPv4 address"
import ipaddress
import sys

address = ipaddress.ip_address(sys.argv[1])
if address.version != 4:
    raise SystemExit(1)
PY

PROJECT_DIR="$(realpath -m "$PROJECT_DIR")"
NGINX_SITE="/etc/nginx/sites-available/$DOMAIN"
NGINX_ENABLED="/etc/nginx/sites-enabled/$DOMAIN"
CLOUDFLARE_CLI="/root/.agents/skills/cloudflare-subdomain/tao_ten_mien"
TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
BACKUP_DIR="/root/_Backups/django_site_domain_${DOMAIN//./_}_$TIMESTAMP"

echo "Mode: $MODE"
echo "Project: $PROJECT_DIR"
echo "Domain: $DOMAIN"
echo "Loopback target: 127.0.0.1:$PORT"
echo "DNS IPv4: $IP_ADDRESS"
echo "Nginx site: $NGINX_SITE"
echo "Backup: $BACKUP_DIR"
echo "Cloudflare helper: $CLOUDFLARE_CLI"
echo "Skip DNS: $SKIP_DNS"
echo "Skip SSL: $SKIP_SSL"

if [[ "$MODE" == "dry-run" ]]; then
    [[ -d "$PROJECT_DIR" ]] || echo "WARN: project directory does not exist yet"
    [[ -f "$PROJECT_DIR/docker-compose.yml" ]] || echo "WARN: docker-compose.yml not found"
    [[ -f "$PROJECT_DIR/.env" ]] || echo "WARN: .env not found; run scripts/prepare_env.sh before apply"
    [[ -x "$CLOUDFLARE_CLI" ]] || echo "WARN: Cloudflare helper is missing or not executable"
    exit 0
fi

[[ "$EUID" -eq 0 ]] || fail "apply mode must run as root"
for command_name in docker nginx curl dig realpath; do
    command -v "$command_name" >/dev/null 2>&1 || fail "missing command: $command_name"
done
if [[ "$SKIP_SSL" -eq 0 ]]; then
    command -v certbot >/dev/null 2>&1 || fail "missing command: certbot"
fi
[[ -d "$PROJECT_DIR" ]] || fail "project directory not found"
[[ -f "$PROJECT_DIR/docker-compose.yml" ]] || fail "docker-compose.yml not found"
[[ -f "$PROJECT_DIR/.env" ]] || fail ".env not found; run scripts/prepare_env.sh first"
if [[ "$SKIP_DNS" -eq 0 ]]; then
    [[ -x "$CLOUDFLARE_CLI" ]] || fail "Cloudflare helper is missing or not executable"
fi
grep -Fq "127.0.0.1:$PORT:8000" "$PROJECT_DIR/docker-compose.yml" \
    || fail "docker-compose.yml does not bind 127.0.0.1:$PORT:8000"

cd "$PROJECT_DIR"
docker compose config >/dev/null
docker compose up -d --build

APP_READY=0
for _ in $(seq 1 20); do
    if curl -fsS -o /dev/null -H "Host: $DOMAIN" "http://127.0.0.1:$PORT/"; then
        APP_READY=1
        break
    fi
    sleep 3
done
[[ "$APP_READY" -eq 1 ]] || fail "Django app did not become ready on loopback"

mkdir -p "$BACKUP_DIR"
PREVIOUS_ENABLED_TARGET=""
if [[ -e "$NGINX_SITE" ]]; then
    cp -a "$NGINX_SITE" "$BACKUP_DIR/"
fi
if [[ -L "$NGINX_ENABLED" ]]; then
    PREVIOUS_ENABLED_TARGET="$(readlink "$NGINX_ENABLED")"
fi

TMP_NGINX="$(mktemp)"
cat >"$TMP_NGINX" <<EOF
server {
    listen 80;
    listen [::]:80;
    server_name $DOMAIN;

    location / {
        proxy_pass http://127.0.0.1:$PORT;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header X-Forwarded-Host \$host;
        proxy_set_header X-Forwarded-Port \$server_port;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 3600s;
        proxy_send_timeout 3600s;
    }
}
EOF

install -m 0644 "$TMP_NGINX" "$NGINX_SITE"
rm -f "$TMP_NGINX"
ln -sfn "$NGINX_SITE" "$NGINX_ENABLED"

if ! nginx -t; then
    if [[ -f "$BACKUP_DIR/$(basename "$NGINX_SITE")" ]]; then
        cp -a "$BACKUP_DIR/$(basename "$NGINX_SITE")" "$NGINX_SITE"
    else
        rm -f "$NGINX_SITE"
    fi
    if [[ -n "$PREVIOUS_ENABLED_TARGET" ]]; then
        ln -sfn "$PREVIOUS_ENABLED_TARGET" "$NGINX_ENABLED"
    else
        rm -f "$NGINX_ENABLED"
    fi
    nginx -t || true
    fail "new Nginx config is invalid; previous state restored"
fi

if command -v systemctl >/dev/null 2>&1; then
    systemctl reload nginx
else
    service nginx reload
fi

if [[ "$SKIP_DNS" -eq 0 ]]; then
    EXISTING_IPS="$(dig +short A "$DOMAIN" @1.1.1.1 | sort -u || true)"
    if grep -Fxq "$IP_ADDRESS" <<<"$EXISTING_IPS"; then
        echo "DNS already points to $IP_ADDRESS; skipping record creation"
    elif [[ -n "$EXISTING_IPS" ]]; then
        echo "Existing DNS values:" >&2
        sed 's/^/  - /' <<<"$EXISTING_IPS" >&2
        fail "DNS exists but does not point to the requested IP"
    else
        "$CLOUDFLARE_CLI" "$DOMAIN" "$IP_ADDRESS"
    fi
fi

if [[ "$SKIP_SSL" -eq 0 ]]; then
    DNS_READY=0
    for _ in $(seq 1 18); do
        if dig +short A "$DOMAIN" @1.1.1.1 | grep -Fxq "$IP_ADDRESS"; then
            DNS_READY=1
            break
        fi
        sleep 10
    done
    [[ "$DNS_READY" -eq 1 ]] || fail "DNS did not resolve to $IP_ADDRESS in time; rerun after propagation"

    CERTBOT_ARGS=(--nginx -d "$DOMAIN" --non-interactive --redirect)
    if [[ -n "$CERTBOT_EMAIL" ]]; then
        CERTBOT_ARGS+=(--agree-tos --email "$CERTBOT_EMAIL")
    fi
    certbot "${CERTBOT_ARGS[@]}"
    nginx -t
    curl -fsSI --resolve "$DOMAIN:443:127.0.0.1" "https://$DOMAIN/" >/dev/null
fi

docker compose ps
curl -fsSI -H "Host: $DOMAIN" http://127.0.0.1/ >/dev/null
if [[ "$SKIP_SSL" -eq 0 ]]; then
    echo "Deployment completed for https://$DOMAIN/"
else
    echo "Deployment completed for http://$DOMAIN/"
fi
