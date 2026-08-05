---
name: tao-ebook-chia-se-alt
description: Tạo ebook chia sẻ cộng đồng theo chuẩn Anh Lập Trình/ALT, gồm nội dung Markdown dễ hiểu cho người mới, logo bo tròn, hình minh họa hoặc mô phỏng màn hình, script xuất PDF và file PDF cuối trong /root/Second_Brain/07_ebook_chia_se. Use when Codex is asked to tạo ebook, viết ebook, xuất PDF ebook, làm tài liệu chia sẻ, hướng dẫn cài đặt/cách dùng công cụ, hoặc tạo ebook ngắn 5-10 trang cho cộng đồng theo giọng Anh Lập Trình.
---

# Tao Ebook Chia Se ALT

## Muc Tieu

Tạo ebook thực chiến để người chưa biết gì vẫn làm theo được. Mỗi ebook phải có bản Markdown nguồn, tài nguyên minh họa, script xuất PDF, và PDF cuối. Giọng văn dùng phong cách Anh Lập Trình: rõ, gần gũi, thực tế, làm được việc thật.

Khẩu hiệu bắt buộc xuất hiện ở bìa hoặc lời kết:

```text
Cứ ứng dụng vào công việc đi, vướng đâu gỡ đó.
```

## Thu Muc Mac Dinh

Vault ebook:

```text
/root/Second_Brain/07_ebook_chia_se
```

Cấu trúc dùng khi tạo ebook mới:

```text
02_dang_viet/yyyy_mm_dd_ten_chu_de/
├── 00_ebook_ten_chu_de.md
├── ebook_spec.json
├── assets/
│   ├── logo_anh_lap_trinh.png
│   └── logo_anh_lap_trinh_bo_tron.png
└── scripts/
    └── export_pdf.py

04_pdf_da_xuat/yyyy_mm_dd_ten_chu_de.pdf
```

Logo nguồn ưu tiên:

```text
/root/Second_Brain/07_ebook_chia_se/05_tai_nguyen_chung/logo/logo_anh_lap_trinh.png
```

Nếu không có, tìm logo Anh Lập Trình trong các project liên quan trước khi tự tạo placeholder.

## Workflow

1. Xác định chủ đề, độc giả, độ dài PDF mong muốn. Nếu user không nói, mặc định 5-10 trang A4.
2. Nếu chủ đề là công cụ/phần mềm/quy định có thể thay đổi, kiểm tra nguồn chính thức hoặc nguồn hiện hành trước khi viết.
3. Tạo folder ebook trong `02_dang_viet` theo chuẩn tên `yyyy_mm_dd_ten_chu_de`.
4. Viết Markdown nguồn: dễ hiểu, từng bước, không viết kiểu mỗi câu một dòng như Facebook.
5. Tạo ảnh minh họa hoặc mô phỏng màn hình cho từng bước quan trọng. Nếu ảnh không phải screenshot thật, ghi rõ là minh họa mô phỏng.
6. Copy logo vào `assets/`, tạo bản logo bo tròn, rồi dùng trên bìa PDF.
7. Tạo `ebook_spec.json` và dùng script `scripts/export_step_ebook_pdf.py` của skill này, hoặc copy script vào ebook nếu cần chỉnh riêng.
8. Xuất PDF vào cả folder ebook và `04_pdf_da_xuat`.
9. Kiểm tra PDF: số trang, font tiếng Việt, logo, bố cục, link/nguồn, và đọc lướt text bằng `pypdf`.
10. Cập nhật `01_y_tuong_ebook/00_danh_sach_y_tuong.md` sang trạng thái đã xuất PDF nếu có dòng tương ứng.

## Chuan Noi Dung

Mỗi ebook nên có:

- Bìa: tên ebook, logo bo tròn, tác giả, phiên bản, khẩu hiệu.
- Trang chuẩn bị: người đọc cần máy/tài khoản/file gì.
- Hướng dẫn từng bước: mỗi bước nói rõ mở gì, bấm gì, chọn gì, kết quả mong đợi là gì.
- Minh họa: sơ đồ, bảng, terminal giả lập, trình duyệt giả lập, hoặc screenshot thật nếu có.
- Lỗi thường gặp: lỗi, nguyên nhân, cách gỡ.
- Checklist hoàn thành.
- Trang tóm tắt cuối: làm theo thứ tự nào.

Nguyên tắc viết:

- Viết cho người mới hoàn toàn.
- Tránh thuật ngữ nếu chưa giải thích.
- Đừng nói chung chung kiểu "cài như bình thường"; phải nói từng bước.
- Với công cụ thay đổi giao diện, dùng câu: "Ảnh là minh họa mô phỏng, giao diện thật có thể thay đổi nhẹ theo phiên bản."
- Không đưa API key, token, email thật, thông tin đăng nhập thật, cookie, profile trình duyệt vào ebook.

## Xuat PDF

Script helper:

```bash
python3 /root/.agents/skills/tao-ebook-chia-se-alt/scripts/export_step_ebook_pdf.py \
  --spec /duong/dan/ebook_spec.json \
  --output /duong/dan/file.pdf
```

`ebook_spec.json` tối thiểu:

```json
{
  "title": "Cài Đặt Antigravity",
  "kicker": "Ebook cầm tay chỉ việc",
  "subtitle": "Dành cho người chưa biết gì vẫn làm theo được.",
  "author": "Nguyễn Văn Nhuần - Anh Lập Trình",
  "version": "2026_06_22",
  "logo": "assets/logo_anh_lap_trinh.png",
  "slogan": "Cứ ứng dụng vào công việc đi, vướng đâu gỡ đó.",
  "pages": [
    {
      "heading": "Trước khi cài, chuẩn bị 3 thứ",
      "paragraphs": ["Nội dung hướng dẫn..."],
      "cards": [
        {"title": "Máy của bạn", "body": "Windows, macOS hay Linux?"}
      ]
    }
  ]
}
```

Các page block được hỗ trợ: `paragraphs`, `cards`, `steps`, `checklist`, `terminal`, `browser_mockup`, `table`, `note`.

## Kiem Tra

Sau khi xuất PDF, chạy:

```bash
pdfinfo output.pdf | sed -n '1,24p'
python3 - <<'PY'
from pypdf import PdfReader
r = PdfReader("output.pdf")
print("pages", len(r.pages))
for i, p in enumerate(r.pages, 1):
    print(i, (p.extract_text() or "")[:180].replace("\n", " | "))
PY
```

Nếu có `pdftoppm`, render 1-3 trang đầu để xem trực quan:

```bash
pdftoppm -png -f 1 -l 3 output.pdf /tmp/ebook_preview
```

## Khi Bao Cao Ket Qua

Trả lời ngắn gọn:

- Đường dẫn PDF cuối.
- Đường dẫn folder nguồn.
- Số trang.
- Đã kiểm tra những gì.

