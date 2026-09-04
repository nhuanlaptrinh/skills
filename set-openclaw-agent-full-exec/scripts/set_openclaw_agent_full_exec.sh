#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_NAME="$(basename "$0")"
ACTION=""
MEMBER=""
AGENT_ID="main"
OPENCLAW_ROOT=""
CONTAINER=""
RUNTIME_HOME=""
BACKUP_BASE="/root/_Backups/openclaw-agent-full-exec"
NO_RESTART=false
CONFIG_CANDIDATE=""
APPROVALS_CANDIDATE=""
APPROVALS_CURRENT=""
CONFIG_CHANGED=true
APPROVALS_CHANGED=true
APPROVALS_BACKEND=""
NATIVE_DB=""
APPROVALS_LOCATOR=""
BACKUP_APPROVALS_PATH=""
BACKUP_APPROVALS_EXISTS=false

usage() {
  cat <<'EOF'
Usage:
  set_openclaw_agent_full_exec.sh --member MEMBER --agent AGENT (--dry-run|--apply|--check) [options]
  set_openclaw_agent_full_exec.sh --openclaw-root PATH --agent AGENT (--dry-run|--apply|--check) [options]

Options:
  --member NAME          Use the standard member VPS paths and container user-NAME.
  --openclaw-root PATH   Host path containing openclaw.json and OpenClaw approval state.
  --agent ID             Agent ID to update (default: main).
  --container NAME       Runtime container for validate/restart.
  --runtime-home PATH    HOME used by OpenClaw at runtime.
  --backup-dir PATH      Backup base (default: /root/_Backups/openclaw-agent-full-exec).
  --no-restart           Apply files without restarting Gateway.
  --dry-run              Show the safe field-level diff only.
  --apply                Backup, write, validate, restart and verify.
  --check                Verify files and runtime without changes.
  -h, --help             Show this help.
EOF
}

die() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

cleanup() {
  [ -z "$CONFIG_CANDIDATE" ] || rm -f -- "$CONFIG_CANDIDATE"
  [ -z "$APPROVALS_CANDIDATE" ] || rm -f -- "$APPROVALS_CANDIDATE"
  [ -z "$APPROVALS_CURRENT" ] || rm -f -- "$APPROVALS_CURRENT"
}
trap cleanup EXIT

sanitize_output() {
  sed -E \
    -e 's/([Tt]oken|[Kk]ey|[Ss]ecret)([^[:space:]]*)[=:][^[:space:]]+/\1\2=<redacted>/g' \
    -e 's/[0-9]{6,}:[A-Za-z0-9_-]{20,}/<redacted>/g'
}

set_action() {
  local requested="$1"
  [ -z "$ACTION" ] || die "Choose exactly one of --dry-run, --apply or --check"
  ACTION="$requested"
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --member)
      [ "$#" -ge 2 ] || die "--member requires a value"
      MEMBER="$2"
      shift 2
      ;;
    --openclaw-root)
      [ "$#" -ge 2 ] || die "--openclaw-root requires a value"
      OPENCLAW_ROOT="$2"
      shift 2
      ;;
    --agent)
      [ "$#" -ge 2 ] || die "--agent requires a value"
      AGENT_ID="$2"
      shift 2
      ;;
    --container)
      [ "$#" -ge 2 ] || die "--container requires a value"
      CONTAINER="$2"
      shift 2
      ;;
    --runtime-home)
      [ "$#" -ge 2 ] || die "--runtime-home requires a value"
      RUNTIME_HOME="$2"
      shift 2
      ;;
    --backup-dir)
      [ "$#" -ge 2 ] || die "--backup-dir requires a value"
      BACKUP_BASE="$2"
      shift 2
      ;;
    --no-restart)
      NO_RESTART=true
      shift
      ;;
    --dry-run)
      set_action dry-run
      shift
      ;;
    --apply)
      set_action apply
      shift
      ;;
    --check)
      set_action check
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      die "Unknown option: $1"
      ;;
  esac
done

[ -n "$ACTION" ] || die "Choose one of --dry-run, --apply or --check"
[ "$EUID" -eq 0 ] || die "Run as root"
[[ "$AGENT_ID" =~ ^[A-Za-z0-9._-]+$ ]] || die "Unsafe agent ID"

if [ -n "$MEMBER" ]; then
  [ -z "$OPENCLAW_ROOT" ] || die "Do not combine --member with --openclaw-root"
  [[ "$MEMBER" =~ ^[A-Za-z0-9._-]+$ ]] || die "Unsafe member name"
  OPENCLAW_ROOT="/root/Apps/member_vps/docker-users/data/$MEMBER/root/.openclaw"
  [ -n "$CONTAINER" ] || CONTAINER="user-$MEMBER"
  [ -n "$RUNTIME_HOME" ] || RUNTIME_HOME="/root"
  TARGET_LABEL="$MEMBER"
else
  [ -n "$OPENCLAW_ROOT" ] || die "Use --member or --openclaw-root"
  TARGET_LABEL="custom-$(basename "$(dirname "$OPENCLAW_ROOT")")"
fi

[[ "$CONTAINER" =~ ^[A-Za-z0-9._-]*$ ]] || die "Unsafe container name"
[[ "$OPENCLAW_ROOT" = /* ]] || die "--openclaw-root must be absolute"
[[ "$BACKUP_BASE" = /* ]] || die "--backup-dir must be absolute"
[ -d "$OPENCLAW_ROOT" ] || die "OpenClaw root not found: $OPENCLAW_ROOT"
OPENCLAW_ROOT="$(realpath "$OPENCLAW_ROOT")"
[ -n "$RUNTIME_HOME" ] || RUNTIME_HOME="$(dirname "$OPENCLAW_ROOT")"
[[ "$RUNTIME_HOME" = /* ]] || die "--runtime-home must be absolute"

CONFIG_FILE="$OPENCLAW_ROOT/openclaw.json"
APPROVALS_FILE="$OPENCLAW_ROOT/exec-approvals.json"
NATIVE_DB="$OPENCLAW_ROOT/state/openclaw.sqlite"
NATIVE_HELPER="$(dirname "$0")/native_approvals.py"
[ -f "$CONFIG_FILE" ] || die "Missing config: $CONFIG_FILE"
[ ! -L "$CONFIG_FILE" ] || die "Refusing symlink config: $CONFIG_FILE"
[ ! -e "$APPROVALS_FILE" ] || [ -f "$APPROVALS_FILE" ] || die "Approval path is not a regular file"
[ ! -L "$APPROVALS_FILE" ] || die "Refusing symlink approvals file"
[ ! -L "$OPENCLAW_ROOT/state" ] || die "Refusing symlink native state directory"
[ ! -e "$OPENCLAW_ROOT/state" ] || [ -d "$OPENCLAW_ROOT/state" ] || die "Native state path is not a directory"
[ ! -L "$NATIVE_DB" ] || die "Refusing symlink native approvals database"

if { [ -e "$NATIVE_HELPER" ] && [ ! -f "$NATIVE_HELPER" ]; } || [ -L "$NATIVE_HELPER" ]; then
  die "Native approvals helper is not a regular file"
fi
[ -f "$NATIVE_HELPER" ] || die "Missing native approvals helper: $NATIVE_HELPER"

for command_name in jq mktemp sha256sum stat realpath python3; do
  command -v "$command_name" >/dev/null 2>&1 || die "Missing dependency: $command_name"
done

jq empty "$CONFIG_FILE" >/dev/null || die "Invalid JSON: $CONFIG_FILE"
if [ -f "$APPROVALS_FILE" ]; then
  jq empty "$APPROVALS_FILE" >/dev/null || die "Invalid JSON: $APPROVALS_FILE"
fi

native_schema_present() {
  [ -f "$NATIVE_DB" ] || return 1
  python3 - "$NATIVE_DB" <<'PY'
import sqlite3
import sys

path = sys.argv[1]
try:
    connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=2)
    try:
        row = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='exec_approvals_config'"
        ).fetchone()
        raise SystemExit(0 if row else 1)
    finally:
        connection.close()
except sqlite3.Error:
    raise SystemExit(2)
PY
}

if [ -f "$NATIVE_DB" ]; then
  if native_schema_present; then
    native_status=0
  else
    native_status=$?
  fi
  if [ "$native_status" -eq 0 ]; then
    APPROVALS_BACKEND="sqlite"
  elif [ -f "$APPROVALS_FILE" ]; then
    APPROVALS_BACKEND="legacy"
  else
    die "Native approvals database is missing the OpenClaw schema"
  fi
elif [ -f "$APPROVALS_FILE" ]; then
  APPROVALS_BACKEND="legacy"
else
  # A fresh 2026.8 root initializes the native row on first approval write.
  APPROVALS_BACKEND="sqlite"
fi

if [ "$APPROVALS_BACKEND" = sqlite ]; then
  APPROVALS_LOCATOR="$NATIVE_DB#exec_approvals_config"
else
  APPROVALS_LOCATOR="$APPROVALS_FILE"
fi

APPROVALS_CURRENT="$(mktemp "$OPENCLAW_ROOT/.exec-approvals.current.XXXXXX")"
chmod 600 "$APPROVALS_CURRENT"

load_current_approvals() {
  local metadata
  if [ "$APPROVALS_BACKEND" = sqlite ]; then
    metadata="$(python3 "$NATIVE_HELPER" export --root "$OPENCLAW_ROOT" --output "$APPROVALS_CURRENT")" \
      || die "Unable to read native OpenClaw approvals"
  else
    cp -a -- "$APPROVALS_FILE" "$APPROVALS_CURRENT"
    chmod 600 "$APPROVALS_CURRENT"
    metadata=''
  fi
  jq empty "$APPROVALS_CURRENT" >/dev/null || die "Invalid active approvals document"
}

load_current_approvals

backup_approvals_state() {
  local destination="$1" metadata
  metadata="$(python3 "$NATIVE_HELPER" backup \
    --root "$OPENCLAW_ROOT" --destination "$destination" --label exec-approvals)" \
    || die "Unable to back up active OpenClaw approvals"
  BACKUP_APPROVALS_PATH="$(jq -r '.path // empty' <<<"$metadata")"
  [ -n "$BACKUP_APPROVALS_PATH" ] || die "Approval backup path was not returned"
  BACKUP_APPROVALS_EXISTS="$(jq -r 'if .exists then "true" else "false" end' <<<"$metadata")"
  printf '%s\n' "$metadata" > "$destination/approval-backup-metadata.json"
  chmod 600 "$destination/approval-backup-metadata.json"
}

restore_approvals_state() {
  local path="$1" backend="$2" exists="$3"
  local -a command=(python3 "$NATIVE_HELPER" restore
    --root "$OPENCLAW_ROOT" --backend "$backend" --path "$path")
  [ "$exists" = true ] && command+=(--exists)
  "${command[@]}" >/dev/null || die "Unable to restore OpenClaw approvals"
  load_current_approvals
}

save_approvals_state() {
  if [ "$APPROVALS_BACKEND" = sqlite ]; then
    # The native CLI owns schema initialization and socket-token preservation.
    local status
    if OPENCLAW_STATE_DIR="$OPENCLAW_ROOT" OPENCLAW_CONFIG_PATH="$CONFIG_FILE" \
      openclaw approvals set --stdin --json < "$APPROVALS_CANDIDATE" \
      >/dev/null 2>/dev/null; then
      status=0
    else
      status=$?
    fi
    [ "$status" -eq 0 ] || die "Native OpenClaw approvals update failed"
  else
    local mode owner group
    if [ -f "$APPROVALS_FILE" ]; then
      mode="$(stat -c '%a' "$APPROVALS_FILE")"
      owner="$(stat -c '%u' "$APPROVALS_FILE")"
      group="$(stat -c '%g' "$APPROVALS_FILE")"
      chmod "$mode" "$APPROVALS_CANDIDATE"
      chown "$owner:$group" "$APPROVALS_CANDIDATE"
    else
      chmod 600 "$APPROVALS_CANDIDATE"
      chown --reference="$CONFIG_FILE" "$APPROVALS_CANDIDATE"
    fi
    mv -f -- "$APPROVALS_CANDIDATE" "$APPROVALS_FILE"
    APPROVALS_CANDIDATE=""
  fi
  load_current_approvals
}

AGENT_SCHEMA="$(jq -r '
  if ((.agents | type) == "object" and (.agents | has("entries"))) then
    if (.agents.entries | type) == "object" then "entries" else "unsupported" end
  elif ((.agents | type) == "object" and (.agents | has("list"))) then
    if (.agents.list | type) == "array" then "list" else "unsupported" end
  else "unsupported"
  end
' "$CONFIG_FILE")"
[ "$AGENT_SCHEMA" != unsupported ] || die "Unsupported agents schema; expected agents.entries or agents.list"
if [ "$AGENT_SCHEMA" = entries ]; then
  AGENT_COUNT="$(jq --arg agent "$AGENT_ID" '[.agents.entries[$agent] | select(type == "object")] | length' "$CONFIG_FILE")"
else
  AGENT_COUNT="$(jq --arg agent "$AGENT_ID" '[.agents.list[]? | select(.id == $agent)] | length' "$CONFIG_FILE")"
fi
[ "$AGENT_COUNT" -eq 1 ] || die "Agent '$AGENT_ID' must exist exactly once; found $AGENT_COUNT"

config_snapshot() {
  if [ "$AGENT_SCHEMA" = entries ]; then
    jq -c --arg agent "$AGENT_ID" '
      .agents.entries[$agent] |
      {
        host: (.tools.exec.host // null),
        mode: (.tools.exec.mode // null),
        security_override: (.tools.exec.security // null),
        ask_override: (.tools.exec.ask // null),
        strictInlineEval: (
          if (.tools.exec | has("strictInlineEval"))
          then .tools.exec.strictInlineEval
          else null
          end
        )
      }
    ' "$1"
  else
    jq -c --arg agent "$AGENT_ID" '
      .agents.list[] | select(.id == $agent) |
      {
        host: (.tools.exec.host // null),
        mode: (.tools.exec.mode // null),
        security_override: (.tools.exec.security // null),
        ask_override: (.tools.exec.ask // null),
        strictInlineEval: (
          if (.tools.exec | has("strictInlineEval"))
          then .tools.exec.strictInlineEval
          else null
          end
        )
      }
    ' "$1"
  fi
}

approvals_snapshot() {
  local file="$1"
  jq -c --arg agent "$AGENT_ID" '
    (.agents[$agent] // {}) |
    {
      security: (.security // null),
      ask: (.ask // null),
      askFallback: (.askFallback // null),
      autoAllowSkills: (
        if has("autoAllowSkills")
        then .autoAllowSkills
        else null
        end
      ),
      allowlist_count: ((.allowlist // []) | length)
    }
  ' "$file"
}

json_equal() {
  jq -e -s '.[0] == .[1]' "$1" "$2" >/dev/null 2>&1
}

make_candidates() {
  CONFIG_CANDIDATE="$(mktemp "$OPENCLAW_ROOT/.openclaw.json.full-exec.XXXXXX")"
  APPROVALS_CANDIDATE="$(mktemp "$OPENCLAW_ROOT/.exec-approvals.full-exec.XXXXXX")"

  if [ "$AGENT_SCHEMA" = entries ]; then
    jq --arg agent "$AGENT_ID" '
      .agents.entries[$agent] |= (
        .tools = (.tools // {}) |
        .tools.exec = ((.tools.exec // {}) + {
          host: "gateway",
          mode: "full",
          strictInlineEval: false
        }) |
        if .tools.exec.security? != null then .tools.exec.security = "full" else . end |
        if .tools.exec.ask? != null then .tools.exec.ask = "off" else . end
      )
    ' "$CONFIG_FILE" > "$CONFIG_CANDIDATE"
  else
    jq --arg agent "$AGENT_ID" '
      .agents.list |= map(
        if .id == $agent then
          .tools = (.tools // {}) |
          .tools.exec = ((.tools.exec // {}) + {
            host: "gateway",
            mode: "full",
            strictInlineEval: false
          }) |
          if .tools.exec.security? != null then .tools.exec.security = "full" else . end |
          if .tools.exec.ask? != null then .tools.exec.ask = "off" else . end
        else . end
      )
    ' "$CONFIG_FILE" > "$CONFIG_CANDIDATE"
  fi

  jq --arg agent "$AGENT_ID" '
    .version = (.version // 1) |
    .agents = (.agents // {}) |
    .agents[$agent] = ((.agents[$agent] // {}) + {
      security: "full",
      ask: "off",
      askFallback: "full",
      autoAllowSkills: true
    })
  ' "$APPROVALS_CURRENT" > "$APPROVALS_CANDIDATE"

  jq empty "$CONFIG_CANDIDATE" >/dev/null || die "Generated invalid config candidate"
  jq empty "$APPROVALS_CANDIDATE" >/dev/null || die "Generated invalid approvals candidate"

  CONFIG_CHANGED=true
  APPROVALS_CHANGED=true
  json_equal "$CONFIG_FILE" "$CONFIG_CANDIDATE" && CONFIG_CHANGED=false
  json_equal "$APPROVALS_CURRENT" "$APPROVALS_CANDIDATE" && APPROVALS_CHANGED=false
  return 0
}

files_compliant() {
  local status=0
  if [ "$AGENT_SCHEMA" = entries ]; then
    jq -e --arg agent "$AGENT_ID" '
      (.agents.entries[$agent].tools.exec) as $exec |
      $exec.host == "gateway" and
      $exec.mode == "full" and
      $exec.strictInlineEval == false and
      (($exec.security // "full") == "full") and
      (($exec.ask // "off") == "off")
    ' "$CONFIG_FILE" >/dev/null 2>&1 || status=$?
  else
    jq -e --arg agent "$AGENT_ID" '
      (.agents.list[] | select(.id == $agent) | .tools.exec) as $exec |
      $exec.host == "gateway" and
      $exec.mode == "full" and
      $exec.strictInlineEval == false and
      (($exec.security // "full") == "full") and
      (($exec.ask // "off") == "off")
    ' "$CONFIG_FILE" >/dev/null 2>&1 || status=$?
  fi
  [ "$status" -eq 0 ] &&
  jq -e --arg agent "$AGENT_ID" '
    .agents[$agent].security == "full" and
    .agents[$agent].ask == "off" and
    .agents[$agent].askFallback == "full" and
    .agents[$agent].autoAllowSkills == true
  ' "$APPROVALS_CURRENT" >/dev/null 2>&1
}

validate_runtime() {
  local output status
  if [ -n "$CONTAINER" ]; then
    command -v docker >/dev/null 2>&1 || die "docker is required for --container"
    docker inspect "$CONTAINER" >/dev/null 2>&1 || die "Container not found: $CONTAINER"
    output="$(docker exec -e HOME="$RUNTIME_HOME" "$CONTAINER" openclaw config validate 2>&1)" || status=$?
  else
    command -v openclaw >/dev/null 2>&1 || die "openclaw command not found"
    output="$(HOME="$RUNTIME_HOME" OPENCLAW_STATE_DIR="$OPENCLAW_ROOT" OPENCLAW_CONFIG_PATH="$CONFIG_FILE" openclaw config validate 2>&1)" || status=$?
  fi
  printf '%s\n' "$output" | sanitize_output
  [ "${status:-0}" -eq 0 ] || return "$status"
}

runtime_approval_check() {
  local snapshot
  if [ -n "$CONTAINER" ]; then
    snapshot="$(docker exec -e HOME="$RUNTIME_HOME" "$CONTAINER" openclaw approvals get --gateway --json 2>/dev/null)" || return 1
  else
    snapshot="$(HOME="$RUNTIME_HOME" OPENCLAW_STATE_DIR="$OPENCLAW_ROOT" OPENCLAW_CONFIG_PATH="$CONFIG_FILE" openclaw approvals get --gateway --json 2>/dev/null)" || return 1
  fi
  printf '%s\n' "$snapshot" | jq -e --arg agent "$AGENT_ID" '
    ((.file.agents // .agents)[$agent]) as $policy |
    $policy.security == "full" and $policy.ask == "off"
  ' >/dev/null
}

preflight_restart() {
  $NO_RESTART && return 0
  if [ -n "$CONTAINER" ]; then
    command -v docker >/dev/null 2>&1 || die "docker is required for --container"
    [ "$(docker inspect "$CONTAINER" --format '{{.State.Running}}' 2>/dev/null)" = "true" ] || die "Container is not running: $CONTAINER"
    local gateway_pid parent_pid parent_comm
    gateway_pid="$(docker exec "$CONTAINER" sh -lc "pgrep -o -f '^openclaw-gateway$'" 2>/dev/null)" || die "Gateway process not found in $CONTAINER"
    parent_pid="$(docker exec "$CONTAINER" sh -lc "ps -o ppid= -p '$gateway_pid' | tr -d ' '" 2>/dev/null)"
    parent_comm="$(docker exec "$CONTAINER" sh -lc "ps -o comm= -p '$parent_pid' | tr -d ' '" 2>/dev/null)"
    [[ "$parent_comm" == *supervisord* ]] || die "Gateway parent is '$parent_comm', not Supervisor; rerun with --no-restart"
  else
    command -v openclaw >/dev/null 2>&1 || die "openclaw command not found"
  fi
}

restart_gateway() {
  $NO_RESTART && {
    printf 'restart=skipped (--no-restart)\n'
    return
  }

  if [ -n "$CONTAINER" ]; then
    local old_pid new_pid attempt
    old_pid="$(docker exec "$CONTAINER" sh -lc "pgrep -o -f '^openclaw-gateway$'")"
    docker exec "$CONTAINER" sh -lc "kill '$old_pid'"
    new_pid=""
    for attempt in $(seq 1 30); do
      new_pid="$(docker exec "$CONTAINER" sh -lc "pgrep -o -f '^openclaw-gateway$' || true")"
      if [ -n "$new_pid" ] && [ "$new_pid" != "$old_pid" ]; then
        break
      fi
      sleep 1
    done
    [ -n "$new_pid" ] && [ "$new_pid" != "$old_pid" ] || die "Gateway did not respawn; config backup remains available"
    printf 'gateway_respawned=true old_pid=%s new_pid=%s\n' "$old_pid" "$new_pid"
    docker exec -e HOME="$RUNTIME_HOME" "$CONTAINER" openclaw gateway status 2>&1 | sanitize_output | grep -E 'Connectivity probe|Listening|Gateway version' || true
    docker exec -e HOME="$RUNTIME_HOME" "$CONTAINER" openclaw channels status --probe 2>&1 | sanitize_output | grep -E 'Gateway reachable|Telegram|Zalo' || true
  else
    HOME="$RUNTIME_HOME" OPENCLAW_STATE_DIR="$OPENCLAW_ROOT" OPENCLAW_CONFIG_PATH="$CONFIG_FILE" openclaw gateway restart 2>&1 | sanitize_output
  fi
}

print_summary() {
  printf 'target=%s\nagent=%s\nopenclaw_root=%s\n' "$TARGET_LABEL" "$AGENT_ID" "$OPENCLAW_ROOT"
  [ -z "$CONTAINER" ] || printf 'container=%s\n' "$CONTAINER"
  printf 'config_exec=%s\n' "$(config_snapshot "$CONFIG_FILE")"
  printf 'approval_locator=%s\n' "$APPROVALS_LOCATOR"
  printf 'approval_backend=%s\n' "$APPROVALS_BACKEND"
  printf 'approval_policy=%s\n' "$(approvals_snapshot "$APPROVALS_CURRENT")"
}

if [ "$ACTION" = "check" ]; then
  print_summary
  files_compliant || die "Exec settings are not compliant"
  validate_runtime
  if $NO_RESTART; then
    printf 'gateway_approval_runtime=skipped (--no-restart)\n'
  else
    runtime_approval_check || die "Gateway approval runtime is not full/off for agent '$AGENT_ID'"
    printf 'gateway_approval_runtime=full_off\n'
  fi
  printf 'check=pass\n'
  exit 0
fi

make_candidates

if [ "$ACTION" = "dry-run" ]; then
  printf 'action=dry-run\n'
  printf 'target=%s\nagent=%s\n' "$TARGET_LABEL" "$AGENT_ID"
  printf 'config_before=%s\n' "$(config_snapshot "$CONFIG_FILE")"
  printf 'config_after=%s\n' "$(config_snapshot "$CONFIG_CANDIDATE")"
  printf 'approvals_before=%s\n' "$(approvals_snapshot "$APPROVALS_CURRENT")"
  printf 'approvals_after=%s\n' "$(approvals_snapshot "$APPROVALS_CANDIDATE")"
  if ! $CONFIG_CHANGED && ! $APPROVALS_CHANGED; then
    printf 'changes_required=false\n'
  else
    printf 'changes_required=true\n'
  fi
  if ! $CONFIG_CHANGED && ! $APPROVALS_CHANGED; then
    printf 'restart=not-needed\n'
  else
    printf 'restart=%s\n' "$([ "$NO_RESTART" = true ] && printf skipped || printf planned)"
  fi
  exit 0
fi

preflight_restart

if ! $CONFIG_CHANGED && ! $APPROVALS_CHANGED; then
  printf 'changes_required=false\n'
  files_compliant || die "Files match candidates but compliance check failed"
  validate_runtime
  if $NO_RESTART; then
    printf 'gateway_approval_runtime=skipped (--no-restart)\n'
  else
    runtime_approval_check || die "Gateway approval runtime is not full/off"
    printf 'gateway_approval_runtime=full_off\n'
  fi
  printf 'apply=already-compliant\n'
  exit 0
fi

TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
BACKUP_DIR="$BACKUP_BASE/$TARGET_LABEL/$TIMESTAMP"
mkdir -p "$BACKUP_DIR"
chmod 700 "$BACKUP_DIR"
cp -a "$CONFIG_FILE" "$BACKUP_DIR/openclaw.json"
backup_approvals_state "$BACKUP_DIR"
sha256sum "$BACKUP_DIR/openclaw.json" > "$BACKUP_DIR/SHA256SUMS"
if [ -f "$BACKUP_APPROVALS_PATH" ]; then
  sha256sum "$BACKUP_APPROVALS_PATH" >> "$BACKUP_DIR/SHA256SUMS"
fi
printf 'target=%s\nagent=%s\ncreated_utc=%s\n' "$TARGET_LABEL" "$AGENT_ID" "$TIMESTAMP" > "$BACKUP_DIR/metadata.txt"
printf 'approval_backend=%s\napproval_locator=%s\napproval_backup=%s\napproval_backup_exists=%s\n' \
  "$APPROVALS_BACKEND" "$APPROVALS_LOCATOR" "$BACKUP_APPROVALS_PATH" "$BACKUP_APPROVALS_EXISTS" \
  >> "$BACKUP_DIR/metadata.txt"
chmod 600 "$BACKUP_DIR/SHA256SUMS" "$BACKUP_DIR/metadata.txt"

if $CONFIG_CHANGED; then
  chmod --reference="$CONFIG_FILE" "$CONFIG_CANDIDATE"
  chown --reference="$CONFIG_FILE" "$CONFIG_CANDIDATE"
  mv -f -- "$CONFIG_CANDIDATE" "$CONFIG_FILE"
  CONFIG_CANDIDATE=""
else
  rm -f -- "$CONFIG_CANDIDATE"
  CONFIG_CANDIDATE=""
fi

if $APPROVALS_CHANGED; then
  save_approvals_state
else
  rm -f -- "$APPROVALS_CANDIDATE"
  APPROVALS_CANDIDATE=""
fi

if ! validate_runtime; then
  cp -a "$BACKUP_DIR/openclaw.json" "$CONFIG_FILE"
  if $APPROVALS_CHANGED; then
    restore_approvals_state "$BACKUP_APPROVALS_PATH" "$APPROVALS_BACKEND" "$BACKUP_APPROVALS_EXISTS"
  fi
  die "Validation failed; files restored from $BACKUP_DIR"
fi

restart_gateway
files_compliant || die "Post-apply compliance check failed"
if $NO_RESTART; then
  printf 'gateway_approval_runtime=skipped (--no-restart)\n'
else
  runtime_approval_check || die "Gateway approval runtime is not full/off after apply"
  printf 'gateway_approval_runtime=full_off\n'
fi
print_summary
printf 'backup_dir=%s\napply=pass\n' "$BACKUP_DIR"
