#!/usr/bin/env bash
set -uo pipefail

CONTAINER="${CONTAINER:-}"
MEMBER_HOME="${MEMBER_HOME:-/home/member}"
MEMBER_LABEL="${MEMBER_LABEL:-member}"
PROJECT_KEY="${PROJECT_KEY:-member_zalo_delivery}"
STATE_FILE="${STATE_FILE:-/root/Automation/watchdog/shared_self_healing/state/${PROJECT_KEY}.json}"
SKILL_DIR="${SKILL_DIR:-/root/.agents/skills/openclaw-zalo-reliability-deploy}"
FAULT_WINDOW_SECONDS="${FAULT_WINDOW_SECONDS:-300}"
COOLDOWN_SECONDS="${COOLDOWN_SECONDS:-600}"
ACTIVE_DELIVERY_GRACE_SECONDS="${ACTIVE_DELIVERY_GRACE_SECONDS:-120}"
DRY_RUN=false

usage() { echo "Usage: CONTAINER=... MEMBER_HOME=... MEMBER_LABEL=... $0 [--dry-run]"; }
while (($#)); do
  case "$1" in
    --dry-run) DRY_RUN=true; shift;;
    -h|--help) usage; exit 0;;
    *) usage >&2; exit 2;;
  esac
done
if [[ -z "$CONTAINER" ]]; then echo "CONTAINER is required" >&2; exit 2; fi

log() { printf '[%s] %s\n' "$(TZ=Asia/Ho_Chi_Minh date '+%Y-%m-%d %H:%M:%S %Z')" "$*"; }
exec_member() {
  docker exec "$CONTAINER" sh -lc "export HOME='$MEMBER_HOME'; if [ -f '$MEMBER_HOME/.openclaw/gateway.env' ]; then set -a; . '$MEMBER_HOME/.openclaw/gateway.env'; set +a; fi; $1"
}
healthy() {
  printf '%s\n' "$1" | grep -Eq 'Zalo Personal .*configured,.*[,[:space:]]running([,[:space:]]|$).*works'
}

if ! docker inspect -f '{{.State.Running}}' "$CONTAINER" 2>/dev/null | grep -qx true; then
  log "MANUAL_REQUIRED container_not_running label=$MEMBER_LABEL"
  exit 0
fi

probe="$(exec_member 'timeout 45s openclaw channels status --probe' 2>&1 || true)"
gateway_log="$(docker exec "$CONTAINER" sh -lc 'ls -1t /tmp/openclaw/openclaw-*.log 2>/dev/null | head -1' 2>/dev/null || true)"
tmp="$(mktemp)"; trap 'rm -f "$tmp"' EXIT
if [[ -n "$gateway_log" ]]; then
  docker exec "$CONTAINER" sh -lc "tail -n 800 '$gateway_log'" >"$tmp" 2>/dev/null || true
fi
scan="$(python3 "$SKILL_DIR/scripts/scan_delivery_faults.py" "$tmp" --window "$FAULT_WINDOW_SECONDS")"
count="$(python3 -c 'import json,sys; print(json.load(sys.stdin).get("count",0))' <<<"$scan" 2>/dev/null || echo 0)"
fingerprint="$(python3 -c 'import json,sys; print(json.load(sys.stdin).get("fingerprint", ""))' <<<"$scan" 2>/dev/null || true)"

if [[ "$count" == 0 ]]; then
  python3 - "$STATE_FILE" <<'PY'
import json
import pathlib
import sys
p=pathlib.Path(sys.argv[1])
try:
    d=json.loads(p.read_text())
except Exception:
    d={}
d['fingerprint']=''
d['consecutive']=0
p.parent.mkdir(parents=True, exist_ok=True)
p.write_text(json.dumps(d, ensure_ascii=False, indent=2)+'\n')
PY
  log "HEALTHY delivery_faults=0 label=$MEMBER_LABEL channel=$(healthy "$probe" && echo ready || echo not_ready)"
  exit 0
fi

# A delivery fault may be emitted while the Gateway is still uploading or
# draining the current turn. Restarting in this window creates HTTP 503 and
# leaves the receipt ambiguous, so defer until the bounded grace window clears.
if [[ -n "$gateway_log" ]] && docker exec "$CONTAINER" sh -lc "tail -n 800 '$gateway_log'" 2>/dev/null | \
  python3 "$SKILL_DIR/scripts/scan_active_delivery.py" /dev/stdin --window "$ACTIVE_DELIVERY_GRACE_SECONDS" >/dev/null 2>&1; then
  log "DEFER active_delivery_grace_seconds=$ACTIVE_DELIVERY_GRACE_SECONDS label=$MEMBER_LABEL"
  exit 0
fi

# A healthy Zalo probe means the listener is alive. Delivery/upload faults are
# ambiguous and must not trigger a Gateway restart: doing so interrupts the
# active tool and causes restart recovery to replay the same group request.
if healthy "$probe"; then
  log "DEFER delivery_faults_with_healthy_channel label=$MEMBER_LABEL"
  exit 0
fi

mkdir -p "$(dirname "$STATE_FILE")"
read_state="$(python3 - "$STATE_FILE" "$fingerprint" <<'PY'
import json
import pathlib
import sys
p=pathlib.Path(sys.argv[1]); fp=sys.argv[2]
try:
    d=json.loads(p.read_text())
except Exception:
    d={}
same=d.get('fingerprint') == fp and bool(fp)
consecutive=int(d.get('consecutive',0))+1 if same else 1
print(consecutive, int(d.get('last_restart_epoch',0)))
d={'fingerprint':fp,'consecutive':consecutive,'last_restart_epoch':int(d.get('last_restart_epoch',0))}
p.write_text(json.dumps(d, ensure_ascii=False, indent=2)+'\n')
PY
)"
consecutive="${read_state%% *}"; last_restart="${read_state##* }"; now="$(date +%s)"
log "OBSERVED delivery_faults=$count consecutive=$consecutive fingerprint=$fingerprint label=$MEMBER_LABEL"
if [[ "$consecutive" -lt 2 ]]; then exit 0; fi
if ! healthy "$probe"; then log "DEFER channel_not_ready label=$MEMBER_LABEL"; exit 0; fi
if (( now - last_restart < COOLDOWN_SECONDS )); then log "COOLDOWN restart_skipped label=$MEMBER_LABEL"; exit 0; fi
if [[ "$DRY_RUN" == true ]]; then log "DRY_RUN would_restart_gateway label=$MEMBER_LABEL"; exit 0; fi

python3 - "$STATE_FILE" "$now" <<'PY'
import json
import pathlib
import sys
p=pathlib.Path(sys.argv[1]); d=json.loads(p.read_text()); d['last_restart_epoch']=int(sys.argv[2]); p.write_text(json.dumps(d, ensure_ascii=False, indent=2)+'\n')
PY
if exec_member 'command -v supervisorctl >/dev/null 2>&1 && supervisorctl status openclaw-gateway >/dev/null 2>&1'; then
  log "RESTART gateway_owner=supervisor label=$MEMBER_LABEL"
  exec_member 'supervisorctl restart openclaw-gateway' >/dev/null 2>&1 || true
else
  log "RESTART gateway_owner=process-manager label=$MEMBER_LABEL"
  exec_member 'pid=$(pgrep -f "^openclaw-gateway$" | head -1 || true); [ -n "$pid" ] && kill -TERM "$pid"' >/dev/null 2>&1 || true
fi

recovered=false
for attempt in 1 2 3 4 5 6; do
  sleep 10
  probe="$(exec_member 'timeout 20s openclaw channels status --probe' 2>&1 || true)"
  if healthy "$probe"; then recovered=true; break; fi
done
if [[ "$recovered" == true ]]; then log "RECOVERED label=$MEMBER_LABEL"; else log "MANUAL_REQUIRED probe_not_recovered label=$MEMBER_LABEL"; fi
exit 0
