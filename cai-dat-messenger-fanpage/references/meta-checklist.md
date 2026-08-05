# Meta Messenger Setup Checklist

Checklist này hướng dẫn phần kết nối Meta mà không lưu hoặc hiển thị credential thật.

## Chuẩn Bị

- Xác nhận đúng Meta App và đúng Fanpage.
- Xác nhận người thao tác có quyền quản trị cần thiết.
- Xác định callback dùng `direct` hay `dispatcher`.
- Xác định public HTTPS URL đã có SSL hợp lệ.
- Xác định `META_GRAPH_VERSION` còn được hỗ trợ tại thời điểm setup.

## Credential Mapping

Người vận hành nhập trực tiếp vào project `.env` mode `600`:

| Biến | Nguồn |
|---|---|
| `META_VERIFY_TOKEN` | Chuỗi ngẫu nhiên do operator tự đặt |
| `META_APP_SECRET` | Meta App Secret |
| `META_PAGE_ACCESS_TOKEN` | Page Access Token của đúng Fanpage |
| `META_PAGE_ID` | ID của đúng Fanpage |
| `META_APP_ID` | App ID dùng phân biệt bot echo |
| `META_GRAPH_VERSION` | Phiên bản Graph API đã xác nhận |

Không dán các giá trị này vào chat, README, skill, nhật ký thay đổi, lệnh có history công khai hoặc log.

## Callback

Direct mode:

```text
https://<domain>/messenger-<code>/webhook/facebook
```

Dispatcher mode:

```text
https://<domain>/<shared-callback>/webhook/facebook
```

Trước khi bấm Verify trong Meta:

- Bot/dispatcher service active.
- Nginx route đúng và `nginx -t` đạt.
- HTTPS callback truy cập được.
- GET verification trả đúng challenge khi token khớp.
- Không log verify token.

## Webhook Fields

Chỉ subscribe các field cần cho code hiện tại. Tối thiểu phải có:

- Tin nhắn khách hàng để bot nhận câu hỏi.
- `message_echoes` để phát hiện nhân viên/Page trả lời và auto-pause bot.

Nếu code xử lý postback hoặc event khác, thêm đúng field tương ứng và bổ sung unit test. Không subscribe rộng chỉ vì tiện.

## Page Subscription

- Kết nối đúng Page với đúng App.
- Xác nhận Page ID trong `.env` khớp Page đã subscribe.
- Nếu dùng dispatcher, restart dispatcher sau khi nhập Page ID để reload route.
- Không bật bot khi route đang rơi vào `DEFAULT_TARGET` do thiếu Page ID.

## App Mode And Permissions

- Dùng tài khoản test/Page role khi app chưa production-ready.
- Trước khi phục vụ người dùng ngoài role/tester, xác nhận app mode và quyền Messenger/Page cần thiết đã được Meta chấp thuận cho phạm vi sử dụng.
- Không suy đoán quyền hiện hành; kiểm tra trực tiếp trong Meta Developer tại thời điểm triển khai.

## Verification Without Live Reply

1. Unit test signature validation.
2. Local GET verify test, token chỉ đọc trong process và không print.
3. Local signed POST với payload giả.
4. Human echo simulation bằng PSID giả.
5. Health check bot và dispatcher.
6. AI smoke test gọi `answer_question()` trực tiếp, không gọi Meta Send API.
7. Chỉ sau khi mọi bước đạt mới xin phê duyệt gửi một tin test thật.

## Go-Live Checklist

- [ ] Page ID/App ID/token thuộc đúng Fanpage và Meta App.
- [ ] Callback URL đúng mode đã chọn.
- [ ] Verify callback thành công.
- [ ] Message field và `message_echoes` đã subscribe.
- [ ] Bot echo không tạo human pause giả.
- [ ] Human reply tạo pause đúng thời gian.
- [ ] OpenClaw agent trả lời đúng dữ liệu Fanpage mới.
- [ ] Fallback không lộ tên provider hoặc thông tin nội bộ cho khách.
- [ ] Lịch sử dùng mã khách ẩn danh, không lưu PSID thật.
- [ ] Service tự khởi động lại và health ổn định.
- [ ] Project-specific skill, registry và changelog đã cập nhật.

