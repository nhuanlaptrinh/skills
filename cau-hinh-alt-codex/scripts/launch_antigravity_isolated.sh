#!/usr/bin/env bash
set -euo pipefail

profile_id=""
app=""
profile_root="${ALT_CODEX_PROFILE_ROOT:-${XDG_STATE_HOME:-$HOME/.local/state}/your-product/codex-profiles}"
user_data_dir=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --profile-id) profile_id=${2:-}; shift 2 ;;
    --app) app=${2:-}; shift 2 ;;
    --profile-root) profile_root=${2:-}; shift 2 ;;
    --user-data-dir) user_data_dir=${2:-}; shift 2 ;;
    --) shift; break ;;
    -h|--help)
      echo 'Usage: launch_antigravity_isolated.sh --profile-id ID --app /absolute/path/to/executable [--profile-root DIR] [--user-data-dir DIR] [-- APP_ARGS...]'
      exit 0 ;;
    *) echo "Unknown argument: $1" >&2; exit 2 ;;
  esac
done

if [[ ! "$profile_id" =~ ^[A-Za-z0-9][A-Za-z0-9._-]*$ || "$profile_id" == *..* || "$profile_id" == *. ]]; then
  echo 'Invalid profile ID.' >&2; exit 2
fi
if [[ "$app" != /* || ! -f "$app" || ! -x "$app" ]]; then
  echo 'Pass the absolute path to the Antigravity executable with --app.' >&2; exit 2
fi
if [[ ! -d "$profile_root" ]]; then
  echo 'Profile root does not exist; create the profile first.' >&2; exit 1
fi
profile_root=$(cd -P -- "$profile_root" && pwd)
profile_path="$profile_root/$profile_id"
if [[ ! -d "$profile_path/.codex" || "$(cd -P -- "$profile_path" && pwd)" != "$profile_path" || "$(cd -P -- "$profile_path/.codex" && pwd)" != "$profile_path/.codex" || ! -f "$profile_path/.codex/config.toml" ]]; then
  echo 'Profile config is missing or resolves outside the profile root.' >&2; exit 1
fi
if [[ -n "$user_data_dir" ]]; then
  if [[ "$user_data_dir" != /* ]]; then echo 'User-data directory must be absolute.' >&2; exit 2; fi
  set -- "--user-data-dir=$user_data_dir" "$@"
else
  echo 'Using existing application data; browser sessions are not isolated by CODEX_HOME.' >&2
fi

export CODEX_HOME="$profile_path/.codex"
unset ELECTRON_RUN_AS_NODE
echo "CODEX_HOME: $CODEX_HOME" >&2
exec "$app" "$@"
