---
name: logo-bo-goc-video
description: Khi dựng video dọc hoặc demo cần logo Anh Lập Trình; áp dụng logo ngang bo bốn góc và kiểm tra render cuối.
---

# Logo bo góc video

## Quy trình

1. Trong workspace HyperFrames, dùng đúng asset logo thương hiệu `logo1.png`; không lấy logo từ MP4 đã render.
2. Đặt logo ở lớp trên cùng, góc phải phía trên bằng phần tử `<img>` riêng có id ổn định; dùng `position:absolute` và `z-index` cao hơn footage.
3. Giữ logo dạng hình chữ nhật ngang: `height:58px`, `width:auto`, `max-width:250px`, `object-fit:contain`.
4. Bo tròn bốn góc bằng `border-radius:14px`; tuyệt đối không dùng `border-radius:50%`.
5. Dùng nền trắng hơi trong, padding nhỏ, viền xanh nhẹ và bóng mềm để logo rõ nhưng không lấn át thumbnail:
   `background:rgba(255,255,255,.96); padding:8px 14px; box-shadow:0 8px 24px rgba(0,0,0,.28),0 0 0 2px rgba(106,255,189,.72),0 0 20px rgba(106,255,189,.25)`.
6. Chạy HyperFrames lint trước khi render; sửa mọi lỗi media thiếu id và clip chồng cùng track.
7. Render lại từ composition nguồn sạch, không patch logo lên MP4 cũ.
8. QC bằng `ffprobe` và giải mã toàn bộ video; kiểm tra frame đầu và một frame sau thumbnail để xác nhận logo vẫn là hình ngang bo bốn góc, chữ không méo hoặc bị cắt.

## Không được làm

- Không biến logo thành hình tròn.
- Không dùng FFmpeg `drawbox`, `drawtext` hoặc dán logo lên MP4 cũ.
- Nếu chỉ sửa logo, giữ nguyên voiceover, subtitle, cảnh và timing.
