---
name: openclaw-python-docx-telegram
description: Create and deliver Vietnamese DOCX reports from OpenClaw Telegram using the member document Python environment. Use when a Telegram requester asks for a Word report, a formatted DOCX attachment, or a rerender of a report based on chat/file data.
---

# OpenClaw Python DOCX + Telegram

## Khi nào dùng

- Khi người dùng yêu cầu xuất báo cáo Word/DOCX.
- Khi đã có dữ liệu trong phiên chat hoặc file PDF/XLSX và cần tạo tệp đính kèm.
- Khi cần gửi lại một DOCX đã tạo nhưng lần trước chỉ trả lời bằng văn bản.

## Thành phần

- Python environment: `/root/.openclaw/tools/document-venv`
- Script: `/root/.openclaw/workspace/skills/openclaw-python-docx-telegram/scripts/create_docx_report.py`
- Input: JSON UTF-8 do agent tạo trong workspace, gồm `title`, `subtitle`, `metadata`, `sections`, `tables`, `footer`.
- Output: DOCX trung gian trong workspace; bản gửi Telegram nên stage tại `/root/.openclaw/media/outbound/`.

## Quy trình

1. Đọc dữ liệu nguồn trong phiên hiện tại; không đoán số liệu chưa có.
2. Tạo một file JSON tạm trong workspace với nội dung báo cáo.
3. Chạy dry-run:

```bash
/root/.openclaw/tools/document-venv/bin/python \
  /root/.openclaw/workspace/skills/openclaw-python-docx-telegram/scripts/create_docx_report.py \
  --input-json /root/.openclaw/workspace/reports/report.json \
  --output /root/.openclaw/workspace/reports/report.docx \
  --dry-run
```

4. Chạy thật bằng cùng lệnh, bỏ `--dry-run`.
5. Kiểm tra JSON kết quả báo `valid=true`; nếu có thể, mở/preview DOCX hoặc kiểm tra ZIP structure trước khi gửi.
6. Với member Docker, copy file hợp lệ vào `/root/.openclaw/media/outbound/` và dùng đường dẫn bên trong container khi gửi:

```bash
mkdir -p /root/.openclaw/media/outbound
cp /root/.openclaw/workspace/reports/report.docx /root/.openclaw/media/outbound/report.docx
```

7. Không truyền đường dẫn host như `/root/Apps/member_vps/docker-users/data/<member>/...` vào `message`; đường dẫn đó không tồn tại bên trong member container.
8. Gửi nội dung hoàn tất và tệp bằng công cụ `message` tới đúng Telegram chat/group/thread của request hiện tại. Không đoán target từ owner mặc định.
9. Chỉ coi là đã gửi khi công cụ trả `messageId` và metadata đích khớp; sau đó không gửi thêm tin trùng.

## Rerun/rerender

- Giữ file JSON đầu vào để có thể rerender cùng nội dung.
- Dùng tên output mới hoặc ghi đè có chủ đích sau khi kiểm tra file đích thuộc request hiện tại.
- Không xóa file nguồn hoặc transcript; không dùng dữ liệu của chat khác.

## An toàn

- Không ghi token, API key, cookie, mật khẩu, private key hoặc ID đích riêng tư vào JSON, skill, log hay báo cáo vận hành.
- Chỉ tạo file trong workspace được cấp; không sửa `.env` hoặc credential.
- Kiểm tra `unzip -tqq`/khả năng đọc trước khi copy sang `media/outbound`; chỉ gửi path member-visible, không gửi path host.
- Nếu vẫn gặp `LocalMediaAccessError`, chạy skill `openclaw-member-media-allowlist` để kiểm tra member/container path và policy trước khi sửa Telegram root.
- `exec` và `message` chỉ được dùng để hoàn thành yêu cầu DOCX; giữ nguyên các deny policy còn lại cho sender không được cấp quyền.
- Với file lỗi hoặc receipt gửi không rõ ràng, không tuyên bố đã giao; kiểm tra lại rồi retry tối đa một lần khi an toàn.
