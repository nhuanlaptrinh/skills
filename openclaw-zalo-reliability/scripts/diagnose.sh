#!/usr/bin/env bash
set -euo pipefail

CONTAINER="${1:-}"
MEMBER_HOME="${2:-}"
ZALO_ID="${3:-}"
LOG_LOOKBACK_LINES="${LOG_LOOKBACK_LINES:-1200}"

if [ -z "$CONTAINER" ] || [ -z "$MEMBER_HOME" ]; then
  echo "Usage: $0 <container> <member-home> [zalo-id]" >&2
  exit 2
fi

if [ -n "$ZALO_ID" ] && ! [[ "$ZALO_ID" =~ ^[0-9]+$ ]]; then
  echo "zalo-id must contain digits only" >&2
  exit 2
fi

redact() {
  sed -E 's/(token|secret|password|cookie|api[_-]?key)[=: ]+[^ ,}]*/\1=REDACTED/Ig; s/[0-9]{7,}:[A-Za-z0-9_-]{25,}/REDACTED/g'
}

container_exec() {
  docker exec "$CONTAINER" sh -lc "export HOME='$MEMBER_HOME'; if [ -f '$MEMBER_HOME/.openclaw/gateway.env' ]; then set -a; . '$MEMBER_HOME/.openclaw/gateway.env'; set +a; fi; $1"
}

count_matches() {
  local pattern="$1"
  local count
  count="$(printf '%s\n' "$POST_START_LOG" | rg -c "$pattern" || true)"
  printf '%s' "${count:-0}"
}

if ! docker inspect -f '{{.State.Running}}' "$CONTAINER" 2>/dev/null | rg -qx true; then
  echo "container_running=no"
  exit 1
fi

echo "container_running=yes"
echo "container=$CONTAINER"
echo "member_home=$MEMBER_HOME"

gateway_pid="$(docker exec "$CONTAINER" pgrep -f '^openclaw-gateway$' | head -1 || true)"
if [ -z "$gateway_pid" ]; then
  gateway_pid="$(docker exec "$CONTAINER" pgrep -xo openclaw 2>/dev/null || true)"
fi
echo "gateway_pid=${gateway_pid:-not_found}"

core_version="$(container_exec 'openclaw --version' 2>&1 | tail -1 | redact)"
echo "core_version=$core_version"

plugin_output="$(container_exec 'openclaw plugins inspect zalouser' 2>&1 || true)"
plugin_status="$(printf '%s\n' "$plugin_output" | awk -F': ' '/^Status:/{print $2; exit}')"
plugin_version="$(printf '%s\n' "$plugin_output" | awk -F': ' '/^Version:/{print $2; exit}')"
echo "plugin_status=${plugin_status:-unknown}"
echo "plugin_version=${plugin_version:-unknown}"

probe_output="$(container_exec 'timeout 45s openclaw channels status --probe' 2>&1 || true)"
probe_line="$(printf '%s\n' "$probe_output" | rg '^- Zalo Personal' | tail -1 | redact || true)"
echo "zalo_probe=${probe_line:-unavailable}"
if printf '%s\n' "$probe_output" | rg -q 'Gateway auth unavailable'; then
  echo "gateway_auth_probe=unavailable"
else
  echo "gateway_auth_probe=resolved"
fi

latest_log="$(docker exec "$CONTAINER" sh -lc 'ls -1t /tmp/openclaw/openclaw-*.log 2>/dev/null | head -1' || true)"
echo "latest_log=${latest_log:-not_found}"

RECENT_LOG=""
POST_START_LOG=""
if [ -n "$latest_log" ]; then
  RECENT_LOG="$(docker exec "$CONTAINER" tail -n "$LOG_LOOKBACK_LINES" "$latest_log" 2>/dev/null || true)"
  last_start_line="$(printf '%s\n' "$RECENT_LOG" | rg -n 'starting zalouser provider' | tail -1 | cut -d: -f1 || true)"
  if [ -n "$last_start_line" ]; then
    POST_START_LOG="$(printf '%s\n' "$RECENT_LOG" | tail -n "+$last_start_line")"
  else
    POST_START_LOG="$RECENT_LOG"
  fi
  latest_start="$(printf '%s\n' "$POST_START_LOG" | jq -r 'select((."1" // "") | contains("starting zalouser provider")) | ._meta.date // empty' 2>/dev/null | head -1 || true)"
  echo "latest_provider_start=${latest_start:-not_found_in_window}"
fi

listener_failures="$(count_matches 'Zalo listener closed|channel exited: Zalo listener|giving up after [0-9]+ restart attempts')"
outbound_failures="$(count_matches 'Zalouser final reply failed: OutboundDeliveryError|\[zalouser-send\].*failed')"
cipher_failures="$(count_matches 'Invalid data length or missing cipher key')"
long_running="$(count_matches 'long-running session')"
no_reply_payloads="$(count_matches 'visible channel turn dispatched with no queued reply payloads')"

echo "listener_failures_after_start=$listener_failures"
echo "outbound_failures_after_start=$outbound_failures"
echo "cipher_failures_after_start=$cipher_failures"
echo "long_running_events_after_start=$long_running"
echo "no_reply_payload_events_after_start=$no_reply_payloads"

patch_count="$(docker exec "$CONTAINER" sh -lc "find '$MEMBER_HOME/.openclaw/npm/projects' -path '*/node_modules/@openclaw/zalouser/dist/send-*.js' -type f -exec grep -l 'ZALO_SEND_MAX_ATTEMPTS' {} + 2>/dev/null | wc -l" || true)"
if [ "${patch_count:-0}" -gt 0 ]; then
  echo "send_retry_patch=present"
else
  echo "send_retry_patch=absent"
fi

if [ -n "$ZALO_ID" ]; then
  allow_file="$MEMBER_HOME/.openclaw/credentials/zalouser-default-allowFrom.json"
  if docker exec "$CONTAINER" sh -lc "test -f '$allow_file' && grep -Fq '$ZALO_ID' '$allow_file'"; then
    echo "pairing_id_present=yes"
  else
    echo "pairing_id_present=no_or_file_missing"
  fi

  sessions_output="$(container_exec 'openclaw sessions --json --limit all' 2>/dev/null || true)"
  session_key="agent:main:zalouser:direct:$ZALO_ID"
  session_summary="$(printf '%s' "$sessions_output" | jq -c --arg key "$session_key" '(.sessions // .)[]? | select((.key // .sessionKey) == $key) | {sessionId,totalTokens,contextTokens,updatedAt}' 2>/dev/null | head -1 || true)"
  echo "target_session=${session_summary:-not_found}"
else
  echo "pairing_id_present=unchecked"
  echo "target_session=unchecked"
fi

if [ "$cipher_failures" -gt 0 ]; then
  echo "diagnosis_hint=align_core_and_plugin_then_restart_before_qr_login"
elif [ "$listener_failures" -gt 0 ]; then
  echo "diagnosis_hint=listener_failed_after_latest_start"
elif [ "$outbound_failures" -gt 0 ]; then
  echo "diagnosis_hint=inbound_may_work_but_zalo_outbound_failed"
elif [ "$long_running" -gt 0 ] || [ "$no_reply_payloads" -gt 0 ]; then
  echo "diagnosis_hint=inspect_and_compact_target_session"
elif printf '%s\n' "$probe_line" | rg -q 'configured,.*running,.*works'; then
  echo "diagnosis_hint=currently_healthy_check_target_timeline"
else
  echo "diagnosis_hint=probe_or_channel_state_requires_manual_review"
fi

echo "read_only=yes"
