#!/usr/bin/env bash
set -euo pipefail

CLOUDFLARED_VERSION="2026.8.2"
CLOUDFLARED_SHA256="fcfb02b575a52ca1af2e3267af4e1517bcdeb30ac48c834c69abaed3c0576ad2"
CLOUDFLARED_URL="https://github.com/cloudflare/cloudflared/releases/download/${CLOUDFLARED_VERSION}/cloudflared-linux-amd64"

container=""
data_dir=""
member_home=""
origin="http://127.0.0.1:80"
mode=""
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

usage() {
  cat <<'EOF'
Usage:
  setup_member_cloudflare_tunnel.sh \
    --container user-<member> \
    --data-dir /root/Apps/member_vps/docker-users/data/<member> \
    --member-home /home/<member> \
    [--origin http://127.0.0.1:<port>] \
    (--dry-run | --apply)
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --container)
      container="${2:-}"
      shift 2
      ;;
    --data-dir)
      data_dir="${2:-}"
      shift 2
      ;;
    --member-home)
      member_home="${2:-}"
      shift 2
      ;;
    --origin)
      origin="${2:-}"
      shift 2
      ;;
    --dry-run)
      mode="dry-run"
      shift
      ;;
    --apply)
      mode="apply"
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ -z "$container" || -z "$data_dir" || -z "$member_home" || -z "$mode" ]]; then
  usage >&2
  exit 2
fi

if [[ ! "$container" =~ ^[A-Za-z0-9_.-]+$ ]]; then
  echo "Invalid container name." >&2
  exit 2
fi

if [[ ! "$data_dir" =~ ^/root/Apps/member_vps/docker-users/data/[A-Za-z0-9_.-]+$ ]]; then
  echo "Data directory must be a member path under docker-users/data." >&2
  exit 2
fi

if [[ ! "$member_home" =~ ^/home/[A-Za-z0-9_.-]+$ ]]; then
  echo "Member home must be an absolute path under /home." >&2
  exit 2
fi

if [[ ! "$origin" =~ ^http://(127\.0\.0\.1|localhost):([0-9]{1,5})$ ]]; then
  echo "Origin must use http://127.0.0.1:<port> or http://localhost:<port>." >&2
  exit 2
fi

origin_port="${BASH_REMATCH[2]}"
if (( origin_port < 1 || origin_port > 65535 )); then
  echo "Origin port is outside 1-65535." >&2
  exit 2
fi

for dependency in docker curl sha256sum jq awk; do
  if ! command -v "$dependency" >/dev/null 2>&1; then
    echo "Missing dependency: $dependency" >&2
    exit 1
  fi
done

if [[ ! -d "$data_dir" ]]; then
  echo "Member data directory does not exist: $data_dir" >&2
  exit 1
fi

if [[ "$(docker inspect --format '{{.State.Running}}' "$container" 2>/dev/null || true)" != "true" ]]; then
  echo "Container is not running: $container" >&2
  exit 1
fi

mounted_destination="$(docker inspect "$container" | jq -r --arg source "$data_dir" '.[0].Mounts[]? | select(.Source == $source) | .Destination' | head -n 1)"
if [[ "$mounted_destination" != "$member_home" ]]; then
  echo "Expected $data_dir to be mounted at $member_home, found: ${mounted_destination:-none}" >&2
  exit 1
fi

token_host_path="${data_dir}/.cloudflared/tunnel-token"
token_container_path="${member_home}/.cloudflared/tunnel-token"
binary_host_path="${data_dir}/.local/bin/cloudflared"
binary_container_path="${member_home}/.local/bin/cloudflared"
domain_command_host_path="${data_dir}/.local/bin/gan-domain"
domain_command_container_path="${member_home}/.local/bin/gan-domain"
runtime_supervisor_host_path="${data_dir}/.cloudflared/supervisord.conf"
runtime_supervisor_container_path="${member_home}/.cloudflared/supervisord.conf"

if [[ ! -s "$token_host_path" ]]; then
  echo "Tunnel token file is missing or empty: $token_host_path" >&2
  exit 1
fi

token_mode="$(stat -c '%a' "$token_host_path")"
if [[ "$token_mode" != "600" ]]; then
  echo "Tunnel token must have mode 600; current mode is $token_mode." >&2
  exit 1
fi

cat <<EOF
Container: $container
Member data: $data_dir
Member home: $member_home
Origin: $origin
Persistent binary: $binary_host_path
Persistent token: $token_host_path (contents not read)
Mode: $mode
EOF

if [[ "$mode" == "dry-run" ]]; then
  docker exec "$container" curl -fsSIL --max-time 10 "$origin" | sed -n '1,10p'
  echo "Dry-run passed; no production files changed."
  exit 0
fi

if [[ ${EUID} -ne 0 ]]; then
  echo "Apply mode must run as root." >&2
  exit 1
fi

backup_stamp="$(date -u +%Y%m%dT%H%M%SZ)"
backup_dir="/root/_Backups/member_vps/${container}/cloudflared/${backup_stamp}"
install -d -m 700 "$backup_dir"
docker cp "${container}:/usr/local/bin/member-vps-entrypoint.sh" "$backup_dir/member-vps-entrypoint.sh.before"
docker cp "${container}:/etc/supervisor/conf.d/member-vps.conf" "$backup_dir/member-vps.conf.before"
chmod -R go-rwx "$backup_dir"

temporary_dir="$(mktemp -d)"
trap 'rm -rf "$temporary_dir"' EXIT

curl -fsSL --retry 3 --connect-timeout 20 "$CLOUDFLARED_URL" -o "$temporary_dir/cloudflared"
printf '%s  %s\n' "$CLOUDFLARED_SHA256" "$temporary_dir/cloudflared" | sha256sum -c -
install -d -m 755 "$(dirname "$binary_host_path")"
install -m 755 "$temporary_dir/cloudflared" "$binary_host_path"
install -m 755 "${script_dir}/gan-domain" "$domain_command_host_path"

install -d -m 700 "${data_dir}/.cloudflared"
cat >"$runtime_supervisor_host_path" <<EOF
[unix_http_server]
file=${member_home}/.cloudflared/supervisor.sock
chmod=0700

[supervisord]
nodaemon=false
pidfile=${member_home}/.cloudflared/supervisord.pid
logfile=${member_home}/.cloudflared/supervisord.log
childlogdir=${member_home}/.cloudflared

[rpcinterface:supervisor]
supervisor.rpcinterface_factory=supervisor.rpcinterface:make_main_rpcinterface

[supervisorctl]
serverurl=unix://${member_home}/.cloudflared/supervisor.sock

[program:cloudflared-tunnel]
command=${binary_container_path} tunnel --no-autoupdate --metrics 127.0.0.1:49312 --loglevel info run --token-file ${token_container_path} --url ${origin}
directory=${member_home}
environment=HOME="${member_home}"
user=root
autorestart=true
startsecs=5
startretries=20
stopasgroup=true
killasgroup=true
stdout_logfile=${member_home}/.cloudflared/cloudflared.log
stderr_logfile=${member_home}/.cloudflared/cloudflared.log
stdout_logfile_maxbytes=10MB
stdout_logfile_backups=3
EOF
chmod 600 "$runtime_supervisor_host_path"

docker cp "${container}:/usr/local/bin/member-vps-entrypoint.sh" "$temporary_dir/member-vps-entrypoint.sh"
if ! grep -q '# BEGIN member-vps-cloudflare-domain-bootstrap' "$temporary_dir/member-vps-entrypoint.sh"; then
  bootstrap_block="# BEGIN member-vps-cloudflare-domain-bootstrap
if [[ -x ${domain_command_container_path} ]]; then
  ln -sfn ${domain_command_container_path} /usr/local/bin/gan-domain
fi
domain_config_dir=${member_home}/.gan-domain/nginx
if [[ -d \"\${domain_config_dir}\" ]]; then
  shopt -s nullglob
  for domain_config in \"\${domain_config_dir}\"/*.conf; do
    ln -sfn \"\${domain_config}\" \"/etc/nginx/conf.d/gan-domain-\$(basename \"\${domain_config}\")\"
  done
  shopt -u nullglob
fi
# END member-vps-cloudflare-domain-bootstrap
"

  awk -v block="$bootstrap_block" '
    BEGIN { inserted = 0 }
    /^cat >\/etc\/supervisor\/conf\.d\/member-vps\.conf/ && inserted == 0 { print block; inserted = 1 }
    { print }
    END { if (inserted == 0) exit 42 }
  ' "$temporary_dir/member-vps-entrypoint.sh" >"$temporary_dir/member-vps-entrypoint.bootstrap.sh"
  mv "$temporary_dir/member-vps-entrypoint.bootstrap.sh" "$temporary_dir/member-vps-entrypoint.sh"
fi

if ! grep -q '^\[program:cloudflared-tunnel\]$' "$temporary_dir/member-vps-entrypoint.sh"; then
  supervisor_block="[program:cloudflared-tunnel]
command=${binary_container_path} tunnel --no-autoupdate --metrics 127.0.0.1:49312 --loglevel info run --token-file ${token_container_path} --url ${origin}
directory=${member_home}
environment=HOME=\"${member_home}\"
autorestart=true
startsecs=5
startretries=20
stopasgroup=true
killasgroup=true
stdout_logfile=${member_home}/.cloudflared/cloudflared.log
stderr_logfile=${member_home}/.cloudflared/cloudflared.log
stdout_logfile_maxbytes=10MB
stdout_logfile_backups=3
"

  awk -v block="$supervisor_block" '
    BEGIN { inserted = 0 }
    $0 == "[program:nginx]" && inserted == 0 { print block; inserted = 1 }
    { print }
    END { if (inserted == 0) exit 42 }
  ' "$temporary_dir/member-vps-entrypoint.sh" >"$temporary_dir/member-vps-entrypoint.cloudflared.sh"
  mv "$temporary_dir/member-vps-entrypoint.cloudflared.sh" "$temporary_dir/member-vps-entrypoint.sh"
fi

bash -n "$temporary_dir/member-vps-entrypoint.sh"
install -m 700 "$temporary_dir/member-vps-entrypoint.sh" "${data_dir}/.cloudflared/member-vps-entrypoint.cloudflared.sh"
docker cp "$temporary_dir/member-vps-entrypoint.sh" "${container}:/usr/local/bin/member-vps-entrypoint.sh"
docker exec "$container" chmod 755 /usr/local/bin/member-vps-entrypoint.sh
docker exec "$container" ln -sfn "$domain_command_container_path" /usr/local/bin/gan-domain

if ! docker exec "$container" pgrep -f '[c]loudflared.*tunnel.*token-file' >/dev/null 2>&1; then
  rm -f "${data_dir}/.cloudflared/supervisord.pid" "${data_dir}/.cloudflared/supervisor.sock"
  docker exec "$container" /usr/bin/supervisord -c "$runtime_supervisor_container_path"
fi

status_output=""
for attempt in $(seq 1 20); do
  status_output="$(docker exec "$container" supervisorctl -c "$runtime_supervisor_container_path" status 2>&1 || true)"
  if grep -q 'RUNNING' <<<"$status_output"; then
    break
  fi
  sleep 1
done

if ! grep -q 'RUNNING' <<<"$status_output"; then
  printf '%s\n' "$status_output" >&2
  exit 1
fi

printf '%s\n' "$status_output"
docker exec "$container" sh -lc "curl -fsS http://127.0.0.1:49312/metrics | grep '^cloudflared_tunnel_ha_connections '"
echo "Backup: $backup_dir"
echo "Cloudflare Tunnel connector is running. Add Public Hostnames in the Cloudflare dashboard."
