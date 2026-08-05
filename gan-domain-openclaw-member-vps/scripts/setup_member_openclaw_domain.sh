#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  setup_member_openclaw_domain.sh --member NAME --domain FQDN --zone ZONE --ip PUBLIC_IP [--dry-run|--apply]

Environment for --apply:
  CLOUDFLARE_API_TOKEN     Required. Cloudflare token with DNS Edit permission.
  OPENCLAW_GATEWAY_TOKEN   Optional. Sets gateway.auth.token without exposing it in argv.
EOF
}

die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }
log() { printf '[%s] %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*"; }
require_cmd() { command -v "$1" >/dev/null 2>&1 || die "Missing command: $1"; }

member=''
domain=''
zone=''
public_ip=''
mode='dry-run'

while (($#)); do
  case "$1" in
    --member) member="${2:-}"; shift 2 ;;
    --domain) domain="${2:-}"; shift 2 ;;
    --zone) zone="${2:-}"; shift 2 ;;
    --ip) public_ip="${2:-}"; shift 2 ;;
    --dry-run) mode='dry-run'; shift ;;
    --apply) mode='apply'; shift ;;
    -h|--help) usage; exit 0 ;;
    *) die "Unknown argument: $1" ;;
  esac
done

[[ -n "$member" && "$member" =~ ^[a-z0-9][a-z0-9_-]*$ ]] || die 'Invalid or missing --member'
[[ -n "$domain" && "$domain" =~ ^[A-Za-z0-9.-]+$ ]] || die 'Invalid or missing --domain'
[[ -n "$zone" && "$zone" =~ ^[A-Za-z0-9.-]+$ ]] || die 'Invalid or missing --zone'
[[ "$domain" == *".$zone" ]] || die '--domain must belong to --zone'
[[ -n "$public_ip" && "$public_ip" =~ ^[0-9]{1,3}(\.[0-9]{1,3}){3}$ ]] || die 'Invalid or missing --ip'

require_cmd docker
require_cmd jq
require_cmd curl
require_cmd nginx

container="user-${member}"
member_home="/home/${member}"
data_dir="/root/Apps/member_vps/docker-users/data/${member}"
openclaw_json="${data_dir}/.openclaw/openclaw.json"
container_nginx_source="${data_dir}/openclaw-nginx.conf"
host_nginx="/etc/nginx/sites-available/${domain}"
host_nginx_enabled="/etc/nginx/sites-enabled/${domain}"

docker inspect "$container" >/dev/null 2>&1 || die "Container not found: $container"
[[ -d "$data_dir" ]] || die "Member data folder not found: $data_dir"
[[ -f "$openclaw_json" ]] || die "OpenClaw config not found: $openclaw_json"

web_port="$(docker inspect "$container" | jq -r '.[0].NetworkSettings.Ports["80/tcp"][0].HostPort // empty')"
[[ -n "$web_port" ]] || die "Container $container has no host mapping for port 80"

log "Member: $member"
log "Domain: $domain"
log "Zone: $zone"
log "Public IP: $public_ip"
log "Container web port: $web_port"
log "Mode: $mode"

docker exec "$container" sh -lc "HOME=${member_home} openclaw gateway status" | grep -E 'Connectivity probe|Listening' || true

if [[ "$mode" == 'dry-run' ]]; then
  log 'DRY-RUN: would backup OpenClaw and Nginx configs'
  log 'DRY-RUN: would configure container and host reverse proxies'
  log 'DRY-RUN: would add allowed origin and loopback trusted proxies'
  if [[ -n "${OPENCLAW_GATEWAY_TOKEN:-}" ]]; then
    log 'DRY-RUN: would update gateway token from environment'
  else
    log 'DRY-RUN: would keep the current gateway token'
  fi
  log 'DRY-RUN: would create/update Cloudflare A record, issue SSL, and run health checks'
  exit 0
fi

[[ ${EUID} -eq 0 ]] || die '--apply must run as root'
[[ -n "${CLOUDFLARE_API_TOKEN:-}" ]] || die 'CLOUDFLARE_API_TOKEN is required for --apply'
require_cmd certbot

timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
backup_dir="/root/_Backups/member_openclaw_domain_${member}_${timestamp}"
mkdir -p "$backup_dir"
cp -a "$openclaw_json" "$backup_dir/openclaw.json.before"
docker cp "$container:/etc/nginx/sites-available/default" "$backup_dir/container-nginx-default.before"
[[ ! -e "$host_nginx" ]] || cp -a "$host_nginx" "$backup_dir/host-nginx.before"
log "Backup: $backup_dir"

cat >"$container_nginx_source" <<'EOF'
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:18789;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $http_x_forwarded_proto;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 3600s;
        proxy_send_timeout 3600s;
        proxy_buffering off;
    }
}
EOF

cat >"$host_nginx" <<EOF
server {
    listen 80;
    listen [::]:80;
    server_name ${domain};

    location ^~ /.well-known/acme-challenge/ {
        root /var/www/letsencrypt;
        default_type "text/plain";
        try_files \$uri =404;
    }

    location / {
        proxy_pass http://127.0.0.1:${web_port};
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 3600s;
        proxy_send_timeout 3600s;
        proxy_buffering off;
    }
}
EOF

ln -sfn "$host_nginx" "$host_nginx_enabled"
docker cp "$container_nginx_source" "$container:/etc/nginx/sites-available/default"

DOMAIN="$domain" MEMBER_HOME="$member_home" docker exec \
  -e DOMAIN="$domain" \
  -e MEMBER_HOME="$member_home" \
  -e OC_GATEWAY_CREDENTIAL="${OPENCLAW_GATEWAY_TOKEN:-}" \
  -i "$container" node <<'NODE'
const fs = require('fs');
const path = `${process.env.MEMBER_HOME}/.openclaw/openclaw.json`;
const config = JSON.parse(fs.readFileSync(path, 'utf8'));
config.gateway ??= {};
config.gateway.controlUi ??= {};
const origin = `https://${process.env.DOMAIN}`;
const origins = Array.isArray(config.gateway.controlUi.allowedOrigins)
  ? config.gateway.controlUi.allowedOrigins.filter((value) => value !== '*')
  : [];
if (!origins.includes(origin)) origins.push(origin);
config.gateway.controlUi.allowedOrigins = origins;
config.gateway.trustedProxies = ['127.0.0.1', '::1'];
if (process.env.OC_GATEWAY_CREDENTIAL) {
  config.gateway.auth ??= {};
  config.gateway.auth.mode = 'token';
  config.gateway.auth.token = process.env.OC_GATEWAY_CREDENTIAL;
}
fs.writeFileSync(path, JSON.stringify(config, null, 2) + '\n');
NODE

zone_response="$(curl -fsS -G 'https://api.cloudflare.com/client/v4/zones' \
  -H "Authorization: Bearer ${CLOUDFLARE_API_TOKEN}" \
  -H 'Content-Type: application/json' \
  --data-urlencode "name=${zone}")"
zone_id="$(jq -r '.result[0].id // empty' <<<"$zone_response")"
[[ -n "$zone_id" ]] || die "Cloudflare zone not found: $zone"

record_response="$(curl -fsS -G "https://api.cloudflare.com/client/v4/zones/${zone_id}/dns_records" \
  -H "Authorization: Bearer ${CLOUDFLARE_API_TOKEN}" \
  -H 'Content-Type: application/json' \
  --data-urlencode 'type=A' \
  --data-urlencode "name=${domain}")"
record_id="$(jq -r '.result[0].id // empty' <<<"$record_response")"
payload="$(jq -nc --arg name "$domain" --arg content "$public_ip" '{type:"A",name:$name,content:$content,ttl:1,proxied:false}')"

if [[ -n "$record_id" ]]; then
  curl -fsS -X PUT "https://api.cloudflare.com/client/v4/zones/${zone_id}/dns_records/${record_id}" \
    -H "Authorization: Bearer ${CLOUDFLARE_API_TOKEN}" \
    -H 'Content-Type: application/json' \
    --data "$payload" | jq -e '.success == true' >/dev/null
  log 'Updated Cloudflare A record'
else
  curl -fsS -X POST "https://api.cloudflare.com/client/v4/zones/${zone_id}/dns_records" \
    -H "Authorization: Bearer ${CLOUDFLARE_API_TOKEN}" \
    -H 'Content-Type: application/json' \
    --data "$payload" | jq -e '.success == true' >/dev/null
  log 'Created Cloudflare A record'
fi

docker exec "$container" nginx -t
nginx -t
docker exec "$container" nginx -s reload
nginx -s reload
docker exec "$container" sh -lc "HOME=${member_home} openclaw config validate"
docker exec "$container" sh -lc "HOME=${member_home} tmux kill-session -t openclaw 2>/dev/null || true; HOME=${member_home} tmux new-session -d -s openclaw 'HOME=${member_home} openclaw gateway'; sleep 8; HOME=${member_home} openclaw gateway status"

resolved=''
for _ in $(seq 1 24); do
  resolved="$(dig +short "$domain" @1.1.1.1 2>/dev/null | tail -n 1 || true)"
  [[ "$resolved" == "$public_ip" ]] && break
  sleep 5
done
[[ "$resolved" == "$public_ip" ]] || die "Public DNS has not resolved to $public_ip yet; rerun after propagation"

if [[ ! -d "/etc/letsencrypt/live/${domain}" ]]; then
  certbot --nginx -d "$domain" --non-interactive --agree-tos --redirect
else
  certbot --nginx -d "$domain" --non-interactive --agree-tos --redirect --keep-until-expiring
fi

nginx -t
curl --resolve "${domain}:443:${public_ip}" -fsS "https://${domain}/" | grep -q '<title>OpenClaw Control'
docker exec "$container" sh -lc "HOME=${member_home} openclaw gateway status" | grep -q 'Connectivity probe: ok'
docker exec "$container" sh -lc "HOME=${member_home} openclaw channels status --probe"
log "Completed: https://${domain}/"
