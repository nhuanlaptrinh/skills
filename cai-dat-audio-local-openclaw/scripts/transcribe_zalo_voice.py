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
CANONICAL_CLIENT_DIR = Path(__file__).resolve().parent
CANONICAL_SHARED_CLIENT = CANONICAL_CLIENT_DIR / "transcribe_shared.py"
CANONICAL_LOCAL_CLIENT = CANONICAL_CLIENT_DIR / "transcribe_local.py"
LEGACY_SHARED_CLIENT = (
    Path.home()
    / ".openclaw"
    / "workspace"
    / "skills"
    / "openclaw-shared-voice-stt"
    / "scripts"
    / "transcribe_shared.py"
)
LEGACY_LOCAL_CLIENT = (
    Path.home()
    / ".openclaw"
    / "workspace"
    / "skills"
    / "openclaw-local-voice-stt"
    / "scripts"
    / "transcribe_local.py"
)
LOCAL_STT_PYTHON = Path.home() / ".openclaw" / "tools" / "local-stt-venv" / "bin" / "python"
SHARED_TOKEN_PATH = Path.home() / ".openclaw" / "credentials" / "shared-local-stt.token"


def default_stt_client() -> Path:
    if SHARED_TOKEN_PATH.is_file():
        for candidate in (CANONICAL_SHARED_CLIENT, LEGACY_SHARED_CLIENT):
            if candidate.is_file():
                return candidate
    for candidate in (CANONICAL_LOCAL_CLIENT, LEGACY_LOCAL_CLIENT):
        if candidate.is_file() and LOCAL_STT_PYTHON.is_file():
            return candidate
    for candidate in (CANONICAL_SHARED_CLIENT, LEGACY_SHARED_CLIENT):
        if candidate.is_file():
            return candidate
    return CANONICAL_SHARED_CLIENT


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


def transcribe(audio_path: Path, stt_client: Path) -> str:
    if not stt_client.is_file():
        fail("Khong tim thay local STT client")
    interpreter = sys.executable
    if stt_client.name == "transcribe_local.py" and LOCAL_STT_PYTHON.is_file():
        interpreter = str(LOCAL_STT_PYTHON)
    try:
        result = subprocess.run(
            [interpreter, str(stt_client), str(audio_path)],
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
        )
    except subprocess.TimeoutExpired:
        fail("Local STT qua thoi gian xu ly")
    transcript = result.stdout.strip()
    if result.returncode != 0 or not transcript:
        fail("Local STT khong tra transcript")
    return transcript


def main() -> None:
    parser = argparse.ArgumentParser(description="Transcribe a Zalo Personal AAC voice URL")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("url", nargs="?", help="HTTPS zdn.vn voice URL")
    source.add_argument("--audio-file", type=Path, help=argparse.SUPPRESS)
    parser.add_argument(
        "--stt-client",
        "--shared-client",
        dest="stt_client",
        type=Path,
        default=default_stt_client(),
        help="Path to a shared or standalone local STT client",
    )
    args = parser.parse_args()
    stt_client = args.stt_client.expanduser().resolve()
    if args.audio_file:
        audio_path = args.audio_file.expanduser().resolve()
        if not audio_path.is_file():
            fail("Khong tim thay file audio")
        if audio_path.stat().st_size > MAX_AUDIO_BYTES:
            fail("Voice Zalo vuot gioi han 25 MB")
        print(transcribe(audio_path, stt_client))
        return
    url = validate_url(args.url)
    with tempfile.TemporaryDirectory(prefix="zalo-voice-") as temp_dir:
        source = Path(temp_dir) / "voice.aac"
        download_audio(url, source)
        print(transcribe(source, stt_client))


if __name__ == "__main__":
    main()
