---
name: zalo-group-session-finder
description: Find and verify Zalo Personal group sessions when sessions_list is unavailable or returns an authentication error.
---

# Zalo group session finder

Use this skill when a user gives a Zalo group name, screenshot, or asks to reply in a group and `sessions_list` is empty or fails authentication.

## Required fallback

1. Do not ask for a Group ID merely because `sessions_list` failed. The tool may reject `relationship=owned` with `relationship requires an authenticated requesting user` even while the Gateway has the group session.
2. First inspect the current member session store. Use the exact member data directory and agent database; select keys matching `agent:<agent>:zalouser:group:<numeric-id>`. Match the normalized group name against `display_name`, `label`, `session_key` suffix, and recent transcript metadata.
3. Prefer the most recently updated matching group session. Verify it with session history or transcript metadata before sending.
4. If the current inbound message already has a session key `agent:<agent>:zalouser:group:<id>`, use that key directly. Never call `sessions_list` to rediscover its ID.
5. Send through the exact group session or native Gateway message with `target=group:<numeric-id>`. Require a real message ID and matching thread/conversation receipt.
6. If the group is not present in the session store, wait for one inbound message in that group; do not ask the user to manually provide an ID unless the store and current inbound context both lack it.

## Safe read-only lookup

The session database is commonly:

`<member-data>/.openclaw/agents/<agent>/agent/openclaw-agent.sqlite`

Read only `session_nodes`/`session_windows` and transcript metadata. Never print or persist private sender IDs, message text, tokens, cookies, or credentials. Redact numeric IDs in diagnostic output.

## Sending and recovery

A group session can be changed by restart recovery while an image/file tool is running. Before `sessions_send`, verify the session is not being restarted and use the current `session_id`; if it changes, reacquire the session key and do not replay a non-idempotent media action. For generated media, keep the output in the originating task, then send once through the current Gateway group route and verify the receipt.

## Task ownership and duplicate prevention

For image/file work requested from a group, retain the inbound group session key as the task owner. Do not create a separate worker that later calls `sessions_send` into the group unless the handoff carries an idempotency key and current session ID. Before a non-idempotent send, reconcile any prior delivery record; a restart or dead-lettered handoff is an unknown outcome, not permission to replay.
