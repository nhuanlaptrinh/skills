#!/usr/bin/env python3
"""Read-only lookup of Zalo group session candidates by normalized name."""
import argparse, json, re, sqlite3, unicodedata

def norm(s):
    s=unicodedata.normalize('NFKD', s or '').encode('ascii','ignore').decode().lower()
    return re.sub(r'[^a-z0-9]+','',s)

p=argparse.ArgumentParser(); p.add_argument('--db',required=True); p.add_argument('--name',required=True); a=p.parse_args()
needle=norm(a.name)
con=sqlite3.connect('file:'+a.db+'?mode=ro',uri=True)
rows=[]
for key,sid,status,display,label,updated in con.execute("select session_key,current_session_id,status,display_name,label,updated_at from session_nodes where session_key like 'agent:%:zalouser:group:%'"):
    hay=' '.join([key,display or '',label or ''])
    if needle in norm(hay):
        rows.append({'sessionKey':key,'sessionId':sid,'status':status,'updatedAt':updated})
rows.sort(key=lambda x:x['updatedAt'] or 0,reverse=True)
print(json.dumps({'matches':rows},ensure_ascii=False))
