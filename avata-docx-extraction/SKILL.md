# Avata DOCX extraction

Use when working with Word `.docx`/`.docm` files received by member `avata`.

- Preferred script: `/root/.agents/skills/openclaw-docx-reader/scripts/read_word.py` (shared read-only mount inside the container).
- Inbound root: `/root/.openclaw/media/inbound/`.
- Read by exact path:

  `python3 /root/.agents/skills/openclaw-docx-reader/scripts/read_word.py --input /root/.openclaw/media/inbound/<file>.docx --output /root/.openclaw/workspace/tmp_extract/<file>.txt --json`

- If only the Telegram filename is present, use `--name "<filename>" --inbound-dir /root/.openclaw/media/inbound`; it selects the newest matching attachment and refuses an unmatched name.
- The reader validates the OOXML ZIP/CRC and extracts paragraphs, tables, headers/footers, footnotes/endnotes, and comments without package installation or secrets.
- The older `/root/.openclaw/workspace/tools/extract_docx.py` remains for compatibility but is not the preferred path because it lacks ZIP limits and auxiliary-part extraction.
- Preserve originals and save extracted drafts under `/root/.openclaw/workspace/tmp_extract/`.
