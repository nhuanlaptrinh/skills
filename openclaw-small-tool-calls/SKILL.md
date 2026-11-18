---
name: openclaw-small-tool-calls
description: Process Excel/CSV files and generate scripts with small tool arguments and bounded previews. Use when handling large tables, long generated code, or the OpenClaw error Exceeded tool-call argument buffer limit.
---

# Small tool calls for file processing

Keep data in local files and send paths plus short operations to tools. This
skill reduces oversized model-generated arguments; it is an agent workflow,
not a runtime guarantee that every model response stays within a byte limit.

## When diagnosing this error

OpenClaw 2026.10.6's installed OpenAI-completions transport on Cat Minh rejects
buffered tool-call arguments above **256,000 UTF-8 bytes**. Confirm the deployed
version/source for other installations. This limit applies to generated tool
arguments, not the attachment size, context window, or tool result size.
Log text alone does not prove whether the model generated useful long code,
repeated content, or copied data. Do not claim a specific cause without evidence.

## Working budget

- Aim for at most **16 KiB of serialized arguments per tool call**. Write/edit
  at most **8 KiB of new code/text per call**, leaving room for JSON escaping,
  old/new edit text, paths, and other fields. These are conservative working
  budgets, not new OpenClaw settings; UTF-8 bytes differ from character counts.
- Before a large write/exec/edit, split code into small functions or modules.
  Do not place all chunks into one heredoc, tool-call batch, or JSON argument.
  Append the next chunk only after the previous write has completed.
- Pass existing input/output paths. Do not inline full rows, document text,
  base64, or a serialized DataFrame in a shell command or write argument.
- Generate repetitive data locally with loops/templates. Do not ask the model
  to emit thousands of literal rows. Run an existing script by its path.
- Bound tool output as well: normally schema and 3-5 rows, at most 4 KiB.
  Save detailed logs and full tables to files. Output limits alone do not fix
  oversized arguments.

## Inspect a table

Resolve the current attachment's local path and the active workspace. Use an
existing Python with pandas/openpyxl; check `.venv/bin/python` if necessary.
Do not install packages or switch libraries just to inspect an ordinary file.

The helper is `scripts/inspect_table.py` beside this SKILL.md. In a deployed
workspace it is `skills/openclaw-small-tool-calls/scripts/inspect_table.py`.
From that workspace, use:

```bash
python3 skills/openclaw-small-tool-calls/scripts/inspect_table.py \
  --input /absolute/path/current.xlsx --dry-run
python3 skills/openclaw-small-tool-calls/scripts/inspect_table.py \
  --input /absolute/path/current.xlsx --sheet Sheet1 --sample-rows 3
```

Dry-run checks file readability and supported suffix without parsing contents.
The real inspection reads only the requested preview rows from one sheet,
returns bounded JSON, and writes nothing. Omit `--sheet` to use the first Excel
sheet; omit it for CSV. Supported formats: `.xlsx`, `.xlsm`, UTF-8 `.csv`.
It does not execute macros. Preview row counts are **not total row counts**.
It shows at most 12 columns, 10 sheet names, and 96 characters per text value.
JSON output, including its newline, is at most 4096 UTF-8 bytes; truncation is
explicit. If a needed column is outside the preview, inspect that column with
a short targeted pandas call. Do not infer business logic from omitted data.

## Perform the requested calculation

1. Create a request-specific directory under `output/<request-id>/` in the
   active workspace. Preserve the source; identify sheet/header, data types,
   required formulas, and expected totals before transforming anything.
2. Write a short `process.py` (and separate modules if needed). Read the source
   with pandas, calculate locally, and save complete results in the job folder.
   Use CSV chunks when necessary; for Excel, select sheets/columns or partition
   work by meaningful groups. Use openpyxl for workbook formatting/formulas,
   retaining any stricter existing workspace requirements for pandas.
3. Make this per-job script accept `--input` and `--output-dir`. A minimal
   syntax preflight and a real run, after choosing the correct paths, are:

```bash
python3 -c 'import ast,pathlib,sys; ast.parse(pathlib.Path(sys.argv[1]).read_text()); print("syntax_ok")' output/request-id/process.py
python3 output/request-id/process.py \
  --input /absolute/path/current.xlsx --output-dir output/request-id/result
```

   These commands assume the job script has been created for the user's task;
   the skill does not ship a universal accounting transformation.
4. For long work, checkpoint input hash, completed partitions, artifact paths,
   and validation state in `job-state.json`. Resume only verified partitions
   with the same input hash. Do not append processed rows twice on rerun; use a
   fresh result directory or an explicitly implemented resume mode.
5. Reopen the generated workbook and check expected sheets, row counts, key
   totals, and required formulas. Report only a short result and artifact path.
   External delivery follows the current request and existing receipt rules.

If the buffer error recurs, inspect completed artifacts first and retry once
with smaller code/data operations. Do not repeat the same oversized call. If
that retry also fails, preserve the checkpoint and report the exact failure.
Do not reset a whole session or raise the transport limit as the default fix.

## Deployment and verification

- Global source on the host: `/root/.agents/skills/openclaw-small-tool-calls/`.
- Cat Minh member: `/root/Apps/member_vps/docker-users/data/trolyketoancatminh/`;
  container `user-trolyketoancatminh`, runtime HOME `/home/trolyketoancatminh`.
- Copy this entire skill directory into each intended workspace's `skills/`.
  Add the small-call rule to its existing AGENTS.md so it is present even when
  the skill is not selected. Back up exact files, preserve unrelated rules,
  and keep each AGENTS.md under the configured bootstrap limit.
- Verify discovery using `openclaw skills --agent <agent-id> info
  openclaw-small-tool-calls --json`, config validation, and channel probes.
  Use an isolated diagnostic session and synthetic data for a calculation test;
  do not use `--deliver` or messaging tools. Confirm artifact totals and actual
  serialized tool-call sizes, not merely a model claim of success.
- These are instructions for subsequent turns; they cannot rewrite an already
  streaming tool call. No Gateway restart is normally needed for workspace
  instructions/skills. Preserve active user sessions and ongoing tasks.
- No Sheet/API writes, publishing, or scheduled jobs are part of this skill.
  Never place credentials, private message bodies, or full customer data in the
  skill or test artifacts. Record deployment in both relevant Second AI Brains.
