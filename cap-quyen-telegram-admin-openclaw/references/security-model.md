# Mô Hình Bảo Mật

## Bốn Lớp Quyền

1. Telegram DM access: `dmPolicy` và `allowFrom` quyết định sender có được nhận hay không.
2. Owner commands: `commands.ownerAllowFrom` quyết định quyền dùng lệnh owner-only.
3. Exec approvals: `channels.telegram.execApprovals.approvers` quyết định ai được duyệt lệnh cần approval.
4. Agent routing: direct peer binding quyết định DM của user đi vào agent nào và tool profile nào.

Một ID chỉ thực sự có quyền quản trị đầy đủ khi cả bốn lớp được cấu hình đồng bộ.

## Ranh Giới

- Chỉ dùng direct peer `kind: direct` với đúng Telegram user ID.
- Không dùng `allowFrom: ["*"]` cho DM.
- Không bind `owner-admin` vào group.
- Không đổi `tools.profile` toàn cục sang `full`; chỉ đặt profile trên agent admin riêng.
- Không tắt exec approvals. `auto` vẫn cho phép vận hành đầy đủ nhưng giữ điểm chặn đối với lệnh nhạy cảm.
- Nếu một peer đã bind tới agent khác, dừng để xác minh. Chỉ thay bằng `--replace-binding` sau khi người dùng đồng ý rõ.
- Khi thu hồi, xóa đồng bộ cả bốn lớp quyền và credential pairing liên quan.

## Kiểm Thử An Toàn

- Kiểm tra direct binding bằng `openclaw agents bindings` và che ID khác khi ghi log.
- Kiểm tra config bằng `openclaw config validate` sau khi source env provider.
- Kiểm tra Telegram bằng `openclaw channels status --probe`.
- Yêu cầu user nhắn DM và thử `id`, `pwd`, hoặc đọc trạng thái service trước.
- Không dùng lệnh xóa dữ liệu, restart VPS, thay firewall hoặc SSH để smoke test.
