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
file=$(docker exec -i "$container" python3 - <<'PY'
from pathlib import Path
root=Path('/usr/lib/node_modules/openclaw/dist')
files=[p for p in root.glob('message-action-normalization-*') if p.suffix in ('.mjs','.js') and 'function hydrateSendBufferMediaParams' in p.read_text()]
if len(files)!=1: raise SystemExit(f'expected one normalization bundle, found {len(files)}')
print(files[0])
PY
)
member=$(docker inspect -f '{{.Name}}' "$container" | sed 's#^/##; s/^user-//')
stamp=$(date -u +%Y%m%dT%H%M%SZ)
backup_root="/root/_Backups/${member}-zalo-buffer-hydration/${stamp}"
echo "target=$container:$file mode=$mode"
python3 - "$container" "$file" "$mode" "$backup_root" <<'PY'
import hashlib, pathlib, subprocess, sys
container, file_name, mode, backup_root = sys.argv[1:]
text = subprocess.check_output(["docker", "exec", container, "cat", file_name], text=True)
marker = "Portable Zalo buffer hydration guard v2"
if marker in text:
    print("already patched v2")
    raise SystemExit(0)
new_fn = '''/** Portable Zalo buffer hydration guard v2: stage local media before gateway upload. */
async function hydrateSendBufferMediaParams(params) {
\tconst rawBuffer = readToolStringParam(params.args, "buffer", { trim: false });
\tif (!rawBuffer) {
\t\tconst mediaHint = readAttachmentMediaHint(params.args);
\t\tconst fileHint = readAttachmentFileHint(params.args);
\t\tif (mediaHint || fileHint) {
\t\t\tawait hydrateAttachmentPayload({
\t\t\t\tcfg: params.cfg,
\t\t\t\tchannel: params.channel,
\t\t\t\taccountId: params.accountId,
\t\t\t\targs: params.args,
\t\t\t\tdryRun: params.dryRun,
\t\t\t\tcontentTypeParam: readToolStringParam(params.args, "contentType") ?? readToolStringParam(params.args, "mimeType"),
\t\t\t\tmediaHint,
\t\t\t\tfileHint,
\t\t\t\tmediaPolicy: params.mediaPolicy,
\t\t\t});
\t\t\tconst hydrated = readToolStringParam(params.args, "buffer", { trim: false });
\t\t\tif (hydrated && !params.dryRun) {
\t\t\t\tconst normalized = normalizeBase64Payload({
\t\t\t\t\tbase64: hydrated,
\t\t\t\t\tcontentType: readToolStringParam(params.args, "contentType") ?? readToolStringParam(params.args, "mimeType")
\t\t\t\t});
\t\t\t\tconst maxBytes = resolveSendBufferMaxBytes(params);
\t\t\t\tconst canonicalBase64 = validateBoundedBase64Attachment({ base64: normalized.base64, maxBytes });
\t\t\t\tconst filename = readToolStringParam(params.args, "filename") ?? inferAttachmentFilename({ mediaHint: mediaHint ?? fileHint, contentType: normalized.contentType });
\t\t\t\tconst staged = await resolveOutboundAttachmentFromBuffer(Buffer.from(canonicalBase64, "base64"), maxBytes, {
\t\t\t\t\tcontentType: normalized.contentType,
\t\t\t\t\tfilename
\t\t\t\t});
\t\t\t\tparams.args.media = staged.path;
\t\t\t\tparams.args.mediaUrl = staged.path;
\t\t\t\tparams.args.mediaUrls = [staged.path];
\t\t\t\tif (staged.contentType && !readToolStringParam(params.args, "contentType")) params.args.contentType = staged.contentType;
\t\t\t}
\t\t}
\t\treturn;
\t}
\tif (hasExplicitSendMediaSource(params.args, params.extraParamKeys)) {
\t\tdelete params.args.buffer;
\t\treturn;
\t}'''
old_v1 = '''/** Portable Zalo buffer hydration guard: hydrate a local media path before gateway upload. */
async function hydrateSendBufferMediaParams(params) {
\tconst rawBuffer = readToolStringParam(params.args, "buffer", { trim: false });
\tif (!rawBuffer) {
\t\tconst mediaHint = readAttachmentMediaHint(params.args);
\t\tconst fileHint = readAttachmentFileHint(params.args);
\t\tif (mediaHint || fileHint) {
\t\t\tawait hydrateAttachmentPayload({
\t\t\t\tcfg: params.cfg,
\t\t\t\tchannel: params.channel,
\t\t\t\taccountId: params.accountId,
\t\t\t\targs: params.args,
\t\t\t\tdryRun: params.dryRun,
\t\t\t\tcontentTypeParam: readToolStringParam(params.args, "contentType") ?? readToolStringParam(params.args, "mimeType"),
\t\t\t\tmediaHint,
\t\t\t\tfileHint,
\t\t\t\tmediaPolicy: params.mediaPolicy,
\t\t\t});
\t\t}
\t\treturn;
\t}
\tif (hasExplicitSendMediaSource(params.args, params.extraParamKeys)) {
\t\tdelete params.args.buffer;
\t\treturn;
\t}'''
old_original = '''async function hydrateSendBufferMediaParams(params) {
\tif (hasExplicitSendMediaSource(params.args, params.extraParamKeys)) {
\t\tdelete params.args.buffer;
\t\treturn;
\t}
\tconst rawBuffer = readToolStringParam(params.args, "buffer", { trim: false });
\tif (!rawBuffer) return;'''
if old_v1 in text:
    text = text.replace(old_v1, new_fn, 1)
elif old_original in text:
    text = text.replace(old_original, new_fn, 1)
    old_call = '''\t\textraParamKeys: params.extraParamKeys
\t\t});
\t\treturn;
\t}
\tif (params.action !== "sendAttachment"'''
    new_call = '''\t\textraParamKeys: params.extraParamKeys,
\t\t\tmediaPolicy: params.mediaPolicy
\t\t});
\t\treturn;
\t}
\tif (params.action !== "sendAttachment"'''
    if text.count(old_call) != 1: raise SystemExit(f'send call anchor count: {text.count(old_call)}')
    text = text.replace(old_call, new_call, 1)
else:
    raise SystemExit('hydration function anchor not found')
if mode == 'dry-run':
    print('anchors verified; would stage hydrated media and replace local path; no changes')
    raise SystemExit(0)
backup = pathlib.Path(backup_root); backup.mkdir(parents=True, mode=0o700)
orig = backup / pathlib.Path(file_name).name
subprocess.run(["docker", "cp", f"{container}:{file_name}", str(orig)], check=True)
(backup / "SHA256SUMS.before").write_text(hashlib.sha256(subprocess.check_output(["docker", "exec", container, "cat", file_name])).hexdigest()+"  "+orig.name+"\n")
code = ('import pathlib,subprocess,sys,os; p=pathlib.Path(sys.argv[1]); '
        'tmp=p.with_name(p.stem+".zalo-buffer-staged"+p.suffix); '
        'tmp.write_text(sys.stdin.read()); tmp.chmod(p.stat().st_mode); '
        'subprocess.run(["node","--check",str(tmp)],check=True); os.replace(tmp,p)')
subprocess.run(["docker", "exec", "-i", container, "python3", "-c", code, file_name], input=text, text=True, check=True)
print(f'applied backup={backup}')
PY
if [[ "$mode" == apply ]]; then
  docker exec "$container" node --check "$file"
fi
