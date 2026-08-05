---
name: tao-video-hyperframes
description: Tạo video HyperFrames hoàn chỉnh từ transcript và audio có sẵn. Dùng khi cần kiểm tra hoặc tải project Nhà Máy Sản Xuất Video, dựng video tiếng Việt mới có phụ đề và motion graphics, render MP4 cuối, kiểm tra tính toàn vẹn hình ảnh và âm thanh, kiểm tra frame và tỷ lệ logo, đồng thời báo cáo warning mà không publish hoặc gửi media.
---

# Tạo Video HyperFrames

Dùng skill này để tạo video hoàn chỉnh thực sự, không chỉ tạo bản smoke test. Bảo vệ các file production cũ và không đặt tên đầu ra là `test`, `demo` hoặc `smoke`, trừ khi người dùng yêu cầu rõ các tên đó.

## Bối Cảnh Bắt Buộc

Đọc các file sau trước khi thay đổi project:

1. `/root/_Second_AI_Brain/START_HERE.md`
2. `/root/_Second_AI_Brain/01_Ban_Do_VPS.md`
3. `/root/_Second_AI_Brain/02_Danh_Sach_Project.md`
4. `AGENTS.md` và `CLAUDE.md` của project đích
5. Các skill cục bộ liên quan đến `hyperframes`, `hyperframes-cli` và `gsap` khi viết HTML

Không được mở, in, sao chép vào câu trả lời hoặc làm lộ nội dung `.env`, credential, cookie, token hay private key. Không publish, gửi Telegram, gửi tin nhắn mạng xã hội hoặc gọi API trả phí, trừ khi người dùng yêu cầu riêng và rõ ràng.

## Project Và Source Drive Mặc Định

Với yêu cầu nói về Nhà Máy Sản Xuất Video nhưng không chỉ định đường dẫn khác, dùng:

- Project: `/root/Apps/04_Nha_May_San_Xuat_Video`
- Thư mục Google Drive: `https://drive.google.com/drive/folders/15MckQPMHapn2195kj5v67DuEG-bxEwEx?usp=sharing`
- ID thư mục gốc trên Drive: `15MckQPMHapn2195kj5v67DuEG-bxEwEx`
- Remote Rclone: `gdrive:`

Trước khi đọc file project hoặc dựng video, phải chạy:

```bash
bash /root/.agents/skills/tao-video-hyperframes/scripts/ensure_project_downloaded.sh \
  /root/Apps/04_Nha_May_San_Xuat_Video
```

Script kiểm tra các file mốc bắt buộc của project. Nếu thư mục chưa tồn tại hoặc chưa đầy đủ, script sẽ tải thư mục từ Drive bằng remote `gdrive:` rồi kiểm tra lại các file mốc. Nếu remote hoặc quyền truy cập link không hoạt động, phải dừng và báo rõ trở ngại; không tự tạo source giả và không âm thầm dùng thư mục khác.

**Quy tắc xử lý source:** nếu source đã đầy đủ thì dùng ngay và không tải lại; nếu source thiếu hoặc chưa hoàn chỉnh thì tự tải về rồi mới tiếp tục.

## Hợp Đồng Đầu Vào

Trích xuất các giá trị sau từ brief của người dùng:

- `project_dir`: thư mục gốc của project HyperFrames.
- `transcript`: transcript hoặc nguồn text có sẵn ở local.
- `voice_audio`: audio thuyết minh có sẵn. Phải dùng lại audio này; không tạo TTS mới nếu người dùng chưa yêu cầu.
- `brief`: nội dung từng cảnh, phong cách hình ảnh, ngôn ngữ và yêu cầu caption.
- `output_video`: đường dẫn MP4 cuối trong `output/<slug>/<slug>.mp4`.
- `width`, `height` và `fps`: dùng đúng giá trị người dùng yêu cầu; nếu là video ngang mới và không nêu rõ thì mặc định `1280x720` ở `30 fps`.

Nếu brief thiếu giá trị không quan trọng, dùng quy ước của project. Chỉ hỏi lại khi việc tiếp tục có thể làm ghi đè dữ liệu production, thay đổi credential hoặc chọn nhầm audio nguồn.

## Quy Tắc Nội Dung Tiếng Việt

- Giữ Unicode tiếng Việt có đầy đủ dấu trong mọi headline, caption, nhãn cảnh, báo cáo, mô tả filename và tin nhắn gửi người dùng.
- Không chuyển tiếng Việt sang ASCII và không bỏ các chữ `ă`, `â`, `đ`, `ê`, `ô`, `ơ`, `ư` hoặc dấu thanh.
- Caption phải đồng bộ đúng ý nghĩa với lời thuyết minh tiếng Việt được cung cấp; không thay text có dấu bằng nội dung tự nghĩ không dấu.
- Dùng kiểu chữ tiếng Việt dễ đọc, xuống dòng tự nhiên, dấu câu đúng và không thêm hashtag overlay nếu người dùng không yêu cầu.

## Quy Trình Production

1. Chạy `ensure_project_downloaded.sh` và xác nhận thư mục đích đúng là project cần làm.
2. Đọc `AGENTS.md` và `CLAUDE.md`; tìm transcript, audio thuyết minh, logo, font và quy ước composition hiện có mà không mở `.env`.
3. Ưu tiên workspace tách biệt như `<project_dir>/workspaces/<slug>` với `index.html`, `styles.css`, `package.json` và media local riêng. Video đầu ra vẫn là video hoàn chỉnh thật trong thư mục `output/` của project; workspace chỉ là vùng an toàn để triển khai.
4. Dùng tên stylesheet `styles.css` cho workspace. Công cụ HyperFrames tự động nhận diện quy ước này; render trực tiếp file độc lập trong `compositions/` có thể âm thầm bỏ qua stylesheet tùy chỉnh.
5. Dùng `ffprobe` xác định thời lượng audio, lập ranh giới cảnh theo lời thuyết minh và dùng lại audio hiện có thay vì tạo voice mới.
6. Tạo `.hyperframes/expanded-prompt.md` hoặc file tương đương có `<slug>` trước khi viết composition nhiều cảnh.
7. Nếu bắt buộc sửa `index.html` hoặc `styles.css` chính, phải backup file gốc vào `/root/_Backups/video_<slug>_<UTC timestamp>/` trước. Không ghi đè MP4 cuối đã có nếu người dùng chưa yêu cầu render lại và chưa có backup phù hợp.

## Quy Tắc Composition

- Mọi phần tử có thời gian phải có `data-start`, `data-duration`, `data-track-index` và `class="clip"` khi hiển thị trên timeline.
- Đăng ký timeline ở trạng thái paused trong `window.__timelines` bằng đúng `data-composition-id`.
- Đặt audio trong các phần tử `<audio>` riêng; dùng phần tử `<video>` tắt tiếng cho nguồn video.
- Chỉ tạo timeline xác định: không dùng `Date.now()`, `Math.random()`, vòng lặp vô hạn hoặc tải dữ liệu mạng lúc chạy.
- Phải có hình minh họa có ý nghĩa xuất hiện trong ba giây đầu; chỉ có nền và caption là chưa đủ.
- Caption, headline, hình minh họa và lời thuyết minh phải khớp nội dung với nhau. Dùng transcript và audio được cung cấp, không chèn nội dung không liên quan.
- Với nhận diện Anh Lập Trình, xem `logo1.png` là logo ngang và dùng `width:auto`, `height` cố định, `max-width` cùng `object-fit:contain`; tuyệt đối không ép width và height bằng nhau.
- Dùng transition giữa các cảnh và animation xuất hiện cho các phần tử. Không chạy exit animation trước transition.

## Check, Render Và Xác Minh

Chạy lệnh từ workspace triển khai production:

```bash
npm run check
```

Không được render khi lệnh trả về mã lỗi khác `0` hoặc báo error. Phải xem lại warning và đưa toàn bộ warning còn tồn tại vào báo cáo cuối.

Chỉ render video hoàn chỉnh thật sau khi check đạt yêu cầu:

```bash
npm run render -- --output /absolute/path/to/output/<slug>/<slug>.mp4 --fps 30 --quality standard
```

Kiểm tra MP4 cuối bằng script đi kèm:

```bash
bash /root/.agents/skills/tao-video-hyperframes/scripts/verify_video.sh \
  /absolute/path/to/output/<slug>/<slug>.mp4 \
  /absolute/path/to/output/<slug>/verification \
  1280 720 30
```

Script kiểm tra stream hình và tiếng, kích thước cùng fps nếu được cung cấp, giải mã toàn bộ bằng FFmpeg, thời lượng, trích frame và SHA-256. Sau đó dùng công cụ xem ảnh để kiểm tra các frame và xác nhận:

- Frame đầu có hook tiếng Việt rõ ràng cùng hình minh họa có ý nghĩa, không chỉ có nền và caption.
- Các frame khoảng `3s`, `8s` và gần cuối hiển thị đúng cảnh dự kiến.
- Caption tiếng Việt có dấu, đồng bộ với audio và không bị cắt.
- Logo giữ đúng tỷ lệ, không bị méo.
- Video không bị trống, trắng, hỏng hoặc mất audio.

## Báo Cáo Cuối

Báo cáo bằng tiếng Việt có đầy đủ dấu:

- Đường dẫn MP4 cuối.
- Thời lượng, kích thước, fps, codec video, codec audio và dung lượng.
- Kết quả kiểm tra hoặc tải source project.
- Kết quả `npm run check` và toàn bộ warning còn tồn tại.
- Kết quả kiểm tra stream và giải mã toàn bộ video.
- Kết quả kiểm tra frame và tỷ lệ logo.
- Mọi hành động đã bỏ qua, đặc biệt là publish, Telegram, API trả phí, credential hoặc sửa production.

Sau thay đổi quan trọng, ghi một mục đã được làm sạch thông tin nhạy cảm vào `/root/_Second_AI_Brain/06_Nhat_Ky_Thay_Doi.md`. Tuyệt đối không ghi secret vào nhật ký.

## Cách Gọi Ngắn Gọn

Về sau, người dùng có thể nói:

> Dùng `$tao-video-hyperframes` để tạo video thật trong `/root/Apps/04_Nha_May_San_Xuat_Video`. Kiểm tra source Drive trước; nếu thiếu thì tải về bằng link Drive mặc định. Dùng transcript và audio có sẵn, giữ tiếng Việt có đầy đủ dấu, tạo video `<brief>`, lưu tại `output/<slug>/<slug>.mp4`, sau đó chạy check, render, ffprobe và kiểm tra frame. Không đụng `.env`, không publish, không gửi Telegram và không dùng API trả phí.
