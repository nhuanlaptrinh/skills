# Mẫu Brief Tạo Video Thật

Dùng mẫu ngắn này thay vì lặp lại toàn bộ checklist vận hành:

```text
Dùng $tao-video-hyperframes trong:
<project_dir>

Transcript:
<transcript_path>

Audio lời đọc có sẵn:
<voice_audio_path>

Tạo video thật <width>x<height>, <fps> fps theo phong cách:
<style>

Các cảnh:
1. <hook>
2. <vấn đề>
3. <giải pháp>
4. <kết luận>

Lưu video cuối tại:
<output_video_path>

Không đọc hoặc sửa `.env`, không ghi đè video production, không publish, không gửi Telegram và không gọi API trả phí.
```

Skill tự xử lý các bước lặp lại: kiểm tra/tải source Drive, workspace an toàn, dùng lại asset local, check trước render, render video thật, `ffprobe`, giải mã toàn file, trích frame, kiểm tra logo và báo cáo đã khử thông tin nhạy cảm.
