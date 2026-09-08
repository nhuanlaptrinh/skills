#!/usr/bin/env bash
set -euo pipefail
usage(){ cat <<'EOF'
Usage: patch_zca_upload_ack_guard.sh --member-data-dir DIR [--dry-run|--apply]
DIR must directly contain the member's .openclaw directory. Dry-run is default.
EOF
}
MEMBER_DATA_DIR=; MODE=dry-run
while (($#)); do
 case "$1" in
  --member-data-dir) MEMBER_DATA_DIR=${2:-}; shift 2;;
  --dry-run) MODE=dry-run; shift;;
  --apply) MODE=apply; shift;;
  -h|--help) usage; exit 0;;
  *) echo "Unknown argument: $1" >&2; usage >&2; exit 2;;
 esac
done
[[ -n "$MEMBER_DATA_DIR" ]] || { echo "--member-data-dir is required" >&2; exit 2; }
[[ -d "$MEMBER_DATA_DIR/.openclaw" ]] || { echo "Not a member data dir (missing .openclaw): $MEMBER_DATA_DIR" >&2; exit 2; }
export MEMBER_DATA_DIR MODE
python3 - <<'PY'
import glob, hashlib, json, os, pathlib, shutil, sys, time
root=pathlib.Path(os.environ['MEMBER_DATA_DIR']).resolve(); mode=os.environ['MODE']
backup_base=pathlib.Path('/root/_Backups')/f'{root.name}-zalo-upload-ack-guard'
matches=[p for p in root.glob('.openclaw/npm/projects/*/node_modules/@openclaw/zalouser/node_modules/zca-js') if (p/'package.json').is_file()]
if len(matches)!=1: raise SystemExit(f'Refusing: expected exactly one active zca-js bundle, found {len(matches)}')
pkg=matches[0]; meta=json.loads((pkg/'package.json').read_text())
if meta.get('version')!='2.1.2': raise SystemExit(f'Refusing: expected zca-js 2.1.2, found {meta.get("version")!r}')
upload=pkg/'dist/apis/uploadAttachment.js'; listen=pkg/'dist/apis/listen.js'; helper_src=pathlib.Path('/root/.agents/skills/openclaw-zalo-reliability/scripts/upload-completion-guard.js'); helper=pkg/'dist/upload-completion-guard.js'
for p in (upload,listen,helper_src):
 if not p.is_file(): raise SystemExit(f'Refusing: missing expected file {p}')
u=upload.read_text(); l=listen.read_text()
if 'upload-completion-guard.js' in u or 'upload-completion-guard.js' in l: raise SystemExit('Refusing: guard marker already present; inspect before rerunning')
anchor='import { apiFactory, getFileExtension, getFileName, getFileSize, getImageMetaData, getMd5LargeFileObject, resolveResponse, } from "../utils.js";'
if u.count(anchor)!=1: raise SystemExit('Refusing: upload import anchor changed')
u=u.replace(anchor,anchor+'\nimport { waitForUploadCompletion } from "../upload-completion-guard.js";',1)
start='                    if (resData && resData.fileId != "-1" && resData.photoId != "-1")\n                        await new Promise((resolve) => {'
si=u.find(start)
if si<0: raise SystemExit('Refusing: upload Promise anchor changed')
ei=u.find('                }));',si)
if ei<0: raise SystemExit('Refusing: upload request closing anchor changed')
replacement='''                    if (resData && resData.fileId != "-1" && resData.photoId != "-1") {
                        if (data.fileType == "video" || data.fileType == "others") {
                            const result = await waitForUploadCompletion(ctx, resData.fileId, async (wsData) => {
                                return Object.assign(Object.assign(Object.assign({ fileType: data.fileType }, resData), wsData), {
                                    totalSize: data.fileData.totalSize,
                                    fileName: data.fileData.fileName,
                                    checksum: (await getMd5LargeFileObject(data.source, data.fileData.totalSize)).data,
                                });
                            });
                            results[atmIndex] = result;
                        }
                        if (data.fileType == "image") {
                            const result = {
                                fileType: "image",
                                width: data.fileData.width,
                                height: data.fileData.height,
                                totalSize: data.fileData.totalSize,
                                hdSize: data.fileData.totalSize,
                                finished: resData.finished,
                                normalUrl: resData.normalUrl,
                                hdUrl: resData.hdUrl,
                                thumbUrl: resData.thumbUrl,
                                chunkId: resData.chunkId,
                                photoId: resData.photoId,
                                clientFileId: resData.clientFileId,
                            };
                            results[atmIndex] = result;
                        }
                    }
'''
u=u[:si]+replacement+u[ei:]
li=l.find('\n')
if li<0: raise SystemExit('Refusing: listener import anchor changed')
l=l[:li+1]+'import { dispatchUploadCompletion } from "../upload-completion-guard.js";\n'+l[li+1:]
old='''                            const uploadCallback = this.ctx.uploadCallbacks.get(String(control.content.fileId));
                            if (uploadCallback)
                                uploadCallback(data);
                            this.ctx.uploadCallbacks.delete(String(control.content.fileId));'''
if l.count(old)!=1: raise SystemExit(f'Refusing: listener callback anchor changed/count={l.count(old)}')
l=l.replace(old,'                            dispatchUploadCompletion(this.ctx, data);',1)
print(f'target={pkg}\nversion={meta["version"]}\nmode={mode}')
if mode=='dry-run':
 print(f'would-copy=dist/upload-completion-guard.js\nwould-edit=dist/apis/uploadAttachment.js,dist/apis/listen.js\nwould-backup={backup_base}/<timestamp>/zca-js-2.1.2'); raise SystemExit(0)
stamp=time.strftime('%Y%m%dT%H%M%SZ',time.gmtime()); backup_root=backup_base/stamp/'zca-js-2.1.2'; backup_root.mkdir(parents=True,exist_ok=False)
for rel in ('package.json','dist/apis/uploadAttachment.js','dist/apis/listen.js','dist/context.js'):
 src=pkg/rel; dst=backup_root/rel; dst.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(src,dst)
(backup_root/'SHA256SUMS').write_text('\n'.join(f'{hashlib.sha256((pkg/r).read_bytes()).hexdigest()}  {r}' for r in ('package.json','dist/apis/uploadAttachment.js','dist/apis/listen.js','dist/context.js'))+'\n')
shutil.copy2(helper_src,helper); upload.write_text(u); listen.write_text(l)
print(f'backup={backup_root}\napplied=guard helper and bounded upload/listener handling')
PY
