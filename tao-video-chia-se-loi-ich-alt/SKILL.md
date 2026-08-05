---
name: tao-video-chia-se-loi-ich-alt
description: Tạo video chia sẻ lợi ích kèm ebook hướng dẫn ALT. Use when Codex needs to create a benefit-focused Vietnamese sharing video from provided content, especially with /root/10.Nha_May_San_Xuat_Video, HyperFrames, Video Giọng Đọc Motion, and an accompanying ebook/PDF in /root/Second_Brain/07_ebook_chia_se; always copy the final MP4 to /root/05_skill_facebook_zalo/images for Facebook/Zalo posting.
---

# Tạo video chia sẻ lợi ích ALT

Dùng khi anh Nhuần yêu cầu tạo **video chia sẻ lợi ích** từ một nội dung/hướng dẫn, thường kèm yêu cầu tạo ebook hướng dẫn cài đặt hoặc thao tác.

## Nguyên tắc bắt buộc

- Video làm trong `/root/10.Nha_May_San_Xuat_Video`.
- Nếu anh nói dùng template **Video Giọng Đọc Motion** hoặc video ngang không có video người nói, dùng template `02_audio_motion_graphics_1280x720`.
- Nếu anh nói tạo video dọc, Shorts, Reels, TikTok, Zalo/Facebook short video, hoặc cần tỉ lệ điện thoại, dùng template `03_audio_motion_graphics_720x1280`.
- Tên folder output và tên file MP4 cuối phải theo chuẩn Anh Lập Trình: bắt đầu bằng số thứ tự (`00_`, `01_`, `02_`), lowercase, không dấu, dùng `_`, và kết thúc bằng kích thước video trước extension, ví dụ `02_tencent_edgeone_ai_agent_1280x720/02_tencent_edgeone_ai_agent_1280x720.mp4` hoặc `03_short_ai_720x1280/03_short_ai_720x1280.mp4`.
- Quy tắc đặt tên trên áp dụng cho **tất cả template** và mọi video xuất trong `output/`; luôn kiểm tra file chuẩn chung `/root/Apps/video_factory/10.Nha_May_San_Xuat_Video/templates/00_QUY_TAC_DAT_TEN_OUTPUT_VIDEO.md` khi tạo video mới.
- Ebook làm theo chuẩn trong `/root/Second_Brain/07_ebook_chia_se`, không tự bịa chuẩn mới.
- Ebook phải dùng nội dung anh cung cấp làm nguồn chính. Không lan man sang nội dung khác.
- Nếu video chỉ nói về lợi ích, transcript video chỉ nói lợi ích; phần hướng dẫn chi tiết đưa vào ebook.
- Kết quả gửi lại Telegram gồm video MP4 và ebook PDF; kèm Markdown nếu hữu ích để chỉnh sửa.
- Mỗi video hoàn thành phải có thêm file `.txt` cùng tên với file MP4, chứa tiêu đề/caption hấp dẫn để anh dùng đăng Facebook, Zalo, TikTok, YouTube Shorts hoặc các nền tảng mạng xã hội khác.
- Nếu có ebook/PDF đi kèm, phải có thêm file `.txt` cùng tên với file PDF, chứa tiêu đề/caption giới thiệu ebook để anh đăng hoặc gửi kèm tài liệu.
- Sau khi tạo xong video/ebook, phải lưu thông tin đăng bài vào Google Sheet bằng tool trong `/root/05_skill_update_content_ggs/01_up_content_ggs` với đúng 4 cột: `Tiêu Đề`, `Ebook`, `Hình ảnh Hoặc Video`, `Status`.
- Khi ghi Google Sheet, cột `Ebook` lưu link Google Drive public của PDF ebook nếu có ebook; nếu không có ebook thì để trống.
- Khi ghi Google Sheet, cột `Hình ảnh Hoặc Video` chỉ lưu tên file có đuôi như `ten_video.mp4`, `hinh.png`; không lưu đường dẫn đầy đủ.
- Video/ebook mới tạo xong mặc định append Google Sheet với `Status` là `PA`.

## Quy trình ebook chuẩn

1. Đọc `/root/Second_Brain/07_ebook_chia_se/00_tong_quan/00_muc_luc_ebook_chia_se.md`.
2. Đọc template `/root/Second_Brain/07_ebook_chia_se/99_templates/00_template_ebook_chia_se.md`.
3. Ghi ý tưởng vào `/root/Second_Brain/07_ebook_chia_se/01_y_tuong_ebook/00_danh_sach_y_tuong.md` nếu chưa có.
4. Tạo folder đúng chuẩn tên:
   - `/root/Second_Brain/07_ebook_chia_se/02_dang_viet/yyyy_mm_dd_ten_chu_de/`
5. Viết bản Markdown theo cấu trúc:
   - Bìa/thông tin ebook
   - Ebook này giúp bạn làm gì
   - Cần chuẩn bị gì
   - Hướng dẫn từng bước
   - Lỗi thường gặp và cách xử lý
   - Checklist hoàn thành
   - Lời kết, nhắc tinh thần: “Cứ ứng dụng vào công việc đi, vướng thì gỡ.”
6. Copy bản chốt sang:
   - `/root/Second_Brain/07_ebook_chia_se/03_ban_xuat_ban/yyyy_mm_dd_ten_chu_de/`
7. Xuất PDF vào:
   - `/root/Second_Brain/07_ebook_chia_se/04_pdf_da_xuat/yyyy_mm_dd_ten_chu_de.pdf`
8. Tạo file tiêu đề/caption cùng tên với PDF:
   - `/root/Second_Brain/07_ebook_chia_se/04_pdf_da_xuat/yyyy_mm_dd_ten_chu_de.txt`
   - Dòng đầu là tiêu đề ebook hấp dẫn, rõ lợi ích chính.
   - Các dòng sau là caption 2-5 câu ngắn, nói ebook giúp ai, giải quyết việc gì, nên đọc khi nào.
   - Không bịa link tải; nếu cần nhắc tài liệu thì viết theo hướng “Mình gửi kèm ebook này...” hoặc “Anh em có thể xem tài liệu đi kèm...”.
9. Nếu video/ebook được chuẩn bị để đăng Facebook/Zalo, copy thêm PDF và file `.txt` của PDF sang:
   - `/root/05_skill_facebook_zalo/images/yyyy_mm_dd_ten_chu_de.pdf`
   - `/root/05_skill_facebook_zalo/images/yyyy_mm_dd_ten_chu_de.txt`
10. Upload PDF ebook lên Google Drive bằng script:
   - Script: `/root/05_skill_update_content_ggs/01_up_content_ggs/upload_ebook_to_drive.py`
   - Chạy từ folder `/root/05_skill_update_content_ggs/01_up_content_ggs` để dùng đúng `.env` và `googlesheetcn.json`.
   - Câu lệnh mẫu:
     ```bash
     .venv/bin/python upload_ebook_to_drive.py \
       --pdf "/root/05_skill_facebook_zalo/images/yyyy_mm_dd_ten_chu_de.pdf"
     ```
   - Lấy link public trả về để ghi vào cột `Ebook` của Google Sheet.

## Quy trình video chia sẻ lợi ích

1. Tạo transcript ngắn theo thời lượng anh yêu cầu, thường 30-40 giây.
2. Nội dung video tập trung vào lợi ích:
   - Vấn đề trước khi dùng giải pháp
   - Lợi ích chính
   - Tác dụng thực tế cho content/video/ebook/khóa học
   - CTA cuối nếu anh yêu cầu, ví dụ: “Click vào link bên dưới để xem hướng dẫn cài đặt.”
3. Lưu transcript vào `/root/10.Nha_May_San_Xuat_Video/input/`.
4. Tạo audio voice bằng công cụ đang dùng trong workspace video. Nếu dùng HeyGen, giữ metadata đã loại URL/key, không lộ `.env`.
5. Tạo caption timing từ word timestamps thật, không chia đều cảm tính.
6. Render theo HyperFrames. Chạy `npm run check` trước khi render.
7. Render MP4 và copy bản cuối vào:
   - `/root/10.Nha_May_San_Xuat_Video/output/<numbered_project_slug>_<width>x<height>/<numbered_project_slug>_<width>x<height>.mp4`
   - Ví dụ video ngang: `/root/10.Nha_May_San_Xuat_Video/output/02_tencent_edgeone_ai_agent_1280x720/02_tencent_edgeone_ai_agent_1280x720.mp4`
   - Ví dụ video dọc: `/root/10.Nha_May_San_Xuat_Video/output/03_short_ai_720x1280/03_short_ai_720x1280.mp4`
8. Tạo file tiêu đề/caption cùng tên với video:
   - `/root/10.Nha_May_San_Xuat_Video/output/<numbered_project_slug>_<width>x<height>/<numbered_project_slug>_<width>x<height>.txt`
   - Nội dung file `.txt` phải dùng tiếng Việt tự nhiên, có dấu, dễ gây chú ý nhưng không giật tít quá đà.
   - Dòng đầu là tiêu đề chính ngắn, mạnh, hợp nội dung video.
   - Các dòng sau là caption đăng mạng xã hội: 2-5 câu ngắn nêu vấn đề, lợi ích, lời mời xem video hoặc tải ebook nếu có.
   - Nếu video có ebook đi kèm, nhắc nhẹ rằng có tài liệu hướng dẫn chi tiết, nhưng không bịa link.
   - Không đưa hashtag hàng loạt; tối đa 3 hashtag nếu thật sự phù hợp.
9. Luôn copy thêm 1 bản MP4 kết quả sang folder dùng đăng Facebook/Zalo:
   - `/root/05_skill_facebook_zalo/images/<numbered_project_slug>_<width>x<height>.mp4`
   - Nếu folder `/root/05_skill_facebook_zalo/images` chưa có thì tạo folder trước khi copy.
10. Copy thêm file tiêu đề/caption `.txt` sang cùng folder đăng Facebook/Zalo:
   - `/root/05_skill_facebook_zalo/images/<numbered_project_slug>_<width>x<height>.txt`
   - Ngoại lệ: nếu video được tạo từ pipeline `/root/Automation/content_pipeline/05_Facebook_Youtube_Zalo_GGS/01_google_sheet_transcript_video`, không cần tạo/copy file `.txt`; chỉ copy MP4 vào thư mục trend AI tin tức theo prompt pipeline.
11. Lưu thông tin vào Google Sheet bằng script:
   - Script: `/root/05_skill_update_content_ggs/01_up_content_ggs/add_content_to_sheet.py`
   - Chạy từ folder `/root/05_skill_update_content_ggs/01_up_content_ggs` để dùng đúng `.env` và `googlesheetcn.json`.
   - Câu lệnh mẫu:
     ```bash
     .venv/bin/python add_content_to_sheet.py \
       --title "Tiêu đề/caption chính của video" \
       --ebook "https://drive.google.com/file/d/FILE_ID/view?usp=sharing" \
       --media "/root/05_skill_facebook_zalo/images/<project_slug>_video.mp4" \
       --status "PA"
     ```
   - Nếu không có ebook, để `--ebook ""` hoặc bỏ trống trong metadata.
   - Nếu có ebook, không ghi tên file PDF vào cột `Ebook`; phải upload Google Drive và ghi link public của PDF.
   - Nếu có cả hình ảnh và video, ưu tiên ghi file video vào cột `Hình ảnh Hoặc Video` vì đó là nội dung chính để đăng.

## Kiểm tra trước khi gửi

- `npm run check` không có lỗi; warning nhỏ có thể chấp nhận nếu render ổn.
- Video có âm thanh, caption, logo, đúng tỉ lệ ngang 1280x720 khi dùng template Video Giọng Đọc Motion.
- Có thêm bản MP4 trong `/root/05_skill_facebook_zalo/images` để dùng cho Facebook/Zalo.
- Có file `.txt` cùng tên với MP4 trong cả thư mục output video và `/root/05_skill_facebook_zalo/images`, nội dung dùng được ngay làm tiêu đề/caption đăng mạng xã hội.
- Ebook PDF mở được, có tiếng Việt đúng dấu, có cấu trúc đúng chuẩn `07_ebook_chia_se`.
- Nếu có ebook/PDF, có file `.txt` cùng tên với PDF trong `/root/Second_Brain/07_ebook_chia_se/04_pdf_da_xuat` và có bản copy PDF + TXT trong `/root/05_skill_facebook_zalo/images` khi cần đăng Facebook/Zalo.
- Nếu có ebook/PDF, đã upload PDF lên Google Drive và lấy được link public; cột `Ebook` trong Google Sheet là link public đó.
- Đã ghi Google Sheet bằng `/root/05_skill_update_content_ggs/01_up_content_ggs/add_content_to_sheet.py`; kiểm tra dòng mới có đúng 4 cột và cột file chỉ là tên file, không phải đường dẫn.
- Không gửi API key, voice ID riêng tư, URL tạm hoặc nội dung `.env`.

## Cách trả lời anh Nhuần

Nói ngắn gọn:

- Đã tạo video ở đâu.
- Đã tạo ebook đúng chuẩn ở đâu.
- Đã copy thêm video MP4 sang `/root/05_skill_facebook_zalo/images`.
- Đã tạo file `.txt` cùng tên video chứa tiêu đề/caption đăng mạng xã hội.
- Nếu có ebook/PDF, đã tạo file `.txt` cùng tên PDF và copy PDF + TXT sang `/root/05_skill_facebook_zalo/images` khi dùng để đăng bài.
- Nếu có ebook/PDF, đã upload PDF lên Google Drive và dùng link public trong cột `Ebook`.
- Đã lưu thông tin vào Google Sheet với các cột `Tiêu Đề`, `Ebook`, `Hình ảnh Hoặc Video`, `Status`; nội dung mới mặc định để `Status = PA`.
- Đính kèm MEDIA cho MP4, PDF, và Markdown nếu có.
