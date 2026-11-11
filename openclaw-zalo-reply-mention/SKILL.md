---
name: openclaw-zalo-reply-mention
description: Configure or troubleshoot native Zalo group reply mentions of the current sender in OpenClaw on Windows, macOS, Linux, or Docker, without changing group access policy or private chats.
---

# Zalo reply mention

For an automatic reply in a group, start with a real native mention targeting the current inbound sender, not the author or mentions in quoted content. Use a trustworthy provider username only when the API actually exposes one; otherwise send a genuine Zalo mention entity with the exact sender ID and its display label. Display name alone is not a username, and plain `@name` alone is not a Zalo mention entity. If the sender ID or label cannot be verified, fail safely and report the limitation. Do not alter direct chats, group incoming-mention policy, allowlists, or exec permissions.

## Workflow

1. Identify the installed OpenClaw and Zalo plugin versions, active runtime/plugin location, accounts, routing, service manager and health. A captured or built plugin may differ from its source. Do not print credentials, account IDs or private content. Inspect the exact version's outbound API, message schema, chunking, and all reply paths; the normal callback and durable outbound adapter can be different paths.
2. Prefer a supported plugin option/API over modifying packaged code. If none exists and the owner authorizes a patch, review `references/compatibility.md` and the exact version-limited patch. Check current sender data and provider entity shape instead of guessing. Avoid applying a historical patch to another build merely because the filenames resemble it.
3. Back up the changed plugin files in a private directory, validate patch context before writing, and keep a reversible copy. Never modify the Zalo login profile or force logout. Treat a gateway restart as a possible connection interruption and obtain permission; apply using the existing service manager, not a second gateway. Preserve access settings.
4. Test offline with the actual chunker, fake sender, plain text, styles, Unicode/UTF-16 offsets, splitting, media/audio, both accounts, direct chats, quoted messages, missing sender fields, and the durable adapter/queue. Test concurrent group turns and retries where practical. A mocked test does not establish actual Zalo rendering.
5. After activation, verify gateway and every existing account are linked/running/connected and probe succeeds. Do not send a live message without permission. Ask the owner to test each assistant in its group, or request permission for a controlled test. Report whether native entity rendering and correct recipient were actually observed. Do not claim success solely because `@name` appears as text.

The bundled reference is an example for one observed OpenClaw/plugin build, not an upstream extension API or a guarantee for other versions/OSes. Plugin updates can overwrite it. Windows, macOS and Linux use the same logical checks; resolve each runtime's paths and service controls locally.
