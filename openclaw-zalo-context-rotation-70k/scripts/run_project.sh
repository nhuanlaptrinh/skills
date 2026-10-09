#!/usr/bin/env bash
set -euo pipefail
exec python3 - "$(cd -- "$(dirname -- "$0")" && pwd)" "${1:?project key required}" <<'PY'
import fcntl
import json
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone

center, key = sys.argv[1:]
entry = json.loads((Path(center) / 'project_config.json').read_text())[key]
log = Path(entry['log_file'])
lock = Path(entry['lock_file'])
log.parent.mkdir(parents=True, exist_ok=True)
lock.parent.mkdir(parents=True, exist_ok=True)
with lock.open('a') as handle, log.open('a') as output:
    try:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        raise SystemExit(0)
    print(datetime.now(timezone.utc).isoformat(), 'start', key, file=output, flush=True)
    result = subprocess.run(['/bin/bash', '-lc', entry['run_command']], cwd=entry['project_root'], stdout=output, stderr=output)
    print(datetime.now(timezone.utc).isoformat(), 'finish', key, 'status', result.returncode, file=output, flush=True)
    raise SystemExit(result.returncode)
PY
