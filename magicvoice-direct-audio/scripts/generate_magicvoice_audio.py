#!/usr/bin/env python3
"""Generate direct audio with local MagicVoice/OmniVoice."""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import time
from pathlib import Path, PureWindowsPath

import imageio_ffmpeg
import numpy as np
import soundfile as sf
import torch
import torchaudio
from omnivoice import OmniVoice

DEFAULT_CLIENT = Path("/root/Apps/huggingface_audio/hub/models--k2-fsa--OmniVoice/MagicVoice_Client")
DEFAULT_VOICE = "Nhuan Voice V2"


def preprocess_text(text: str) -> str:
    text = text.replace("//", ". ")
    text = re.sub(r"(?<![a-zA-Z0-9:])\/(?![a-zA-Z0-9:/\\])", ", ", text)
    text = text.replace("…", "... ")
    text = re.sub(r"\.{3,}", "... ", text)
    return text.strip()


def resolve_ref_audio(client: Path, ref_audio_path: str) -> str:
    if not ref_audio_path:
        return ""
    path = Path(ref_audio_path)
    if path.exists():
        return str(path)
    candidates = [
        path.name,
        PureWindowsPath(ref_audio_path).name,
        str(ref_audio_path).replace("\\", "/").split("/")[-1],
    ]
    for file_name in dict.fromkeys(candidates):
        if not file_name:
            continue
        local_path = client / "clone_refs" / file_name
        if local_path.exists():
            return str(local_path)
    return ""


def load_voice(client: Path, voice_name: str) -> dict:
    voices_path = client / "voices_library.json"
    voices = json.loads(voices_path.read_text("utf-8"))
    for voice in voices:
        if voice.get("name") == voice_name:
            return voice
    names = ", ".join(v.get("name", "") for v in voices if v.get("name"))
    raise SystemExit(f"Voice not found: {voice_name}\nAvailable voices: {names}")


def save_audio(item, wav_path: Path) -> None:
    if isinstance(item, np.ndarray):
        item = torch.from_numpy(item.copy())
    if hasattr(item, "dim") and item.dim() == 1:
        item = item.unsqueeze(0)
    try:
        torchaudio.save(str(wav_path), item, 24000)
    except Exception:
        sf.write(str(wav_path), item.squeeze().cpu().numpy(), 24000)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate audio with local MagicVoice/OmniVoice")
    parser.add_argument("args", nargs="*", help="Text to synthesize, or optional voice name followed by text")
    parser.add_argument("--text-file", help="UTF-8 text file to synthesize")
    parser.add_argument("--client", default=str(DEFAULT_CLIENT), help="MagicVoice_Client path")
    parser.add_argument("--out-dir", default="output_direct", help="Output directory, relative to client unless absolute")
    parser.add_argument("--basename", default="", help="Optional output basename without extension")
    parser.add_argument("--keep-wav", action="store_true", help="Keep WAV file next to MP3")
    args = parser.parse_args()

    client = Path(args.client).expanduser().resolve()
    voice_name = DEFAULT_VOICE
    inline_text = " ".join(args.args).strip()
    if len(args.args) >= 2:
        voices_path = Path(args.client).expanduser().resolve() / "voices_library.json"
        voice_names = {v.get("name") for v in json.loads(voices_path.read_text("utf-8")) if v.get("name")}
        if args.args[0] in voice_names:
            voice_name = args.args[0]
            inline_text = " ".join(args.args[1:]).strip()

    if args.text_file:
        text = Path(args.text_file).read_text("utf-8")
    elif inline_text:
        text = inline_text
    else:
        raise SystemExit("Provide inline text or --text-file")

    out_dir = Path(args.out_dir)
    if not out_dir.is_absolute():
        out_dir = client / out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    os.environ.setdefault("HF_HOME", "/root/Apps/huggingface_audio")
    os.environ.setdefault("HUGGINGFACE_HUB_CACHE", "/root/Apps/huggingface_audio/hub")
    os.environ.setdefault("TRANSFORMERS_CACHE", "/root/Apps/huggingface_audio/hub")

    voice = load_voice(client, voice_name)
    ref_audio = resolve_ref_audio(client, voice.get("ref_audio", ""))
    if voice.get("mode") == "clone" and not ref_audio:
        raise SystemExit(f"Missing ref_audio for voice: {voice_name}")

    clean_text = preprocess_text(text)
    kwargs = {
        "text": clean_text,
        "num_step": int(voice.get("steps", 16)),
        "speed": float(voice.get("speed", 1.0)),
    }
    if ref_audio:
        kwargs["ref_audio"] = ref_audio
    if voice.get("ref_text"):
        kwargs["ref_text"] = voice["ref_text"]
    if voice.get("instruct"):
        kwargs["instruct"] = voice["instruct"]

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    safe_voice = re.sub(r"[^a-zA-Z0-9_-]+", "_", voice_name.strip()).strip("_").lower()
    basename = args.basename or f"{safe_voice}_{timestamp}"
    wav_path = out_dir / f"{basename}.wav"
    mp3_path = out_dir / f"{basename}.mp3"

    print(f"Loading model for voice: {voice_name}")
    print(f"Chars: {len(clean_text)} | Instruct: {voice.get('instruct', '')}")
    model = OmniVoice.from_pretrained("k2-fsa/OmniVoice", device_map="cpu", dtype=torch.float32)
    torch.manual_seed(42)
    with torch.inference_mode():
        result = model.generate(**kwargs)

    item = result[0] if hasattr(result, "__getitem__") else result
    save_audio(item, wav_path)

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    proc = subprocess.run(
        [ffmpeg, "-y", "-i", str(wav_path), "-codec:a", "libmp3lame", "-b:a", "320k", "-ar", "44100", str(mp3_path)],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr)
    if not args.keep_wav:
        wav_path.unlink(missing_ok=True)

    print(f"MP3: {mp3_path}")
    if args.keep_wav:
        print(f"WAV: {wav_path}")


if __name__ == "__main__":
    main()
