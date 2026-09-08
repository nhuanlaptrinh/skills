#!/usr/bin/env python3
"""
Video Factory Auto Production CLI
Tự động tạo video ngắn (15-60s) từ kịch bản, giọng đọc AI (ElevenLabs / Edge-TTS) và B-roll Pexels API.
"""

import argparse
import base64
import json
import os
import re
import subprocess
import sys
import urllib.parse
import requests


def load_env(env_path):
    env = {}
    if os.path.exists(env_path):
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    k, v = line.split('=', 1)
                    env[k.strip()] = v.strip()
    return env


def generate_elevenlabs_voice(api_key, voice_id, model_id, text, out_audio, out_words):
    print(f"[ElevenLabs] Generating TTS with voice '{voice_id}', model '{model_id}'...")
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/with-timestamps"
    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json"
    }
    payload = {
        "text": text,
        "model_id": model_id
    }
    r = requests.post(url, json=payload, headers=headers, timeout=60)
    if r.status_code != 200:
        raise RuntimeError(f"ElevenLabs API error ({r.status_code}): {r.text[:300]}")

    data = r.json()
    audio_bytes = base64.b64decode(data['audio_base64'])
    os.makedirs(os.path.dirname(out_audio) or '.', exist_ok=True)
    with open(out_audio, 'wb') as f:
        f.write(audio_bytes)

    alignment = data.get('alignment', {})
    chars = alignment.get('characters', [])
    starts = alignment.get('character_start_times_seconds', [])
    ends = alignment.get('character_end_times_seconds', [])

    words = []
    cur_word = ""
    cur_start = None
    cur_end = None

    for ch, s, e in zip(chars, starts, ends):
        if ch == " ":
            if cur_word:
                words.append({"word": cur_word, "start": round(cur_start, 3), "end": round(cur_end, 3)})
                cur_word = ""
                cur_start = None
                cur_end = None
        else:
            if cur_start is None:
                cur_start = s
            cur_end = e
            cur_word += ch

    if cur_word:
        words.append({"word": cur_word, "start": round(cur_start, 3), "end": round(cur_end, 3)})

    with open(out_words, 'w', encoding='utf-8') as f:
        json.dump(words, f, ensure_ascii=False, indent=2)

    cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", out_audio]
    dur_str = subprocess.check_output(cmd).decode().strip()
    duration = float(dur_str)
    print(f"[ElevenLabs] Saved {len(words)} words, duration: {duration:.2f}s -> {out_audio}")
    return duration, words


def download_pexels_clips(pexels_key, queries_with_durations, out_dir):
    print(f"[Pexels] Downloading {len(queries_with_durations)} B-roll clips...")
    os.makedirs(out_dir, exist_ok=True)
    headers = {"Authorization": pexels_key}
    downloaded_paths = []

    for i, (query, clip_duration) in enumerate(queries_with_durations, start=1):
        url = f"https://api.pexels.com/videos/search?query={urllib.parse.quote(query)}&per_page=5&orientation=landscape"
        res = requests.get(url, headers=headers, timeout=15)
        if res.status_code != 200:
            raise RuntimeError(f"Pexels search failed for query '{query}': {res.status_code}")

        videos = res.json().get('videos', [])
        if not videos:
            raise RuntimeError(f"No Pexels videos found for query: {query}")

        v = videos[0]
        files = v.get('video_files', [])
        candidates = [f for f in files if f.get('width') == 1280 or f.get('height') == 720]
        if not candidates:
            candidates = [f for f in files if f.get('quality') == 'hd']
        if not candidates:
            candidates = files

        chosen = candidates[0]
        raw_path = f"/tmp/pexels_raw_{i}.mp4"
        out_path = os.path.join(out_dir, f"clip{i}_{re.sub(r'[^a-zA-Z0-9_]', '_', query)[:15]}.mp4")

        print(f"  [{i}/{len(queries_with_durations)}] Downloading '{query}' (Pexels ID {v['id']})...")
        r = requests.get(chosen['link'], stream=True, timeout=60)
        with open(raw_path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=65536):
                if chunk:
                    f.write(chunk)

        # Normalize with ffmpeg: 1280x720, 30fps H.264 without audio
        norm_cmd = [
            "ffmpeg", "-y", "-i", raw_path,
            "-t", str(clip_duration + 1.0),
            "-vf", "scale=1280:720:force_original_aspect_ratio=increase,crop=1280:720,fps=30",
            "-c:v", "libx264", "-preset", "fast", "-crf", "20", "-an",
            out_path
        ]
        subprocess.run(norm_cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        downloaded_paths.append(out_path)
        print(f"  -> Normalized to 1280x720: {out_path}")

    return downloaded_paths


def main():
    parser = argparse.ArgumentParser(description="Video Factory Auto Production CLI")
    parser.add_argument("--project-dir", default="/root/Apps/member_vps/docker-users/data/nv6_taovideo4/04_Nha_May_San_Xuat_Video", help="Path to Video Factory project root")
    parser.add_argument("--text", required=True, help="Full narration text in Vietnamese")
    parser.add_argument("--voice-id", help="ElevenLabs voice ID (default: reads ELEVENLABS_VOICE_THANG from .env)")
    parser.add_argument("--model-id", help="ElevenLabs model ID (default: reads ELEVENLABS_MODEL_ID from .env or 'eleven_v3')")
    parser.add_argument("--output-name", required=True, help="Subfolder and filename under output/, e.g. hoc_ai_20s")
    parser.add_argument("--queries", nargs="+", default=["ai technology", "coding developer", "robot automation", "future digital"], help="Search queries for Pexels B-roll")

    args = parser.parse_args()

    project_dir = os.path.abspath(args.project_dir)
    env_file = os.path.join(project_dir, ".env")
    env = load_env(env_file)

    eleven_key = env.get("ELEVANLABS_API_KEY") or env.get("ELEVENLABS_API_KEY")
    voice_id = args.voice_id or env.get("ELEVENLABS_VOICE_THANG", "I17U3AyPj7ZvX0kSQB9n")
    model_id = args.model_id or env.get("ELEVENLABS_MODEL_ID", "eleven_v3")
    pexels_key = env.get("PEXELS_API_KEY")

    if not eleven_key:
        sys.exit("Error: Missing ElevenLabs API key in .env")
    if not pexels_key:
        sys.exit("Error: Missing Pexels API key in .env")

    out_folder = os.path.join(project_dir, "output", args.output_name)
    os.makedirs(out_folder, exist_ok=True)

    voice_audio = os.path.join(project_dir, "input", f"{args.output_name}_voice.mp3")
    words_json = os.path.join(project_dir, "input", f"{args.output_name}_words.json")

    # 1. Generate Voiceover
    dur, words = generate_elevenlabs_voice(eleven_key, voice_id, model_id, args.text, voice_audio, words_json)

    # 2. Download Pexels B-roll (divide duration across queries, ~3-6s each)
    num_clips = len(args.queries)
    clip_dur = dur / num_clips
    queries_durs = [(q, clip_dur) for q in args.queries]
    video_dir = os.path.join(project_dir, "assets", "videos")
    clips = download_pexels_clips(pexels_key, queries_durs, video_dir)

    print(f"\n[Ready] Audio ({dur:.2f}s) and {len(clips)} B-roll clips prepared.")
    print(f"To render final video, run:")
    print(f"  npx --yes hyperframes@0.6.96 render --low-memory-mode -o output/{args.output_name}/{args.output_name}.mp4\n")


if __name__ == "__main__":
    main()
