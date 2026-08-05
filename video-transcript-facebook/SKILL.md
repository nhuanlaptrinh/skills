---
name: video-transcript-facebook
description: "Lấy transcript/phụ đề từ video Facebook (Reels, video công khai) bằng yt-dlp + 9Router STT Whisper. Use when Codex needs to get text transcript, captions, subtitles, speech-to-text từ Facebook video URL. Facebook không có transcript API công cộng, skill này tải audio rồi dùng Whisper API để nhận dạng giọng nói."
---

# Video Transcript Facebook

Lấy transcript nội dung video Facebook bằng cách:
1. Tải audio từ Facebook video bằng `yt-dlp`
2. Chuyển đổi audio sang định dạng phù hợp bằng `ffmpeg`
3. Gửi lên **9Router STT** (Whisper API) để nhận dạng giọng nói → transcript
4. Xuất ra file `.txt`, `.srt` (phụ đề), `.json` (có timestamp)

## Yêu Cầu

```bash
# yt-dlp - tải audio từ Facebook
apt-get install -y yt-dlp

# ffmpeg - chuyển đổi audio
apt-get install -y ffmpeg

# 9Router STT - cần NINEROUTER_URL + NINEROUTER_KEY
echo "NINEROUTER_URL=$NINEROUTER_URL"
echo "NINEROUTER_KEY=${NINEROUTER_KEY:+đã có}"
```

## Cách Dùng

### Lệnh cơ bản

```bash
python3 /root/.agents/skills/video-transcript-facebook/scripts/facebook_transcript.py \
  "https://www.facebook.com/reel/1890122975007643" \
  --output-dir /tmp/facebook-transcript
```

### Kết quả

Trong thư mục output sẽ có:

| File | Nội dung |
|---|---|
| `transcript.txt` | Transcript full text |
| `transcript.srt` | Phụ đề định dạng SRT (có timestamp) |
| `transcript.json` | JSON chi tiết segments + timestamps |
| `audio.mp3` | Audio gốc tải từ Facebook (để kiểm tra) |

### Workflow với HyperFrames hoặc pipeline

```bash
FB_URL="https://www.facebook.com/reel/1890122975007643"
OUTPUT="/root/hyperframes/templates/video-clone-ytb/assets"

# Bước 1: Lấy transcript
python3 /root/.agents/skills/video-transcript-facebook/scripts/facebook_transcript.py \
  "$FB_URL" --output-dir "$OUTPUT" --lang vi

# Bước 2: Xem transcript
cat "$OUTPUT/transcript.txt"

# Bước 3: Dùng transcript cho pipeline tiếp theo
```

## Các Tham Số

| Tham số | Mô tả |
|---|---|
| `URL` | Facebook video/reel URL (bắt buộc) |
| `--output-dir` | Thư mục lưu kết quả (mặc định: `facebook-transcript-<videoId>`) |
| `--lang` | Ngôn ngữ, VD: `vi`, `en` (mặc định: `vi`) |
| `--model` | Model STT, VD: `openai/whisper-1`, `openai/whisper-1` (mặc định: `openai/whisper-1`) |
| `--keep-audio` | Giữ lại file audio sau khi xử lý |
| `--no-caption-fallback` | Không thử tải caption từ yt-dlp, chỉ dùng STT |

## Xử Lý Lỗi

- Nếu `yt-dlp` không tải được audio → báo lỗi URL không hợp lệ hoặc video private
- Nếu `9Router STT` không khả dụng → kiểm tra `NINEROUTER_URL` và `NINEROUTER_KEY`
- Audio quá dài (>25MB với một số model) → tự động split thành đoạn nhỏ

## Lưu Ý

- **Facebook không có API transcript công cộng** nên bắt buộc phải qua STT (Whisper).
- Model `openai/whisper-1` chạy nhanh nhất, phù hợp cho tiếng Việt.
- Video càng dài, thời gian xử lý càng lâu (audio length).
- Nếu video có phụ đề ẩn (auto-captions), yt-dlp có thể tải được VTT, skill sẽ ưu tiên dùng caption thay vì STT.

## Google Sheet Queue

Tương tự workflow video-clone-ytb, có thể đọc từ Google Sheet:

| Cột | Mô tả |
|---|---|
| `LinkFacebook` | URL Facebook video |
| `Status` | `Run` → `Pro` → `Success` / `Error` |
| `Transcript` | Transcript text sẽ được ghi lại |

## Ví Dụ Nhanh

```bash
# Lấy transcript từ Facebook Reel
python3 /root/.agents/skills/video-transcript-facebook/scripts/facebook_transcript.py \
  "https://www.facebook.com/reel/1890122975007643" \
  --output-dir /tmp/fb-reel-1 --lang vi --keep-audio

# Xem kết quả
cat /tmp/fb-reel-1/transcript.txt
cat /tmp/fb-reel-1/transcript.srt
```
