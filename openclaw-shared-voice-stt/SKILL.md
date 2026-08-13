---
name: openclaw-shared-voice-stt
description: Use the internal VPS faster-whisper service to transcribe Telegram attachments or downloaded Zalo voice files locally without a paid STT API. Use after a member OpenClaw has a shared-local-stt token and tools.media.audio CLI configured.
---

# OpenClaw Shared Voice STT

Call the bundled client with one local audio file. The client sends audio only to the internal Docker gateway endpoint and prints the transcript to stdout.

```bash
python3 /root/.openclaw/workspace/skills/openclaw-shared-voice-stt/scripts/transcribe_shared.py /path/to/audio.ogg
```

## Install For A Member

1. Copy `scripts/transcribe_shared.py` into the member workspace.
2. Replace `MEMBER_ID` with the member ID.
3. Store the shared token in `~/.openclaw/credentials/shared-local-stt.token` with mode `0600`.
4. Configure `tools.media.audio.models` to call this client with `{{MediaPath}}`.
5. Validate config, respawn only the OpenClaw gateway, and test with a local fixture.

## Input And Output

- Input: one audio file supported by the shared faster-whisper service, maximum 20 MB.
- Output: transcript text on stdout; nonzero exit on failure.
- Service metrics must not contain audio or transcript text.

## Safety

- Never print the internal token or transcript in operational logs.
- Never copy a member token into documentation or source code.
- Do not add a paid transcription fallback without explicit approval.
- Keep the internal endpoint private to the Docker network.
