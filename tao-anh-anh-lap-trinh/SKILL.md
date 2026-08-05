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

## Checklist Chống Lỗi Bố Cục Và Chữ Tràn

Áp dụng checklist này trước khi gửi ảnh final, nhất là khi có ảnh người thật, nhiều khung chữ, logo hoặc CTA:

### 1. Đúng yêu cầu loại bỏ nội dung

- Nếu người dùng yêu cầu bỏ một chữ/cụm chữ cụ thể như `OPLW`, `website`, `link`, `giá`, `hôm nay` thì phải kiểm tra toàn ảnh và bảo đảm không còn xuất hiện.
- Nếu người dùng yêu cầu không cần link website, không được để URL, domain, QR, hoặc chữ gợi ý truy cập website.
- Nếu vẫn cần tên khóa/brand, ưu tiên dùng ngắn gọn: `Khóa học OpenClaw`, `Học OpenClaw`, hoặc `Học thực chiến cùng Anh Lập Trình`.

### 2. Safe area và chống tràn khung

- Chừa tối thiểu 50 px lề an toàn quanh ảnh 1080x1080.
- Chừa tối thiểu 24 px padding bên trong mỗi box chữ.
- Không để chữ chạm viền box, chạm mép ảnh, nằm sát ảnh người, hoặc sát logo.
- Không để badge/CTA lấn ra khỏi panel chính; nếu dùng nhiều dòng, giảm font hoặc tăng chiều cao box.
- Mọi khung chữ phải có khoảng thở rõ ràng ở trên/dưới/trái/phải.
- Tránh đặt text ở vùng có ảnh người, logo, biểu đồ, laptop hoặc icon nổi; nếu bắt buộc, thêm nền đủ tương phản.

### 3. Đọc được trên điện thoại

- Headline: thường 60-76 px ở ảnh 1080x1080.
- Dòng phụ/CTA: tối thiểu 24-30 px.
- Bullet nhỏ: tối thiểu 20-24 px, không dùng chữ mảnh trên nền sáng.
- Không dùng quá 3 bullet chính nếu ảnh đã có ảnh người thật.
- Mỗi bullet nên có một tiêu đề ngắn + một dòng mô tả ngắn, không quá 45 ký tự mỗi dòng.

### 4. Ảnh người thật

- Crop ảnh người gọn, ưu tiên thấy mặt + laptop/công cụ làm việc, tránh nhiều trần/tường trống.
- Nếu nền ảnh gốc có dây điện, ly, vật thừa, hoặc rèm rối thì crop/che bớt bằng khung bo góc, shadow nhẹ, hoặc overlay màu dịu.
- Không để ảnh người che chữ, và không để chữ đè lên mặt/người.
- Khung ảnh người nên có border mỏng và shadow mềm để nhìn chuyên nghiệp.

### 5. Màu sắc đề xuất cho ảnh OpenClaw/AI/Zalo

Ưu tiên palette hấp dẫn nhưng vẫn sạch:

- Nền chính: navy / xanh đậm `#061A33`, `#082B55`.
- Màu hành động: xanh lá AI `#35E096`, `#2EC66D`.
- Màu nhấn: vàng/cam `#FFD54A`, `#FFB72E`.
- Màu phụ: xanh Zalo/tech `#0078FF`, cyan `#00B8E6`.
- Nền card: trắng ngà `#F8FCFF` hoặc navy đậm, không dùng quá nhiều màu bão hòa cùng lúc.

Quy tắc phối màu:

- Một ảnh chỉ nên có 1 nền chính + 2 màu nhấn.
- Headline nên dùng trắng/vàng trên nền xanh đậm.
- CTA nên dùng xanh lá hoặc xanh dương, không dùng hai CTA quá nổi ngang nhau.
- Logo cần có nền trắng hoặc khoảng trống đủ sáng để nhận diện.

### 6. Checklist kiểm ảnh bằng mắt/vision trước khi gửi

Bắt buộc kiểm tra final bằng mắt hoặc công cụ vision với các câu hỏi:

- Có còn chữ/cụm chữ người dùng đã yêu cầu bỏ không?
- Có link website/URL nếu người dùng đã bảo không cần link không?
- Có chữ nào bị cắt, che, tràn khỏi khung, sát mép, hoặc thiếu dấu không?
- Các dòng nhỏ có đọc được trên điện thoại không?
- Logo Anh Lập Trình có rõ và không sát mép quá không?
- Ảnh người thật có bị méo/crop kỳ, che mặt, hoặc làm bố cục rối không?
- Tổng thể nhìn sạch, chuyên nghiệp, có khoảng thở không?

Nếu bất kỳ câu trả lời nào là không đạt, phải sửa ảnh rồi kiểm lại, không gửi bản lỗi.

## Kiểm Tra Chất Lượng

Trước khi trả lời người dùng, kiểm tra ảnh bằng mắt:

- Ảnh có đúng vuông 1:1 không?
- Chữ có đúng tiếng Việt có dấu không?
- Có lỗi chính tả hoặc thiếu dấu không?
- Có chữ thừa hoặc chữ giả nhìn như chữ thật không?
- Logo `logo3.png` có xuất hiện và không che nội dung chính không?
- Có còn chữ/cụm chữ mà người dùng đã yêu cầu bỏ không?
- Có link website nếu người dùng đã yêu cầu không cần link không?
- Có chữ nào bị tràn/cắt/che hoặc quá sát mép/khung không?
- Các dòng nhỏ có đủ tương phản để đọc trên điện thoại không?

Nếu có lỗi chữ, bố cục, logo, màu sắc, hoặc yêu cầu loại bỏ nội dung chưa được đáp ứng, sửa bằng `compose_square_post.py` hoặc tạo lại nền không chữ rồi chèn chữ lại; không giao ảnh lỗi cho người dùng.
