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
if [[ "$mode" == apply ]]; then
  docker cp "$(dirname "$0")/verify_buffer_hydration.mjs" "$container:/tmp/openclaw-buffer-hydration-verify.mjs"
fi
python3 - "$container" "$file" "$mode" "$backup_root" <<'PY'
import hashlib, pathlib, subprocess, sys
container, file_name, mode, backup_root = sys.argv[1:]
text = subprocess.check_output(["docker", "exec", container, "cat", file_name], text=True)
marker = "Portable Zalo buffer hydration guard v3"
if marker in text:
    print("already patched v3")
    raise SystemExit(0)
new_fn = '''/** Portable Zalo buffer hydration guard v3: stage Zalo media with the native bounded loader. */
async function hydrateSendBufferMediaParams(params) {
\tconst rawBuffer = readToolStringParam(params.args, "buffer", { trim: false });
\tconst mediaHint = readAttachmentMediaHint(params.args);
\tconst fileHint = readAttachmentFileHint(params.args);
\tconst mediaSource = mediaHint ?? fileHint;
\tif (params.channel === "zalouser" && !rawBuffer && mediaSource) {
\t\tif (params.dryRun) return;
\t\tconst maxBytes = resolveAttachmentMaxBytes(params) ?? 5242880;
\t\tconst forceDocument = readBooleanParam(params.args, "forceDocument") ?? readBooleanParam(params.args, "asDocument") ?? false;
\t\tconst media = await loadWebMedia(mediaSource, buildAttachmentMediaLoadOptions({
\t\t\tpolicy: params.mediaPolicy,
\t\t\tmaxBytes,
\t\t\toptimizeImages: forceDocument ? false : void 0
\t\t}));
\t\tconst contentType = readToolStringParam(params.args, "contentType") ?? readToolStringParam(params.args, "mimeType") ?? media.contentType;
\t\tconst filename = readToolStringParam(params.args, "filename") ?? inferAttachmentFilename({
\t\t\tmediaHint: media.fileName ?? mediaSource,
\t\t\tcontentType
\t\t});
\t\tconst staged = await resolveOutboundAttachmentFromBuffer(media.buffer, maxBytes, {
\t\t\tcontentType,
\t\t\tfilename,
\t\t\tassertCommitAllowed: params.assertClientUploadAllowed
\t\t});
\t\tparams.args.buffer = media.buffer.toString("base64");
\t\tparams.args.media = staged.path;
\t\tparams.args.mediaUrl = staged.path;
\t\tparams.args.mediaUrls = [staged.path];
\t\tif (contentType && !readToolStringParam(params.args, "contentType")) params.args.contentType = contentType;
\t\tif (!readToolStringParam(params.args, "filename")) params.args.filename = filename;
\t\treturn;
\t}
\tif (hasExplicitSendMediaSource(params.args, params.extraParamKeys)) {
\t\tdelete params.args.buffer;
\t\treturn;
\t}
\tif (!rawBuffer) return;'''
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
if 'Portable Zalo buffer hydration guard v2' in text:
    start = text.index('/** Portable Zalo buffer hydration guard v2')
    tail = '\tconst normalized = normalizeBase64Payload({\n\t\tbase64: rawBuffer,'
    end = text.index(tail, start)
    text = text[:start] + new_fn + '\n' + text[end:]
elif old_v1 in text:
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
for symbol in ['resolveAttachmentMaxBytes', 'buildAttachmentMediaLoadOptions', 'loadWebMedia', 'resolveOutboundAttachmentFromBuffer']:
    if text.count(symbol) < 2:
        raise SystemExit(f'native hydration dependency missing: {symbol}')
if mode == 'dry-run':
    print('anchors verified; would stage hydrated media and replace local path; no changes')
    raise SystemExit(0)
backup = pathlib.Path(backup_root); backup.mkdir(parents=True, mode=0o700)
orig = backup / pathlib.Path(file_name).name
subprocess.run(["docker", "cp", f"{container}:{file_name}", str(orig)], check=True)
(backup / "SHA256SUMS.before").write_text(hashlib.sha256(subprocess.check_output(["docker", "exec", container, "cat", file_name])).hexdigest()+"  "+orig.name+"\n")
code = '''import pathlib, subprocess, sys, os
p = pathlib.Path(sys.argv[1])
tmp = p.with_name(p.stem + ".zalo-buffer-staged" + p.suffix)
try:
    tmp.write_text(sys.stdin.read())
    tmp.chmod(p.stat().st_mode)
    subprocess.run(["node", "--check", str(tmp)], check=True)
    subprocess.run(["node", "/tmp/openclaw-buffer-hydration-verify.mjs", str(tmp)], check=True)
    os.replace(tmp, p)
finally:
    if tmp.exists():
        tmp.unlink()
'''
subprocess.run(["docker", "exec", "-i", container, "python3", "-c", code, file_name], input=text, text=True, check=True)
print(f'applied backup={backup}')
PY
if [[ "$mode" == apply ]]; then
  docker exec "$container" node --check "$file"
  docker exec "$container" node /tmp/openclaw-buffer-hydration-verify.mjs "$file"
fi
