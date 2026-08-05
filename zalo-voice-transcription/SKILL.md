---
name: zalo-voice-transcription
description: Transcribe Zalo Personal voice messages delivered by the zalouser plugin as zdn.vn AAC URLs. Use when an OpenClaw member VPS receives a Zalo voice URL ending in .aac instead of an automatic transcript, especially when tools.media.audio does not trigger.
---

# Zalo Voice Transcription

## Cách chạy

Khi tin nhắn Zalo Personal chỉ chứa URL voice `https://...zdn.vn/...aac`, chạy:

```bash
python3 /root/.openclaw/workspace/skills/zalo-voice-transcription/scripts/transcribe_zalo_voice.py '<URL_VOICE_ZALO>'
```

Lấy transcript stdout làm nội dung người dùng vừa nói, rồi trả lời yêu cầu đó. Không gửi lại URL, không nói rằng không nghe được và không yêu cầu người dùng gõ lại nếu script thành công.

## Luồng xử lý

- Chỉ chấp nhận HTTPS từ hostname `zdn.vn` hoặc subdomain của `zdn.vn`.
- Tải AAC vào thư mục tạm, giới hạn 25 MB.
- Dùng `ffmpeg` chuyển sang MP3 mono 16 kHz.
- Gọi `https://codex.anhlaptrinh.vn/v1/audio/transcriptions` với model `gpt-4o-mini-transcribe`, ngôn ngữ `vi`.
- Đọc API key từ provider `openai`, `9rt` hoặc `9r` trong OpenClaw config; không in key.
- Tự xóa file tạm khi kết thúc.

## Cài đặt

Project/script dùng chung:

```bash
apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y ffmpeg
mkdir -p /root/.openclaw/workspace/skills/zalo-voice-transcription/scripts
cp /root/.agents/skills/zalo-voice-transcription/scripts/transcribe_zalo_voice.py \
  /root/.openclaw/workspace/skills/zalo-voice-transcription/scripts/
cp /root/.agents/skills/zalo-voice-transcription/SKILL.md \
  /root/.openclaw/workspace/skills/zalo-voice-transcription/SKILL.md
```

## Input/Output

- Input: một URL voice Zalo `.aac`.
- Output thành công: transcript tiếng Việt trên stdout.
- Output lỗi: thông báo ngắn trên stderr và exit code khác 0.
- Không ghi Sheet/API khác và không giữ file audio sau khi chạy.

## Kiểm tra

```bash
ffmpeg -version | head -1
python3 /root/.openclaw/workspace/skills/zalo-voice-transcription/scripts/transcribe_zalo_voice.py '<URL_VOICE_ZALO>' >/tmp/zalo_transcript_test.txt
test -s /tmp/zalo_transcript_test.txt
```

## An toàn

- Không in hoặc lưu API key, cookie hay Zalo credential.
- Không chấp nhận URL ngoài domain Zalo `zdn.vn`.
- Không đưa transcript/audio riêng tư vào log vận hành hoặc câu trả lời kỹ thuật.
- Không cài `ffmpeg` cho VPS chỉ dùng Telegram; skill này dành cho voice AAC của Zalo Personal.

