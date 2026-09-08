---
name: "zalo-proactive-group-messaging"
description: "Cấp quyền và gửi tin chủ động vào Zalo group bằng message trực tiếp, xác minh messageId/threadId và xử lý lỗi delivery."
---

# Zalo Proactive Group Messaging

## Mục đích

Cho phép OpenClaw chủ động gửi tin nhắn text vào Zalo Personal group bằng đường gửi trực tiếp của channel adapter, không nhầm với `sessions_send` (chỉ chuyển nội dung giữa các session nội bộ).

## Khi dùng

Dùng khi người dùng yêu cầu:

- Chủ động nhắn tin vào một group Zalo.
- Gửi tin kiểm tra kết nối vào group.
- Sửa lỗi bot đã xử lý nhưng group không thấy phản hồi.
- Xác minh một tin đã thực sự đi ra Zalo.

Không dùng skill này cho nhắc lịch/cron định kỳ; việc đó dùng `zalo-group-reminder-delivery`.

## Quy tắc an toàn và chính xác

1. Không dùng `sessions_send` để tuyên bố đã gửi ra Zalo. Công cụ này chỉ gửi vào session nội bộ.
2. Target phải giữ dạng `group:<NUMERIC_GROUP_ID>`.
3. Không tự suy đoán group ID từ tên group. Lấy ID từ session Zalo hiện tại hoặc yêu cầu người dùng xác nhận.
4. Trước khi gửi, kiểm tra quyền công cụ. Với `tools.profile: "coding"`, bổ sung tối thiểu `tools.alsoAllow: ["message"]` bằng config patch; không thay toàn bộ cấu hình và không dùng `allow` cùng `alsoAllow` trong cùng scope.
5. Sau patch, chạy validate. Không cần restart nếu OpenClaw báo nạp nóng thành công; nếu cần restart thì dùng gateway restart hoặc supervisor phù hợp với môi trường.
6. Gửi qua `message(action="send", channel="zalouser", accountId="default", target="group:<ID>", message="...")` hoặc qua helper gửi group nếu có.
7. Chỉ xác nhận thành công khi biên nhận có cả:
   - platform `messageId` khác rỗng;
   - `threadId`/`conversationId` khớp đúng numeric group ID;
   - trạng thái sent/delivery tương ứng.
8. Exit code hoặc `accepted/pending` một mình không phải bằng chứng giao thành công.
9. Tin kiểm tra nên ngắn, không gửi lặp nhiều lần nếu chưa có bằng chứng lỗi.

## Quy trình gửi trực tiếp

### Bước 1: Xác định session và group ID

- Tìm session key dạng `agent:main:zalouser:group:<ID>`.
- Đối chiếu tên group và ID từ lịch sử/session metadata hiện tại.
- Không tái sử dụng ID của group khác.

### Bước 2: Kiểm tra quyền

Đọc config hiện tại, giữ nguyên các trường khác. Nếu chưa có quyền message, áp dụng patch tối thiểu:

```json5
{ tools: { alsoAllow: ["message"] } }
```

Sau đó kiểm tra `openclaw config validate` hoặc kết quả patch.

### Bước 3: Gửi một tin duy nhất

Dùng message tool trực tiếp, không dùng sessions_send. Nội dung kiểm tra mẫu:

```text
Nhi gửi tin kiểm tra chủ động vào group này. Anh thấy tin nhắn vui lòng phản hồi “Đã thấy”.
```

### Bước 4: Xác minh biên nhận

Ghi lại message ID. Kiểm tra các trường `messageId`, `receipt.primaryPlatformMessageId`, `receipt.threadId` và `payload.to`. Nếu thiếu hoặc lệch ID, coi là thất bại và báo đúng trạng thái.

### Bước 5: Nếu bot vẫn không tự phản hồi inbound

Phân biệt hai đường:

- **Outbound chủ động thành công nhưng inbound không kích hoạt bot:** kiểm tra `channels.zalouser.groupPolicy`, `groups.<ID>.enabled`, `requireMention`, allowFrom và log inbound/dispatch.
- **Inbound được xử lý nhưng không có tin ra:** tìm log `visible channel turn dispatched with no queued reply payloads`, `EmbeddedAttemptSessionTakeoverError`, timeout, context overflow hoặc stuck session; kiểm tra queue/dispatch.

Không gửi lại theo phương pháp cũ trước khi xác định đường nào đang lỗi.

## Helper tùy chọn

Nếu dùng script group helper, phải kiểm tra helper trả về message ID thật và thread ID đúng group ID. Không coi `delivered` không kèm ID là thành công.

## Mẫu báo cáo

### Thành công

- Đã cấp quyền `message` nếu cần.
- Đã gửi trực tiếp qua Zalo adapter.
- `messageId: ...`
- `threadId: ...` (khớp group ID)
- `deliveryStatus: sent`

### Chưa thành công

Nêu rõ một trong các trạng thái: không có quyền, không xác định được group ID, queued/pending, thiếu message ID, thread ID lệch, inbound không dispatch, hoặc model/session timeout. Không dùng câu “đã gửi” nếu chưa có biên nhận đạt đủ tiêu chí.

## Tài liệu liên quan

- `zalo-group-reminder-delivery` — reminder/cron vào group.
- `diagnose-missing-reply-or-file` — chẩn đoán reply/file bị thiếu.
