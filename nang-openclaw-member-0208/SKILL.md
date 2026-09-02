---
name: "nang-openclaw-member-0208"
description: "Nâng OpenClaw member lên 02.08, migrate an toàn và kiểm tra Telegram/Zalo."
---

# Nâng OpenClaw Member 02.08

Nâng OpenClaw trong Docker member VPS lên bản stable 02.08 (2026.8.2), bảo toàn cấu hình và xác nhận Telegram Bot cùng Zalo Personal hoạt động.

## Quy trình

1. Xác định đúng member, container, thư mục bind mount và cơ chế quản lý Gateway; hoàn tất khi không nhầm sang member khác.
2. Đọc `AGENTS.md`, tài liệu vận hành, project note và checklist production của member; hoàn tất khi biết các file cần giữ nguyên và các kiểm tra hậu nâng.
3. Chạy preflight chỉ đọc: `openclaw --version`, `openclaw update status --json`, `openclaw config validate`, agent bindings, `channels status --channel telegram --probe --json`, và `channels status --channel zalouser --probe --json`; ghi lại bản cũ và trạng thái kênh nhưng không ghi secret.
4. Tạo backup có timestamp trước lần ghi đầu tiên; sao lưu `openclaw.json`, bản last-good/pre-update nếu có, SQLite cùng WAL/SHM companions, entrypoint và cấu hình process manager. Đặt quyền chỉ owner đọc/ghi và không sao chép token/credential vào tài liệu.
5. Dừng đúng một Gateway theo process manager thực tế và xác nhận Gateway đã dừng; không gọi Telegram `getUpdates` khi Gateway còn chạy.
6. Dùng updater chính thức với target `2026.8.2`, `--no-restart --yes --json`; chỉ dùng npm reinstall khi updater thất bại hoặc package integrity bị hỏng. Xác nhận output có `before` và `after` đúng target.
7. Cho chạy migration/doctor hậu nâng theo lệnh chính thức; xem kỹ các thay đổi. Nếu Zalo Personal credential được migrate, giữ lại archive do doctor tạo và không sửa credential thủ công. Nếu plugin Zalo báo thiếu capability consent sau khi đồng bộ phiên bản, chạy `openclaw plugins enable zalouser --accept-capabilities`, rồi xác nhận plugin vẫn enabled và không còn cảnh báo consent.
8. Khởi động lại đúng một Gateway bằng cơ chế quản lý hiện hữu sau mọi thay đổi plugin; xác nhận chỉ có một process Gateway, listening đúng port và không phát sinh process chạy tay thứ hai.
9. Chạy acceptance: phiên bản 2026.8.2, config valid, gateway status connectivity probe OK, Telegram account configured/running/connected/probe OK/polling/no error, Zalo Personal configured/linked/running/connected/probe OK/no error. Kiểm tra log sau thời điểm nâng không có 409 Conflict, package import error, tombstone hoặc dispatch failure.
10. Ghi nhật ký thay đổi đã loại bỏ secret, nêu member, phiên bản cũ/mới, backup, migration và trạng thái các kênh. Chỉ kết luận gửi/nhận tin thật thành công khi có kiểm thử tin nhắn được ủy quyền và bằng chứng message/event tương ứng.

## An toàn

- Không in hoặc lưu bot token, API key, cookie, mật khẩu, private key, nội dung tin nhắn.
- Không xóa toàn bộ sessions/database để sửa một lỗi; chỉ dùng lifecycle command chính thức cho session cụ thể khi có bằng chứng.
- Không thay đổi model/provider, routing, workspace, credential hoặc bind network nếu không thuộc nguyên nhân đã chứng minh.
- Nếu process manager không quản lý Gateway (ví dụ Gateway đang chạy trong tmux), ghi rõ residual risk và không tự chuyển sang Supervisor trong cùng lần nâng nếu chưa có kế hoạch riêng.

## Báo cáo

Báo cáo target container/member, old/new version, backup path, migration đã chạy, process manager/Gateway status, Telegram probe, Zalo probe, warning còn lại và giới hạn kiểm thử. Không báo cáo secret hoặc nội dung riêng tư.
