---
name: anh-lap-trinh-logo-chuan
description: Dùng khi tạo mới hoặc cập nhật bất kỳ website/domain nào trên VPS1 (course_websites, *.anhlaptrinh.vn, ví dụ 38_domain_emtl) cần logo Anh Lập Trình ở header. Logo chuẩn là "ANH LẬP TRÌNH Minimalist Badge.png".
---
# Logo chuẩn Anh Lập Trình (từ 19/11/2026)

## File chuẩn
- Bản gốc: `/root/_Brand/anh_lap_trinh/ANH LẬP TRÌNH Minimalist Badge.png` (2170x725, khung trắng bo tròn sẵn, chữ ANH LẬP TRÌNH màu đen).
- Bản dùng cho web: `/root/_Brand/anh_lap_trinh/logo-alt-rounded.png` (640x168, đã cắt viền trắng thừa, nền ngoài khung trong suốt).
- Không dùng logo chữ cũ `logo.png` 289x55 hay `company_logo.png` cho site mới.

## Cách gắn vào header
1. Sao lưu template trước khi sửa (`/root/_Backups/<site>_logo_<UTCts>/`).
2. Copy `logo-alt-rounded.png` vào static của project (vd `trolyai/static/trolyai/images/logo-alt-rounded.png`).
3. Thẻ img ở header, góc trái, cạnh tên sản phẩm:
   `<img class="brand-logo" src="{% static .../logo-alt-rounded.png %}" alt="Anh Lập Trình" width="152" height="40">`
4. CSS: `.brand-logo{height:40px;width:auto;max-width:210px;flex:0 0 auto;object-fit:contain;display:block}` và `@media(max-width:480px){.brand-logo{height:32px;max-width:168px}}`.
   Không thêm border-radius hay khung tròn: logo đã bo sẵn, ép tròn sẽ cắt mất chữ.
5. Nếu CSS nằm trong template/static: restart riêng container của site (hoặc collectstatic nếu dùng file static), không đụng site khác.
6. Kiểm tra: trang trả 200, URL ảnh logo trả 200 image/png, logo không méo trên máy tính và điện thoại.

## Tham chiếu
- Site đang dùng đúng chuẩn: emtl.anhlaptrinh.vn (`/root/Apps/course_websites/10Web_BH/38_domain_emtl`).
