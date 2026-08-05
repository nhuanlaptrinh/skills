---
name: magicvoice-direct-audio
description: Generate MP3/WAV audio directly from text using the local MagicVoice/OmniVoice project on this VPS. Use when the user asks to chạy trực tiếp tạo audio, tạo giọng đọc bằng Nhuan Voice, sinh audio không qua Telegram bot, use MagicVoice_Client, OmniVoice, voices_library.json, clone_refs, or needs a short command to create TTS output from transcript/text.
---

# MagicVoice Direct Audio

Use the local project at:

`/root/Apps/huggingface_audio/hub/models--k2-fsa--OmniVoice/MagicVoice_Client`

## Quick Command

Generate audio from inline text with the default owner voice clone (`Nhuan Voice V2`):

```bash
cd /root/Apps/huggingface_audio/hub/models--k2-fsa--OmniVoice/MagicVoice_Client
./mv-tts "Nội dung cần đọc"
```

Generate audio from a text file:

```bash
cd /root/Apps/huggingface_audio/hub/models--k2-fsa--OmniVoice/MagicVoice_Client
./mv-tts --text-file /path/to/transcript.txt
```

To override the voice explicitly, pass the voice name before the text:

```bash
./mv-tts "Other Voice Name" "Nội dung cần đọc"
```

Output files are saved to:

`/root/Apps/huggingface_audio/hub/models--k2-fsa--OmniVoice/MagicVoice_Client/output_direct`

## Workflow

1. Use `Nhuan Voice V2` by default for the owner's voice clone unless the user explicitly asks for another voice.
2. Check the voice exists in `voices_library.json`.
3. Check `ref_audio` exists under `clone_refs/` or as an absolute path.
4. Run `./mv-tts "text"` from `MagicVoice_Client` for the default voice, or `./mv-tts "Voice Name" "text"` only when overriding.
5. If text is long or multi-line, write it to a `.txt` file and run `./mv-tts --text-file file.txt`.
6. Report the final `.mp3` path to the user.

## Notes

- The command uses the project venv at `MagicVoice_Client/venv`.
- The command sets Hugging Face cache paths to `/root/Apps/huggingface_audio` to avoid re-downloading models.
- Default voice for the owner's clone is `Nhuan Voice V2`, backed by `clone_refs/Nhuan Voice V2.mp3`.
- CPU generation can take a few minutes for longer text.
- Do not print `.env`, bot tokens, Firebase credentials, or private logs.

## Useful Service Commands

Telegram bot status is separate from direct generation:

```bash
systemctl status magicvoice-telegram-bot.service
systemctl restart magicvoice-telegram-bot.service
```
