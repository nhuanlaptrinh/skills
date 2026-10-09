---
name: local-image-fallback
description: Tạo poster, banner, thumbnail và infographic bằng SVG/Python local khi không cần hoặc không có image-provider API key.
---

# Local Image Fallback

Dùng skill này trước khi báo thiếu kết nối tạo ảnh nếu yêu cầu là poster, banner, thumbnail, infographic, cover khóa học hoặc ảnh quảng bá có chữ.

## Khi dùng

- Dùng SVG/Python local cho thiết kế có chữ, hình khối, gradient, icon và bố cục thương hiệu.
- Dùng image provider đã cấu hình khi người dùng yêu cầu ảnh photorealistic, minh họa phức tạp, style nghệ thuật sinh ảnh hoặc chỉnh sửa ảnh tham chiếu bằng AI.
- Không yêu cầu thêm API key cho poster thiết kế local.

## Quy trình bắt buộc

1. Rút nội dung thành headline, subtitle, tối đa 3 bullet và CTA; giữ tiếng Việt có dấu.
2. Tạo file SVG trong `/root/.openclaw/workspace` với kích thước theo yêu cầu, mặc định poster dọc là `1080x1350`.
3. Xuất PNG bằng `rsvg-convert`; nếu không có thì dùng `convert` hoặc giữ SVG nếu người dùng chấp nhận SVG.
4. Kiểm tra file tồn tại, MIME type và kích thước trước khi phản hồi.
5. Gửi đúng file ảnh qua workflow `reliable-media-delivery` hoặc kênh chat đang dùng.

## Mẫu lệnh

```bash
rsvg-convert /root/.openclaw/workspace/poster.svg -o /root/.openclaw/workspace/poster.png
```

## Quy tắc trung thực

- Không nói đã tạo xong nếu chưa có file output thực tế.
- Không nói hệ thống bị thiếu API key nếu yêu cầu vẫn có thể hoàn thành bằng SVG/Python local.
- Nếu công cụ render không có, tạo SVG trước, báo rõ định dạng đã tạo và không tự nhận là PNG.
- Không ghi API key, token hoặc credential vào file ảnh, skill hay câu trả lời.

## Chất lượng

- Dùng font an toàn: `Arial`, `Helvetica`, `DejaVu Sans`.
- Chừa lề an toàn, tránh chữ sát mép và tránh quá nhiều chữ.
- Kiểm tra chính tả, dấu tiếng Việt, chữ không bị tràn/cắt và CTA còn đọc được trên điện thoại.
