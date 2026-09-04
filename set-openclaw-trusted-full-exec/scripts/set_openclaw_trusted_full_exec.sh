#!/usr/bin/env bash
set -Eeuo pipefail

ACTION=""
MEMBER=""
OPENCLAW_ROOT=""
CONTAINER=""
RUNTIME_HOME=""
BACKUP_BASE="/root/_Backups/openclaw-trusted-full-exec"
NO_RESTART=false
CONFIG_CANDIDATE=""
APPROVALS_CANDIDATE=""
REPORT_FILE=""
CONFIG_CHANGED=true
APPROVALS_CHANGED=true

usage() {
  cat <<'EOF'
Usage:
  set_openclaw_trusted_full_exec.sh --member MEMBER (--dry-run|--apply|--check) [options]
  set_openclaw_trusted_full_exec.sh --openclaw-root PATH (--dry-run|--apply|--check) [options]

Options:
  --member NAME          Use the standard member VPS paths and container user-NAME.
  --openclaw-root PATH   Host path containing openclaw.json and exec-approvals.json.
  --container NAME       Runtime container for validate/restart.
  --runtime-home PATH    HOME used by OpenClaw at runtime.
  --backup-dir PATH      Backup base.
  --no-restart           Apply files without restarting Gateway.
  --dry-run              Show a safe summary only.
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
  [ -z "$REPORT_FILE" ] || rm -f -- "$REPORT_FILE"
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
CREDENTIALS_DIR="$OPENCLAW_ROOT/credentials"
[ -f "$CONFIG_FILE" ] || die "Missing config: $CONFIG_FILE"
[ ! -L "$CONFIG_FILE" ] || die "Refusing symlink config: $CONFIG_FILE"
[ ! -e "$APPROVALS_FILE" ] || [ -f "$APPROVALS_FILE" ] || die "Approval path is not a regular file"
[ ! -L "$APPROVALS_FILE" ] || die "Refusing symlink approvals file"

for command_name in jq node mktemp sha256sum stat realpath; do
  command -v "$command_name" >/dev/null 2>&1 || die "Missing dependency: $command_name"
done

jq empty "$CONFIG_FILE" >/dev/null || die "Invalid JSON: $CONFIG_FILE"
if [ -f "$APPROVALS_FILE" ]; then
  jq empty "$APPROVALS_FILE" >/dev/null || die "Invalid JSON: $APPROVALS_FILE"
fi

json_equal() {
  jq -e -s '.[0] == .[1]' "$1" "$2" >/dev/null 2>&1
}

make_candidates() {
  CONFIG_CANDIDATE="$(mktemp "$OPENCLAW_ROOT/.openclaw.json.trusted-full-exec.XXXXXX")"
  APPROVALS_CANDIDATE="$(mktemp "$OPENCLAW_ROOT/.exec-approvals.json.trusted-full-exec.XXXXXX")"
  REPORT_FILE="$(mktemp "$OPENCLAW_ROOT/.trusted-full-exec-report.XXXXXX")"

  env \
    CONFIG_FILE="$CONFIG_FILE" \
    APPROVALS_FILE="$APPROVALS_FILE" \
    CREDENTIALS_DIR="$CREDENTIALS_DIR" \
    CONFIG_CANDIDATE="$CONFIG_CANDIDATE" \
    APPROVALS_CANDIDATE="$APPROVALS_CANDIDATE" \
    REPORT_FILE="$REPORT_FILE" \
    node <<'NODE'
const fs = require('fs');
const path = require('path');

const configPath = process.env.CONFIG_FILE;
const approvalsPath = process.env.APPROVALS_FILE;
const credentialsDir = process.env.CREDENTIALS_DIR;
const configCandidatePath = process.env.CONFIG_CANDIDATE;
const approvalsCandidatePath = process.env.APPROVALS_CANDIDATE;
const reportPath = process.env.REPORT_FILE;

const readJson = (file) => JSON.parse(fs.readFileSync(file, 'utf8'));
const config = readJson(configPath);
const originalConfig = JSON.parse(JSON.stringify(config));

const isObject = (value) => value && typeof value === 'object' && !Array.isArray(value);
const hasEntries = isObject(config?.agents)
  && Object.prototype.hasOwnProperty.call(config.agents, 'entries');
if (hasEntries && !isObject(config.agents.entries)) throw new Error('agents.entries must be an object');
const entryMap = hasEntries ? config.agents.entries : null;
const agents = entryMap
  ? Object.entries(entryMap).map(([id, agent]) => ({ id, agent }))
  : (Array.isArray(config?.agents?.list)
    ? config.agents.list.map((agent) => ({ id: String(agent?.id ?? ''), agent }))
    : []);
if (agents.length === 0) throw new Error('No agents found in agents.entries or agents.list');
const agentIds = agents.map(({ id }) => String(id));
if (agentIds.some((id) => !/^[A-Za-z0-9._-]+$/.test(id))) throw new Error('Unsafe or missing agent ID');
if (new Set(agentIds).size !== agentIds.length) throw new Error('Duplicate agent ID');
if (agents.some(({ agent }) => !isObject(agent))) throw new Error('Agent entries must be objects');

const normalizeEntries = (values) => {
  if (!Array.isArray(values)) return [];
  return values
    .map((value) => String(value).trim())
    .filter((value) => value.length > 0 && value !== '*');
};
const uniqueSorted = (values) => [...new Set(values)].sort((a, b) => a.localeCompare(b, 'en'));
const arraysEqual = (left, right) => JSON.stringify(left) === JSON.stringify(right);
const telegram = config?.channels?.telegram;
if (!isObject(telegram)) throw new Error('Missing channels.telegram config');
const baseAllowFrom = Array.isArray(telegram.allowFrom) ? telegram.allowFrom : [];
const baseRestrictive = normalizeEntries(baseAllowFrom);
const ownerIds = normalizeEntries((config?.commands?.ownerAllowFrom ?? [])
  .map((entry) => String(entry))
  .filter((entry) => entry.toLowerCase().startsWith('telegram:'))
  .map((entry) => entry.slice('telegram:'.length)));

const accountObject = isObject(telegram.accounts) ? telegram.accounts : {};
const accountIds = Object.keys(accountObject);
const accountScopes = accountIds.length > 0
  ? accountIds.map((id) => ({ id, account: accountObject[id] }))
  : [{ id: 'default', account: telegram }];

const resolveEffectiveAllowFrom = (account) => {
  if (!Object.prototype.hasOwnProperty.call(account, 'allowFrom')) return baseAllowFrom;
  const accountAllow = Array.isArray(account.allowFrom) ? account.allowFrom : [];
  const hasWildcard = accountAllow.some((entry) => String(entry).trim() === '*');
  if (baseRestrictive.length > 0 && hasWildcard) {
    const accountRestrictive = normalizeEntries(accountAllow);
    return accountRestrictive.length > 0 ? accountRestrictive : baseAllowFrom;
  }
  return accountAllow;
};

const loadPairingAllowFrom = (accountId) => {
  if (!/^[A-Za-z0-9._-]+$/.test(accountId)) throw new Error(`Unsafe Telegram account ID: ${accountId}`);
  const file = path.join(credentialsDir, `telegram-${accountId}-allowFrom.json`);
  if (!fs.existsSync(file)) return [];
  const parsed = readJson(file);
  return normalizeEntries(parsed?.allowFrom);
};

const accountReports = [];
for (const scope of accountScopes) {
  if (!isObject(scope.account)) throw new Error(`Invalid Telegram account config: ${scope.id}`);
  const paired = loadPairingAllowFrom(scope.id);
  const trusted = uniqueSorted([
    ...normalizeEntries(resolveEffectiveAllowFrom(scope.account)),
    ...paired,
    ...ownerIds
  ]);
  if (trusted.length === 0) throw new Error(`Trusted sender set is empty for Telegram account: ${scope.id}`);
  if (trusted.includes('*')) throw new Error(`Wildcard sender is forbidden for Telegram account: ${scope.id}`);

  const before = JSON.parse(JSON.stringify(scope.account));
  scope.account.dmPolicy = 'pairing';
  scope.account.allowFrom = trusted;
  scope.account.groupPolicy = 'allowlist';
  scope.account.groupAllowFrom = trusted;
  if (!isObject(scope.account.groups)) scope.account.groups = {};
  if (!isObject(scope.account.groups['*'])) scope.account.groups['*'] = {};

  for (const [groupId, rawGroup] of Object.entries(scope.account.groups)) {
    const group = isObject(rawGroup) ? rawGroup : {};
    group.allowFrom = trusted;
    if (isObject(group.topics)) {
      for (const [topicId, rawTopic] of Object.entries(group.topics)) {
        const topic = isObject(rawTopic) ? rawTopic : {};
        topic.allowFrom = trusted;
        group.topics[topicId] = topic;
      }
    }
    scope.account.groups[groupId] = group;
  }

  const afterGroupEntries = Object.values(scope.account.groups);
  const allGroupListsMatch = afterGroupEntries.every((group) => {
    if (!isObject(group) || !arraysEqual(group.allowFrom, trusted)) return false;
    if (!isObject(group.topics)) return true;
    return Object.values(group.topics).every((topic) => isObject(topic) && arraysEqual(topic.allowFrom, trusted));
  });
  const beforeCompliant = before.dmPolicy === 'pairing'
    && arraysEqual(uniqueSorted(normalizeEntries(before.allowFrom)), trusted)
    && before.groupPolicy === 'allowlist'
    && arraysEqual(uniqueSorted(normalizeEntries(before.groupAllowFrom)), trusted)
    && isObject(before.groups)
    && isObject(before.groups['*'])
    && arraysEqual(uniqueSorted(normalizeEntries(before.groups['*'].allowFrom)), trusted)
    && Object.values(before.groups).every((group) => {
      if (!isObject(group) || !arraysEqual(uniqueSorted(normalizeEntries(group.allowFrom)), trusted)) return false;
      if (!isObject(group.topics)) return true;
      return Object.values(group.topics).every((topic) => isObject(topic)
        && arraysEqual(uniqueSorted(normalizeEntries(topic.allowFrom)), trusted));
    });
  if (!allGroupListsMatch) throw new Error(`Failed to build trusted group policy for account: ${scope.id}`);
  accountReports.push({
    id: scope.id,
    trustedSenderCount: trusted.length,
    pairingSenderCount: paired.length,
    beforeCompliant
  });
}

const agentReports = [];
for (const { id, agent } of agents) {
  const beforeExec = agent?.tools?.exec;
  const beforeCompliant = beforeExec?.host === 'gateway'
    && beforeExec?.mode === 'full'
    && beforeExec?.strictInlineEval === false
    && (beforeExec?.security === undefined || beforeExec.security === 'full')
    && (beforeExec?.ask === undefined || beforeExec.ask === 'off');
  agent.tools ??= {};
  agent.tools.exec = {
    ...(isObject(agent.tools.exec) ? agent.tools.exec : {}),
    host: 'gateway',
    mode: 'full',
    strictInlineEval: false
  };
  if (Object.prototype.hasOwnProperty.call(agent.tools.exec, 'security')) agent.tools.exec.security = 'full';
  if (Object.prototype.hasOwnProperty.call(agent.tools.exec, 'ask')) agent.tools.exec.ask = 'off';
  agentReports.push({ id, beforeCompliant });
}

let approvals;
if (fs.existsSync(approvalsPath)) approvals = readJson(approvalsPath);
else approvals = {
  version: 1,
  defaults: {
    security: 'allowlist',
    ask: 'on-miss',
    askFallback: 'deny',
    autoAllowSkills: false
  },
  agents: {}
};
approvals.version ??= 1;
if (!isObject(approvals.agents)) approvals.agents = {};
for (const agentId of agentIds) {
  const previous = isObject(approvals.agents[agentId]) ? approvals.agents[agentId] : {};
  approvals.agents[agentId] = {
    ...previous,
    security: 'full',
    ask: 'off',
    askFallback: 'full',
    autoAllowSkills: true
  };
}

fs.writeFileSync(configCandidatePath, `${JSON.stringify(config, null, 2)}\n`);
fs.writeFileSync(approvalsCandidatePath, `${JSON.stringify(approvals, null, 2)}\n`);
fs.writeFileSync(reportPath, `${JSON.stringify({
  agents: agentReports,
  accounts: accountReports,
  originalAgentCount: agents.length
}, null, 2)}\n`);
NODE

  jq empty "$CONFIG_CANDIDATE" >/dev/null || die "Generated invalid config candidate"
  jq empty "$APPROVALS_CANDIDATE" >/dev/null || die "Generated invalid approvals candidate"
  jq empty "$REPORT_FILE" >/dev/null || die "Generated invalid report"

  CONFIG_CHANGED=true
  APPROVALS_CHANGED=true
  if json_equal "$CONFIG_FILE" "$CONFIG_CANDIDATE"; then
    CONFIG_CHANGED=false
  fi
  if [ -f "$APPROVALS_FILE" ]; then
    if json_equal "$APPROVALS_FILE" "$APPROVALS_CANDIDATE"; then
      APPROVALS_CHANGED=false
    fi
  fi
}

print_safe_summary() {
  printf 'target=%s\nopenclaw_root=%s\n' "$TARGET_LABEL" "$OPENCLAW_ROOT"
  [ -z "$CONTAINER" ] || printf 'container=%s\n' "$CONTAINER"
  jq -r '
    "agent_count=\(.agents | length)",
    "telegram_account_count=\(.accounts | length)",
    "agents_requiring_change=\([.agents[] | select(.beforeCompliant == false)] | length)",
    "accounts_requiring_change=\([.accounts[] | select(.beforeCompliant == false)] | length)",
    (.accounts[] | "telegram_account=\(.id) trusted_sender_count=\(.trustedSenderCount) pairing_sender_count=\(.pairingSenderCount)")
  ' "$REPORT_FILE"
  printf 'config_changes_required=%s\napproval_changes_required=%s\n' "$CONFIG_CHANGED" "$APPROVALS_CHANGED"
}

validate_candidate() {
  local output status=0 runtime_candidate
  if [ -n "$CONTAINER" ]; then
    runtime_candidate="$RUNTIME_HOME/.openclaw/$(basename "$CONFIG_CANDIDATE")"
    output="$(docker exec \
      -e HOME="$RUNTIME_HOME" \
      -e OPENCLAW_CONFIG_PATH="$runtime_candidate" \
      "$CONTAINER" \
      openclaw config validate 2>&1)" || status=$?
  else
    output="$(env \
      HOME="$RUNTIME_HOME" \
      OPENCLAW_CONFIG_PATH="$CONFIG_CANDIDATE" \
      openclaw config validate 2>&1)" || status=$?
  fi
  printf '%s\n' "$output" | sanitize_output
  [ "$status" -eq 0 ]
}

validate_config() {
  local output status=0
  if [ -n "$CONTAINER" ]; then
    command -v docker >/dev/null 2>&1 || die "docker is required for --container"
    output="$(docker exec -e HOME="$RUNTIME_HOME" "$CONTAINER" openclaw config validate 2>&1)" || status=$?
  else
    command -v openclaw >/dev/null 2>&1 || die "openclaw command not found"
    output="$(env HOME="$RUNTIME_HOME" openclaw config validate 2>&1)" || status=$?
  fi
  printf '%s\n' "$output" | sanitize_output
  [ "$status" -eq 0 ]
}

validate_skills() {
  local output status=0
  if [ -n "$CONTAINER" ]; then
    output="$(docker exec -e HOME="$RUNTIME_HOME" "$CONTAINER" openclaw skills check 2>&1)" || status=$?
  else
    output="$(env HOME="$RUNTIME_HOME" openclaw skills check 2>&1)" || status=$?
  fi
  printf '%s\n' "$output" | sanitize_output
  [ "$status" -eq 0 ]
}

runtime_approval_check() {
  local snapshot
  if [ -n "$CONTAINER" ]; then
    snapshot="$(docker exec -e HOME="$RUNTIME_HOME" "$CONTAINER" openclaw approvals get --gateway --json 2>/dev/null)" || return 1
  else
    snapshot="$(env HOME="$RUNTIME_HOME" openclaw approvals get --gateway --json 2>/dev/null)" || return 1
  fi
  printf '%s\n' "$snapshot" | jq -e --slurpfile report "$REPORT_FILE" '
    (.file.agents // .agents) as $policies |
    $report[0].agents | all(.id as $id |
      $policies[$id].security == "full" and
      $policies[$id].ask == "off" and
      $policies[$id].askFallback == "full"
    )
  ' >/dev/null
}

preflight_restart() {
  $NO_RESTART && return 0
  if [ -n "$CONTAINER" ]; then
    command -v docker >/dev/null 2>&1 || die "docker is required for --container"
    [ "$(docker inspect "$CONTAINER" --format '{{.State.Running}}' 2>/dev/null)" = "true" ] || die "Container is not running: $CONTAINER"
    local gateway_pid parent_pid parent_comm
    gateway_pid="$(docker exec "$CONTAINER" sh -lc "pgrep -o -f '^openclaw-gateway$'" 2>/dev/null)" || die "Gateway process not found in $CONTAINER"
    parent_pid="$(docker exec "$CONTAINER" sh -lc "ps -o ppid= -p '$gateway_pid' | tr -d ' '")"
    parent_comm="$(docker exec "$CONTAINER" sh -lc "ps -o comm= -p '$parent_pid' | tr -d ' '")"
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
    printf 'gateway_respawned=true\n'
  else
    local output status=0 health_output health_status=0
    output="$(env HOME="$RUNTIME_HOME" openclaw gateway restart 2>&1)" || status=$?
    printf '%s\n' "$output" | sanitize_output
    if [ "$status" -ne 0 ]; then
      health_output="$(env HOME="$RUNTIME_HOME" openclaw gateway status 2>&1)" || health_status=$?
      if [ "$health_status" -ne 0 ] || ! printf '%s\n' "$health_output" | grep -F 'Connectivity probe: ok' >/dev/null; then
        printf '%s\n' "$health_output" | sanitize_output
        return "$status"
      fi
      printf 'restart_command_status=nonzero_but_gateway_healthy\n'
    fi
  fi
}

wait_for_telegram_accounts() {
  $NO_RESTART && {
    printf 'telegram_connectivity=skipped (--no-restart)\n'
    return 0
  }
  local total_accounts output account_id connected attempt status_line active inactive unknown
  total_accounts="$(jq '.accounts | length' "$REPORT_FILE")"
  [ "$total_accounts" -gt 0 ] || {
    printf 'telegram_connectivity=no_accounts\n'
    return 0
  }

  set +e
  for attempt in 1 2 3 4 5 6; do
    if [ -n "$CONTAINER" ]; then
      output="$(docker exec -e HOME="$RUNTIME_HOME" "$CONTAINER" openclaw channels status --probe 2>&1)" || true
    else
      output="$(env HOME="$RUNTIME_HOME" openclaw channels status --probe 2>&1)" || true
    fi
    connected=0
    active=0
    inactive=0
    unknown=0
    while IFS= read -r account_id; do
      status_line="$(printf '%s\n' "$output" | grep -i -F "Telegram $account_id:" | head -n 1)"
      if [ -z "$status_line" ]; then
        unknown=$((unknown + 1))
      elif printf '%s\n' "$status_line" | grep -i -E 'disabled|not configured' >/dev/null; then
        inactive=$((inactive + 1))
      elif printf '%s\n' "$status_line" | grep -F 'enabled, configured' >/dev/null; then
        active=$((active + 1))
        if printf '%s\n' "$status_line" | grep -F 'running, connected,' | grep -F 'works' >/dev/null; then
          connected=$((connected + 1))
        fi
      else
        unknown=$((unknown + 1))
      fi
    done < <(jq -r '.accounts[].id' "$REPORT_FILE")
    printf 'telegram_probe_attempt=%s connected=%s active=%s inactive=%s unknown=%s\n' \
      "$attempt" "$connected" "$active" "$inactive" "$unknown"
    if [ "$connected" -eq "$active" ] && [ "$unknown" -eq 0 ]; then
      if [ "$active" -eq 0 ]; then
        printf 'telegram_connectivity=no_active_accounts\n'
      else
        printf 'telegram_connectivity=pass\n'
      fi
      set -e
      return 0
    fi
    sleep 10
  done
  set -e
  return 1
}

make_candidates

if [ "$ACTION" = "dry-run" ]; then
  validate_candidate || die "Generated candidate failed OpenClaw validation"
  printf 'action=dry-run\n'
  print_safe_summary
  if ! $CONFIG_CHANGED && ! $APPROVALS_CHANGED; then
    printf 'changes_required=false\nrestart=not-needed\n'
  else
    printf 'changes_required=true\nrestart=%s\n' "$([ "$NO_RESTART" = true ] && printf skipped || printf planned)"
  fi
  exit 0
fi

if [ "$ACTION" = "check" ]; then
  print_safe_summary
  ! $CONFIG_CHANGED || die "OpenClaw config is not compliant; run --dry-run then --apply"
  ! $APPROVALS_CHANGED || die "Exec approvals are not compliant; run --dry-run then --apply"
  validate_config || die "OpenClaw config validation failed"
  if $NO_RESTART; then
    printf 'gateway_approval_runtime=skipped (--no-restart)\n'
    printf 'telegram_connectivity=skipped (--no-restart)\n'
  else
    runtime_approval_check || die "Gateway approval runtime is not full/off for every agent"
    printf 'gateway_approval_runtime=full_off_all_agents\n'
    wait_for_telegram_accounts || die "Not all Telegram accounts are connected"
  fi
  printf 'check=pass\n'
  exit 0
fi

preflight_restart
validate_skills || die "OpenClaw skills check failed; no files changed"
validate_candidate || die "Generated candidate failed OpenClaw validation; no files changed"

if ! $CONFIG_CHANGED && ! $APPROVALS_CHANGED; then
  printf 'changes_required=false\n'
  validate_config || die "OpenClaw config validation failed"
  if $NO_RESTART; then
    printf 'gateway_approval_runtime=skipped (--no-restart)\n'
  else
    runtime_approval_check || die "Gateway approval runtime is not full/off for every agent"
    printf 'gateway_approval_runtime=full_off_all_agents\n'
    wait_for_telegram_accounts || die "Not all Telegram accounts are connected"
  fi
  printf 'apply=already-compliant\n'
  exit 0
fi

TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
BACKUP_DIR="$BACKUP_BASE/$TARGET_LABEL/$TIMESTAMP"
install -d -m 700 "$BACKUP_DIR"
cp -a "$CONFIG_FILE" "$BACKUP_DIR/openclaw.json"
if [ -f "$APPROVALS_FILE" ]; then
  cp -a "$APPROVALS_FILE" "$BACKUP_DIR/exec-approvals.json"
else
  : > "$BACKUP_DIR/exec-approvals.json.missing"
  chmod 600 "$BACKUP_DIR/exec-approvals.json.missing"
fi
sha256sum "$BACKUP_DIR/openclaw.json" > "$BACKUP_DIR/SHA256SUMS"
if [ -f "$BACKUP_DIR/exec-approvals.json" ]; then
  sha256sum "$BACKUP_DIR/exec-approvals.json" >> "$BACKUP_DIR/SHA256SUMS"
fi
printf 'target=%s\ncreated_utc=%s\nagent_count=%s\ntelegram_account_count=%s\n' \
  "$TARGET_LABEL" \
  "$TIMESTAMP" \
  "$(jq '.agents | length' "$REPORT_FILE")" \
  "$(jq '.accounts | length' "$REPORT_FILE")" \
  > "$BACKUP_DIR/metadata.txt"
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
  if [ -f "$APPROVALS_FILE" ]; then
    chmod --reference="$APPROVALS_FILE" "$APPROVALS_CANDIDATE"
    chown --reference="$APPROVALS_FILE" "$APPROVALS_CANDIDATE"
  else
    chmod 600 "$APPROVALS_CANDIDATE"
    chown --reference="$CONFIG_FILE" "$APPROVALS_CANDIDATE"
  fi
  mv -f -- "$APPROVALS_CANDIDATE" "$APPROVALS_FILE"
  APPROVALS_CANDIDATE=""
else
  rm -f -- "$APPROVALS_CANDIDATE"
  APPROVALS_CANDIDATE=""
fi

if ! validate_config; then
  cp -a "$BACKUP_DIR/openclaw.json" "$CONFIG_FILE"
  if [ -f "$BACKUP_DIR/exec-approvals.json" ]; then
    cp -a "$BACKUP_DIR/exec-approvals.json" "$APPROVALS_FILE"
  else
    rm -f -- "$APPROVALS_FILE"
  fi
  die "Validation failed; files restored from $BACKUP_DIR"
fi

restart_gateway
runtime_approval_check || die "Gateway approval runtime is not full/off for every agent after apply"
printf 'gateway_approval_runtime=full_off_all_agents\n'
wait_for_telegram_accounts || die "Not all Telegram accounts recovered after Gateway restart"
print_safe_summary
printf 'backup_dir=%s\napply=pass\n' "$BACKUP_DIR"
