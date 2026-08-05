#!/usr/bin/env python3
import json
import subprocess
import sys
from pathlib import Path


ENDPOINT = "http://172.17.0.1:18080/v1/audio/transcriptions"
TOKEN_PATH = Path.home() / ".openclaw" / "credentials" / "shared-local-stt.token"


def main():
    if len(sys.argv) != 2:
        raise SystemExit("Usage: transcribe_shared.py AUDIO_PATH")
    audio_path = Path(sys.argv[1]).resolve()
    if not audio_path.is_file():
        raise SystemExit("Audio file not found")
    token = TOKEN_PATH.read_text(encoding="utf-8").strip()
    result = subprocess.run([
        "curl", "--fail-with-body", "--silent", "--show-error",
        "--max-time", "180",
        "-H", f"Authorization: Bearer {token}",
        "-H", "X-Member-Id: anhlaptrinhthu",
        "-F", f"file=@{audio_path}",
        ENDPOINT,
    ], check=True, capture_output=True, text=True)
    payload = json.loads(result.stdout)
    transcript = str(payload.get("text", "")).strip()
    if not transcript:
        raise RuntimeError("Shared STT returned an empty transcript")
    print(transcript)


if __name__ == "__main__":
    main()
