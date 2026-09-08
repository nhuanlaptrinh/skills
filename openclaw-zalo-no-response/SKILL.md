---
name: openclaw-zalo-no-response
description: Compatibility entry point for diagnosing and recovering OpenClaw Zalo Personal no-response incidents on member VPS. Use openclaw-zalo-reliability as the canonical workflow.
---

# OpenClaw Zalo No Response

Use `/root/.agents/skills/openclaw-zalo-reliability/SKILL.md` as the canonical workflow for Zalo no-response, outbound delivery, listener, session, Gateway, watchdog, and attachment recovery.

For `lehuynhphong`, resolve and verify `user-lehuynhphong`, `/home/lehuynhphong`, and `/root/Apps/member_vps/docker-users/data/lehuynhphong` before any change. Run the canonical diagnostic first:

```bash
bash /root/.agents/skills/openclaw-zalo-reliability/scripts/diagnose.sh user-lehuynhphong /home/lehuynhphong
```

Preserve credentials, pairing, routing, and transcripts. Use schema-supported OpenClaw 2026.8.2 compaction settings only; do not add legacy `reserveTokensFloor` or `maxHistoryShare`. Do not send a real test message without explicit owner authorization.
