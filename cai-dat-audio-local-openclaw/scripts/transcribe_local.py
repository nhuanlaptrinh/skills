#!/usr/bin/env python3
import argparse
import fcntl
import json
import os
import resource
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser(description="Offline speech-to-text with faster-whisper")
    parser.add_argument("audio_path")
    parser.add_argument("--model", default=os.getenv("LOCAL_STT_MODEL", "small"))
    parser.add_argument("--language", default=os.getenv("LOCAL_STT_LANGUAGE", "vi"))
    return parser.parse_args()


def run(command):
    return subprocess.run(command, check=True, capture_output=True, text=True)


def audio_duration(path):
    result = run([
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(path),
    ])
    return float(result.stdout.strip())


def append_metrics(log_path, payload):
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def main():
    args = parse_args()
    source = Path(args.audio_path).resolve()
    if not source.is_file():
        raise FileNotFoundError(f"Audio file not found: {source}")
    if source.stat().st_size > 20 * 1024 * 1024:
        raise ValueError("Audio exceeds the 20 MB local STT limit")

    duration = audio_duration(source)
    if duration <= 0 or duration > 600:
        raise ValueError("Audio duration must be between 0 and 600 seconds")

    home = Path.home()
    lock_path = home / ".openclaw" / "tools" / "local-stt.lock"
    metrics_path = home / ".openclaw" / "logs" / "local-stt-metrics.jsonl"
    lock_path.parent.mkdir(parents=True, exist_ok=True)

    started_wall = time.monotonic()
    started_cpu = time.process_time()
    status = "error"
    transcript = ""
    error_type = ""

    try:
        with lock_path.open("w", encoding="utf-8") as lock_handle:
            fcntl.flock(lock_handle, fcntl.LOCK_EX)
            with tempfile.TemporaryDirectory(prefix="openclaw-local-stt-") as temp_dir:
                normalized = Path(temp_dir) / "audio.wav"
                run([
                    "ffmpeg",
                    "-nostdin",
                    "-loglevel",
                    "error",
                    "-i",
                    str(source),
                    "-ac",
                    "1",
                    "-ar",
                    "16000",
                    "-c:a",
                    "pcm_s16le",
                    str(normalized),
                ])

                from faster_whisper import WhisperModel

                model = WhisperModel(
                    args.model,
                    device="cpu",
                    compute_type="int8",
                    cpu_threads=int(os.getenv("LOCAL_STT_CPU_THREADS", "4")),
                    num_workers=1,
                    download_root=str(home / ".cache" / "faster-whisper"),
                )
                segments, _ = model.transcribe(
                    str(normalized),
                    language=args.language,
                    beam_size=3,
                    vad_filter=True,
                    condition_on_previous_text=True,
                )
                transcript = " ".join(segment.text.strip() for segment in segments).strip()
                if not transcript:
                    raise RuntimeError("No speech was detected")
                status = "ok"
                print(transcript)
    except Exception as exc:
        error_type = type(exc).__name__
        print(f"Local STT failed: {error_type}", file=sys.stderr)
        raise
    finally:
        wall_seconds = max(time.monotonic() - started_wall, 0.001)
        cpu_seconds = max(time.process_time() - started_cpu, 0.0)
        max_rss_mb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
        append_metrics(metrics_path, {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": status,
            "model": args.model,
            "language": args.language,
            "audio_seconds": round(duration, 3),
            "wall_seconds": round(wall_seconds, 3),
            "cpu_seconds": round(cpu_seconds, 3),
            "cpu_percent_equivalent": round(cpu_seconds / wall_seconds * 100, 1),
            "max_rss_mb": round(max_rss_mb, 1),
            "transcript_chars": len(transcript),
            "error_type": error_type,
        })


if __name__ == "__main__":
    main()
