---
name: n8n-gmail-trigger-cleanup
description: Disable confirmed repeatedly failing Gmail polling workflows on the host n8n without deleting credentials, changing other workflows, or restarting n8n. Includes scoped dry-run, official API deactivation, and version-aware rollback guidance.
---

# n8n Gmail Trigger Cleanup

## Scope And Paths

Use when the owner authorizes stopping Gmail trigger error loops. Match workflow IDs from recent logs, not node names alone: several healthy workflows use identical names. Inspect the published version as well as the draft.

- Project: `/root/Apps/n8n/N8n_Project/n8nalt.anhlaptrinh.vn`.
- Runtime: `n8nalt-app`; management API: `http://127.0.0.1:5678/api/v1`.
- Read-only database: `/var/lib/docker/volumes/root_n8n3_data/_data/database.sqlite`.
- Protected website/Zalo workflow: `IQSLZpjfCa6AOcl9`; do not deactivate or change it.
- Backup root: `/root/_Backups/n8n-gmail-trigger-deactivate/`, directory mode `0700`, private files `0600`.
- Existing audit/rollback reference: `/root/_Backups/n8n-gmail-trigger-deactivate/20261015T075836Z/`.

On 2026-10-15 the owner authorized deactivation, not deletion, of these four workflows:

| Workflow ID | Failing published node |
| --- | --- |
| `07y0VBv8BqlGDUn6` | `Gmail Trigger - New Email` |
| `ow38vMC4KJhVP1eU` | `Gmail Trigger` |
| `EbKuBGOonvORs6bK` | `Gmail Trigger` |
| `JQgSmeB9oppWv9sM8Emo9` | `1. Nhận Gmail` |

Other Gmail workflows with only historical startup/OOM errors were not disabled. This historical approval does not authorize adding new IDs or reactivating workflows.

## Dry Run And Authorized Deactivation

The command defaults to a read-only state check. To deactivate the same approved set after rechecking current intent and recent errors, change `MODE=dry-run` to `MODE=deactivate`. It uses an existing owner API key only in memory and sends no emails, Zalo messages, or Sheet writes. Do not print request headers, raw responses, or private workflow definitions.

```bash
MODE=dry-run python3 - <<'PY'
import datetime
import json
import os
import sqlite3
from pathlib import Path

mode = os.environ.get('MODE', 'dry-run')
if mode not in ('dry-run', 'deactivate'):
    raise SystemExit('Unsupported mode')
workflow_ids = ['07y0VBv8BqlGDUn6', 'ow38vMC4KJhVP1eU', 'EbKuBGOonvORs6bK', 'JQgSmeB9oppWv9sM8Emo9']
connection = sqlite3.connect('file:/var/lib/docker/volumes/root_n8n3_data/_data/database.sqlite?mode=ro', uri=True)
connection.row_factory = sqlite3.Row
records = []
for workflow_id in workflow_ids:
    row = connection.execute('SELECT id,active,versionId,activeVersionId FROM workflow_entity WHERE id=?', (workflow_id,)).fetchone()
    if row is None:
        raise SystemExit('Workflow missing; stop')
    records.append(dict(row))
print(json.dumps({'mode': mode, 'workflows': records}))
if mode == 'deactivate':
    import requests
    candidates = connection.execute("SELECT k.apiKey,k.scopes FROM user_api_keys k JOIN user u ON u.id=k.userId WHERE u.roleSlug='global:owner' AND k.audience='public-api' ORDER BY k.createdAt DESC").fetchall()
    api_key = next((row['apiKey'] for row in candidates if {'workflow:read', 'workflow:deactivate'}.issubset(json.loads(row['scopes'] or '[]'))), None)
    if not api_key:
        raise SystemExit('No suitable existing owner API key; do not create or rotate credentials')
    os.umask(0o077)
    timestamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    backup = Path('/root/_Backups/n8n-gmail-trigger-deactivate') / timestamp
    backup.mkdir(parents=True, mode=0o700)
    (backup / 'workflows_before.json').write_text(json.dumps({'workflows': records}, indent=2) + '\n')
    session = requests.Session()
    session.trust_env = False
    for record in records:
        if not record['active']:
            continue
        try:
            response = session.post('http://127.0.0.1:5678/api/v1/workflows/' + record['id'] + '/deactivate', headers={'X-N8N-API-KEY': api_key}, timeout=(5, 30), allow_redirects=False)
        except requests.RequestException:
            raise SystemExit('Uncertain API outcome; inspect state before retrying') from None
        print(json.dumps({'id': record['id'], 'http_status': response.status_code}))
        if response.status_code != 200:
            raise SystemExit('Deactivation not confirmed; stop and inspect state')
    print(json.dumps({'backup_dir': str(backup)}))
connection.close()
PY
```

Input is the fixed ID allowlist and mode; output is sanitized state/status plus the backup path. Rerunning skips workflows already inactive. This is a manual operation, not a scheduled guard; no cron/service is installed.

## Verification And Rollback

- Rerun the dry-run: all four must have `active=0` and `activeVersionId=null`.
- GET `http://127.0.0.1:5678/healthz/readiness`: expect HTTP 200 and `status: ok`.
- Observe at least 130 seconds after the last deactivation. Count only new error lines for these exact IDs; do not confuse historical errors with a new failure. No workflow execution or test message is needed.
- Confirm `IQSLZpjfCa6AOcl9` is still active with the same published version and webhook registrations.
- Rollback requires fresh owner approval and reconnecting the affected Gmail account through n8n's OAuth UI. Do not attempt to manufacture a Google refresh token.
- For rollback, read `activeVersionId` from the original manifest and POST `/api/v1/workflows/<ID>/activate` with JSON `{"versionId":"<original-activeVersionId>"}` using the existing key in memory. Verify the API response and published version. Reactivation can immediately poll Gmail and run downstream actions.
- `ow38vMC4KJhVP1eU` had a different draft and published version: restoring the latest draft is not equivalent to restoring the original live workflow.
- Private `workflow_definitions.private.json` in the original backup contains draft and published definitions for recovery; never paste it into documentation or responses. Do not restore the entire shared database for a workflow-state rollback.

## Safety And Documentation

Use the live API so pollers are removed in memory. Do not directly update SQLite `active`, run a database-only CLI change, restart shared n8n, delete workflow history/credentials, or disable every Gmail node by name. Keep working Gmail send nodes and the website/Zalo workflow untouched.

Record changes and the observation window in `/root/_Second_AI_Brain/06_Nhat_Ky_Thay_Doi.md` and the relevant n8n project note. Update this skill if the scope, API procedure, or backup/output format changes. Scan newly written skill/documentation for secrets; API keys, OAuth tokens, passwords, cookies, and `.env` contents must not be included.
