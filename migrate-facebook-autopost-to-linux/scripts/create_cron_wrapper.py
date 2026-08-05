#!/usr/bin/env python3
"""Create a cron-safe wrapper for Linux Facebook auto-post projects."""

from __future__ import annotations

import argparse
from pathlib import Path


def shell_quote(value: str) -> str:
    return "'" + value.replace("'", "'\"'\"'") + "'"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument(
        "--script-path",
        default=".agents/skills/fb-auto-poster/scripts/OpenFBV2POST.py",
    )
    parser.add_argument(
        "--output",
        default=".agents/skills/fb-auto-poster/scripts/run_5min_post.sh",
    )
    parser.add_argument("--log-name", default="personal_5min_post.log")
    parser.add_argument("--lock-name", default=None)
    parser.add_argument("--python", default="/usr/bin/python3")
    parser.add_argument("--timezone", default="Asia/Ho_Chi_Minh")
    args = parser.parse_args()

    project_root = Path(args.project_root).expanduser().resolve()
    script_path = Path(args.script_path)
    if not script_path.is_absolute():
        script_path = project_root / script_path
    output = Path(args.output)
    if not output.is_absolute():
        output = project_root / output

    lock_name = args.lock_name or f"{project_root.name}_5min.lock"
    lock_file = f"/tmp/{lock_name}"

    content = f"""#!/usr/bin/env bash
set -uo pipefail

PROJECT_ROOT={shell_quote(str(project_root))}
SCRIPT_PATH={shell_quote(str(script_path))}
LOG_DIR="$PROJECT_ROOT/logs"
LOG_FILE="$LOG_DIR/{args.log_name}"
LOCK_FILE={shell_quote(lock_file)}

mkdir -p "$LOG_DIR"
export TZ={shell_quote(args.timezone)}

{{
  echo "============================================================"
  echo "[$(date '+%Y-%m-%d %H:%M:%S %Z')] Start 5-minute personal post check"
  cd "$PROJECT_ROOT" || exit 1

  /usr/bin/flock -n "$LOCK_FILE" /usr/bin/xvfb-run -a {shell_quote(args.python)} "$SCRIPT_PATH"
  status=$?

  if [ "$status" -eq 1 ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S %Z')] Another run is already active; skipped."
  fi

  echo "[$(date '+%Y-%m-%d %H:%M:%S %Z')] Finished with exit code $status"
  exit "$status"
}} >> "$LOG_FILE" 2>&1
"""

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(content, encoding="utf-8")
    output.chmod(0o755)
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
