# Configuration and Operations

## Environment contract

All values may be supplied by the process environment or a config file passed with `--config`. Process environment values take precedence over the config file.

| Variable | Required | Default | Purpose |
|---|---:|---|---|
| `GIONGAI_API_BASE_URL` | no | `https://api.giongai.cloud/v1` | API root. Both a root URL and a URL ending in `/v1` are accepted. |
| `GIONGAI_AUTH_MODE` | no | `xi-api-key` | `xi-api-key` for direct GiongAI API keys, or `bearer` when the account documentation requires it. |
| `GIONGAI_API_KEY` | one of key options | — | Direct secret value. Prefer a protected key file instead. |
| `GIONGAI_API_KEY_FILE` | one of key options | — | Protected env file containing the key. |
| `GIONGAI_API_KEY_NAME` | with key file | `GIONGAI_API_KEY` | Variable name to read from the key file. |
| `GIONGAI_VOICE_ID` | yes | — | Voice ID selected in the GiongAI account. |
| `GIONGAI_PROVIDER` | no | `minimax` | Provider accepted by the account. |
| `GIONGAI_MODEL_ID` | no | `speech-2.8-turbo` | Model accepted by the provider. |
| `GIONGAI_LANGUAGE_CODE` | no | `Vietnamese` | Language sent to the API. |
| `GIONGAI_SPEED` | no | `1.0` | Voice speed. |
| `GIONGAI_PITCH` | no | `0` | MiniMax pitch setting. |
| `GIONGAI_VOLUME` | no | `1.0` | MiniMax volume setting. |
| `GIONGAI_CHUNK_CHARS` | no | `4200` | Maximum characters submitted per task. |
| `GIONGAI_TIMEOUT_SECONDS` | no | `600` | Polling deadline per task. |

Compatibility fallbacks are supported for an existing video-factory env: `VOICE_API_KEY`, `VOICE_API_VOICE_ID`, `VOICE_API_PROVIDER`, `VOICE_API_MODEL_ID`, and `VOICE_API_BASE_URL`.

## Protected config example

```dotenv
GIONGAI_API_BASE_URL=https://api.giongai.cloud/v1
GIONGAI_AUTH_MODE=xi-api-key
GIONGAI_API_KEY_FILE=/srv/app/secrets/giongai.env
GIONGAI_API_KEY_NAME=GIONGAI_API_KEY
GIONGAI_VOICE_ID=voice-id-from-account
GIONGAI_PROVIDER=minimax
GIONGAI_MODEL_ID=speech-2.8-turbo
GIONGAI_LANGUAGE_CODE=Vietnamese
```

Create the protected file outside the skill directory:

```bash
install -d -m 700 /srv/app/secrets
install -m 600 /dev/null /srv/app/secrets/giongai.env
# Edit it without printing its contents:
# GIONGAI_API_KEY=the-real-key
```

Do not put a real key in `runtime.env.example`, Git, chat, command history, or a generated metadata file.

The skill includes `runtime.env.example` at its root. A standard Linux setup is:

```bash
install -d -m 700 "$HOME/.config/text-file-to-mp3-messenger"
install -m 600 runtime.env.example \
  "$HOME/.config/text-file-to-mp3-messenger/runtime.env"
```

## Checks

```bash
python3 scripts/text_file_to_mp3.py --config /path/runtime.env --doctor
python3 scripts/text_file_to_mp3.py --config /path/runtime.env --self-test --input sample.txt
python3 scripts/text_file_to_mp3.py --help
```

The first check authenticates with a read-only account request. The second checks decoding, cleanup, chunking, and output naming without spending credits. A real conversion should be run only after the owner approves credit usage.

## API flow

For each chunk, the helper sends:

```text
POST {api-base}/text-to-speech/{voice_id}
GET  {api-base}/history/{task_id}
```

The request body contains `text`, `provider`, `model_id`, `language_code`, `voice_settings`, and `export_transcript=false`. The response may be immediate audio or an asynchronous task containing `id`, `task_id`, or `request_id`; the helper accepts the known response variants and looks for `audio_url` only after a successful task state.
