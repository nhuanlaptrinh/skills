#!/usr/bin/env bash
set -euo pipefail
container=""; mode=dry-run
while (($#)); do
 case "$1" in
  --container) container=${2:-}; shift 2;;
  --dry-run) mode=dry-run; shift;;
  --apply) mode=apply; shift;;
  -h|--help) echo "Usage: $0 --container CONTAINER [--dry-run|--apply]"; exit 0;;
  *) echo "Unknown argument: $1" >&2; exit 2;;
 esac
done
[[ -n "$container" ]] || { echo "--container is required" >&2; exit 2; }
docker inspect -f '{{.State.Running}}' "$container" | grep -qx true || { echo "container is not running" >&2; exit 1; }
f=$(docker exec "$container" python3 -c 'import pathlib; root=pathlib.Path("/usr/lib/node_modules/openclaw/dist"); files=[p for p in root.glob("message-action-normalization-*") if p.suffix in (".js", ".mjs") and "function normalizeMessageActionInput(params)" in p.read_text()]; assert len(files)==1, "ambiguous or missing normalization bundle"; print(files[0])')
docker exec "$container" test -f "$f"
if docker exec "$container" grep -q 'Scoped Zalo group target guard' "$f"; then echo "already patched: $container:$f"; exit 0; fi
echo "target=$container:$f mode=$mode"
member=$(docker inspect -f '{{.Name}}' "$container" | sed 's#^/##; s/^user-//')
stamp=$(date -u +%Y%m%dT%H%M%SZ); b=/root/_Backups/${member}-zalo-core-group-guard/$stamp
python3 - "$container" "$f" "$mode" "$b" <<'PY'
import subprocess,sys
c,f,mode,b=sys.argv[1:]; s=subprocess.check_output(['docker','exec',c,'cat',f],text=True)
a='''/** Normalizes message-action args before target validation and dispatch. */
function normalizeMessageActionInput(params) {'''
i='''/** Scoped Zalo group target guard: never reinterpret another channel or ID. */
function enforceZalouserGroupTarget(params, inferredChannel, normalizedArgs) {
\tif (params.action !== "send") return;
\tconst provider = normalizeMessageChannel(params.toolContext?.currentChannelProvider) ?? "";
\tif (provider.trim().toLowerCase() !== "zalouser" || inferredChannel.trim().toLowerCase() !== "zalouser") return;
\tif (normalizeChatType(params.toolContext?.currentChatType) !== "group") return;
\tconst rawTarget = normalizeOptionalString(normalizedArgs.target) ?? "";
\tif (!/^\\d+$/.test(rawTarget)) return;
\tconst currentValues = [params.toolContext?.currentMessagingTarget, params.toolContext?.currentChannelId];
\tconst currentIds = currentValues.map((value) => normalizeOptionalString(value) ?? "").map((value) => value.replace(/^zalouser:/i, "").replace(/^(group|user):/i, "").trim()).filter((value) => /^\\d+$/.test(value));
\tif (currentIds.includes(rawTarget)) normalizedArgs.target = `group:${rawTarget}`;
}
/** Normalizes message-action args before target validation and dispatch. */
function normalizeMessageActionInput(params) {'''
if s.count(a)!=1: raise SystemExit('anchor changed')
s=s.replace(a,i,1)
a2='''\tif (!explicitChannel) {
\t\tif (inferredChannel && isDeliverableMessageChannel(inferredChannel)) normalizedArgs.channel = inferredChannel;
\t}
\tapplyTargetToParams({'''
i2='''\tif (!explicitChannel) {
\t\tif (inferredChannel && isDeliverableMessageChannel(inferredChannel)) normalizedArgs.channel = inferredChannel;
\t}
\tenforceZalouserGroupTarget(params, inferredChannel, normalizedArgs);
\tapplyTargetToParams({'''
if s.count(a2)!=1: raise SystemExit('call anchor changed')
s=s.replace(a2,i2,1)
if mode=='dry-run':
 print('anchors verified; would apply scoped group guard; no changes')
 raise SystemExit(0)
import pathlib
backup=pathlib.Path(b);backup.mkdir(parents=True,mode=0o700)
subprocess.run(['docker','cp',c+':'+f,str(backup/(pathlib.Path(f).name+'.orig'))],check=True)
code='import pathlib,subprocess,sys,os; p=pathlib.Path(sys.argv[1]); tmp=p.with_name(p.stem+".upgrade-staged"+p.suffix); tmp.write_text(sys.stdin.read()); tmp.chmod(p.stat().st_mode); subprocess.run(["node","--check",str(tmp)],check=True); os.replace(tmp,p)'
subprocess.run(['docker','exec','-i',c,'python3','-c',code,f],input=s,text=True,check=True)
PY
if [[ "$mode" == apply ]]; then
 docker exec "$container" node --check "$f"
 echo "applied backup=$b"
fi
