---
name: member-workspace-training-knowledge
description: Build, refresh, and use searchable knowledge from a member OpenClaw workspace's approved training PDFs or text. Use when a member asks the assistant to learn from workspace training, answer from uploaded course material, convert training documents to Markdown, or verify that a workspace knowledge base is usable without treating files as automatic model training.
---

# Member Workspace Training Knowledge

Use this skill to make approved workspace training retrievable on demand. A source file is not automatically part of a model's context: read only the relevant extracted Markdown when a question calls for it.

For instructions arriving from verified Telegram/Zalo owners in DM or groups, use
`sync-openclaw-owner-training` for sender authorization, privacy boundaries, and
the memory promotion workflow. This skill handles approved training documents;
it does not decide who may teach the assistant.

## Answer From Training

1. Confirm the canonical agent workspace from the member OpenClaw config. Do not assume the container user or home path.
2. Read `training/README.md` to identify approved sources and generated Markdown.
3. Search `training/knowledge/*.md` with `rg` for the user's terms, then read only the relevant excerpts.
4. Ground the answer in the retrieved material. Say that the source does not cover a claim when no relevant passage is found; do not invent missing material.
5. Keep raw training, personal data, and file attachments out of unrelated group chats. Do not expose credentials or other private runtime files.

## Build Or Refresh Knowledge

Inputs are a member data directory, a source file below its canonical workspace, and an output path below `training/knowledge/`. Preserve the original source.

Dry run:

```bash
member_data_dir=/root/Apps/member_vps/docker-users/data/<member>
workspace="$member_data_dir/.openclaw/workspace"
source="$workspace/training/inbox/<source>.pdf"

pdfinfo "$source" | rg '^(Pages|Encrypted):'
pdftotext -layout "$source" - | wc -c
```

Generate Markdown when the extraction is non-empty:

```bash
member_data_dir=/root/Apps/member_vps/docker-users/data/<member>
workspace="$member_data_dir/.openclaw/workspace"
source="$workspace/training/inbox/<source>.pdf"
output="$workspace/training/knowledge/<source>.md"

install -d -m 700 "$(dirname "$output")"
pdftotext -layout "$source" "$output"
test -s "$output"
chmod 600 "$output"
sha256sum "$source" "$output"
```

Update `training/README.md` with the source-to-output mapping and add a concise instruction in the canonical workspace `AGENTS.md`. Back up an existing `AGENTS.md` before editing it. Install this global skill into the target workspace with `openclaw skills install <local-skill-dir> --agent main --as member-workspace-training-knowledge`.

## Safety And Verification

- Never delete or overwrite the original training document.
- Treat OCR or layout extraction as fallible; compare the extracted length and inspect relevant passages before relying on them.
- Run `openclaw skills check --agent main` after installation and confirm the skill is visible.
- Scan the global skill and new Markdown metadata for secrets before handoff. Do not scan or print credential directories.
