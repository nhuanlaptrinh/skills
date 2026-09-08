---
name: "zalo-group-file-delivery-recovery"
description: "Diagnose and recover missing file delivery to Zalo Personal groups with verified group receipts."
---

# Zalo group file delivery recovery

Use when a file was reported sent to a Zalo Personal group but members cannot see it, or when file delivery times out/fails.

## Workflow

1. Identify the exact file and group session from current history or session metadata.
   - Resolve the numeric group ID anew from `agent:<agent>:zalouser:group:<group-id>`.
   - Never infer an ID from the group name or reuse one from another conversation.
2. Inspect before retrying:
   - Confirm each file exists, is readable, and has the expected format/size.
   - Check the previous tool result and logs for timeout, `SIGTERM`, cross-context denial, empty target, direct-user routing, or attachment failure.
   - Do not treat a nested-session reply, `delivery.status: pending`, or an announce receipt as proof that the group received the file.
3. If the current session is not bound to `zalouser`, do not call `message` directly across providers. Route the operation through the exact Zalo group session with `sessions_send`.
4. In the Zalo group session, send each file as a separate `message` tool call with all fields explicit:
   - `action=send`
   - `channel=zalouser`
   - `accountId=default` unless the session specifies another account
   - `target=group:<numeric-group-id>`
   - `media=<absolute-file-path>`
   - `filename=<basename>`
   - a short caption/message
5. Never use an empty target, a bare numeric target, or only a final `MEDIA:` directive for this recovery path.
6. Verify every file independently. Success requires a platform receipt containing:
   - non-empty `messageId` or `primaryPlatformMessageId`
   - `kind: media`
   - `threadId` equal to the numeric group ID
   - `conversationId` equal to the numeric group ID when present
7. If a send times out or receives `SIGTERM`, report it as unconfirmed. Check logs and retry once through the same exact group session; do not claim success without a new receipt.
8. Report concise evidence per file: filename, platform message ID, and verified group/thread ID.

## Guardrails

- Never claim “sent successfully” from `delivery.status: pending` alone.
- Never trust a receipt produced with an empty or direct-user target as group-delivery proof.
- Preserve exact error messages during diagnosis.
- For multiple files, send and verify one at a time.
- This skill concerns immediate file delivery. For scheduled Zalo group reminders, use `zalo-group-reminder-delivery` and avoid announce delivery.
