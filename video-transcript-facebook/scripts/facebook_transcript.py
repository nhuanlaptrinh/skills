#!/usr/bin/env python3
"""
facebook_transcript.py - Lấy transcript từ Facebook video
Dùng yt-dlp tải audio + caption, fallback 9Router STT (Whisper API)
"""

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.parse
from pathlib import Path

# ─── Helpers ────────────────────────────────────────────────────────────────

def run(cmd, **kwargs):
    """Run a command and return stdout, stderr, returncode."""
    result = subprocess.run(cmd, capture_output=True, text=True, **kwargs)
    return result.stdout.strip(), result.stderr.strip(), result.returncode


def extract_video_id(url):
    """Extract Facebook video ID from URL."""
    # Pattern: /reel/ID or /videos/ID or watch?v=ID
    m = re.search(r'/(?:reel|videos)/(\d+)', url)
    if m:
        return m.group(1)
    m = re.search(r'[?&]v=(\d+)', url)
    if m:
        return m.group(1)
    # Fallback: hash the URL
    return str(hash(url) & 0xFFFFFFFF)


def download_audio(url, output_dir, keep_audio=True):
    """Download audio from Facebook video using yt-dlp."""
    print(f"[1/4] Đang tải audio từ Facebook...")
    audio_path = os.path.join(output_dir, "audio.mp3")
    
    cmd = [
        "yt-dlp", "-x", "--audio-format", "mp3",
        "-o", audio_path.replace(".mp3", ".%(ext)s"),
        "--no-playlist",
        "--socket-timeout", "30",
        url
    ]
    
    stdout, stderr, rc = run(cmd)
    if rc != 0:
        # Try with cookies/proxy fallback
        print("  ⚠️  Thử lại không có proxy...")
        cmd += ["--no-proxy"]
        stdout, stderr, rc = run(cmd)
    
    if rc != 0:
        print(f"  ❌ Lỗi tải audio: {stderr[:200]}")
        return None
    
    # Find the actual file
    for f in os.listdir(output_dir):
        if f.startswith("audio."):
            actual_path = os.path.join(output_dir, f)
            # Rename to audio.mp3 if needed
            if f != "audio.mp3":
                os.rename(actual_path, audio_path)
            break
    
    if os.path.exists(audio_path):
        size = os.path.getsize(audio_path)
        print(f"  ✅ Audio tải xong: {size/1024:.1f} KB")
        return audio_path
    
    return None


def try_get_captions(url, output_dir):
    """Try to download captions from Facebook video using yt-dlp."""
    print(f"[2/4] Đang thử tải caption/phụ đề từ Facebook...")
    
    cmd = [
        "yt-dlp", "--skip-download",
        "--write-subs", "--write-auto-subs",
        "--sub-langs", "all",
        "--sub-format", "vtt/txt",
        "-o", os.path.join(output_dir, "caption.%(ext)s"),
        "--no-playlist",
        "--socket-timeout", "30",
        url
    ]
    
    stdout, stderr, rc = run(cmd)
    
    # Check if any subtitle file was created
    caption_files = [f for f in os.listdir(output_dir) if f.startswith("caption.")]
    
    if caption_files:
        print(f"  ✅ Tìm thấy phụ đề: {caption_files}")
        # Convert VTT to text
        for cf in caption_files:
            cf_path = os.path.join(output_dir, cf)
            with open(cf_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
            
            # Extract text from VTT
            text_lines = []
            for line in content.split('\n'):
                line = line.strip()
                # Skip metadata lines, timestamps, and blank lines
                if not line or line.startswith('WEBVTT') or line.startswith('Kind:') or \
                   line.startswith('Language:') or '-->' in line or line.startswith('NOTE'):
                    continue
                text_lines.append(line)
            
            if text_lines:
                transcript_path = os.path.join(output_dir, "transcript.txt")
                with open(transcript_path, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(text_lines))
                print(f"  ✅ Transcript từ caption: {len(text_lines)} dòng")
                return transcript_path
    
    print(f"  ℹ️  Không tìm thấy phụ đề, sẽ dùng STT")
    return None


def transcribe_with_9router(audio_path, output_dir, lang="vi", model="openai/whisper-1"):
    """Transcribe audio using 9Router STT API."""
    print(f"[3/4] Đang nhận dạng giọng nói qua 9Router STT (model: {model})...")
    
    ninerouter_url = os.environ.get("NINEROUTER_URL", "https://codex.anhlaptrinh.vn")
    ninerouter_key = os.environ.get("NINEROUTER_KEY", "")
    
    if not ninerouter_key:
        print("  ❌ Lỗi: NINEROUTER_KEY chưa được set")
        return None
    
    # Build curl command
    api_url = f"{ninerouter_url}/v1/audio/transcriptions"
    
    curl_cmd = [
        "curl", "-s", "-X", "POST", api_url,
        "-H", f"Authorization: Bearer {ninerouter_key}",
        "-F", f"model={model}",
        "-F", f"file=@{audio_path}",
        "-F", f"language={lang}",
        "-F", "response_format=verbose_json"
    ]
    
    stdout, stderr, rc = run(curl_cmd)
    
    if rc != 0:
        print(f"  ❌ Lỗi gọi 9Router STT: {stderr[:200]}")
        return None
    
    try:
        result = json.loads(stdout)
    except json.JSONDecodeError:
        print(f"  ❌ Lỗi parse JSON response: {stdout[:200]}")
        return None
    
    if "error" in result:
        print(f"  ❌ 9Router error: {result['error']}")
        return None
    
    text = result.get("text", "")
    segments = result.get("segments", [])
    
    if not text:
        print("  ⚠️  Không nhận được text từ STT")
        return None
    
    print(f"  ✅ STT hoàn tất: {len(text)} ký tự, {len(segments)} segments")
    
    # Save transcript.txt
    txt_path = os.path.join(output_dir, "transcript.txt")
    with open(txt_path, 'w', encoding='utf-8') as f:
        f.write(text)
    
    # Save transcript.srt
    srt_path = os.path.join(output_dir, "transcript.srt")
    with open(srt_path, 'w', encoding='utf-8') as f:
        for i, seg in enumerate(segments, 1):
            start = seg.get("start", 0)
            end = seg.get("end", 0)
            seg_text = seg.get("text", "").strip()
            if not seg_text:
                continue
            f.write(f"{i}\n")
            f.write(f"{_fmt_srt_time(start)} --> {_fmt_srt_time(end)}\n")
            f.write(f"{seg_text}\n\n")
    
    # Save transcript.json
    json_path = os.path.join(output_dir, "transcript.json")
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump({
            "text": text,
            "segments": segments,
            "language": lang,
            "model": model,
            "source": "facebook"
        }, f, ensure_ascii=False, indent=2)
    
    print(f"  📄 transcript.txt: {txt_path}")
    print(f"  📄 transcript.srt: {srt_path}")
    print(f"  📄 transcript.json: {json_path}")
    
    return txt_path


def _fmt_srt_time(seconds):
    """Format seconds to SRT time format (HH:MM:SS,mmm)."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds - int(seconds)) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


# ─── Main ───────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Lấy transcript từ Facebook video")
    parser.add_argument("url", help="Facebook video/reel URL")
    parser.add_argument("--output-dir", help="Thư mục lưu kết quả")
    parser.add_argument("--lang", default="vi", help="Ngôn ngữ (mặc định: vi)")
    parser.add_argument("--model", default="openai/whisper-1",
                        help="Model STT (mặc định: openai/whisper-1)")
    parser.add_argument("--keep-audio", action="store_true", default=True,
                        help="Giữ lại file audio")
    parser.add_argument("--no-caption-fallback", action="store_true",
                        help="Không thử tải caption, chỉ dùng STT")
    args = parser.parse_args()
    
    url = args.url.strip()
    if not url.startswith("http"):
        print("❌ URL không hợp lệ. Cần URL Facebook video.")
        sys.exit(1)
    
    # Setup output directory
    video_id = extract_video_id(url)
    if args.output_dir:
        output_dir = args.output_dir
    else:
        output_dir = f"facebook-transcript-{video_id}"
    
    os.makedirs(output_dir, exist_ok=True)
    print(f"📁 Output: {output_dir}")
    print(f"🔗 URL: {url}")
    print(f"🆔 Video ID: {video_id}")
    print()
    
    # Step 1: Download audio
    audio_path = download_audio(url, output_dir, args.keep_audio)
    if not audio_path:
        print("❌ Không thể tải audio. Kiểm tra URL hoặc kết nối.")
        sys.exit(1)
    
    # Step 2: Try captions
    transcript_path = None
    if not args.no_caption_fallback:
        transcript_path = try_get_captions(url, output_dir)
    
    # Step 3: STT fallback
    if not transcript_path:
        if not audio_path:
            print("❌ Cần audio để chạy STT.")
            sys.exit(1)
        transcript_path = transcribe_with_9router(
            audio_path, output_dir, lang=args.lang, model=args.model
        )
    
    # Step 4: Cleanup if needed
    if not args.keep_audio and audio_path and os.path.exists(audio_path):
        os.remove(audio_path)
        print(f"🧹 Đã xoá file audio tạm")
    
    print()
    if transcript_path:
        print(f"✅ Hoàn tất! Transcript tại: {transcript_path}")
        # Print preview
        with open(transcript_path, 'r', encoding='utf-8') as f:
            preview = f.read()[:500]
        print(f"\n📝 Preview:\n{preview}")
    else:
        print("❌ Không lấy được transcript.")
        sys.exit(1)


if __name__ == "__main__":
    main()
