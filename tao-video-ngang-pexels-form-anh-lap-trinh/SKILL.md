---
name: "tao-video-ngang-pexels-form-anh-lap-trinh"
description: "Video ngang 1280×720 với Pexels, voice Minimax và subtitle nhỏ đẹp theo mẫu 26_tro_ly_ai_hieu_sep; kèm nhánh dọc 1080×1920 khi được yêu cầu."
---

# Video ngang Pexels với subtitle nhỏ đẹp theo mẫu

## Mặc định
- Khung hình 1280×720.
- Trước khi tải cảnh hoặc dựng timeline, kiểm tra khả năng xác thực của Voice AI và tạo thử voice cho đúng transcript; nếu xác thực không hợp lệ thì dừng ở bước chuẩn bị, không render hoặc gửi bản tạm có audio không khớp nội dung.
- Truyền transcript cho helper tạo voice bằng tùy chọn đọc file mà helper thực sự hỗ trợ (hiện tại là `--input`, không dùng tùy chọn tự đặt như `--text-file`). Chạy từ gốc Nhà Máy (không phải workspace): `python3 scripts/voice_ai_tts.py --input <workspace>/transcript_voice.txt --output <workspace>/voiceover_vi.mp3 --metadata-output <workspace>/voiceover_meta.json --env .env`.
- Helper gọi API bất đồng bộ khoảng 1–2 phút: cho đủ thời gian chờ (exec `timeoutSeconds` ≥ 400 rồi poll), hoặc chạy tách session bằng `setsid nohup python3 -u <lệnh trên> > <workspace>/voice_run.log 2>&1 < /dev/null &` rồi kiểm tra `voiceover_vi.mp3` có dung lượng > 0. Chỉ chuyển sang bước cảnh khi đã có MP3.
- Dùng clip minh họa Pexels khoảng 5–10 giây/đoạn khi ngữ cảnh phù hợp.
- Nếu helper Pexels trả `HTTP Error 401`, coi đó là chặn bot/Cloudflare chứ không phải key sai: gọi lại API kèm `User-Agent` trình duyệt (ví dụ `Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36`) và dùng đúng UA đó cho cả request tải file. Cùng một key có thể trả 200 cho truy vấn này và 401 cho truy vấn khác, nên probe nhanh vài chục truy vấn ứng viên rồi chỉ tải từ truy vấn trả 200; đừng đi tìm key khác vì key trong `.env` lẫn bản backup `/root/_Backups/*/.env` đều trả 401 khi gọi kiểu helper cũ.
- Nếu vẫn không tải được sau vài lượt thử hợp lệ, dùng clip Pexels đã có trong workspace/input của Nhà Máy, loại clip trùng video tham chiếu, trích frame giữa ghép contact sheet để chọn bộ cảnh đa dạng đúng mạch nội dung, rồi chép vào workspace mới.
- Chuẩn hóa từng clip về đúng khung composition (1280×720 ngang, 1080×1920 dọc), H.264 30 fps CFR, dài 5–10 giây, keyframe cách nhau tối đa 1 giây (`-r 30 -g 30 -keyint_min 30 -movflags +faststart`); lấp đầy rồi cắt giữa khung bằng `-vf "scale=<W>:<H>:force_original_aspect_ratio=increase,crop=<W>:<H>"`; cắt bằng `-ss`/`-t` trước khi encode; chỉ đặt `-c:a copy` khi nguồn có audio cần giữ.
- Nếu yêu cầu cấm QR, barcode, watermark hoặc nội dung màn hình rủi ro, lấy ít nhất ba frame đầu/giữa/cuối mỗi clip để lập contact sheet kiểm tra; thay clip có nội dung cấm trước khi dựng.
- Voice Minimax: Voice ID `b2d15d82-ec3b-4e8d-bca7-0afa39c69c56`, model `speech-2.8-turbo`, tiếng Việt, tốc độ 1.15x.
- Từ `AI` trong transcript phải viết thành `ây-ai` trong voice script để phát âm tiếng Anh; subtitle vẫn hiển thị `AI`.

## Subtitle chuẩn đã duyệt và quy tắc DUY NHẤT 1 LỚP SUB
Style chuẩn tuyệt đối theo video mẫu `26_tro_ly_ai_hieu_sep`:
- Chữ trắng nhỏ gọn (~16px trên canvas 1280×720, font-weight ~700, font `BeVietnam`), nền xanh đen trong nhẹ `rgba(2,10,22,.78)`, viền mảnh `1px solid rgba(255,255,255,.24)`, bo tròn viên nhộng `border-radius:999px`, padding gọn `8px 17px`, text-shadow `0 2px 3px #000`.
- Đặt ở vùng an toàn sát đáy màn hình (bottom: 24px - 28px), căn giữa, không che nội dung visual hay logo.

## QUY TẮC BẤT DI BẤT DỊCH: KHẮC PHỤC TRIỆT ĐỂ LỖI SUB CHỒNG CHÉO
1. **DUY NHẤT MỘT LUỒNG SUBTITLE TRÊN TOÀN BỘ VIDEO:**
   - Tuyệt đối **KHÔNG** tạo thêm các khối `chapter-card` hay thẻ tiêu đề chữ to (`.kicker`, `<h2>`) ở giữa màn hình lặp lại nội dung câu đọc. Khung hình Pexels là để minh họa bối cảnh, phụ đề dưới đáy là để thể hiện lời nói. Việc nhét thêm thẻ chữ to ở giữa màn hình sẽ biến video thành "2 phần sub" gây rối mắt người xem.
   - Nếu cần nhấn mạnh ý chính, chỉ dùng đồ họa visual (icon, checklist đồ họa, sơ đồ mũi tên) hoặc giữ bối cảnh video Pexels sạch sẽ, **KHÔNG** đặt text dài tóm tắt lời thoại.
2. **TUYỆT ĐỐI CẤM DÙNG FFMPEG DÁN ĐÈ SUB LÊN VIDEO CŨ:**
   - Nghiêm cấm lấy file MP4 render cũ rồi dùng `-vf "subtitles=..."` để dán phụ đề mới đè lên.
   - Nghiêm cấm dùng FFmpeg `drawbox` vẽ hộp đen để che chữ cũ trong video. Mọi phụ đề phải được render sạch 1 lần duy nhất từ mã nguồn HyperFrames `index.html`.
3. **KHÔNG ĐỂ SUBTITLE TĨNH KÉO DÀI:**
   - Tuyệt đối không để 1 thẻ caption có thời lượng kéo dài toàn bộ video (như lỗi kẹt chữ "Hôm nay đăng gì nhỉ?").
   - Mỗi câu subtitle phải hiển thị đúng thời điểm câu nói bắt đầu và ẩn đi khi câu nói kết thúc, dựa 100% vào `alignment.json`.
4. **THUMBNAIL ĐẦU VIDEO (3-5 GIÂY) PHẢI ĐẦY ĐỦ DẤU TIẾNG VIỆT:**
   - Thumbnail mở đầu phải dựng bằng chính thẻ `<section id="thumb" class="clip thumbnail">` trong file `index.html` của HyperFrames, sử dụng font `BeVietnamPro-Bold` với dấu tiếng Việt chuẩn 100%.
   - Tuyệt đối không dùng lệnh FFmpeg `drawtext` thô làm rụng hết dấu tiếng Việt của tiêu đề.
5. **QUY TRÌNH BẮT BUỘC KHI NGƯỜI DÙNG YÊU CẦU SỬA ĐỔI, ĐỔI THUMBNAIL HOẶC LÀM LẠI (CẤM ĐI ĐƯỜNG TẮT FFMPEG, CẤM GỬI LẠI VIDEO CŨ):**
   - Khi người dùng phản hồi "Sửa lại...", "Làm lại...", "Đổi thumbnail...", "Đổi tiêu đề...", "Xóa sub chữ to...", "Chỉnh lại nội dung...":
   - **CẤM TUYỆT ĐỐI**:
     + Không lấy video cũ gửi lại ngay mà không render.
     + Không lấy file MP4 cũ rồi dùng FFmpeg (concat, drawbox, drawtext, subtitles) chắp vá. Việc cắt ghép chắp vá trên MP4 làm rụng dấu tiếng Việt và gây lỗi 2-3 tầng sub đè lên nhau.
   - **BẮT BUỘC THỰC HIỆN 100% TẠI MÃ NGUỒN GỐC**:
     a. Vào đúng thư mục workspace nguồn của video (`workspaces/<project-slug>/`).
     b. Sửa trực tiếp file mã nguồn HTML (`index.html`), CSS (`styles.css`), hoặc tạo file ảnh thumbnail mới (đầy đủ dấu tiếng Việt chuẩn, logo) chép vào workspace.
     c. Chạy lệnh re-render sạch 100% bằng HyperFrames (`npx --yes hyperframes@0.6.96 render .`).
     d. Convert sang H.264 và bàn giao bản render mới. Mọi bản sửa đổi đều phải là bản render sạch từ đầu.

## Đồng bộ voice và subtitle
1. Voice script và subtitle giữ cùng nội dung, chỉ khác cách viết `ây-ai` trong voice script và `AI` trên subtitle.
2. Đo duration voiceover bằng ffprobe. Khi người dùng yêu cầu thời lượng cụ thể, tạo voice, đo rồi rút gọn/bổ sung transcript và tạo lại đến khi audio lệch mục tiêu không quá khoảng 0,2 giây; giữ tốc độ 1.15x, không kéo giãn audio hoặc chèn khoảng lặng để ép thời lượng. Tốc độ đọc Minimax 1.15x dao động khoảng 3,8–5,0 từ/giây (133 từ ≈ 28,5 giây; 114 từ ≈ 23,0 giây; nhưng 113 từ nhiều số và ký tự viết tắt mất tới 29,8 giây) — chỉ dùng để ước lượng lúc viết, luôn đo lại bằng ffprobe rồi mới chốt.
3. Chỉ căn subtitle sau khi chốt voice cuối. Chạy từ gốc Nhà Máy (`/root/Apps/04_Nha_May_San_Xuat_Video`, nơi có `.venv_align` và `scripts/`, không phải workspace): `.venv_align/bin/python scripts/align_clean_transcript_captions.py --video <workspace>/<audio-cuối> --transcript <workspace>/<transcript-hiển-thị> --out <workspace>/alignment.json --model small`. Dùng `captions[].start/end/text` để dựng phụ đề; kiểm tra `match_ratio` và các từ không khớp trước khi chốt timeline.
4. Composition kết thúc ngay sau voiceover, không để đoạn dư cuối. Tổng duration các scene phải bằng duration voiceover: lấy mốc scene theo nhóm câu trong `alignment.json` và kéo scene cuối cho khớp nếu tổng bị hụt.
5. **Cấu trúc sinh phụ đề chuẩn trong HyperFrames (index.html):**
   Trong file `index.html`, sinh danh sách subtitle trực tiếp từ `captions[]` của `alignment.json`:
   ```html
   <div class="subtitle-safe">
     <span class="subtitle-line clip" data-start="0.00" data-duration="2.45" data-track-index="50">Nội dung câu 1...</span>
     <span class="subtitle-line clip" data-start="2.45" data-duration="3.15" data-track-index="50">Nội dung câu 2...</span>
   </div>
   ```
   CSS chuẩn:
   ```css
   .subtitle-safe {
     position: absolute;
     inset: 0;
     z-index: 120;
     pointer-events: none;
     display: flex;
     align-items: flex-end;
     justify-content: center;
     padding-bottom: 24px;
   }
   .subtitle-line {
     display: inline-block;
     max-width: 1040px;
     padding: 8px 18px;
     border: 1px solid rgba(255,255,255,.24);
     border-radius: 999px;
     background: rgba(2,10,22,.78);
     color: #fff;
     font-family: BeVietnam, Arial, sans-serif;
     font-size: 16px;
     font-weight: 700;
     line-height: 1.25;
     text-align: center;
     white-space: nowrap;
     text-shadow: 0 2px 3px #000;
     box-shadow: 0 6px 22px rgba(0,0,0,.24);
   }
   ```
   GSAP timeline animation cho subtitle:
   ```javascript
   document.querySelectorAll('.subtitle-line').forEach(e => {
     const t = +e.dataset.start, d = +e.dataset.duration;
     tl.from(e, { autoAlpha: 0, y: 8, duration: 0.12, overwrite: 'auto' }, t)
       .to(e, { autoAlpha: 0, duration: 0.12, overwrite: 'auto' }, t + d - 0.12);
   });
   ```
6. Pexels, scene và subtitle dùng chung timeline; không để subtitle chạy trước hoặc sau câu đọc.

## Bản dọc 1080×1920 (chỉ khi được yêu cầu)
- Yêu cầu khổ dọc, Reels/Shorts/TikTok hoặc tỉ lệ điện thoại: giữ nguyên quy trình voice Minimax, căn subtitle và kiểm tra; chỉ đổi khung composition thành 1080×1920.
- Phóng typography theo chiều rộng khung; mức đã chạy đúng ở 1080×1920: chapter title ~60px, kicker ~24px, caption ~40px cách đáy ~150px, logo cao ~46px, thanh tiến trình 8px.
- Khi xin clip Pexels, dùng `orientation=portrait` và chỉ nhận file có `height > width`, `height >= 1080`.
- Thời gian render biến động mạnh: bản ~29 giây dọc khoảng 2,5 phút ở đường capture thường, nhưng tới ~16 phút khi composition chứa clip HDR (clip có `color_transfer=arib-std-b67`/`primaries=bt2020` kích hoạt đường HDR layered). Theo dõi tiến trình frame thay vì kết luận treo khi tiến trình còn chạy; chuẩn hóa màu clip nguồn về bt709 nếu muốn đường render nhanh.

## Khôi phục tác vụ bị gián đoạn
- Trước khi tạo workspace mới, tìm workspace và output mới nhất khớp chủ đề; kiểm tra checkpoint đã có như transcript, voice cuối, alignment, composition, render log và MP4.
- Tiếp tục từ checkpoint hoàn chỉnh gần nhất, chỉ tạo lại phần thiếu hoặc không đạt kiểm tra; giữ nguyên workspace đang dùng và lưu MP4 cuối vào output riêng để không ghi đè sản phẩm cũ.
- Sau khi tiếp tục, chạy lại toàn bộ mục Kiểm tra; chỉ giao đúng MP4 vượt qua kiểm tra cuối.

## Giao sản phẩm qua Telegram
- HyperFrames render ra HEVC 10-bit HLG (`libx265`, `yuv420p10le`, `color_trc=arib-std-b67`), không phải định dạng Telegram phát ổn định. Tạo bản giao H.264/AAC 8-bit từ MP4 đã render rồi mới gửi, và chỉ gửi đúng file H.264 đó: `ffmpeg -y -v error -i <mp4-render> -c:v libx264 -preset fast -crf 21 -pix_fmt yuv420p -profile:v high -level 4.2 -movflags +faststart -c:a aac -b:a 160k /root/.openclaw/workspace/media/<tên>_h264.mp4`.
- Chép MP4 cuối đã kiểm tra vào `/root/.openclaw/workspace/media/<tên>.mp4` để lưu trữ; bản gửi đi là file H.264 ở bước trên.
- Ưu tiên media broker (`telegram_sendvideo`/`telegram_sendfile`). Nếu đường đó trả `telegram_media_adapter_unavailable` hoặc "chưa có xác nhận từ Telegram" lặp lại, fallback bằng `message` `action=send` với trường `media` (nhận cả alias `attachment`) trỏ tới file trong `/root/.openclaw/workspace/media/`.
- Chỉ báo đã gửi khi tool trả `ok: true` kèm `messageId` thật; chưa có thì kiểm tra trạng thái gửi trước khi thử lại để tránh gửi trùng.

## Kiểm tra
- Trước khi render, chép asset `logo1.png` Anh Lập Trình vào workspace, khai báo logo phủ toàn video và đặt góc trên bên phải như mẫu `26_tro_ly_ai_hieu_sep`.
- Chạy `npm run check`; không bỏ qua error.
- Render HyperFrames. Lệnh render không in tiến trình frame ra stdout cho tới khi xong, nên log trống không phải là treo: xác nhận còn chạy bằng `ps` (tiến trình `ffmpeg` còn sống) và sự tồn tại của thư mục `renders/work-*/`, rồi chờ tiếp thay vì kill và render lại.
- Nếu preflight báo `sparse keyframes`, dừng bản giao, chuẩn hóa lại đúng clip được nêu với GOP tối đa 1 giây rồi chạy lại check/render; không dựa vào việc renderer vẫn tiếp tục để coi cảnh không bị đứng hình.
- Trích ít nhất một frame từ MP4 đã render để xác nhận logo hiển thị đúng; chép frame vào `/root/.openclaw/workspace/media/` trước khi mở bằng `view_image`, rồi kiểm tra trực quan logo, phụ đề và lỗi render thay vì chỉ kiểm tra source HTML hay sự tồn tại của asset. Nếu `view_image` chỉ báo đã nạp ảnh mà không trả nội dung ảnh, dùng cách mô tả frame dự phòng ở `references/kiem-tra-frame-bang-vision-cuc-bo.md`. Khi có ràng buộc nội dung cấm, trích contact sheet phủ các cảnh trong MP4 cuối và xác nhận lại không còn QR, barcode, watermark.
- ffprobe kiểm tra thời lượng, đúng khung hình (1280×720 hoặc 1080×1920) và cả video/audio stream; xác nhận file sắp gửi là `h264` + `yuv420p`, không phải bản HEVC 10-bit của renderer.
- Kiểm tra file tồn tại và dung lượng > 0 trước khi gửi.

## Ngoại lệ
Style subtitle này áp dụng mặc định cho các video sau, kể cả khi không dùng Pexels. Pexels chỉ là phần minh họa tùy theo ngữ cảnh; voice Minimax và subtitle style vẫn giữ nguyên.
