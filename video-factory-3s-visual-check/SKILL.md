---
name: "video-factory-3s-visual-check"
description: "Kiểm tra 3s đầu video có hình minh họa, tránh chỉ nền + caption."
---

# Video Mở Đầu 3s Có Hình Minh Họa

Dùng cùng với skill `video-factory-render-checklist` khi tạo/rerender video trong `/root/Apps/video_factory/10.Nha_May_San_Xuat_Video`.

## Mục tiêu

Không để video render ra bị lỗi mấy giây đầu chỉ có nền trừu tượng + caption dưới, trong khi headline/hình minh họa trung tâm bị ẩn.

## Bài học gốc

Video `103_tim_lai_thong_tin_slack_nhanh_720x1280` từng bị lỗi: HTML có visual Slack/kính lúp/card kết quả, nhưng MP4 render ra 11 giây đầu chỉ thấy nền + caption dưới. Nguyên nhân là scene/visual bị ẩn bởi CSS/GSAP visibility state (`visibility:hidden`, `opacity:0`, `autoAlpha`) trong HyperFrames. `npm run check` không bắt được lỗi này; chỉ phát hiện khi trích frame từ MP4 cuối.

## Quy tắc 3 giây đầu

- 0-0.3s phải có headline/hook chính hiện ngay, không chờ animation lâu.
- 0-3s phải có hình minh họa trung tâm gây chú ý và đúng chủ đề.
- Caption dưới chỉ là phụ trợ; không được coi caption là hình minh họa chính.
- Với video công cụ/app, 3 giây đầu nên có UI giả lập, card kết quả, icon/cụm icon, sơ đồ thao tác, hoặc mockup theo keyword chính.

## Cảnh báo HyperFrames scene bị ẩn

- Không để `.scene{opacity:0; visibility:hidden}` làm trạng thái mặc định nếu visibility phụ thuộc hoàn toàn vào GSAP và chưa kiểm chứng bằng frame MP4 cuối.
- Cẩn thận với `tl.set(...,{autoAlpha:0})`, `tl.set(...,{autoAlpha:1})`, và `tl.set(...,{autoAlpha:0}, t+d-.03)` trên scene cha; chúng có thể khiến scene bị ẩn trong render dù caption vẫn chạy.
- Visual/headline chính nên có z-index rõ ràng cao hơn nền và thấp hơn caption nếu cần:
  - `.visual{position:relative; z-index:22}`
  - `.scene h1, .scene p, .kicker{position:relative; z-index:24}`
- Nếu dùng timed scene `.clip`, xác nhận `data-start`, `data-duration`, `data-track-index` đúng và không xung đột với GSAP visibility.

## Kiểm tra bắt buộc sau render

Sau khi render và copy đè MP4 cuối, trích frame từ chính file cuối:

```bash
ffmpeg -y -ss 0.5 -i output/<slug>/<slug>.mp4 -frames:v 1 /tmp/<slug>_t0_5.jpg
ffmpeg -y -ss 3   -i output/<slug>/<slug>.mp4 -frames:v 1 /tmp/<slug>_t3.jpg
ffmpeg -y -ss 8   -i output/<slug>/<slug>.mp4 -frames:v 1 /tmp/<slug>_t8.jpg
ffmpeg -y -ss 11  -i output/<slug>/<slug>.mp4 -frames:v 1 /tmp/<slug>_t11.jpg
```

Kiểm tra bằng mắt hoặc image tool:

- Có headline/text chính ngoài caption dưới.
- Có visual minh họa trung tâm.
- Visual đúng chủ đề transcript.
- Không bị tình trạng chỉ thấy nền + caption dưới.

Nếu frame 0.5s, 3s, 8s hoặc 11s chỉ có nền/caption mà không có scene visual/headline, phải sửa CSS/GSAP và rerender trước khi gửi.

## Backup/copy lưu ý

Khi backup hai file MP4 trùng tên từ `output/<slug>/` và `output/00_output_trend_ai_tintuc/`, đặt tên khác nhau trong thư mục backup, ví dụ:

- `output_folder.mp4`
- `trend_folder.mp4`

Tránh lỗi `cp: will not overwrite just-created`.

## Gửi Telegram

Nếu `MEDIA:` hoặc gửi Telegram báo `Media failed`, tạo bản attach-friendly trong workspace:

```bash
ffmpeg -y -i output/<slug>/<slug>.mp4 \
  -c:v libx264 -preset veryfast -crf 28 -pix_fmt yuv420p \
  -c:a aac -b:a 96k -movflags +faststart \
  /root/AI_Runtime/openclaw/.openclaw/workspace/<slug>_telegram.mp4
```

Gửi lại bản nhẹ này cho người dùng.
