---
name: openclaw-long-document-pipeline
description: Process long PDF, DOCX or text documents in resumable chunks, then merge the result and create a validated DOCX. Use for lengthy Telegram document requests where one-shot reading or translation may time out.
---

# OpenClaw long-document pipeline

Use this skill for a long document that could exceed context, timeout, or output limits. The pipeline stores a source hash, manifest, extracted source and one validated JSON/TXT result per chunk. It resumes completed work and never treats a partial job as complete.

## Avata paths

- Workspace: `/root/.openclaw/workspace`
- Pipeline: `/root/.agents/skills/openclaw-long-document-pipeline/scripts/long_document_pipeline.py`
- Member copy: `/root/.openclaw/workspace/skills/openclaw-long-document-pipeline/scripts/long_document_pipeline.py`
- Python: `/root/.openclaw/tools/document-venv/bin/python`
- Protected provider env: `/root/.openclaw/token-codex.env` (read only; never print)

## Default workflow

1. Use only the current Telegram attachment. The script extracts PDF text or DOCX/DOCM text locally and preserves the original. Scanned/image-only PDF pages and Word images produce warnings and stop translation until checked/OCR'd.
2. Prepare and inspect chunking without an API call:

```bash
/root/.openclaw/tools/document-venv/bin/python \
  /root/.agents/skills/openclaw-long-document-pipeline/scripts/long_document_pipeline.py \
  --input /root/.openclaw/workspace/tmp/docx-reading/current.txt \
  --output-dir /root/.openclaw/workspace/reports/long-document/<request-id> \
  --label "<document label>" --mode read --dry-run
```

For an inbound DOCX, first use `openclaw-docx-reader` when exact Word extraction is needed. TXT input is accepted for already extracted text.

3. Translate using the same input and job directory. The script reads the protected `TOKEN_CODEX_API_KEY`, resolves the member's configured provider/model, validates each JSON block, and uses at most two concurrent requests:

```bash
/root/.openclaw/tools/document-venv/bin/python \
  /root/.agents/skills/openclaw-long-document-pipeline/scripts/long_document_pipeline.py \
  --input /root/.openclaw/workspace/tmp/docx-reading/current.txt \
  --output-dir /root/.openclaw/workspace/reports/long-document/<request-id> \
  --label "<document label>" --mode translate --workers 2 --resume
```

4. If a request stops or reports `partial`, repeat the same command with `--resume`; completed chunks are validated and skipped. `--max-chunks 1` is useful for a small demo or controlled rollout. `--status` reports progress without calling the API.
5. On `status=complete`, the job writes `translated.txt` and `translated.docx`, performs ZIP and python-docx round-trip checks, and records hashes/coverage in `manifest.json`. Only then may an agent stage the DOCX under `/root/.openclaw/media/outbound/` and send it to the known current Telegram target.

## Demo and environment checks

```bash
/root/.openclaw/tools/document-venv/bin/python \
  /root/.agents/skills/openclaw-long-document-pipeline/scripts/long_document_pipeline.py \
  --input /root/.openclaw/workspace/demo/long-document/demo_source.txt \
  --output-dir /root/.openclaw/workspace/demo/long-document/job \
  --label "Demo đọc dữ liệu nhanh" --mode read --dry-run
```

`--check-env` verifies `python-docx`, `pypdf`, and DOCX round-trip support. A real demo translation can use `--mode translate --max-chunks 1`; it consumes one provider request and leaves a resumable partial job if more chunks remain.

## Safety

- Never write API keys, Telegram IDs, cookies or private data to a manifest, skill, log or response.
- Do not reuse a stale inbound file because its name is similar; match the current attachment first.
- Do not delete source text or partial chunks, and do not send a partial output as complete.
- Do not send a file or message unless delivery was requested and the current target is known.
