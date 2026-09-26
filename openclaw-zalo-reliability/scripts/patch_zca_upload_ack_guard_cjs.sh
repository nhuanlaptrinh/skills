#!/usr/bin/env bash
set -euo pipefail
usage(){ cat <<'USAGE'
Usage: patch_zca_upload_ack_guard_cjs.sh --member-data-dir DIR [--dry-run|--apply]
DIR must directly contain the member's .openclaw directory. Dry-run is default.
Use this for zca-js 2.1.2 CommonJS bundles loaded through package exports.require.
USAGE
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
import hashlib, json, os, pathlib, shutil, time
root=pathlib.Path(os.environ['MEMBER_DATA_DIR']).resolve(); mode=os.environ['MODE']
backup_base=pathlib.Path('/root/_Backups')/f'{root.name}-zalo-upload-ack-guard-cjs'
matches=[p for p in root.glob('.openclaw/npm/projects/*/node_modules/@openclaw/zalouser/node_modules/zca-js') if (p/'package.json').is_file()]
if len(matches)!=1: raise SystemExit(f'Refusing: expected exactly one active zca-js bundle, found {len(matches)}')
pkg=matches[0]; meta=json.loads((pkg/'package.json').read_text())
if meta.get('version')!='2.1.2': raise SystemExit(f'Refusing: expected zca-js 2.1.2, found {meta.get("version")!r}')
upload=pkg/'dist/cjs/apis/uploadAttachment.cjs'; listen=pkg/'dist/cjs/apis/listen.cjs'; helper_src=pathlib.Path('/root/.agents/skills/openclaw-zalo-reliability/scripts/upload-completion-guard.cjs'); helper=pkg/'dist/cjs/upload-completion-guard.cjs'
for p in (upload,listen,helper_src):
    if not p.is_file(): raise SystemExit(f'Refusing: missing expected file {p}')
u=upload.read_text(); l=listen.read_text()
if 'upload-completion-guard.cjs' in u or 'upload-completion-guard.cjs' in l:
    print(f'target={pkg}\nversion={meta["version"]}\nmode={mode}\nstatus=guard marker already present; no changes')
    raise SystemExit(0)
req="var utils = require('../utils.cjs');"
if u.count(req)!=1: raise SystemExit('Refusing: upload require anchor changed')
u=u.replace(req,req+"\nvar uploadCompletionGuard = require('../upload-completion-guard.cjs');",1)
old='''                    if (resData && resData.fileId != "-1" && resData.photoId != "-1")
                        await new Promise((resolve) => {
                            if (data.fileType == "video" || data.fileType == "others") {
                                const uploadCallback = async (wsData) => {
                                    const result = Object.assign(Object.assign(Object.assign({ fileType: data.fileType }, resData), wsData), { totalSize: data.fileData.totalSize, fileName: data.fileData.fileName, checksum: (await utils.getMd5LargeFileObject(data.source, data.fileData.totalSize)).data });
                                    results[atmIndex] = result;
                                    resolve();
                                };
                                ctx.uploadCallbacks.set(resData.fileId.toString(), uploadCallback);
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
                                resolve();
                            }
                        });'''
new='''                    if (resData && resData.fileId != "-1" && resData.photoId != "-1") {
                        if (data.fileType == "video" || data.fileType == "others") {
                            const result = await uploadCompletionGuard.waitForUploadCompletion(ctx, resData.fileId, async (wsData) => {
                                return Object.assign(Object.assign(Object.assign({ fileType: data.fileType }, resData), wsData), {
                                    totalSize: data.fileData.totalSize,
                                    fileName: data.fileData.fileName,
                                    checksum: (await utils.getMd5LargeFileObject(data.source, data.fileData.totalSize)).data,
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
                    }'''
if u.count(old)!=1: raise SystemExit(f'Refusing: upload callback block changed/count={u.count(old)}')
u=u.replace(old,new,1)
req="var Typing = require('../models/Typing.cjs');"
if l.count(req)!=1: raise SystemExit('Refusing: listener require anchor changed')
l=l.replace(req,req+"\nvar uploadCompletionGuard = require('../upload-completion-guard.cjs');",1)
old='''                            const uploadCallback = this.ctx.uploadCallbacks.get(String(control.content.fileId));
                            if (uploadCallback)
                                uploadCallback(data);
                            this.ctx.uploadCallbacks.delete(String(control.content.fileId));'''
if l.count(old)!=1: raise SystemExit(f'Refusing: listener callback block changed/count={l.count(old)}')
l=l.replace(old,'                            uploadCompletionGuard.dispatchUploadCompletion(this.ctx, data);',1)
print(f'target={pkg}\nversion={meta["version"]}\nmode={mode}\nstatus=would apply CommonJS bounded upload guard')
if mode=='dry-run':
    print(f'would-copy=dist/cjs/upload-completion-guard.cjs\nwould-edit=dist/cjs/apis/uploadAttachment.cjs,dist/cjs/apis/listen.cjs\nwould-backup={backup_base}/<timestamp>/zca-js-2.1.2')
    raise SystemExit(0)
stamp=time.strftime('%Y%m%dT%H%M%SZ',time.gmtime()); backup_root=backup_base/stamp/'zca-js-2.1.2'; backup_root.mkdir(parents=True,exist_ok=False)
rels=('package.json','dist/cjs/apis/uploadAttachment.cjs','dist/cjs/apis/listen.cjs')
for rel in rels:
    src=pkg/rel; dst=backup_root/rel; dst.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(src,dst)
(backup_root/'SHA256SUMS').write_text('\n'.join(f'{hashlib.sha256((pkg/r).read_bytes()).hexdigest()}  {r}' for r in rels)+'\n')
shutil.copy2(helper_src,helper); upload.write_text(u); listen.write_text(l)
print(f'backup={backup_root}\napplied=CommonJS guard helper and bounded upload/listener handling')
PY
