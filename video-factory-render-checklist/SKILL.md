---
name: video-factory-render-checklist
description: Checklist bắt buộc khi Codex/OpenClaw tạo, render, rerender, sửa template, hoặc ghi đè video trong /root/Apps/video_factory/10.Nha_May_San_Xuat_Video, đặc biệt với template 03_audio_motion_graphics_720x1280; dùng để đảm bảo video dùng lại audio/caption đúng, tên file không đổi khi ghi đè, gửi Telegram sau render, và logo Anh Lập Trình không bị méo.
---

# Video Factory Render Checklist

Dùng checklist này trước mọi task tạo/rerender video trong `/root/Apps/video_factory/10.Nha_May_San_Xuat_Video`.

## Quy tắc bắt buộc

- Đọc `/root/Apps/video_factory/10.Nha_May_San_Xuat_Video/AGENTS.md` trước khi sửa project.
- Nếu rerender video đã có audio HeyGen, không tạo lại audio; dùng lại `input/<slug>_heygen_1_12x.mp3`, `input/<slug>_captions_exact.json`, và transcript cũ.
- Khi ghi đè video cũ, giữ nguyên slug/tên MP4 và copy đè cả `output/<slug>/<slug>.mp4` lẫn `output/00_output_trend_ai_tintuc/<slug>.mp4`.
- Backup MP4 cũ, `index.html`, `styles.css` vào `/root/_Backups/video_rerender_<slug-or-row>_<timestamp>` trước khi ghi đè.
- Chạy `npm run check` trước `npm run render`; chỉ chấp nhận 0 error.
- Sau render, kiểm tra MP4 bằng `ffprobe` để xác nhận đúng kích thước/tỉ lệ yêu cầu, có audio, đúng thời lượng hợp lý.
- Mặc định audio lời đọc phải dùng tốc độ `1.15x` cho video mới, trừ khi người dùng yêu cầu tốc độ khác. Sau khi đổi tốc độ audio phải align lại caption từ audio mới và validate lại.
- Hình minh họa, headline, scene text, caption và lời đọc phải khớp cùng một ý ở từng đoạn video.
- Không hiển thị hashtag trong hình ảnh/video/scene text/caption visual. Hashtag chỉ dùng cho caption bài đăng hoặc cột Sheet; nếu title đầu vào có hashtag, phải lọc bỏ hashtag trước khi đưa vào headline, scene text, card, badge, overlay trong video.
- Nếu audio nghe không rõ hoặc không chắc nội dung, đối chiếu lại transcript gốc trong `input/<slug>_transcript.txt` hoặc dữ liệu nguồn Google Sheet trước khi thiết kế scene/caption.
- Không dùng hình/card/icon minh họa chung chung lặp lại nếu transcript đang nói về một ý cụ thể; ưu tiên minh họa đúng vấn đề, công cụ, lợi ích hoặc bước hướng dẫn đang được đọc.
- Gửi Telegram bằng `scripts/notify_video_telegram.py` sau khi MP4 cuối đã được copy đè.
- Cập nhật `/root/_Second_AI_Brain/06_Nhat_Ky_Thay_Doi.md` sau thay đổi quan trọng.

## Checklist khớp nội dung hình - tiếng - chữ

- Chia transcript thành 3-5 ý chính theo thứ tự lời đọc.
- Mỗi scene chỉ trình bày ý đang được đọc trong khoảng thời gian đó.
- Headline lớn của scene phải là bản rút gọn của câu/ý trong transcript, không tự thêm ý mới.
- Caption phải lấy từ transcript hoặc bản rút gọn rất sát nghĩa; không dùng caption chung chung lệch lời đọc.
- Icon, card, flow, minh họa phải bám vào keyword của đoạn đó, ví dụ: server/demo web, khách hàng, Slack, thumbnail, bảo mật, tập trung.
- Trước khi render, tự kiểm tra nhanh: “nếu tắt tiếng, người xem có hiểu đúng ý đoạn đang đọc không?” và “nếu chỉ nghe tiếng, caption/hình có làm người xem bị lệch ý không?”.
- Sau render demo, trích ít nhất một frame ở đầu và một frame giữa video để kiểm tra hình/caption có khớp lời đọc theo transcript.

## Checklist chống méo logo

- Biết rằng `logo1.png` là logo ngang, không phải ảnh vuông.
- Không đặt `.brand img` kiểu `width:52px;height:52px` hoặc bất kỳ cặp width/height vuông nào.
- CSS logo phải giữ tỷ lệ bằng mẫu:
  `width:auto; height:<fixed>; max-width:<limit>; object-fit:contain;`
- Không dùng `border-radius` lớn làm logo ngang nhìn như icon vuông; ưu tiên `border-radius:0` hoặc rất nhỏ.
- Trước render, chạy script kiểm tra nếu có:
  `python3 scripts/check_logo_ratio_css.py`
- Sau render, trích frame đầu và nhìn logo:
  `ffmpeg -y -ss 2 -i output/00_output_trend_ai_tintuc/<slug>.mp4 -frames:v 1 /tmp/<slug>_logo_check.jpg`

## Prompt OpenClaw nên có

Khi giao task cho OpenClaw, luôn chèn câu này:

```text
Bắt buộc kiểm tra logo Anh Lập Trình trước render: logo1.png là ảnh ngang, CSS .brand img phải dùng width:auto + height cố định + object-fit:contain, không ép width/height bằng nhau. Sau render hãy trích frame kiểm tra logo không méo.
```
