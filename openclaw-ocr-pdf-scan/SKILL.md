---
name: openclaw-ocr-pdf-scan
description: Dùng khi bot OpenClaw của member báo "Request timed out" hoặc treo lâu lúc đọc file PDF scan/ảnh nhiều trang; OCR tiếng Việt bằng tesseract trên máy chủ rồi đưa văn bản cho bot làm tiếp, áp dụng mọi VPS.
---
# OCR file PDF scan cho member OpenClaw

Áp dụng cho member OpenClaw chạy trong container (`user-<member>`) trên bất kỳ VPS nào. Sao lưu trước khi sửa config, không in token/khóa, chỉ thao tác trên đúng container của member đó.

## 1. Xác nhận đúng bệnh
1. Đọc log gateway trong container: `/tmp/openclaw/openclaw-<YYYY-MM-DD>.log` quanh giờ lỗi (log ghi giờ UTC).
2. Dấu hiệu điển hình:
   - `Inbound message ... application/pdf` rồi `lastProgress=tool:pdf:started` lặp lại trong các dòng `stalled session`.
   - `embedded run timeout ... timeoutMs=<agents.defaults.timeoutSeconds × 1000>`.
   - Log proxy/9router cho thấy request vài MB tới combo vision, bị `client_closed` hoặc chạy nhiều phút.
3. Kiểm tra file: `pdfinfo <file>`. Creator kiểu "Scan", nhiều trang, không có lớp chữ thì là bản scan, nên OCR trước.
4. Ghi lại `sessionKey` (ví dụ `agent:main:telegram:direct:<chatId>`), account và chatId của người gửi.

## 2. Nới giới hạn (tùy chọn, nên làm)
- Sao lưu `/root/.openclaw/openclaw.json` ra thư mục backup có timestamp.
- `openclaw config set agents.defaults.timeoutSeconds 900`: hot reload, không cần restart. Nên khớp với timeout của proxy.
- Nếu log có `memory pressure` gần giới hạn: `docker update --memory <N>g --memory-swap <N+1>g user-<member>` (đổi ngay, không restart). Ghi giá trị cũ để rollback. Kiểm tra RAM máy còn dư trước.

## 3. OCR trên máy chủ
1. Cài một lần trên host (Debian/Ubuntu): `apt-get install -y tesseract-ocr tesseract-ocr-vie poppler-utils`. Kiểm tra: `tesseract --list-langs` có `vie`.
2. Lấy file từ container (file inbound thường nằm ở `/root/.openclaw/media/inbound/`):
   - `mkdir -p /root/_tmp_ocr_<member> && cd /root/_tmp_ocr_<member>`
   - `docker cp "user-<member>:<đường dẫn file>" in.pdf`
3. Render và OCR song song:
   - `pdftoppm -r 300 -gray -png in.pdf p`
   - `ls p-*.png | xargs -P 4 -I{} sh -c 'nice tesseract {} {}.out -l vie --psm 6 >/dev/null 2>&1'`
4. Ghép thành một file, có đánh dấu trang:
   - `: > text.txt; for f in $(ls p-*.png | sort -V); do n=$(echo $f | sed 's/p-0*//;s/.png//'); printf '\n===== Trang %s =====\n' $n >> text.txt; cat $f.out.txt >> text.txt; done`
5. Đọc lướt `text.txt` để chắc chắn chữ rõ. Nhớ các thông tin then chốt: số hiệu, ngày ban hành, cơ quan.
6. `docker cp text.txt user-<member>:/root/.openclaw/workspace/ocr_<tên-ngắn>.txt`

## 4. Cho bot làm tiếp trong đúng phiên
1. Trước tiên kiểm tra phiên còn đang chạy ngầm không: tìm `stalled session` mới, và đọc tin cuối trong `session_transcript_fts` của `/root/.openclaw/agents/main/agent/openclaw-agent.sqlite` (mở read-only). Lượt bị báo timeout ở CLI vẫn có thể đang chạy tiếp và đã gửi kết quả. Đừng chồng thêm lượt mới khi lượt cũ chưa xong.
2. Viết chỉ dẫn vào một file (ví dụ `/tmp/resume.txt` trong container). Nội dung: có bản OCR tại `<đường dẫn>`, không dùng công cụ đọc PDF/ảnh nữa; nêu các dữ kiện đã xác nhận (ví dụ ngày ban hành); chỗ OCR không chắc thì ghi chú, không suy đoán; hoàn tất đúng việc người dùng đã yêu cầu ban đầu (xem transcript) và gửi kết quả cho họ.
3. Chạy nền (có thể mất vài phút):
   `docker exec user-<member> openclaw agent --session-key <sessionKey> --message-file /tmp/resume.txt --deliver --reply-channel <telegram|zalouser> --reply-account <accountId> --reply-to <chatId> --timeout 900`
4. Xác minh qua log: `telegram outbound send ok ... operation=sendDocument` (hoặc sendMessage), hoặc dòng tương ứng của kênh khác.

## 5. Báo cho người dùng cuối (chỉ khi owner yêu cầu)
- Gửi qua chính bot: `openclaw message send --channel <kênh> --account <accountId> --target <chatId> --message "..."`.
- Nội dung nên có: xin lỗi vì đợi lâu, giải thích ngắn đang làm gì (đang chuyển bản scan thành văn bản), dặn không cần gửi lại file. Duyệt nội dung với owner trước khi gửi, trừ khi owner đã bảo gửi.

## Ghi chú
- Với bản scan, model vision đọc ảnh mất nhiều phút, mỗi request 3–7 MB. Còn tesseract chỉ mất khoảng 2–3 phút cho 12 trang trên 4 luồng, và bot xử lý văn bản trong vài phút.
- Thư mục `/root/_tmp_ocr_<member>` có thể xóa sau khi xong.
- Rollback: chép lại config backup (hoặc đặt lại timeoutSeconds cũ), chạy `docker update` với giá trị RAM cũ.
