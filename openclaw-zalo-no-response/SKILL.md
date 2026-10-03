---
name: openclaw-zalo-no-response
description: Compatibility entry point for OpenClaw Zalo Personal no-response incidents on member VPS. Route all new work to the consolidated recovery skill.
---

# OpenClaw Zalo No Response

Use `/root/.agents/skills/openclaw-zalo-no-response-recovery/SKILL.md` as the
single end-to-end workflow for Zalo no-response, outbound delivery, listener,
session, Gateway, Docker restart, watchdog, and attachment recovery.

The implementation helpers remain available in:

- `/root/.agents/skills/openclaw-zalo-reliability/SKILL.md`
- `/root/.agents/skills/openclaw-zalo-reliability-deploy/SKILL.md`
- `/root/.agents/skills/shared-watchdog-center/SKILL.md`

Preserve credentials, pairing, routing, and transcripts. Do not QR-login,
delete sessions, replay dead letters, or send a real test message without
explicit owner authorization.
