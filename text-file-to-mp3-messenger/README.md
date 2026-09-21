# Text File To MP3 Messenger

OpenClaw skill that converts an inbound text document to MP3 through GiongAI,
then returns the verified audio to the same Telegram or Zalo conversation.

## Install on another Linux VPS

```bash
git clone https://github.com/giangcr7/text-file-to-mp3-messenger.git "$HOME/.agents/skills/text-file-to-mp3-messenger"
chmod 755 "$HOME/.agents/skills/text-file-to-mp3-messenger/scripts/text_file_to_mp3.py"
```

Install runtime requirements with the operating system package manager:

```bash
sudo apt-get update
sudo apt-get install -y python3 ffmpeg git
```

Create the protected configuration:

```bash
install -d -m 700 "$HOME/.config/text-file-to-mp3-messenger"
install -m 600 \
  "$HOME/.agents/skills/text-file-to-mp3-messenger/runtime.env.example" \
  "$HOME/.config/text-file-to-mp3-messenger/runtime.env"
```

Edit `runtime.env` and replace only the placeholders with the API key and voice
ID from the GiongAI account. Never commit or send that protected file through a
chat application.

Validate without creating paid audio:

```bash
python3 "$HOME/.agents/skills/text-file-to-mp3-messenger/scripts/text_file_to_mp3.py" \
  --config "$HOME/.config/text-file-to-mp3-messenger/runtime.env" \
  --doctor
```

Verify OpenClaw discovery:

```bash
openclaw skills info text-file-to-mp3-messenger
```

See `SKILL.md` for the Telegram/Zalo workflow and `references/configuration.md`
for all environment variables.
