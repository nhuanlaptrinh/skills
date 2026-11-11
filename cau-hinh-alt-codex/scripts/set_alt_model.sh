#!/usr/bin/env bash
set -euo pipefail

MODEL=""
CODEX_CONFIG="${CODEX_HOME:-$HOME/.codex}/config.toml"
ACTIVE_OPENCLAW_CONFIG="${OPENCLAW_CONFIG_PATH:-$HOME/.openclaw/openclaw.json}"
OPENCLAW_CONFIG="$ACTIVE_OPENCLAW_CONFIG"
OPENCLAW_PROVIDER=""
BACKUP_DIR="${ALT_CODEX_BACKUP_DIR:-${XDG_STATE_HOME:-$HOME/.local/state}/cau-hinh-alt-codex/backups}"
DRY_RUN=0
ALL_AGENTS=0
UPDATE_CODEX=1
UPDATE_OPENCLAW=1
RESTART_GATEWAY=0

usage() {
  cat <<EOF
Usage: set_alt_model.sh --model MODEL [options]

MODEL must be the exact model ID supplied by the user or provider.

Options:
  --all-agents              Update agent overrides matching the previous default
  --codex-only              Update only Codex config
  --openclaw-only           Update only OpenClaw config
  --codex-config PATH       Override Codex config path
  --openclaw-config PATH    Override OpenClaw config path
  --openclaw-provider ID    Override detected OpenClaw provider id
  --backup-dir PATH         Override backup directory
  --restart-gateway         Restart the active OpenClaw gateway after change
  --no-restart-gateway      Do not restart the gateway (default)
  --dry-run                 Show planned changes without writing
  -h, --help                Show this help
EOF
}

normalize_model() {
  local requested normalized
  requested=$(printf '%s' "$1" | sed -E 's/^[[:space:]]+//; s/[[:space:]]+$//')
  case "$requested" in
    gpt-5.4|GPT-5.4) printf '%s' 'gpt-5.4'; return ;;
    gpt-5.5|GPT-5.5) printf '%s' 'gpt-5.5'; return ;;
    GPT-5.6|gpt-5.6) printf '%s' 'GPT-5.6'; return ;;
  esac

  normalized=$(printf '%s' "$requested" | tr '[:upper:]_' '[:lower:] ' | sed -E 's/[[:space:]]+/-/g; s/-+/-/g; s/^-|-$//g')
  case "$normalized" in
    gpt-5.6-sol) printf '%s' 'GPT-5.6-sol' ;;
    gpt-5.6-terra) printf '%s' 'GPT-5.6-terra' ;;
    gpt-5.6-luna) printf '%s' 'GPT-5.6-luna' ;;
    *) [[ "$requested" =~ ^[A-Za-z0-9][A-Za-z0-9._-]*$ ]] && printf '%s' "$requested" || return 1 ;;
  esac
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --model) MODEL=${2:-}; shift 2 ;;
    --all-agents) ALL_AGENTS=1; shift ;;
    --codex-only) UPDATE_OPENCLAW=0; shift ;;
    --openclaw-only) UPDATE_CODEX=0; shift ;;
    --codex-config) CODEX_CONFIG=${2:-}; shift 2 ;;
    --openclaw-config) OPENCLAW_CONFIG=${2:-}; shift 2 ;;
    --openclaw-provider) OPENCLAW_PROVIDER=${2:-}; shift 2 ;;
    --backup-dir) BACKUP_DIR=${2:-}; shift 2 ;;
    --restart-gateway) RESTART_GATEWAY=1; shift ;;
    --no-restart-gateway) RESTART_GATEWAY=0; shift ;;
    --dry-run) DRY_RUN=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
done

if [[ -z "$MODEL" ]]; then
  echo "Missing --model" >&2
  usage >&2
  exit 2
fi

if ! MODEL=$(normalize_model "$MODEL"); then
  echo "Invalid model ID. Use letters, numbers, dots, underscores or hyphens." >&2
  exit 2
fi

if [[ $UPDATE_CODEX -eq 0 && $UPDATE_OPENCLAW -eq 0 ]]; then
  echo "Nothing to update." >&2
  exit 2
fi

STAMP=$(date -u +%Y%m%dT%H%M%SZ)

detect_openclaw_provider() {
  local primary provider candidates count provider_count

  if [[ -n "$OPENCLAW_PROVIDER" ]]; then
    if ! jq -e --arg provider "$OPENCLAW_PROVIDER" '.models.providers[$provider] != null' "$OPENCLAW_CONFIG" >/dev/null; then
      echo "OpenClaw provider not found: $OPENCLAW_PROVIDER" >&2
      return 1
    fi
    return 0
  fi

  primary=$(jq -r '.agents.defaults.model.primary // empty' "$OPENCLAW_CONFIG")
  if [[ "$primary" == */* ]]; then
    provider=${primary%%/*}
    if jq -e --arg provider "$provider" '.models.providers[$provider] != null' "$OPENCLAW_CONFIG" >/dev/null; then
      OPENCLAW_PROVIDER="$provider"
      return 0
    fi
  fi

  candidates=$(jq -r --arg model "$MODEL" '
    .models.providers // {}
    | to_entries[]
    | select(any(.value.models[]?;
        .id == "codex" or .id == $model))
    | .key
  ' "$OPENCLAW_CONFIG")
  count=$(printf '%s\n' "$candidates" | sed '/^$/d' | wc -l)
  if [[ "$count" -eq 1 ]]; then
    OPENCLAW_PROVIDER=$(printf '%s\n' "$candidates" | sed '/^$/d')
    return 0
  fi

  provider_count=$(jq -r '(.models.providers // {}) | keys | length' "$OPENCLAW_CONFIG")
  if [[ "$provider_count" -eq 1 ]]; then
    OPENCLAW_PROVIDER=$(jq -r '(.models.providers // {}) | keys[0]' "$OPENCLAW_CONFIG")
    return 0
  fi

  echo "Cannot detect a unique OpenClaw provider. Use --openclaw-provider ID." >&2
  return 1
}

if [[ $UPDATE_OPENCLAW -eq 1 ]]; then
  command -v jq >/dev/null || { echo "jq is required" >&2; exit 1; }
  [[ -f "$OPENCLAW_CONFIG" ]] || { echo "OpenClaw config not found: $OPENCLAW_CONFIG" >&2; exit 1; }
  detect_openclaw_provider
  OPENCLAW_MODEL="$OPENCLAW_PROVIDER/$MODEL"
  if ! jq -e --arg provider "$OPENCLAW_PROVIDER" --arg model "$MODEL" 'any(.models.providers[$provider].models[]?; .id == $model)' "$OPENCLAW_CONFIG" >/dev/null; then
    echo "Model $MODEL is not registered for OpenClaw provider $OPENCLAW_PROVIDER; configure its metadata first." >&2
    exit 1
  fi
fi

echo "Selected model: $MODEL"
echo "Backup directory: $BACKUP_DIR"
[[ $UPDATE_CODEX -eq 1 ]] && echo "Codex config: $CODEX_CONFIG"
if [[ $UPDATE_OPENCLAW -eq 1 ]]; then
  echo "OpenClaw config: $OPENCLAW_CONFIG"
  echo "OpenClaw provider: $OPENCLAW_PROVIDER"
  echo "OpenClaw model ref: $OPENCLAW_MODEL"
  if [[ $RESTART_GATEWAY -eq 1 ]]; then
    echo "Gateway restart: enabled after config update"
  else
    echo "Gateway restart: disabled by request"
  fi
fi
[[ $ALL_AGENTS -eq 1 ]] && echo "Agent overrides: only those matching the previous default will be updated"

if [[ $DRY_RUN -eq 1 ]]; then
  echo "Dry-run: no files changed."
  exit 0
fi

mkdir -p "$BACKUP_DIR"

if [[ $UPDATE_CODEX -eq 1 ]]; then
  [[ -f "$CODEX_CONFIG" ]] || { echo "Codex config not found: $CODEX_CONFIG" >&2; exit 1; }
  CODEX_BACKUP="$BACKUP_DIR/codex-config.toml.$STAMP"
  cp -p "$CODEX_CONFIG" "$CODEX_BACKUP"
  CODEX_TEMP=$(mktemp "${CODEX_CONFIG}.tmp.XXXXXX")
  trap 'rm -f "${CODEX_TEMP:-}"' EXIT
  cp -p "$CODEX_CONFIG" "$CODEX_TEMP"
  MODEL_VALUE="$MODEL" perl -0pi -e 'my $pos = /^[ \t]*\[/m ? $-[0] : length($_); my $top = substr($_, 0, $pos); $top =~ s/^model[ \t]*=[ \t]*"[^"]*"/model = "$ENV{MODEL_VALUE}"/m or die "Top-level model key not found\n"; substr($_, 0, $pos, $top)' "$CODEX_TEMP"
  mv "$CODEX_TEMP" "$CODEX_CONFIG"
  trap - EXIT
fi

if [[ $UPDATE_OPENCLAW -eq 1 ]]; then
  OPENCLAW_BACKUP="$BACKUP_DIR/openclaw.json.$STAMP"
  cp -p "$OPENCLAW_CONFIG" "$OPENCLAW_BACKUP"
  TEMP_FILE=$(mktemp "${OPENCLAW_CONFIG}.tmp.XXXXXX")
  trap 'rm -f "${TEMP_FILE:-}"' EXIT
  cp -p "$OPENCLAW_CONFIG" "$TEMP_FILE"

  jq --arg ref "$OPENCLAW_MODEL" --argjson allAgents "$ALL_AGENTS" '
    (.agents.defaults.model.primary // "") as $previous
    | .agents.defaults.model.primary = $ref
    | .agents.defaults.models = ((.agents.defaults.models // {}) + {($ref): {}})
    | if $allAgents == 1 then
        .agents.list = ((.agents.list // []) | map(
          if $previous == "" then .
          elif (.model? | type) == "string" then
            if .model == $previous then .model = $ref else . end
          elif (.model? | type) == "object" then
            if .model.primary == $previous then .model.primary = $ref else . end
          else . end
        ))
      else . end
  ' "$OPENCLAW_CONFIG" > "$TEMP_FILE"

  jq -e . "$TEMP_FILE" >/dev/null
  mv "$TEMP_FILE" "$OPENCLAW_CONFIG"
  trap - EXIT

  if [[ "$OPENCLAW_CONFIG" == "$ACTIVE_OPENCLAW_CONFIG" ]] && command -v openclaw >/dev/null; then
    if ! openclaw config validate >/dev/null; then
      cp -p "$OPENCLAW_BACKUP" "$OPENCLAW_CONFIG"
      echo "OpenClaw validation failed; restored backup." >&2
      exit 1
    fi
    if [[ $RESTART_GATEWAY -eq 1 ]]; then
      if ! openclaw gateway restart >/dev/null 2>&1; then
        echo "OpenClaw config updated, but gateway restart failed. Run: openclaw gateway restart" >&2
        exit 1
      fi
      if ! openclaw gateway status >/dev/null 2>&1; then
        echo "Gateway restart command completed, but status check failed." >&2
        exit 1
      fi
      echo "OpenClaw gateway restarted and status checked."
    fi
  elif [[ $RESTART_GATEWAY -eq 1 ]]; then
    echo "Skipped gateway restart: custom OpenClaw config path is not the active default." >&2
  fi
fi

echo "Updated model to $MODEL."
[[ $UPDATE_CODEX -eq 1 ]] && echo "Codex backup: $CODEX_BACKUP"
[[ $UPDATE_OPENCLAW -eq 1 ]] && echo "OpenClaw backup: $OPENCLAW_BACKUP"
exit 0
