# Kiến Trúc Cài Audio Local OpenClaw

## Member Shared

```text
Telegram/Zalo voice
  -> OpenClaw member container
  -> CLI client + bearer token
  -> 172.17.0.1:18080
  -> Shared faster-whisper small CPU INT8
  -> transcript
```

Điều kiện:

- Shared service active và health endpoint trả `status=ok`.
- Container truy cập được Docker gateway.
- Firewall chỉ allow subnet Docker.
- Member credential chứa token đúng, mode `600`.
- `tools.media.audio.models` chỉ có CLI shared client nếu không cho phép paid fallback.

## Standalone Local

```text
Telegram/Zalo voice
  -> OpenClaw
  -> local Python CLI
  -> ffmpeg normalize WAV 16 kHz mono
  -> faster-whisper small CPU INT8
  -> transcript
```

Điều kiện:

- Python venv và `faster-whisper` cài thành công.
- Model cache tồn tại sau warm-up.
- `ffmpeg` và `ffprobe` có trong PATH.
- OpenClaw service user đọc được venv, workspace script và model cache.

## Quy Tắc Validation

1. `jq empty openclaw.json`.
2. Không có provider transcription trả phí trong `tools.media.audio.models`.
3. CLI `--help` chạy thành công.
4. Health shared hoặc import `faster_whisper` local thành công.
5. Test một audio nội bộ; không gửi tin thật nếu chưa được phép.
6. Kiểm tra channel status sau restart.
7. Quét skill/script để không chứa secret.
