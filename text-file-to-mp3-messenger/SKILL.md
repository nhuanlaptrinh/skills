---
name: text-file-to-mp3-messenger
description: Convert an inbound text document into an MP3 with the GiongAI/taogiongai API and deliver the finished audio back to the same Telegram or Zalo conversation. Use when a user sends a .txt, .md, .srt, .vtt, .csv, .json, .html, .docx, or another supported text file and asks for voice/audio/MP3, or asks to install this reusable Telegram/Zalo text-to-audio workflow.
---

# Text File To MP3 Messenger

This skill turns one exact inbound text attachment into one MP3, then sends that MP3 back through the same Telegram or Zalo conversation. The implementation is shared by both channels. Resolve the skill directory from the active installation; the standard Linux location is:

`$HOME/.agents/skills/text-file-to-mp3-messenger/scripts/text_file_to_mp3.py`

The script submits asynchronous jobs to GiongAI/taogiongai, polls until each job is complete, downloads the returned audio, joins long-text chunks with FFmpeg, and verifies the final MP3.

## Required workflow

1. Identify the exact file attached to the current inbound message. Do not search for the newest file in a directory and do not use an attachment from another request.
2. Use the current agent's workspace `media/` directory as the output directory. Derive it from the active agent workspace; do not hardcode a different machine's workspace.
3. If generation is likely to take more than 10 seconds, send one short progress acknowledgement with the platform-native messaging tool before starting the work. Do not put future-tense progress text in the normal assistant reply that launches the command.
4. Run the helper with a stable request key made from the current channel/account/chat/message identifiers. Never use an outbound message ID as the only request key.

Portable Linux example:

```bash
SKILL_DIR="$HOME/.agents/skills/text-file-to-mp3-messenger"
CONFIG="$HOME/.config/text-file-to-mp3-messenger/runtime.env"
python3 "$SKILL_DIR/scripts/text_file_to_mp3.py" \
  --config "$CONFIG" \
  --input /exact/path/from/the/current/inbound/file.txt \
  --output-dir "$HOME/.openclaw/workspace/media" \
  --request-key 'telegram:current-chat:current-message'
```

For Zalo, keep the same command but use the active Zalo workspace `media/` directory and the current Zalo request identifiers. The script prints JSON containing the canonical `output` path; use that exact path for delivery.

5. Confirm the command exited successfully, the returned path exists, and the file is a readable MP3. The helper already runs `ffprobe`; if it fails, do not send the file.
6. Deliver exactly one attachment to the same conversation using the platform-native route. For Telegram, natural wording such as `Gửi file vừa tạo` lets the Telegram media broker target the current conversation. For Zalo, use the native Zalo attachment/file route and wait for a real delivery receipt.
7. Treat delivery as successful only when the receipt has a real message ID and matches the current destination. Do not retry an ambiguous upload until receipts/history have been checked. After a verified native delivery, finish the channel turn with `NO_REPLY` when the runtime requires it.

## Configuration

The API key must come from the server-side secret environment, never from this skill, a chat message, logs, metadata, or a public frontend. On a fresh machine, create a mode-600 env file and set at least:

```dotenv
GIONGAI_API_BASE_URL=https://api.giongai.cloud/v1
GIONGAI_AUTH_MODE=xi-api-key
GIONGAI_API_KEY=PUT_THE_SERVER_SIDE_KEY_HERE
GIONGAI_VOICE_ID=PUT_THE_VOICE_ID_HERE
GIONGAI_PROVIDER=minimax
GIONGAI_MODEL_ID=speech-2.8-turbo
GIONGAI_LANGUAGE_CODE=Vietnamese
```

Prefer `GIONGAI_API_KEY_FILE` plus `GIONGAI_API_KEY_NAME` when a deployment already has a protected env file, so the key is not copied into a second file.

Run the non-billing connectivity check before a new deployment:

```bash
python3 "$HOME/.agents/skills/text-file-to-mp3-messenger/scripts/text_file_to_mp3.py" \
  --config "$HOME/.config/text-file-to-mp3-messenger/runtime.env" --doctor
```

`--doctor` calls the authenticated account endpoint and does not submit a speech job. If the API key was copied from `https://giongai.cloud/app`, keep `GIONGAI_AUTH_MODE=xi-api-key` unless the account's API documentation explicitly says the key uses Bearer authentication. The helper supports both modes.

## Supported input

- Plain text-like files: `.txt`, `.md`, `.csv`, `.json`, `.srt`, `.vtt`, `.html`, `.htm`, `.xml`.
- `.docx` is read with the Python standard library.
- The default input limit is 10 MiB and the default extracted-text limit is 200,000 characters. Do not silently process a different file or truncate user content; report the limit and ask the user to split the document.
- SRT/VTT timestamps and cue numbers are removed. Basic Markdown/HTML presentation markup is removed while keeping readable text.
- Unsupported binary formats such as PDF, DOC, and images need a separate extraction step; do not send their raw bytes to the TTS endpoint.

## Fresh-machine setup

1. Install `python3` and `ffmpeg`.
2. Copy this entire skill directory to `$HOME/.agents/skills/text-file-to-mp3-messenger`, preserving `scripts/`.
3. Create a protected runtime config from the included template:

```bash
install -d -m 700 "$HOME/.config/text-file-to-mp3-messenger"
install -m 600 \
  "$HOME/.agents/skills/text-file-to-mp3-messenger/runtime.env.example" \
  "$HOME/.config/text-file-to-mp3-messenger/runtime.env"
```

Edit that protected file with the API key and voice ID, or point `GIONGAI_API_KEY_FILE` at an already protected env file.
4. Set a valid voice ID from the GiongAI account. Do not guess a voice ID. `GIONGAI_VOICE_ID` can be replaced per request with `--voice-id`.
5. Run `--doctor`, then run the local self-test with a small sample file. No systemd service or cron job is required: the Telegram/Zalo OpenClaw agent invokes the helper only when a user requests conversion.
6. Apply the channel's normal media-delivery and duplicate-suppression rules. Do not broaden filesystem allowlists or channel permissions just for this skill.

See `references/configuration.md` for the environment contract and operational checks.

## Safety boundaries

- Never print or echo API keys, cookies, tokens, or the contents of the protected env file.
- Keep one request coordinator per inbound message. The helper reuses a verified existing output for the same input digest unless `--force` is explicitly requested, which helps prevent duplicate credit usage.
- Never send to a guessed chat, group, thread, or account. Never send an intermediate chunk; only send the verified final MP3.
- Do not enable OpenClaw automatic reply TTS for this workflow. This skill creates an explicit MP3 attachment from a user-provided text file.
- If authentication, credits, rate limits, provider errors, polling timeout, or upload acknowledgement fails, report the exact safe state and do not claim that audio was delivered.
