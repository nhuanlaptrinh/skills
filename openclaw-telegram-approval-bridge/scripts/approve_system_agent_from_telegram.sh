#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  approve_system_agent_from_telegram.sh \
    --openclaw-root <runtime-openclaw-root> \
    --telegram-id <numeric-id> \
    --approval-id <system-agent:id> \
    [--agent-id <id>] \
    (--check|--apply)
EOF
}

openclaw_root="${OPENCLAW_ROOT:-${HOME}/.openclaw}"
telegram_id=""
approval_id=""
agent_id="main"
action=""

while (($#)); do
  case "$1" in
    --openclaw-root)
      openclaw_root="${2:-}"
      shift 2
      ;;
    --telegram-id)
      telegram_id="${2:-}"
      shift 2
      ;;
    --approval-id)
      approval_id="${2:-}"
      shift 2
      ;;
    --agent-id)
      agent_id="${2:-}"
      shift 2
      ;;
    --check|--apply)
      if [[ -n "$action" ]]; then
        echo "ERROR: choose exactly one action" >&2
        exit 2
      fi
      action="${1#--}"
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "ERROR: unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

config_path="${OPENCLAW_CONFIG_PATH:-${openclaw_root%/}/openclaw.json}"

if [[ ! "$openclaw_root" = /* || ! "$telegram_id" =~ ^[0-9]+$ || -z "$agent_id" ]]; then
  echo "ERROR: invalid OpenClaw root, Telegram ID, or agent ID" >&2
  exit 2
fi
if [[ "$approval_id" != system-agent:* ]]; then
  echo "ERROR: --approval-id must start with system-agent:" >&2
  exit 2
fi
if [[ "$action" != "check" && "$action" != "apply" ]]; then
  echo "ERROR: choose --check or --apply" >&2
  exit 2
fi
if [[ ! -r "$config_path" ]]; then
  echo "ERROR: OpenClaw config is not readable" >&2
  exit 2
fi

owner_entry="telegram:${telegram_id}"
if ! jq -e --arg owner "$owner_entry" '(.commands.ownerAllowFrom // []) | index($owner) != null' "$config_path" >/dev/null; then
  echo "ERROR: Telegram sender is not a configured command owner" >&2
  exit 3
fi

pending_json="$(OPENCLAW_CONFIG_PATH="$config_path" openclaw approvals pending --json)"
match_count="$(jq -r --arg id "$approval_id" '[.approvals[]? | select(.id == $id)] | length' <<<"$pending_json")"
if [[ "$match_count" != "1" ]]; then
  echo "ERROR: approval is not uniquely pending" >&2
  exit 4
fi

record="$(jq -c --arg id "$approval_id" '.approvals[] | select(.id == $id)' <<<"$pending_json")"
kind="$(jq -r '.kind // ""' <<<"$record")"
record_agent_id="$(jq -r '.agentId // ""' <<<"$record")"
session_key="$(jq -r '.sessionKey // ""' <<<"$record")"
summary="$(jq -r '.summary // ""' <<<"$record")"
expires_at_ms="$(jq -r '.expiresAtMs // 0' <<<"$record")"

if [[ "$kind" != "system-agent" || "$record_agent_id" != "$agent_id" ]]; then
  echo "ERROR: approval is not a system-agent proposal for the configured agent" >&2
  exit 5
fi
if ! jq -ne --arg key "$session_key" --arg prefix "agent:${agent_id}:telegram:" --arg suffix "direct:${telegram_id}" '$key | startswith($prefix) and endswith($suffix)' >/dev/null; then
  echo "ERROR: proposal does not belong to this Telegram owner's direct session" >&2
  exit 5
fi
if [[ "$summary" != "OpenClaw change:"* ]]; then
  echo "ERROR: proposal summary is not a persistent OpenClaw change" >&2
  exit 5
fi
if [[ ! "$expires_at_ms" =~ ^[0-9]+$ ]] || ((expires_at_ms <= $(date +%s%3N))); then
  echo "ERROR: proposal has expired" >&2
  exit 5
fi

printf 'status=pending\n'
printf 'kind=system-agent\n'
printf 'agent_id=%s\n' "$agent_id"
printf 'summary_verified=true\n'

if [[ "$action" == "check" ]]; then
  exit 0
fi

result="$(OPENCLAW_CONFIG_PATH="$config_path" openclaw approvals resolve "$approval_id" allow-once --json --reason "Explicit approval from configured Telegram owner")"
if ! jq -e '(.applied == true) or (.alreadyResolved == true and .approval.status == "allowed")' <<<"$result" >/dev/null; then
  echo "ERROR: Gateway did not confirm approval" >&2
  exit 6
fi

remaining_json="$(OPENCLAW_CONFIG_PATH="$config_path" openclaw approvals pending --json)"
if jq -e --arg id "$approval_id" '.approvals[]? | select(.id == $id)' <<<"$remaining_json" >/dev/null; then
  echo "ERROR: approval is still pending after resolution" >&2
  exit 7
fi

OPENCLAW_CONFIG_PATH="$config_path" openclaw config validate >/dev/null
printf 'status=allowed\n'
printf 'decision=allow-once\n'
