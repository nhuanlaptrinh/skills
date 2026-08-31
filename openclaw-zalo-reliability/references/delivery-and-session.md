# Delivery And Session Reliability

Use this branch when large files, voice, video, long tool output, or oversized
sessions delay or suppress Zalo replies.

## Session Maintenance

Dry-run before applying:

```bash
MEMBER_HOME=<member-home> SESSION_PATTERN='agent:main:zalouser:direct:<id>' \
TOKEN_THRESHOLD_64K=18000 TOKEN_THRESHOLD_128K=40000 \
SESSION_IDLE_SECONDS=600 MAX_COMPACTIONS_PER_RUN=1 COMPACTION_MODE=summary \
  bash /root/Automation/openclaw_member_assistant/scripts/audit_member_sessions.sh <container>
```

Defaults:

- Use `18000` for a 64K context and `40000` for a 128K context unless the
  member project note records a previously validated threshold.
- Use a narrow direct-session pattern for a recurring owner DM.
- Use the broad `agent:main:zalouser:` pattern only for deliberate member-wide
  maintenance.
- Require at least ten idle minutes and compact at most one session per run.
- Use `COMPACTION_MODE=summary` when few transcript lines contain very large
  tool outputs.

Enable preventive context handling when absent:

```bash
openclaw config set agents.defaults.contextPruning.mode cache-ttl
openclaw config set agents.defaults.contextPruning.ttl 5m
openclaw config set agents.defaults.compaction.mode safeguard
openclaw config set agents.defaults.compaction.reserveTokensFloor 40000
openclaw config set agents.defaults.compaction.maxHistoryShare 0.5
openclaw config validate
```

Back up the session index before `--apply`. If compaction cannot repair one idle
session, preserve its transcript and retire only that key while the Gateway is
stopped or frozen.

## File And Message Delivery

- Keep ordinary Zalo replies around 1,800 characters; summarize or send a file
  for longer content.
- The Zalo plugin may split at 2,000 characters, pause 600 ms between chunks,
  and retry up to three times with backoff when the reusable send patch is
  active.
- Validate generated files before delivery:

```bash
python3 /root/Automation/openclaw_member_assistant/scripts/validate_zalo_file.py /path/to/file.xlsx
```

- Install member document tooling only through
  `/root/Automation/openclaw_member_assistant/scripts/setup_member_document_tools.sh`.
- For silent archive groups, use the separate `zalo-silent-group-archive` skill
  and rerun its patch dry-run after Zalo plugin updates.

## Voice Messages

The Zalo plugin may expose AAC voice messages as `zdn.vn` URLs rather than media
attachments. Use `/root/.agents/skills/cai-dat-audio-local-openclaw/SKILL.md`
for the URL-to-Shared-Local-STT flow. Do not apply this requirement to
Telegram-only members.
