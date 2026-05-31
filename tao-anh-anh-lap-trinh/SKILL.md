---
name: tao-anh-anh-lap-trinh
description: Tạo hình ảnh quảng bá vuông theo phong cách Anh Lập Trình cho bài Facebook, Zalo, landing page, khóa học, AI, automation, Python, OpenClaw, Zalo workflow, hoặc công cụ làm việc. Use when Codex needs to generate a square promotional image quickly with fully accented Vietnamese text under 50 words, no spelling mistakes, practical "Anh Lập Trình" visual tone, and the default logo D:\00.Demo\54.Demo3In1\logo3.png attached to the final output.
---

# Tạo Ảnh Anh Lập Trình

## Mục Tiêu

Tạo ảnh vuông tỷ lệ 1:1, dùng cho bài Facebook, Zalo, quảng bá khóa học, chia sẻ công cụ AI/automation, và các nội dung của Anh Lập Trình. Ảnh phải thực tế, rõ thông điệp, ít chữ, đúng chính tả tiếng Việt, và có cảm giác "ứng dụng vào công việc ngay".

## Logo Mặc Định

Luôn gắn logo mặc định vào ảnh mỗi lần tạo:

```text
D:\00.Demo\54.Demo3In1\logo3.png
```

Logo này cũng đã được đóng gói trong skill tại:

```text
assets/anh_lap_trinh_logo.png
```

Khi chạy `scripts/compose_square_post.py`, nếu không truyền `--logo`, script sẽ tự ưu tiên `D:\00.Demo\54.Demo3In1\logo3.png`. Nếu file ngoài không tồn tại, script dùng bản logo trong `assets/anh_lap_trinh_logo.png`.

## Quy Trình Nhanh

Mặc định dùng quy trình này để tạo nhanh và tránh lỗi chữ tiếng Việt:

1. Rút nội dung dài thành 3 dòng chữ ngắn: headline, subheadline, badge/CTA.
2. Kiểm tra tổng chữ dưới 50 từ, tiếng Việt có dấu đầy đủ, đúng chính tả.
3. Dùng `image_gen` tạo ảnh nền vuông 1:1, không có chữ đọc được.
4. Chạy `scripts/compose_square_post.py` để chèn chữ tiếng Việt và gắn logo mặc định.
5. Mở ảnh bằng `view_image` kiểm tra lần cuối: chữ đúng dấu, không sai chính tả, ảnh vuông, logo không che nội dung.
6. Nếu nền có chữ thừa do image model sinh ra, tạo lại nền với prompt có câu `NO READABLE TEXT anywhere`.

## Chữ Trên Ảnh

Giới hạn cứng: dưới 50 từ tiếng Việt trên toàn bộ ảnh.

Yêu cầu bắt buộc:

- Chữ trên ảnh phải là tiếng Việt có dấu đầy đủ.
- Không dùng text không dấu như `Nhan mot cau`, `may chu`, `bao cao`.
- Không sai chính tả, không thiếu dấu câu quan trọng.
- Không để image model tự bịa thêm chữ ở dashboard, file, nút bấm, biểu đồ, chat bubble.
- Nếu chữ sai, phải sửa bằng script hoặc tạo lại, không giao ảnh sai chữ cho người dùng.

Công thức ưu tiên:

```text
Headline: 3-7 từ
Subheadline: 8-18 từ
Badge/CTA: 3-8 từ
```

Ví dụ:

```text
ZALO NGẬP VIỆC?
Để trợ lý thông minh gom việc, hẹn lịch, cập nhật bảng biểu
Học thực chiến cùng Anh Lập Trình
```

## Prompt Nền Không Chữ

Dùng prompt tiếng Anh để tạo nền, không yêu cầu model viết chữ:

```text
Square 1:1 promotional background image in Anh Lap Trinh practical tech style, NO READABLE TEXT anywhere. Visual theme: [describe the user's topic]. Show practical office automation, laptop/dashboard, AI assistant, workflow arrows, spreadsheet/calendar/chat elements, security or confirmation icons if relevant. Clean bright modern professional design, balanced blue green white dark gray with small yellow accents, uncluttered. Leave open clean space in upper-left for headline text overlay and clean space at bottom-right for logo overlay. High quality Facebook square post design. No letters, no words, no labels, no fake text.
```

## Chèn Chữ Và Logo

Sau khi có ảnh nền, dùng script nhanh. Không cần truyền `--logo` nếu muốn dùng logo mặc định `logo3.png`:

```powershell
python C:\Users\nhuan\.codex\skills\tao-anh-anh-lap-trinh\scripts\compose_square_post.py --input <background.png> --output <workspace-output.png> --headline "TRỢ LÝ AI QUA ZALO" --subheadline "Nhắn một câu, máy chủ tự gom báo cáo" --badge "Làm việc thật"
```

Tùy chọn:

```powershell
python C:\Users\nhuan\.codex\skills\tao-anh-anh-lap-trinh\scripts\compose_square_post.py --input in.png --output out.png --headline "..." --subheadline "..." --badge "..." --logo-scale 0.18 --theme ai
```

Script mặc định:

- Ép ảnh về vuông 1080x1080.
- Chèn chữ bằng font Arial Bold hỗ trợ tiếng Việt.
- Thêm lớp nền mờ phía sau chữ để dễ đọc.
- Gắn logo mặc định `D:\00.Demo\54.Demo3In1\logo3.png`, hoặc bản logo trong `assets/anh_lap_trinh_logo.png` nếu file ngoài không có.
- Giữ ảnh gốc, chỉ tạo file mới.

## Phong Cách Hình Ảnh

- Thực chiến, sáng, hiện đại, gần với công việc văn phòng và tự động hóa.
- Nên có màn hình máy tính, workflow, bảng biểu, lịch hẹn, tin nhắn, AI assistant, hoặc người thật đang làm việc.
- Màu sắc cân bằng: xanh dương, xanh lá, trắng, đen/xám đậm, điểm vàng/cam nhỏ. Tránh để ảnh bị một màu.
- Typography to, rõ, đọc được trên điện thoại.
- Không nhồi nhiều icon, không dùng chữ nhỏ li ti, không tạo cảm giác poster dày đặc.
- Nếu nhắc đến nền tảng như Zalo, Facebook, Google Sheets, chỉ dùng biểu tượng chat/bảng biểu chung; tránh copy logo thương hiệu nếu không có file chính thức.

## Kiểm Tra Chất Lượng

Trước khi trả lời người dùng, kiểm tra ảnh bằng mắt:

- Ảnh có đúng vuông 1:1 không?
- Chữ có đúng tiếng Việt có dấu không?
- Có lỗi chính tả hoặc thiếu dấu không?
- Có chữ thừa hoặc chữ giả nhìn như chữ thật không?
- Logo `logo3.png` có xuất hiện và không che nội dung chính không?

Nếu có lỗi chữ, sửa bằng `compose_square_post.py` hoặc tạo lại nền không chữ rồi chèn chữ lại.
