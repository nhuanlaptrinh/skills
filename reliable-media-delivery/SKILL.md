---
name: "reliable-media-delivery"
description: "Verify and recover delivery of files, audio, video, images, and attachments across chat channels."
---

# Reliable media delivery

Use whenever an agent sends a file, document, image, audio/voice note, video, or other media attachment to a chat, group, channel, or thread.

## Required delivery protocol

1. Confirm the local output exists, is readable, and is the intended file before sending.
2. Send using the platform-native messaging tool with the explicit intended destination and thread/group when applicable.
3. Treat a send attempt as **unverified** until the tool/platform returns a real `messageId` and destination metadata confirms the intended channel, recipient/group, and thread when used.
4. Only after that verification may the agent say the item was sent/delivered or record `delivered: true`.

## Failure or uncertainty

If the send returns an error, no `messageId`, wrong destination, or an ambiguous result:

1. Do not silently end the task and do not claim delivery.
2. Inspect the failure safely: source path/existence/readability, attachment type and size, destination/group/thread identifier, permissions, provider error, and connection/service status.
3. Correct a safe, identified issue and retry once with the correct explicit target.
4. Verify the retry with the same receipt requirements.
5. Before retrying after an ambiguous result, inspect available message history/receipts. Do not create duplicate media when a prior successful delivery is possible.
6. If it remains blocked, report the exact current state and known reason to the requester. State that it has not been verified as delivered.

## Group/thread protection

- Resolve the destination from the active request/session; do not guess or reuse a group ID from unrelated work.
- Match the returned receipt to the required group/channel and thread, not only a non-empty message ID.
- Follow workspace-specific delivery skills and rules where they exist. For example, Zalo group reminders may require a dedicated delivery helper.

## Completion checklist

- [ ] Correct asset exists and opens locally.
- [ ] Sent to the intended destination.
- [ ] Receipt has real `messageId`.
- [ ] Receipt destination and thread/group match.
- [ ] User-facing completion statement matches verified status.
