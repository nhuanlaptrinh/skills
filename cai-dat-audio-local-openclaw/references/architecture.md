# Kien Truc Audio OpenClaw

## Inbound STT

### Member/host dung Shared Local STT

```text
Telegram/Zalo attachment
  -> OpenClaw tools.media.audio
  -> unified CLI client + bearer token
  -> 172.17.0.1:18080
  -> faster-whisper small CPU INT8
  -> transcript
```

Dieu kien:

- Shared service active va health endpoint tra thanh cong.
- Container/host truy cap duoc Docker gateway.
- Credential token co mode `0600`; khong nhung token vao JSON/script.
- `tools.media.audio.models` goi `cai-dat-audio-local-openclaw/scripts/transcribe_shared.py`.
- Khong co paid fallback neu yeu cau la zero transcription API cost.

### VPS doc lap dung model local

```text
Telegram/Zalo attachment
  -> OpenClaw tools.media.audio
  -> unified local CLI
  -> ffmpeg WAV 16 kHz mono
  -> faster-whisper small CPU INT8
  -> transcript
```

Can Python venv, `ffmpeg`, `ffprobe`, model cache va quyen doc phu hop voi service user.

### Zalo URL AAC

```text
zalouser message zdn.vn/*.aac
  -> validate HTTPS/domain/size
  -> temporary AAC download
  -> unified shared CLI
  -> transcript
  -> delete temporary audio
```

Luong nay can thiet vi URL trong text khong tu kich hoat `tools.media.audio`.

## Outbound TTS

```text
OpenClaw final text reply
  -> selected Telegram agent tts.auto=inbound|always
  -> Microsoft Edge TTS plugin
  -> text reply + MP3 attachment
```

Giu `messages.tts.auto=off` toan cuc khi runtime co nhieu agent/channel. Chi agent Telegram duoc chon moi override TTS; Zalo va bot khac khong bi anh huong.

## Quy Tac Validation

1. Validate JSON bang CLI OpenClaw cua dung runtime.
2. Shared: health thanh cong; local: import `faster_whisper` va `--help` thanh cong.
3. Test mot fixture audio noi bo; khong gui tin that neu chua duoc phep.
4. Sau respawn/restart, kiem tra channel status va startup log.
5. Neu dung TTS, xac nhan Microsoft plugin da load va text fallback van hoat dong.
6. Quet source/skill de khong chua secret, transcript hoac duong dan credential bi hard-code.

## Tuong Thich Trien Khai Cu

Deployment dang chay co the con tham chieu workspace path:

- `openclaw-local-voice-stt/scripts/transcribe_local.py`
- `openclaw-shared-voice-stt/scripts/transcribe_shared.py`
- `zalo-voice-transcription/scripts/transcribe_zalo_voice.py`

Khong doi cac path production nay chi de don ten skill. Installer moi dung path unified; migrate production chi khi co task rieng, backup va test rollback.
