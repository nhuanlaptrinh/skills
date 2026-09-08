---
name: "zalo-reliable-task-delivery"
description: "Phản hồi sớm, giới hạn câu trả lời, tách việc nặng, kiểm tra file và bàn giao ổn định trên Zalo."
---

# Zalo Reliable Task Delivery

## Phản hồi sớm

- Nếu công việc có khả năng lâu hơn 10 giây, trả lời xác nhận ngay trước khi gọi tool.
- Nêu ngắn gọn đã nhận việc và sẽ báo khi hoàn tất; không hứa thời gian chính xác khi chưa biết.
- Nếu sau 120 giây chưa xong, gửi một cập nhật tiến độ ngắn thay vì im lặng.
- Khi tool chính thất bại và phải chuyển phương án, báo đang thử phương án dự phòng.

## Giới hạn phản hồi Zalo

- Câu trả lời thông thường tối đa 1.800 ký tự; ưu tiên 1.200-1.600 ký tự.
- Nếu nội dung dài hơn, gửi kết luận/tóm tắt trước rồi hỏi người dùng có cần phần chi tiết hay không.
- Báo cáo, log hoặc hướng dẫn dài phải ưu tiên lưu thành file và gửi file thay vì dồn thành nhiều tin.
- Không gửi quá 3 đoạn văn bản dài liên tiếp nếu người dùng không yêu cầu rõ nội dung đầy đủ trong chat.
- Không đưa log thô, HTML, JSON hoặc kết quả tool dài vào Zalo.

## Tách tác vụ nặng

- Tạo ảnh/video, đọc PDF dài, làm Excel nhiều trang, tải web hàng loạt và tác vụ trên 2 phút phải ưu tiên `sessions_spawn`.
- Session chính giữ vai trò nhận yêu cầu, thông báo tiến độ và bàn giao.
- Worker ghi kết quả vào đúng `customers/<channel>__<group-id>/output/` hoặc workspace direct tương ứng.
- Dùng `sessions_yield` để chờ worker; không phụ thuộc `sessions_send` khi tool này chưa ổn định.

## Kiểm tra file trước khi gửi

- Chạy `/home/anhlaptrinh/.openclaw/tools/document-venv/bin/python /home/anhlaptrinh/.openclaw/workspace/tools/validate_zalo_file.py <file>`.
- Không gửi file thiếu, rỗng hoặc XLSX hỏng cấu trúc.
- File lớn hơn 8 MB phải tạo thêm bản nhẹ cho điện thoại nếu có thể.
- Chỉ nói “đã gửi” sau khi file đã được kiểm tra.

## Session dài

- Với session context 64.000 token, compact/rotate từ khoảng 18.000-20.000 token.
- Với session context 128.000 token, compact/rotate từ khoảng 40.000 token.
- Nếu compact timeout hoặc lặp lại lỗi context, lưu thông tin cần thiết rồi dùng session mới.

## Vận hành

- Dry-run session: `bash /root/Automation/openclaw_member_assistant/scripts/audit_member_sessions.sh user-<member>`
- Chạy thật: `SESSION_PATTERN='agent:main:zalouser:' TOKEN_THRESHOLD_64K=18000 TOKEN_THRESHOLD_128K=40000 SESSION_IDLE_SECONDS=600 MAX_COMPACTIONS_PER_RUN=5 bash /root/Automation/openclaw_member_assistant/scripts/audit_member_sessions.sh user-<member> --apply`
- Dry-run patch gửi tin: `bash /root/Automation/openclaw_member_assistant/scripts/patch_zalouser_send_reliability.sh`
- Apply patch gửi tin: `MEMBER_DATA_DIR=/root/Apps/member_vps/docker-users/data/<member> bash /root/Automation/openclaw_member_assistant/scripts/patch_zalouser_send_reliability.sh --apply`

## An toàn

- Không gửi tin test thật khi chưa được phép.
- Backup config, plugin bundle, session index và cron trước khi sửa production.
- Không ghi token, cookie, mật khẩu hoặc nội dung credential vào skill/log.
- Không xóa transcript; compact hoặc reset có backup.

## Gửi file Zalo: chống treo upload

- Trước khi gửi DOCX/PDF/ZIP/video, kiểm tra file tồn tại, đọc được và đúng nội dung.
- Dùng đường gửi native của Gateway; nếu đường dẫn workspace bị policy từ chối,
  dùng Gateway buffer, không nới allowlist tùy tiện và không chạy thêm một Zalo
  login context.
- Nếu tool bị timeout hoặc hiện `blocked_tool_call`, không khẳng định đã gửi và
  không gửi lặp ngay. Kiểm tra receipt, delivery queue và lịch sử trước.
- Không replay mục `send_attempt_started` khi chưa biết nền tảng đã nhận hay chưa.
  Backup SQLite/WAL/SHM trước khi chuyển mục mồ côi sang terminal failure.
- Plugin phải có timeout chờ callback upload (mục tiêu 60 giây), dọn callback khi
  timeout, bắt lỗi checksum/read và xử lý callback `file_done` đến sớm.
- Chỉ trả lời “đã gửi” khi có platform `messageId` đúng người/group; gửi thành
  công xong kết thúc bằng `NO_REPLY`.
