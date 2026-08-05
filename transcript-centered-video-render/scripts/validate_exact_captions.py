#!/usr/bin/env python3
"""Validate transcript-centered caption timing for video-factory renders."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import unicodedata
from pathlib import Path

WORD_RE = re.compile(r"\S+", re.UNICODE)


def normalize_word(word: str) -> str:
    value = word.strip().lower().replace("đ", "d")
    value = "".join(
        ch for ch in unicodedata.normalize("NFD", value)
        if unicodedata.category(ch) != "Mn"
    )
    return re.sub(r"[^0-9a-z]+", "", value)


def words_from_text(text: str) -> list[str]:
    return [w for w in WORD_RE.findall(text.replace("\ufeff", "").strip()) if normalize_word(w)]


def audio_duration(path: Path) -> float:
    output = subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(path)
    ], text=True)
    return float(output.strip())


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate captions_exact.json against transcript and audio duration.")
    parser.add_argument("--audio", required=True, type=Path)
    parser.add_argument("--transcript", required=True, type=Path)
    parser.add_argument("--captions", required=True, type=Path)
    parser.add_argument("--min-match-ratio", type=float, default=0.95)
    parser.add_argument("--max-end-overrun", type=float, default=0.35)
    parser.add_argument("--max-caption-duration", type=float, default=4.8)
    args = parser.parse_args()

    errors: list[str] = []
    for label, path in [("audio", args.audio), ("transcript", args.transcript), ("captions", args.captions)]:
        if not path.exists():
            errors.append(f"Missing {label}: {path}")
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1

    data = json.loads(args.captions.read_text(encoding="utf-8"))
    captions = data.get("captions", [])
    if not captions:
        errors.append("captions_exact.json has no captions")

    transcript_words = [normalize_word(w) for w in words_from_text(args.transcript.read_text(encoding="utf-8-sig"))]
    caption_words: list[str] = []
    last_end = -1.0
    longest = 0.0
    for index, caption in enumerate(captions):
        start = float(caption.get("start", -1))
        end = float(caption.get("end", -1))
        text = str(caption.get("text", ""))
        word_starts = caption.get("wordStarts", [])
        words = words_from_text(text)
        caption_words.extend(normalize_word(w) for w in words)
        duration = end - start
        longest = max(longest, duration)
        if start < 0 or end <= start:
            errors.append(f"Caption {index} has invalid start/end: {start}-{end}")
        if start < last_end - 0.02:
            errors.append(f"Caption {index} overlaps previous caption")
        if duration > args.max_caption_duration:
            errors.append(f"Caption {index} duration {duration:.2f}s exceeds {args.max_caption_duration:.2f}s")
        if len(word_starts) != len(words):
            errors.append(f"Caption {index} wordStarts count {len(word_starts)} != word count {len(words)}")
        last_end = end

    matched_positions = sum(1 for left, right in zip(transcript_words, caption_words) if left == right)
    order_ratio = matched_positions / max(1, len(transcript_words))
    stored_ratio = float(data.get("match_ratio", order_ratio))
    duration = audio_duration(args.audio)
    final_end = float(captions[-1].get("end", 0)) if captions else 0.0
    if final_end > duration + args.max_end_overrun:
        errors.append(f"Caption end {final_end:.2f}s exceeds audio duration {duration:.2f}s")
    if stored_ratio < args.min_match_ratio:
        errors.append(f"Stored match_ratio {stored_ratio:.3f} below {args.min_match_ratio:.3f}")
    if order_ratio < args.min_match_ratio:
        errors.append(f"Caption text order ratio {order_ratio:.3f} below {args.min_match_ratio:.3f}")

    result = {
        "audio_duration": round(duration, 3),
        "caption_count": len(captions),
        "final_caption_end": round(final_end, 3),
        "longest_caption_duration": round(longest, 3),
        "stored_match_ratio": round(stored_ratio, 4),
        "text_order_ratio": round(order_ratio, 4),
        "transcript_words": len(transcript_words),
        "caption_words": len(caption_words),
        "ok": not errors,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
