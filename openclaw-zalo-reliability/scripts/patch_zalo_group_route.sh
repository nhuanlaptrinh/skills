#!/usr/bin/env bash
set -euo pipefail
member_data_dir=""; mode=dry-run
while (($#)); do
  case "$1" in
    --member-data-dir) member_data_dir=${2:-}; shift 2;;
    --dry-run) mode=dry-run; shift;;
    --apply) mode=apply; shift;;
    -h|--help) echo "Usage: $0 --member-data-dir DIR [--dry-run|--apply]"; exit 0;;
    *) echo "Unknown argument: $1" >&2; exit 2;;
  esac
done
[[ -n "$member_data_dir" && -d "$member_data_dir/.openclaw" ]] || { echo "A member data dir directly containing .openclaw is required" >&2; exit 2; }
export MEMBER_DATA_DIR="$member_data_dir" MODE="$mode"
python3 - <<'PY'
import hashlib, os, pathlib, shutil, time
root=pathlib.Path(os.environ['MEMBER_DATA_DIR']).resolve(); mode=os.environ['MODE']
files=list(root.glob('.openclaw/npm/projects/*/node_modules/@openclaw/zalouser/dist/channel-*.js'))
matches=[]
for p in files:
    t=p.read_text()
    if 'chatType: isGroup ? "group" : "direct"' in t and 'to: `zalouser:${peerId}`' in t:
        matches.append((p,t))
if len(matches)!=1: raise SystemExit(f'Refusing: expected one unpatched group adapter, found {len(matches)}')
p,t=matches[0]
old='from: isGroup ? `zalouser:group:${peerId}` : `zalouser:${peerId}`,\n\t\tto: `zalouser:${peerId}`'
new='from: isGroup ? `zalouser:group:${peerId}` : `zalouser:${peerId}`,\n\t\tto: isGroup ? `zalouser:group:${peerId}` : `zalouser:${peerId}`'
if t.count(old)!=1: raise SystemExit('Refusing: exact group route anchor changed')
print(f'target={p}\nmode={mode}\nwould-change=group to target only')
if mode=='dry-run': raise SystemExit(0)
stamp=time.strftime('%Y%m%dT%H%M%SZ',time.gmtime()); b=pathlib.Path('/root/_Backups')/f'{root.name}-zalo-group-route-fix'/stamp; b.mkdir(parents=True,exist_ok=False)
shutil.copy2(p,b/(p.name+'.orig')); (b/'SHA256SUMS').write_text(f'{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}\n')
p.write_text(t.replace(old,new,1)); print(f'backup={b}\napplied=explicit group target route')
PY
