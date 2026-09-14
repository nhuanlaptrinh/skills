#!/usr/bin/env python3
"""Bounded, single-invocation workbook coordinator.
Reads only requested workbook metadata/columns and emits one compact JSON record."""
from __future__ import annotations
import argparse, hashlib, json, os, re, sys, time, zipfile
from email.message import Message
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.parse import unquote, urljoin, urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

MAX_OUT=2000; MAX_INPUTS=2; MAX_SHEETS=32; MAX_SCAN=50000; MAX_DETAIL=500
FORBIDDEN_PARTS={'.env','credential','secret','token','cookie','.openclaw/scripts','/scripts/'}
REMOTE_MAX_BYTES = 20 * 1024 * 1024
REMOTE_TIMEOUT_SECONDS = 20
REMOTE_MAX_REDIRECTS = 3
# Zalo file links start at dlfl.vn, then may redirect through Zalo's flchat.vn
# delivery host and its exact dlmd.me CDN host. Keep patterns exact; do not
# allow a suffix or arbitrary URL supplied in a group message.
REMOTE_HOST_RE = re.compile(
    r"^(?:file-stal-[0-9]+\.(?:dlfl|flchat)\.vn|file-stal-[0-9]+-aka-jpt\.dlmd\.me)$",
    re.I,
)
REMOTE_URL_RE = re.compile(r"https://file-stal-[0-9]+\.(?:dlfl|flchat)\.vn/[^\s<>\"']+", re.I)
REMOTE_MIMES = {
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-excel.sheet.macroenabled.12",
    "text/csv",
    "application/csv",
    "application/octet-stream",
}
REMOTE_EXTENSIONS = {".xlsx", ".xlsm", ".csv"}

def compact(v):
    if hasattr(v,'item'):
        try:v=v.item()
        except Exception:pass
    if v is None: return None
    try:
        import pandas as pd
        if pd.isna(v): return None
    except Exception: pass
    if isinstance(v,(str,int,float,bool)): return v
    return str(v)

def emit(obj, code=0):
    obj=dict(obj); obj.setdefault('ok',code==0)
    s=json.dumps(obj,ensure_ascii=False,separators=(',',':'),default=str)
    if len(s.encode())>MAX_OUT:
        keep={k:obj[k] for k in ('ok','task_id','action','status','message','error','artifact','customer','rows','rates_verified','needs') if k in obj}
        keep['output_truncated']=True
        s=json.dumps(keep,ensure_ascii=False,separators=(',',':'),default=str)
    if len(s.encode())>MAX_OUT: s='{"ok":false,"error":"summary_output_limit"}'; code=1
    print(s); return code

def fail(err, **kw): return emit({'error':err,**kw},1)

class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def remote_url_from_input(raw):
    if not isinstance(raw, str):
        return None
    match = REMOTE_URL_RE.search(raw.strip())
    if not match:
        return None
    return match.group(0).rstrip(").,;\"'")


def validate_remote_url(url):
    parsed = urlparse(url)
    if parsed.scheme.lower() != "https" or parsed.username or parsed.password or parsed.port:
        raise ValueError("remote_url_not_allowed")
    if not REMOTE_HOST_RE.fullmatch((parsed.hostname or "").lower()):
        raise ValueError("remote_host_not_allowed")
    if not parsed.path.startswith("/gr/"):
        raise ValueError("remote_path_not_allowed")


def safe_remote_filename(raw, headers, content_type):
    hint = ""
    if isinstance(raw, str):
        prefix = raw[: raw.find("https://") if "https://" in raw else 0]
        hint = Path(prefix.strip().splitlines()[-1].strip()).name if prefix.strip() else ""
    name = ""
    disposition = headers.get("Content-Disposition", "")
    if disposition:
        message = Message()
        message["content-disposition"] = disposition
        name = message.get_param("filename", header="content-disposition") or ""
        if not name:
            encoded = message.get_param("filename*", header="content-disposition") or ""
            name = encoded.split("''", 1)[-1]
        name = unquote(str(name))
    candidate = Path(name or hint).name
    if not candidate or candidate in {".", ".."}:
        candidate = "zalo_download"
    candidate = re.sub(r"[\x00-\x1f\x7f]+", "_", candidate)
    candidate = re.sub(r"[^A-Za-z0-9._ -]", "_", candidate).strip(" .")[:180]
    ext = Path(candidate).suffix.lower()
    if ext not in REMOTE_EXTENSIONS:
        hint_ext = Path(hint).suffix.lower()
        mime_ext = {
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
            "application/vnd.ms-excel.sheet.macroenabled.12": ".xlsm",
            "text/csv": ".csv",
            "application/csv": ".csv",
        }.get(content_type.lower(), "")
        ext = hint_ext if hint_ext in REMOTE_EXTENSIONS else mime_ext
        if not ext:
            raise ValueError("remote_extension_not_allowed")
        candidate = f"{candidate}{ext}"
    return candidate


def download_remote_input(workspace, raw):
    url = remote_url_from_input(raw)
    if not url:
        raise ValueError("remote_url_invalid")
    validate_remote_url(url)
    cache_key = hashlib.sha256(url.encode("utf-8")).hexdigest()[:24]
    cache_dir = workspace / "incoming" / "zalo"
    cache_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(cache_dir, 0o700)
    opener = build_opener(_NoRedirect())
    current = url
    response = None
    try:
        for _ in range(REMOTE_MAX_REDIRECTS + 1):
            validate_remote_url(current)
            request = Request(current, headers={"User-Agent": "OpenClaw-file-task/1"})
            try:
                response = opener.open(request, timeout=REMOTE_TIMEOUT_SECONDS)
            except HTTPError as error:
                if error.code not in {301, 302, 303, 307, 308}:
                    raise ValueError(f"remote_http_{error.code}") from error
                location = error.headers.get("Location")
                error.close()
                if not location:
                    raise ValueError("remote_redirect_missing_location")
                current = urljoin(current, location)
                continue
            status = getattr(response, "status", response.getcode())
            if status != 200:
                raise ValueError(f"remote_http_{status}")
            break
        else:
            raise ValueError("remote_redirect_limit")
        content_type = (response.headers.get_content_type() or "").lower()
        if content_type not in REMOTE_MIMES:
            raise ValueError("remote_mime_not_allowed")
        content_length = response.headers.get("Content-Length")
        if content_length:
            try:
                declared_bytes = int(content_length)
            except ValueError as error:
                raise ValueError("remote_content_length_invalid") from error
            if declared_bytes < 0 or declared_bytes > REMOTE_MAX_BYTES:
                raise ValueError("remote_file_too_large")
        filename = safe_remote_filename(raw, response.headers, content_type)
        target_dir = cache_dir / cache_key
        target_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(target_dir, 0o700)
        target = target_dir / filename
        if target.is_file() and target.stat().st_size <= REMOTE_MAX_BYTES:
            if target.suffix.lower() not in {".xlsx", ".xlsm"} or zipfile.is_zipfile(target):
                return target
            target.unlink()
        partial = target_dir / ".download.part"
        try:
            total = 0
            with partial.open("wb") as output:
                os.chmod(partial, 0o600)
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > REMOTE_MAX_BYTES:
                        raise ValueError("remote_file_too_large")
                    output.write(chunk)
            if total == 0:
                raise ValueError("remote_file_empty")
            if target.suffix.lower() in {".xlsx", ".xlsm"} and not zipfile.is_zipfile(partial):
                raise ValueError("remote_excel_invalid_zip")
            os.replace(partial, target)
        except Exception:
            partial.unlink(missing_ok=True)
            raise
        return target
    finally:
        if response is not None:
            response.close()


def root_path(workspace, raw):
    remote = remote_url_from_input(raw)
    if remote:
        return download_remote_input(workspace, raw)
    if not isinstance(raw,str) or not raw.strip(): raise ValueError('input_path_required')
    p=Path(raw).expanduser()
    if not p.is_absolute(): p=workspace/p
    p=p.resolve(); wr=workspace.resolve()
    allowed=p.is_relative_to(wr) or p.is_relative_to(wr.parent/'.openclaw'/'media')
    low=str(p).lower()
    if not allowed: raise ValueError('input_outside_workspace')
    if any(x in low for x in FORBIDDEN_PARTS): raise ValueError('forbidden_input_path')
    if not p.is_file(): raise ValueError('input_not_found')
    if p.suffix.lower() not in {'.xlsx','.xlsm','.csv'}: raise ValueError('unsupported_file_type')
    return p

def sha256(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()

def header_info(pd,p,sheet=None):
    if p.suffix.lower()=='.csv':
        raw=pd.read_csv(p,header=None,nrows=15,encoding='utf-8-sig',dtype=object); names=['CSV']; chosen=0
    else:
        with pd.ExcelFile(p) as book:
            names=list(book.sheet_names[:MAX_SHEETS]);
            if sheet is None: return {'sheets':names,'sheet_count':len(book.sheet_names)}
            if sheet not in book.sheet_names: raise ValueError('sheet_not_found')
            raw=pd.read_excel(book,sheet_name=sheet,header=None,nrows=15,dtype=object)
        chosen=choose_header(raw)
    vals=[]
    for x in list(raw.iloc[chosen].tolist()):
        s=str(x).strip() if x is not None else ''
        vals.append(s if s and s.lower()!='nan' else '')
    # keep useful non-empty headers and disambiguate duplicates
    out=[]; seen={}
    for i,x in enumerate(vals):
        if not x: continue
        seen[x]=seen.get(x,0)+1; out.append(x if seen[x]==1 else f'{x}_{seen[x]}')
    return {'sheet':sheet or 'CSV','header_row':chosen,'headers':out[:80]}

def choose_header(raw):
    best=(0,-1)
    keywords=('mã','ma','date','ngày','ngay','customer','khách','khach','cước','cuoc','so','do')
    for i,row in raw.iterrows():
        vals=[str(x).strip().lower() for x in row.tolist() if str(x).strip().lower() not in ('nan','none','')]
        score=len(vals)+sum(2 for x in vals if any(k in x for k in keywords))
        if score>best[1]: best=(i,score)
    return int(best[0])

def sheets_for(pd,p,requested):
    if p.suffix.lower()=='.csv': return [None]
    with pd.ExcelFile(p) as b: alln=list(b.sheet_names)
    if requested:
        q=requested if isinstance(requested,list) else [requested]
        return [x for x in q if x in alln][:MAX_SHEETS]
    return alln[:MAX_SHEETS]

def read_frame(pd,p,sheet=None,max_rows=MAX_SCAN, columns=None):
    hi=header_info(pd,p,sheet); hdr=hi['header_row']
    kwargs={'header':hdr,'nrows':max_rows,'dtype':object}
    if columns: kwargs['usecols']=columns
    if p.suffix.lower()=='.csv': kwargs['encoding']='utf-8-sig'; df=pd.read_csv(p,**kwargs)
    else: df=pd.read_excel(p,sheet_name=sheet,**kwargs)
    df.columns=[str(x).strip() for x in df.columns]; return df,hi

def find_col(cols, aliases):
    low={str(c).strip().lower():c for c in cols}
    for a in aliases:
        if a.lower() in low:return low[a.lower()]
    for c in cols:
        cl=str(c).lower()
        if any(a.lower() in cl for a in aliases): return c
    return None

def safe_num(pd,v):
    if v is None:return None
    s=str(v).replace(',','').replace('.','') if False else str(v)
    s=s.replace('đ','').replace('Đ','').replace('%','').strip()
    # Vietnamese thousands separators; preserve decimal when one separator
    if re.fullmatch(r'[0-9.]+',s) and s.count('.')>1:s=s.replace('.','')
    elif re.fullmatch(r'[0-9]+\.[0-9]{3}',s):s=s.replace('.','')
    s=s.replace(',','.')
    try:return float(s)
    except:return None

def task_id(req,paths):
    if req.get('task_id'): return re.sub(r'[^A-Za-z0-9_.-]','-',str(req['task_id']))[:80]
    x='|'.join(f'{p}:{p.stat().st_size}:{p.stat().st_mtime_ns}' for p in paths)+json.dumps(req,sort_keys=True,ensure_ascii=False)
    return 'ft-'+hashlib.sha256(x.encode()).hexdigest()[:16]

def main(req, workspace):
    import pandas as pd
    action=req.get('action','inspect')
    if action=='status':
        raw_tid=req.get('task_id') or req.get('taskId')
        if not isinstance(raw_tid,str) or not raw_tid.strip(): raise ValueError('task_id_required')
        tid=re.sub(r'[^A-Za-z0-9_.-]','-',raw_tid)[:80]
        outdir=(workspace/'output'/'file-tasks'/tid)
        p=outdir/'summary.json'
        return {'ok':p.exists(),'task_id':tid,'status':'complete' if p.exists() else 'not_found','artifact':str(p.relative_to(workspace)) if p.exists() else None}
    rawins=req.get('inputs',[])
    if not isinstance(rawins,list) or not 1<=len(rawins)<=MAX_INPUTS: raise ValueError('inputs_must_contain_1_or_2_files')
    paths=[root_path(workspace,x) for x in rawins]
    tid=task_id(req,paths); outdir=(workspace/'output'/'file-tasks'/tid); outdir.mkdir(parents=True,exist_ok=True)
    if action=='discover':
        rows=[]
        for p in paths:
            if p.suffix.lower()=='.csv': ss=['CSV']; count=1
            else:
                with pd.ExcelFile(p) as b: ss=list(b.sheet_names[:MAX_SHEETS]); count=len(b.sheet_names)
            rows.append({'file':p.name,'bytes':p.stat().st_size,'sheets':ss,'sheet_count':count,'fingerprint':sha256(p)[:16]})
        result={'ok':True,'task_id':tid,'action':'discover','files':rows}
    elif action=='inspect':
        files=[]
        requested=req.get('sheets')
        for p in paths:
            fs=[]
            for s in sheets_for(pd,p,requested): fs.append(header_info(pd,p,s))
            files.append({'file':p.name,'sheets':fs,'fingerprint':sha256(p)[:16]})
        result={'ok':True,'task_id':tid,'action':'inspect','files':files}
    elif action=='process':
        result=process(pd,paths,req,tid,outdir)
    else: raise ValueError('unknown_action')
    # persist compact summary and optional detail
    result['artifact']=str((outdir/'summary.json').relative_to(workspace))
    (outdir/'summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2,default=str)+'\n',encoding='utf-8')
    return result

def process(pd,paths,req,tid,outdir):
    customer=str(req.get('customer','')).strip()
    if not customer:return {'ok':False,'task_id':tid,'action':'process','status':'needs_input','needs':['customer'],'message':'Cần mã hoặc tên khách hàng cụ thể; chưa tính cước.'}
    tracking=None; so=None
    for p in paths:
        for s in sheets_for(pd,p,req.get('sheets')):
            hi=header_info(pd,p,s); hs=hi['headers']; low=' '.join(hs).lower()
            if ('mã theo dõi' in low or 'ma theo doi' in low) and ('cước/xe' in low or 'cuoc/xe' in low or 'tổng cước' in low): tracking=(p,s,hi)
            if ('cus. code' in low or 'cus code' in low or 'mã khách hàng' in low) and ('cus. name' in low or 'tên khách hàng' in low): so=(p,s,hi)
    if tracking is None:
        return {'ok':False,'task_id':tid,'action':'process','status':'needs_input','needs':['tracking_workbook'],'message':'Không tìm thấy sheet theo dõi book xe có cột cước; chưa tính giá.'}
    p,s,hi=tracking; df,_=read_frame(pd,p,s)
    custcol=find_col(df.columns,['Khách hàng','Cus. Name','Tên khách hàng','customer'])
    if not custcol:return {'ok':False,'task_id':tid,'action':'process','status':'needs_input','needs':['customer_column'],'message':'Thiếu cột khách hàng; chưa tính giá.'}
    mask=df[custcol].fillna('').astype(str).str.contains(customer,case=False,regex=False)
    hit=df.loc[mask].copy()
    if hit.empty:
        so_rows=0
        if so is not None:
            sp,ss,_=so
            sdf,_=read_frame(pd,sp,ss)
            scol=find_col(sdf.columns,['Cus. Name','Tên khách hàng','customer'])
            if scol: so_rows=int(sdf[scol].fillna('').astype(str).str.contains(customer,case=False,regex=False).sum())
        msg=f'Không tìm thấy khách hàng “{customer}” trong sheet book xe; chưa tính giá.'
        if so_rows: msg=f'Tìm thấy {so_rows} dòng SO của “{customer}” nhưng chưa có chuyến book xe tương ứng; chưa tính giá.'
        return {'ok':True,'task_id':tid,'action':'process','status':'needs_input','needs':['booking_match'],'message':msg,'rows':0,'so_rows':so_rows}
    canonical={'tracking_code':['Mã theo dõi'],'date':['Ngày'],'customer':['Khách hàng','Cus. Name'],'gross_kg':['Gross (kg)'],'vehicle_count':['Số xe'],'vehicle_tier':['Nấc xe'],'rate_per_vehicle':['Cước/xe (đ)'],'surcharge':['Phụ phí ghép điểm (đ)'],'total_freight':['Tổng cước (đ)'],'order_value':['Trị giá đơn (đ)'],'freight_ratio':['% cước / trị giá']}
    mapping=req.get('mapping') or {}; records=[]
    for _,row in hit.head(MAX_DETAIL).iterrows():
        rec={}
        for key,aliases in canonical.items():
            col=mapping.get(key) or find_col(df.columns,aliases)
            if col in df.columns: rec[key]=compact(row[col])
        records.append(rec)
    # Never pick a rate silently when the same booking code has conflicting
    # recorded totals.  The caller must resolve that ambiguity explicitly.
    codecol=mapping.get('tracking_code') or find_col(df.columns,['Mã theo dõi'])
    ratecols=[mapping.get('total_freight') or find_col(df.columns,['Tổng cước (đ)']),
              mapping.get('rate_per_vehicle') or find_col(df.columns,['Cước/xe (đ)'])]
    if codecol and any(c in df.columns for c in ratecols if c):
        rc=next(c for c in ratecols if c in df.columns)
        for _, grp in hit.groupby(codecol,dropna=False):
            nums={safe_num(pd,v) for v in grp[rc].tolist() if safe_num(pd,v) is not None}
            if len(nums)>1:
                return {'ok':True,'task_id':tid,'action':'process','status':'needs_input','needs':['ambiguous_rate'],'message':'Có nhiều mức cước khác nhau cho cùng mã theo dõi; cần xác nhận trước khi tính.','rows':int(len(hit))}
    # Rates are accepted only if source has a numeric recorded total/rate; no invented tariff.
    ratecol=find_col(df.columns,['Tổng cước (đ)','Cước/xe (đ)'])
    vals=[safe_num(pd,r.get('total_freight') or r.get('rate_per_vehicle')) for r in records]
    grosscol=mapping.get('gross_kg') or find_col(df.columns,['Gross (kg)'])
    missing_gross=bool(grosscol and hit[grosscol].fillna('').astype(str).str.strip().isin(['','nan','None']).any())
    if missing_gross:
        status='needs_input'; msg='Thiếu Gross (kg) ở một hoặc nhiều chuyến; chưa tính cước an toàn.'
    elif ratecol is None or not any(v is not None for v in vals):
        status='needs_input'; msg='Đã tìm thấy book xe nhưng thiếu cước/bảng giá số; chưa tính giá.'
    else: status='complete'; msg=f'Đã lọc {len(records)} chuyến của khách hàng; dùng cước đã ghi trong sheet book xe.'
    detail={'task_id':tid,'status':status,'customer_query':customer,'source_files':[x.name for x in paths],'rows':records,'scope':'matched_rows_only','source_immutable':True}
    (outdir/'detail.json').write_text(json.dumps(detail,ensure_ascii=False,indent=2,default=str)+'\n',encoding='utf-8')
    out={'ok':status=='complete','task_id':tid,'action':'process','status':status,'message':msg,'customer':customer,'rows':len(records),'detail':str((outdir/'detail.json').name),'rates_verified':status=='complete'}
    if status!='complete': out['needs']=['gross_kg'] if missing_gross else ['rate']
    return out

def parse():
    ap=argparse.ArgumentParser(); ap.add_argument('--workspace',required=True); ap.add_argument('--request-json'); return ap.parse_args()

def run():
    a=parse(); workspace=Path(a.workspace).expanduser().resolve()
    try:
        raw=a.request_json if a.request_json is not None else sys.stdin.read()
        req=json.loads(raw); result=main(req,workspace)
        # A bounded, honest `needs_input` result is a successful task contract;
        # reserve non-zero exit codes for malformed/unsafe requests.
        return emit(result,0)
    except Exception as e:
        return fail(str(e).split(':',1)[0] or 'task_failed')
if __name__=='__main__': raise SystemExit(run())
