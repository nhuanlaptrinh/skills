#!/usr/bin/env python3
import argparse
import subprocess
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


MAX_AUDIO_BYTES = 25 * 1024 * 1024
DEFAULT_SHARED_CLIENT = (
    Path.home()
    / ".openclaw"
    / "workspace"
    / "skills"
    / "openclaw-shared-voice-stt"
    / "scripts"
    / "transcribe_shared.py"
)


def fail(message: str) -> None:
    print(message, file=sys.stderr)
    raise SystemExit(1)


def validate_url(raw_url: str) -> str:
    parsed = urllib.parse.urlparse(raw_url)
    hostname = (parsed.hostname or "").lower()
    if parsed.scheme != "https" or not (hostname == "zdn.vn" or hostname.endswith(".zdn.vn")):
        fail("URL voice Zalo khong hop le")
    return raw_url


def download_audio(url: str, destination: Path) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": "OpenClaw-ZaloVoice/2.0"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response, destination.open("wb") as output:
            total = 0
            while True:
                chunk = response.read(64 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > MAX_AUDIO_BYTES:
                    fail("Voice Zalo vuot gioi han 25 MB")
                output.write(chunk)
    except urllib.error.URLError as error:
        fail(f"Khong tai duoc voice Zalo: {error.reason}")


def transcribe(audio_path: Path, shared_client: Path) -> str:
    if not shared_client.is_file():
        fail("Khong tim thay shared local STT client")
    try:
        result = subprocess.run(
            [sys.executable, str(shared_client), str(audio_path)],
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
        )
    except subprocess.TimeoutExpired:
        fail("Shared local STT qua thoi gian xu ly")
    transcript = result.stdout.strip()
    if result.returncode != 0 or not transcript:
        fail("Shared local STT khong tra transcript")
    return transcript


def main() -> None:
    parser = argparse.ArgumentParser(description="Transcribe a Zalo Personal AAC voice URL")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("url", nargs="?", help="HTTPS zdn.vn voice URL")
    source.add_argument("--audio-file", type=Path, help=argparse.SUPPRESS)
    parser.add_argument(
        "--shared-client",
        type=Path,
        default=DEFAULT_SHARED_CLIENT,
        help="Path to the internal shared local STT client",
    )
    args = parser.parse_args()
    shared_client = args.shared_client.expanduser().resolve()
    if args.audio_file:
        audio_path = args.audio_file.expanduser().resolve()
        if not audio_path.is_file():
            fail("Khong tim thay file audio")
        if audio_path.stat().st_size > MAX_AUDIO_BYTES:
            fail("Voice Zalo vuot gioi han 25 MB")
        print(transcribe(audio_path, shared_client))
        return
    url = validate_url(args.url)
    with tempfile.TemporaryDirectory(prefix="zalo-voice-") as temp_dir:
        source = Path(temp_dir) / "voice.aac"
        download_audio(url, source)
        print(transcribe(source, shared_client))


if __name__ == "__main__":
    main()
