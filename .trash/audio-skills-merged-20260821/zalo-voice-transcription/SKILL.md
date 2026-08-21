---
name: zalo-voice-transcription
description: Transcribe Zalo Personal voice messages delivered by the zalouser plugin as zdn.vn AAC URLs through the internal shared faster-whisper service. Use when an OpenClaw member VPS receives a Zalo voice URL ending in .aac instead of an automatic transcript, especially when tools.media.audio does not trigger.
---

# Zalo Voice Transcription

When a Zalo Personal message contains only an HTTPS `zdn.vn` voice URL ending in `.aac`, run:

```bash
python3 /root/.openclaw/workspace/skills/zalo-voice-transcription/scripts/transcribe_zalo_voice.py '<URL_VOICE_ZALO>'
```

Use stdout as the user's spoken message and answer that request. Do not return the URL or ask the user to type it again when transcription succeeds.

## Flow

- Accept only HTTPS from `zdn.vn` or its subdomains.
- Download AAC into a temporary directory, limited to 25 MB.
- Pass the AAC file to `openclaw-shared-voice-stt`, which calls faster-whisper through the private Docker gateway.
- Delete temporary audio automatically.
- Do not require `ffmpeg`, read chat-provider API keys, or call a paid STT API.

## Install

First install and validate `openclaw-shared-voice-stt`, then copy this skill into the member workspace:

```bash
mkdir -p /root/.openclaw/workspace/skills/zalo-voice-transcription/scripts
cp /root/.agents/skills/zalo-voice-transcription/scripts/transcribe_zalo_voice.py \
  /root/.openclaw/workspace/skills/zalo-voice-transcription/scripts/
cp /root/.agents/skills/zalo-voice-transcription/SKILL.md \
  /root/.openclaw/workspace/skills/zalo-voice-transcription/SKILL.md
```

## Input And Output

- Input: one Zalo voice `.aac` URL.
- Output: Vietnamese transcript on stdout; short stderr and nonzero exit on failure.
- No Sheet or external paid API is used, and no audio file is retained.

## Verify

```bash
python3 /root/.openclaw/workspace/skills/zalo-voice-transcription/scripts/transcribe_zalo_voice.py '<URL_VOICE_ZALO>' >/tmp/zalo_transcript_test.txt
test -s /tmp/zalo_transcript_test.txt
```

## Safety

- Never print or store the shared token, cookies, or Zalo credentials.
- Reject URLs outside Zalo's `zdn.vn` domain.
- Never put private audio or transcript text in operational logs.
- Do not add a paid STT fallback without explicit approval.
