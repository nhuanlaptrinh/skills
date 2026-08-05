#!/usr/bin/env python3
import argparse
import json
import mimetypes
import os
import secrets
import subprocess
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


MAX_AUDIO_BYTES = 25 * 1024 * 1024
TRANSCRIPTION_URL = "https://codex.anhlaptrinh.vn/v1/audio/transcriptions"


def fail(message: str) -> None:
    print(message, file=sys.stderr)
    raise SystemExit(1)


def validate_url(raw_url: str) -> str:
    parsed = urllib.parse.urlparse(raw_url)
    hostname = (parsed.hostname or "").lower()
    if parsed.scheme != "https" or not (hostname == "zdn.vn" or hostname.endswith(".zdn.vn")):
        fail("URL voice Zalo không hợp lệ")
    return raw_url


def find_config() -> Path:
    candidates = [
        os.environ.get("OPENCLAW_CONFIG"),
        "/root/.openclaw/openclaw.json",
        str(Path.home() / ".openclaw" / "openclaw.json"),
    ]
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return Path(candidate)
    fail("Không tìm thấy OpenClaw config")


def load_api_key() -> str:
    config = json.loads(find_config().read_text(encoding="utf-8"))
    providers = config.get("models", {}).get("providers", {})
    for provider_name in ("openai", "9rt", "9r"):
        api_key = providers.get(provider_name, {}).get("apiKey")
        if api_key:
            return api_key
    fail("Không tìm thấy credential 9Router trong OpenClaw config")


def download_audio(url: str, destination: Path) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": "OpenClaw-ZaloVoice/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response, destination.open("wb") as output:
            total = 0
            while True:
                chunk = response.read(64 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > MAX_AUDIO_BYTES:
                    fail("Voice Zalo vượt giới hạn 25 MB")
                output.write(chunk)
    except urllib.error.URLError as error:
        fail(f"Không tải được voice Zalo: {error.reason}")


def convert_to_mp3(source: Path, destination: Path) -> None:
    command = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-i", str(source), "-vn", "-ac", "1", "-ar", "16000",
        "-codec:a", "libmp3lame", "-b:a", "64k", str(destination),
    ]
    result = subprocess.run(command, capture_output=True, text=True, timeout=120, check=False)
    if result.returncode != 0 or not destination.is_file() or destination.stat().st_size == 0:
        fail("Không chuyển đổi được voice Zalo sang MP3")


def multipart_body(audio_path: Path) -> tuple[bytes, str]:
    boundary = f"----OpenClawZaloVoice{secrets.token_hex(12)}"
    audio = audio_path.read_bytes()
    parts = []
    for name, value in (("model", "gpt-4o-mini-transcribe"), ("language", "vi")):
        parts.append(
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"\r\n\r\n{value}\r\n".encode()
        )
    content_type = mimetypes.guess_type(audio_path.name)[0] or "audio/mpeg"
    parts.append(
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"voice.mp3\"\r\nContent-Type: {content_type}\r\n\r\n".encode()
        + audio
        + b"\r\n"
    )
    parts.append(f"--{boundary}--\r\n".encode())
    return b"".join(parts), boundary


def transcribe(audio_path: Path, api_key: str) -> str:
    body, boundary = multipart_body(audio_path)
    request = urllib.request.Request(
        TRANSCRIPTION_URL,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        fail(f"STT 9Router trả HTTP {error.code}")
    except (urllib.error.URLError, json.JSONDecodeError) as error:
        fail(f"Không gọi được STT 9Router: {error}")
    transcript = payload.get("text") or payload.get("transcript")
    if not isinstance(transcript, str) or not transcript.strip():
        fail("STT không trả transcript")
    return transcript.strip()


def main() -> None:
    parser = argparse.ArgumentParser(description="Transcribe a Zalo Personal AAC voice URL")
    parser.add_argument("url", help="HTTPS zdn.vn voice URL")
    args = parser.parse_args()
    url = validate_url(args.url)
    api_key = load_api_key()
    with tempfile.TemporaryDirectory(prefix="zalo-voice-") as temp_dir:
        source = Path(temp_dir) / "voice.aac"
        converted = Path(temp_dir) / "voice.mp3"
        download_audio(url, source)
        convert_to_mp3(source, converted)
        print(transcribe(converted, api_key))


if __name__ == "__main__":
    main()
