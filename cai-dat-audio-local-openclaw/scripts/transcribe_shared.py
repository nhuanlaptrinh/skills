#!/usr/bin/env python3
import json
import subprocess
import sys
from pathlib import Path


ENDPOINT = "http://172.17.0.1:18080/v1/audio/transcriptions"
TOKEN_PATH = Path.home() / ".openclaw" / "credentials" / "shared-local-stt.token"
MEMBER_ID = "replace-me"
MAX_AUDIO_BYTES = 20 * 1024 * 1024


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: transcribe_shared.py AUDIO_PATH")
    audio_path = Path(sys.argv[1]).resolve()
    if not audio_path.is_file():
        raise SystemExit("Audio file not found")
    if audio_path.stat().st_size > MAX_AUDIO_BYTES:
        raise SystemExit("Audio file exceeds the 20 MB limit")
    token = TOKEN_PATH.read_text(encoding="utf-8").strip()
    try:
        result = subprocess.run(
            [
                "curl",
                "--fail-with-body",
                "--silent",
                "--show-error",
                "--max-time",
                "180",
                "-H",
                f"Authorization: Bearer {token}",
                "-H",
                f"X-Member-Id: {MEMBER_ID}",
                "-F",
                f"file=@{audio_path}",
                ENDPOINT,
            ],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as error:
        raise SystemExit("Shared local STT request failed") from error
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise SystemExit("Shared local STT returned an invalid response") from error
    transcript = str(payload.get("text", "")).strip()
    if not transcript:
        raise RuntimeError("Shared STT returned an empty transcript")
    print(transcript)


if __name__ == "__main__":
    main()
