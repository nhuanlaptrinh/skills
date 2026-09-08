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
f=/usr/lib/node_modules/openclaw/dist/message-action-normalization-B08PXYVX.js
docker inspect -f '{{.State.Running}}' "$container" | grep -qx true || { echo "container is not running" >&2; exit 1; }
docker exec "$container" test -f "$f"
if docker exec "$container" grep -q 'Scoped Zalo group target guard' "$f"; then echo "already patched: $container:$f"; exit 0; fi
echo "target=$container:$f mode=$mode"
if [[ "$mode" == dry-run ]]; then echo "would-backup=/root/_Backups/<member>-zalo-core-group-guard/<timestamp>"; exit 0; fi
member=$(docker inspect -f '{{.Name}}' "$container" | sed 's#^/##; s/^user-//')
stamp=$(date -u +%Y%m%dT%H%M%SZ); b=/root/_Backups/${member}-zalo-core-group-guard/$stamp; mkdir -p "$b"
docker cp "$container:$f" "$b/message-action-normalization-B08PXYVX.js.orig"
python3 - "$container" "$f" <<'PY'
import subprocess,sys
c,f=sys.argv[1:]; s=subprocess.check_output(['docker','exec',c,'cat',f],text=True)
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
subprocess.run(['docker','exec','-i',c,'sh','-lc',f'cat > {f}.tmp && mv {f}.tmp {f}'],input=s,text=True,check=True)
PY
docker exec "$container" node --check "$f"
echo "applied backup=$b"
