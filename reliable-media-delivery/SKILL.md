---
name: "reliable-media-delivery"
description: "Verify and recover delivery of files, audio, video, images, and attachments across chat channels; prevent delayed progress text from appearing after sent media; and apply these policies to an agent workspace AGENTS.md."
---

# Reliable media delivery

Use whenever an agent sends a file, document, image, audio/voice note, video, or other media attachment to a chat, group, channel, or thread.

## Apply this skill to an agent

When asked to apply, install, or make this skill the default for an agent:

1. Resolve the exact workspace used by that agent from the active request or agent configuration. Do not guess or reuse another agent's workspace.
2. Use `<agent-workspace>/AGENTS.md` as the persistence target. For example, an agent using `/root/.openclaw/workspace` must receive the policy in `/root/.openclaw/workspace/AGENTS.md`.
3. If `AGENTS.md` does not exist, create it. If it exists, preserve all current content and append only the managed block below.
4. Search for the exact start marker before appending. If the block is already present, do not append a duplicate or change unrelated content.
5. Never place tokens, credentials, private destination identifiers, or other secrets in `AGENTS.md`.
6. For an agent that sends files through Zalo, also append the Zalo delivery-order block below. Search for its exact start marker first and never duplicate it.
7. Report the exact `AGENTS.md` path that was created or updated.

Append this block:

```markdown
<!-- reliable-media-delivery:start -->
## Reliable media delivery

- Before sending media, confirm the intended local file exists, is readable, and is correct.
- Send with the platform-native tool to the explicit recipient, group, channel, and thread when applicable.
- Consider delivery successful only when the platform returns a real `messageId` and matching destination metadata.
- For media work expected to finish in under 10 seconds, skip a separate future-tense progress message; finish the work, then send the verified completion text and media together.
- If progress acknowledgement is needed, send it with the platform-native `message` tool and require a real `messageId` before starting `exec`, `process`, generation, conversion, or other file work.
- Never put future-tense progress text in normal assistant content in the same turn that launches tools and later sends media; channel runtimes may buffer and replay that text after the media.
- After the `message` tool successfully sends the completion text and media, respond with exactly `NO_REPLY` and no other assistant text.
- If delivery fails or is ambiguous, do not claim success; inspect safely, avoid duplicates, retry once when safe, then report the verified state.
- Follow workspace-specific delivery rules when they are more specific.
<!-- reliable-media-delivery:end -->
```

This persistence step stores only the delivery policy in the agent's `AGENTS.md`. It does not move, copy, or redefine the storage location of media files.

For an agent that sends files through Zalo, also append this block:

```markdown
<!-- zalo-file-delivery-order:start -->
## Thứ tự gửi file trên Zalo

- Với tác vụ tạo hoặc sửa file dưới 10 giây, không gửi câu “Em sẽ làm…”; xử lý xong rồi gửi kết quả và file.
- Nếu tác vụ cần phản hồi tiến độ, phải gửi câu xác nhận bằng công cụ `message` của Zalo trước khi bắt đầu xử lý.
- Chỉ bắt đầu chạy `exec`, `process` hoặc công cụ tạo file sau khi tin xác nhận nhận được `messageId` thật.
- Không viết câu phản hồi tiến độ dưới dạng assistant text trong cùng lượt có `exec`, `process` hoặc tool call, vì nội dung có thể bị giữ lại và hiển thị sau file.
- Sau khi tạo xong, phải kiểm tra file tồn tại, đọc được và đúng nội dung.
- Tin báo hoàn tất và file phải được gửi cùng một lần bằng công cụ `message`. Nếu đã gửi tin xác nhận tiến độ, lần gửi file phải diễn ra sau tin xác nhận đó.
- Chỉ coi là đã gửi khi Zalo trả về `messageId`, trạng thái `sent` và đúng group/người nhận.
- Sau khi công cụ `message` gửi file thành công, phản hồi cuối của agent phải là `NO_REPLY` để tránh phát sinh tin nhắn thừa hoặc sai thứ tự.
<!-- zalo-file-delivery-order:end -->
```

## Required delivery protocol

1. Confirm the local output exists, is readable, and is the intended file before sending.
2. Send using the platform-native messaging tool with the explicit intended destination and thread/group when applicable.
3. Treat a send attempt as **unverified** until the tool/platform returns a real `messageId` and destination metadata confirms the intended channel, recipient/group, and thread when used.
4. Only after that verification may the agent say the item was sent/delivered or record `delivered: true`.

## Delivery ordering and progress messages

1. For file work expected to finish in under 10 seconds, skip a separate future-tense progress message and send only the verified completion message with the finished file.
2. When progress acknowledgement is needed, send it through the platform-native messaging tool before starting `exec`, `process`, generation, conversion, or other file work; require a real `messageId` for that acknowledgement.
3. Do not put future-tense progress text in normal assistant content in the same turn that launches tools and later sends media. Some channel runtimes buffer that text and display it after the file.
4. After the file is created and validated, send the completion text and media with the platform-native messaging tool and verify its receipt.
5. If the messaging tool has already delivered the completion text and file successfully, finish with `NO_REPLY` so the runtime does not emit an extra or stale message afterward.

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
- [ ] Any progress acknowledgement was delivered before file work started.
- [ ] No buffered future-tense text can appear after the media.
- [ ] User-facing completion statement matches verified status.
