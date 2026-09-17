---
name: openclaw-docx-reader
description: Đọc và trích xuất nội dung Word .docx/.docm nhận từ Telegram trong OpenClaw member Docker khi bộ tiền xử lý báo Unsupported document format. Dùng để đọc cục bộ, không tải tài liệu ra ngoài.
---

# OpenClaw DOCX reader

## Khi nào dùng

- Khi group Telegram gửi `.docx`, `.docm`, `.dotx` hoặc `.dotm` và OpenClaw báo `Unsupported document format`.
- Khi cần lấy toàn văn Word để dịch, tóm tắt, biên tập hoặc kiểm tra số liệu.
- Không dùng để tự động đọc file của chat khác; phải ghép đúng tên file với attachment của lượt hiện tại.

## Đường dẫn và script

- Inbound Telegram của member có HOME `/root`: `/root/.openclaw/media/inbound/`.
- Script dùng chung (được mount read-only vào container): `/root/.agents/skills/openclaw-docx-reader/scripts/read_word.py`.
- Script chỉ đọc OOXML, không gọi API, không gửi file, không xóa nguồn.

## Cách chạy

Nếu prompt có đường dẫn attachment:

```bash
python3 /root/.agents/skills/openclaw-docx-reader/scripts/read_word.py \
  --input "/root/.openclaw/media/inbound/<file>.docx" \
  --output "/root/.openclaw/workspace/tmp/docx-reading/<file>.txt" --json
```

Nếu prompt chỉ có tên file:

```bash
python3 /root/.agents/skills/openclaw-docx-reader/scripts/read_word.py \
  --name "<tên file Telegram>" \
  --inbound-dir /root/.openclaw/media/inbound \
  --output /root/.openclaw/workspace/tmp/docx-reading/current.txt --json
```

Nếu lượt hiện tại có nhiều Word, chạy từng tên và dùng output riêng. `--name` chọn bản khớp mới nhất; nếu không khớp thì dừng, không tự lấy một file cũ.

## Dry-run / kiểm tra

```bash
python3 /root/.agents/skills/openclaw-docx-reader/scripts/read_word.py \
  --input "/root/.openclaw/media/inbound/<file>.docx" --json > /tmp/docx-preview.txt
```

Script tự kiểm tra cấu trúc ZIP/CRC và giới hạn kích thước trước khi trích xuất; không cần cài `unzip` trong container.

## Kết quả và giới hạn

- Nội dung chính, bảng, đầu/chân trang, footnote/endnote và comment được đưa vào text UTF-8.
- Giữ tab trong bảng và xuống dòng; không đảm bảo bố cục Word, biểu đồ hoặc ảnh được diễn giải.
- `.doc` đời cũ chỉ đọc được nếu container có `antiword`; nếu không, yêu cầu người dùng gửi `.docx` hoặc PDF.
- Giới hạn mặc định: file 25 MB, tổng dữ liệu giải nén 150 MB, text 2 triệu ký tự.
- Chỉ dùng text đã trích xuất làm nguồn; không suy diễn số liệu bị thiếu. Đánh dấu phần cần kiểm chứng trong bản dịch.

## An toàn

- Không in token, cookie, mật khẩu, credential hoặc nội dung sang log vận hành.
- Không truyền đường dẫn host `/root/Apps/member_vps/...` vào công cụ Telegram; đây là đường dẫn host, không phải đường dẫn member-visible.
- Không gửi lại nội dung/file vào group nếu người dùng chưa yêu cầu rõ.
- Sau khi đọc xong, giữ file nguồn; không xóa tự động.
