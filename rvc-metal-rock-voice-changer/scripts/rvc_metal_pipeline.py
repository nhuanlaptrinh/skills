#!/usr/bin/env python3
import argparse
import json
import math
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path


AUDIO_EXTENSIONS = {".wav", ".mp3", ".flac", ".m4a", ".aac", ".ogg", ".opus"}
DEFAULT_YTDLP_PROXY = "http://quocdattranhuu1606:iQVzmppt6C@209.101.200.135:50100"


def run(command, description, cwd=None, capture=False):
    print(f"[*] {description}")
    started = time.monotonic()
    result = subprocess.run(
        [str(part) for part in command],
        cwd=cwd,
        check=True,
        text=True,
        capture_output=capture,
    )
    elapsed = time.monotonic() - started
    print(f"[+] {description}: {elapsed:.1f}s")
    return result, elapsed


def require_file(path, label):
    if not path.is_file():
        raise SystemExit(f"[!] Thiếu {label}: {path}")


def require_command(name):
    path = shutil.which(name)
    if not path:
        raise SystemExit(f"[!] Thiếu lệnh bắt buộc: {name}")
    return Path(path)


def resolve_model(input_dir, model_name):
    pth = input_dir / f"{model_name}.pth"
    index = input_dir / f"{model_name}.index"
    bundled_dir = Path(__file__).resolve().parent.parent / "assets" / "models"
    bundled_pth = bundled_dir / pth.name
    bundled_index = bundled_dir / index.name
    if not pth.is_file() and bundled_pth.is_file():
        print(f"[*] Applio chưa có {pth.name}; đang cài model đi kèm skill")
        shutil.copy2(bundled_pth, pth)
    if not index.is_file() and bundled_index.is_file():
        print(f"[*] Applio chưa có {index.name}; đang cài index đi kèm skill")
        shutil.copy2(bundled_index, index)
    require_file(pth, "model RVC .pth")
    return pth, index if index.is_file() else None


def download_youtube(args, applio_dir, yt_dlp):
    output_template = applio_dir / "input" / f"{args.source_id}.%(ext)s"
    command = [
        yt_dlp,
        "--no-playlist",
        "--force-overwrites",
        "--no-simulate",
        "-x",
        "--audio-format", "wav",
        "--audio-quality", "0",
        "-o", output_template,
    ]
    if args.cookies:
        command.extend(["--cookies", args.cookies])
    if args.proxy:
        command.extend(["--proxy", args.proxy])
    command.append(args.url)
    _, elapsed = run(command, "Tải đúng audio YouTube")
    audio = applio_dir / "input" / f"{args.source_id}.wav"
    require_file(audio, "audio YouTube đã tải")
    return audio, elapsed


def separate_stems(python_env, audio, work_dir):
    command = [python_env, "-m", "demucs", "-n", "htdemucs", "--out", work_dir, audio]
    _, elapsed = run(command, "Demucs tách vocal, drums, bass và other")
    stem_dir = work_dir / "htdemucs" / audio.stem
    stems = {name: stem_dir / f"{name}.wav" for name in ("vocals", "drums", "bass", "other")}
    for name, path in stems.items():
        require_file(path, f"stem {name}")
    return stems, elapsed


def make_accompaniment(stems, output):
    command = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-i", stems["drums"], "-i", stems["bass"], "-i", stems["other"],
        "-filter_complex", "[0:a][1:a][2:a]amix=inputs=3:duration=longest:normalize=0,volume=0.95",
        "-c:a", "pcm_s16le", output,
    ]
    run(command, "Tạo nhạc nền tham chiếu")


def auto_vocal_mask(vocal_file, music_file, output_file, threshold_db, ratio_db, padding, min_duration):
    import numpy as np
    import soundfile as sf

    started = time.monotonic()
    vocal_audio, sample_rate = sf.read(vocal_file, always_2d=True, dtype="float32")
    music_audio, music_rate = sf.read(music_file, always_2d=True, dtype="float32")
    if sample_rate != music_rate:
        raise SystemExit("[!] Vocal và nhạc nền khác sample rate")
    sample_count = min(len(vocal_audio), len(music_audio))
    vocal_audio = vocal_audio[:sample_count]
    music_audio = music_audio[:sample_count]
    vocal_mono = np.mean(vocal_audio, axis=1)
    music_mono = np.mean(music_audio, axis=1)
    frame_size = max(1, int(sample_rate * 0.25))
    hop_size = max(1, int(sample_rate * 0.10))
    starts = np.arange(0, sample_count, hop_size)
    vocal_rms = np.empty(len(starts), dtype=np.float32)
    music_rms = np.empty(len(starts), dtype=np.float32)
    for index, start in enumerate(starts):
        end = min(sample_count, start + frame_size)
        vocal_frame = vocal_mono[start:end]
        music_frame = music_mono[start:end]
        vocal_rms[index] = math.sqrt(float(np.mean(vocal_frame * vocal_frame)) + 1e-12)
        music_rms[index] = math.sqrt(float(np.mean(music_frame * music_frame)) + 1e-12)
    vocal_db = 20 * np.log10(vocal_rms + 1e-8)
    relative_db = 20 * np.log10((vocal_rms + 1e-8) / (music_rms + 1e-8))
    noise_floor = float(np.percentile(vocal_db, 30))
    adaptive_threshold = max(float(threshold_db), min(noise_floor + 10.0, -24.0))
    active = (vocal_db >= adaptive_threshold) & (relative_db >= float(ratio_db))
    padding_frames = max(0, int(round(padding / 0.10)))
    if padding_frames:
        padded = np.zeros_like(active)
        for index in np.flatnonzero(active):
            padded[max(0, index-padding_frames):min(len(active), index+padding_frames+1)] = True
        active = padded
    minimum_frames = max(1, int(round(min_duration / 0.10)))
    intervals = []
    region_start = None
    for index, enabled in enumerate(np.append(active, False)):
        if enabled and region_start is None:
            region_start = index
        elif not enabled and region_start is not None:
            if index - region_start >= minimum_frames:
                start_time = starts[region_start] / sample_rate
                end_index = min(index - 1, len(starts) - 1)
                end_time = min(sample_count / sample_rate, (starts[end_index] + frame_size) / sample_rate)
                intervals.append((start_time, end_time))
            region_start = None
    if not intervals:
        raise SystemExit("[!] Auto Vocal Mask không phát hiện vùng hát")
    mask = np.zeros(sample_count, dtype=np.float32)
    fade_samples = max(1, int(sample_rate * 0.08))
    for start_time, end_time in intervals:
        start = max(0, int(start_time * sample_rate))
        end = min(sample_count, int(end_time * sample_rate))
        mask[start:end] = 1.0
        fade_length = min(fade_samples, max(0, (end-start)//2))
        if fade_length:
            fade = np.linspace(0, 1, fade_length, dtype=np.float32)
            mask[start:start+fade_length] = fade
            mask[end-fade_length:end] = fade[::-1]
    sf.write(output_file, vocal_audio * mask[:, None], sample_rate, subtype="PCM_16")
    elapsed = time.monotonic() - started
    print(f"[+] Auto Vocal Mask: {len(intervals)} vùng, ngưỡng {adaptive_threshold:.1f} dB, {elapsed:.1f}s")
    for start_time, end_time in intervals:
        print(f"    - {start_time:07.2f}s -> {end_time:07.2f}s")
    return intervals, elapsed


def run_rvc(args, applio_dir, python_env, input_audio, output_audio, pth, index):
    command = [
        python_env, applio_dir / "core.py", "infer",
        "--pitch", str(args.pitch),
        "--index_rate", str(args.index_rate),
        "--volume_envelope", "1.0",
        "--protect", "0.33",
        "--f0_method", "rmvpe",
        "--input_path", input_audio.resolve(),
        "--output_path", output_audio.resolve(),
        "--pth_path", pth.resolve(),
        "--index_path", index.resolve() if index else "",
        "--export_format", "WAV",
        "--split_audio", "True",
    ]
    _, elapsed = run(command, "RVC chuyển giọng vocal", cwd=applio_dir)
    require_file(output_audio, "vocal RVC")
    return elapsed


def analyze_and_generate_metal_drums(drums_path, output_path, seed):
    import librosa
    import numpy as np
    import soundfile as sf

    started = time.monotonic()
    audio, sample_rate = librosa.load(drums_path, sr=22050, mono=True)
    duration = librosa.get_duration(y=audio, sr=sample_rate)
    tempo, beat_frames = librosa.beat.beat_track(y=audio, sr=sample_rate, units="frames")
    tempo = float(np.asarray(tempo).reshape(-1)[0])
    metal_tempo = tempo * 2 if tempo < 100 else tempo
    step = 60.0 / metal_tempo
    output_rate = 48000
    sample_count = int(np.ceil(duration * output_rate))
    output = np.zeros((sample_count, 2), dtype=np.float32)
    random = np.random.default_rng(seed)
    rms = librosa.feature.rms(y=audio, frame_length=2048, hop_length=512)[0]
    rms_times = librosa.frames_to_time(np.arange(len(rms)), sr=sample_rate, hop_length=512)
    energy_threshold = float(np.quantile(rms, 0.60))

    def energy_at(moment):
        index = min(len(rms)-1, np.searchsorted(rms_times, moment))
        return float(rms[index])

    def add(sample, moment, pan=0.0, gain=1.0):
        position = int(moment * output_rate)
        if position >= sample_count:
            return
        length = min(len(sample), sample_count-position)
        left = np.sqrt((1-pan)*0.5)
        right = np.sqrt((1+pan)*0.5)
        output[position:position+length, 0] += sample[:length] * gain * left
        output[position:position+length, 1] += sample[:length] * gain * right

    def kick():
        x = np.arange(int(0.20*output_rate))/output_rate
        phase = 2*np.pi*np.cumsum(125*np.exp(-x*28)+48)/output_rate
        return (np.sin(phase)*np.exp(-x*19)+0.18*random.normal(size=len(x))*np.exp(-x*45)).astype(np.float32)

    def snare():
        x = np.arange(int(0.24*output_rate))/output_rate
        return (0.72*random.normal(size=len(x))*np.exp(-x*16)+0.5*np.sin(2*np.pi*190*x)*np.exp(-x*20)).astype(np.float32)

    def hat(open_hat=False):
        x = np.arange(int((0.20 if open_hat else 0.065)*output_rate))/output_rate
        noise = np.diff(np.r_[0, random.normal(size=len(x))])
        return (noise*np.exp(-x*(18 if open_hat else 70))*0.23).astype(np.float32)

    def crash():
        x = np.arange(int(1.5*output_rate))/output_rate
        noise = np.diff(np.r_[0, random.normal(size=len(x))])
        return ((0.42*noise+0.12*np.sin(2*np.pi*6200*x))*np.exp(-x*2.6)).astype(np.float32)

    kick_sample, snare_sample = kick(), snare()
    hat_sample, open_hat_sample, crash_sample = hat(), hat(True), crash()
    grid = np.arange(0, duration, step)
    for index, moment in enumerate(grid):
        strong = energy_at(moment) >= energy_threshold and moment > 20
        beat = index % 4
        if beat in (0, 2) or (strong and beat in (1, 3)):
            add(kick_sample, moment, gain=0.92 if strong else 0.70)
        if strong and beat in (0, 2):
            add(kick_sample, moment+step*0.5, gain=0.68)
        if beat in (1, 3):
            add(snare_sample, moment, gain=0.88 if strong else 0.68)
        add(open_hat_sample if strong and beat == 3 else hat_sample, moment, -0.28 if index % 2 == 0 else 0.28, 0.75)
        add(hat_sample, moment+step*0.5, 0.25 if index % 2 == 0 else -0.25, 0.55)
        if index % 32 == 0 and moment > 2:
            add(crash_sample, moment, -0.18 if (index//32) % 2 == 0 else 0.18, 0.72)
    output = np.tanh(output*1.25)
    output *= 0.92/(np.max(np.abs(output)) or 1)
    sf.write(output_path, output, output_rate, subtype="PCM_24")
    elapsed = time.monotonic() - started
    print(f"[+] BPM gốc: {tempo:.2f}; BPM metal: {metal_tempo:.2f}; beat: {len(beat_frames)}")
    return {"analysis_bpm": tempo, "metal_bpm": metal_tempo, "beats": int(len(beat_frames))}, elapsed


def render_master(stems, converted_vocal, metal_drums, master, duration):
    filters = f"""
[0:a]aresample=48000,apad,highpass=f=75,lowpass=f=15500,equalizer=f=250:t=q:w=1.1:g=-2,equalizer=f=3000:t=q:w=1:g=2.5,deesser=i=0.22:m=0.45:f=0.55,acompressor=threshold=0.10:ratio=3.2:attack=8:release=100:makeup=1.6,volume=1.15[v];
[1:a]aresample=48000,asplit=2[dd][dc];[dd]volume=0.48[dd1];[dc]acompressor=threshold=0.055:ratio=7:attack=4:release=90:makeup=2.2,asoftclip=type=tanh,volume=0.48[dc1];[dd1][dc1]amix=2:normalize=0[dr];
[2:a]aresample=48000,asplit=2[bc][bd];[bc]highpass=f=35,lowpass=f=420,acompressor=threshold=0.08:ratio=4:attack=10:release=120:makeup=1.6,volume=0.66[bc1];[bd]highpass=f=90,lowpass=f=1800,volume=2.3,asoftclip=type=tanh,equalizer=f=700:t=q:w=1:g=3,volume=0.36[bd1];[bc1][bd1]amix=2:normalize=0[bs];
[3:a]aresample=48000,asplit=3[oc][ol][or];[oc]highpass=f=100,lowpass=f=9000,volume=0.34[oc1];[ol]highpass=f=120,lowpass=f=7200,volume=2.6,asoftclip=type=tanh,equalizer=f=1500:t=q:w=0.8:g=4,pan=stereo|FL=FL|FR=0*FR,adelay=0|12,volume=0.34[gl];[or]highpass=f=135,lowpass=f=6800,volume=2.8,asoftclip=type=tanh,equalizer=f=2200:t=q:w=0.9:g=3,pan=stereo|FL=0*FL|FR=FR,adelay=17|0,volume=0.34[gr];
[4:a]aresample=48000,volume=0.65,highpass=f=35,lowpass=f=16000,acompressor=threshold=0.07:ratio=4.5:attack=3:release=75:makeup=1.8,asoftclip=type=tanh,volume=0.62[sd];
[v][dr][bs][oc1][gl][gr][sd]amix=inputs=7:duration=longest:dropout_transition=1:normalize=0,acompressor=threshold=0.16:ratio=2.2:attack=15:release=180:makeup=1.1,loudnorm=I=-11:LRA=7:TP=-1.8,alimiter=limit=0.80:attack=5:release=50:level=0,atrim=duration={duration:.6f}[m]
""".strip()
    command = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "warning",
        "-i", converted_vocal, "-i", stems["drums"], "-i", stems["bass"], "-i", stems["other"], "-i", metal_drums,
        "-filter_complex", filters, "-map", "[m]", "-ar", "48000", "-ac", "2", "-c:a", "pcm_f32le", master,
    ]
    _, elapsed = run(command, "Mix và master metal stereo")
    return elapsed


def probe_duration(path):
    result, _ = run([
        "ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", path
    ], "Đọc thời lượng nguồn", capture=True)
    return float(result.stdout.strip())


def encode_mp3(master, output, title, model):
    command = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "warning", "-i", master,
        "-ar", "48000", "-ac", "2", "-c:a", "libmp3lame", "-b:a", "256k",
        "-metadata", f"title={title} - Metal Rock AI Voice Conversion",
        "-metadata", f"artist=Synthetic RVC voice: {model}",
        "-metadata", "comment=AI-generated voice conversion; not an authentic singer recording",
        output,
    ]
    _, elapsed = run(command, "Xuất MP3 256 kbps, 48 kHz")
    return elapsed


def verify_output(output):
    probe, elapsed_probe = run([
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration,size,bit_rate:stream=codec_name,sample_rate,channels,channel_layout",
        "-of", "json", output,
    ], "Kiểm tra metadata đầu ra", capture=True)
    metadata = json.loads(probe.stdout)
    _, elapsed_decode = run(["ffmpeg", "-v", "error", "-i", output, "-f", "null", "-"], "Giải mã toàn bộ MP3")
    volume, elapsed_peak = run([
        "ffmpeg", "-hide_banner", "-i", output, "-af", "volumedetect", "-f", "null", "-"
    ], "Đo peak MP3", capture=True)
    peak = None
    for line in volume.stderr.splitlines():
        if "max_volume:" in line:
            peak = float(line.split("max_volume:", 1)[1].strip().split()[0])
    return metadata, peak, elapsed_probe + elapsed_decode + elapsed_peak


def parse_args():
    parser = argparse.ArgumentParser(description="RVC vocal + phối metal rock portable cho Applio")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--url", help="YouTube URL")
    source.add_argument("--audio", help="File audio cục bộ")
    parser.add_argument("--source-id", default="rvc_metal_source", help="Tên file tải từ YouTube, không có đuôi")
    parser.add_argument("--title", default="RVC Metal Rock", help="Tên bài ghi vào metadata")
    parser.add_argument("--applio-dir", default=os.getenv("APPLIO_DIR", "/root/Applio"))
    parser.add_argument(
        "--model",
        default="damvinhhung_vietnamese",
        choices=["damvinhhung_vietnamese"],
        help="Skill này cố định model damvinhhung_vietnamese",
    )
    parser.add_argument("--pitch", type=int, default=0)
    parser.add_argument("--index-rate", type=float, default=0.7)
    parser.add_argument("--cookies", default=os.getenv("YTDLP_COOKIES", "/root/cookies.txt"))
    parser.add_argument(
        "--proxy",
        default=os.getenv("YTDLP_PROXY", DEFAULT_YTDLP_PROXY),
        help="Proxy YouTube; ưu tiên YTDLP_PROXY, nếu thiếu dùng Proxy-Seller mặc định của skill",
    )
    parser.add_argument("--output", default="damvinhhung_metal_rock.mp3")
    parser.add_argument("--vocal-threshold-db", type=float, default=-38.0)
    parser.add_argument("--vocal-ratio-db", type=float, default=-14.0)
    parser.add_argument("--vocal-padding", type=float, default=0.45)
    parser.add_argument("--vocal-min-duration", type=float, default=1.3)
    parser.add_argument("--seed", type=int, default=20260717)
    return parser.parse_args()


def main():
    args = parse_args()
    total_started = time.monotonic()
    applio_dir = Path(args.applio_dir).resolve()
    python_env = applio_dir / ".venv" / "bin" / "python"
    require_file(applio_dir / "core.py", "Applio core.py")
    require_file(python_env, "Python virtualenv của Applio")
    require_command("ffmpeg")
    require_command("ffprobe")
    yt_dlp = applio_dir / ".venv" / "bin" / "yt-dlp"
    if args.url:
        require_file(yt_dlp, "yt-dlp trong Applio")
    input_dir = applio_dir / "input"
    output_dir = applio_dir / "output"
    input_dir.mkdir(exist_ok=True)
    output_dir.mkdir(exist_ok=True)
    pth, index = resolve_model(input_dir, args.model)
    timings = {}
    if args.url:
        audio, timings["download"] = download_youtube(args, applio_dir, yt_dlp)
    else:
        audio = Path(args.audio).expanduser().resolve()
        require_file(audio, "audio đầu vào")
        if audio.suffix.lower() not in AUDIO_EXTENSIONS:
            raise SystemExit(f"[!] Định dạng audio không hỗ trợ: {audio.suffix}")
        timings["download"] = 0.0
    work_dir = output_dir / f"_{Path(args.output).stem}_work"
    work_dir.mkdir(parents=True, exist_ok=True)
    duration = probe_duration(audio)
    stems, timings["demucs"] = separate_stems(python_env, audio, work_dir)
    accompaniment = work_dir / "accompaniment_reference.wav"
    make_accompaniment(stems, accompaniment)
    masked_vocal = work_dir / "masked_vocal.wav"
    intervals, timings["auto_vocal_mask"] = auto_vocal_mask(
        stems["vocals"], accompaniment, masked_vocal,
        args.vocal_threshold_db, args.vocal_ratio_db, args.vocal_padding, args.vocal_min_duration,
    )
    converted_vocal = work_dir / f"{args.model}_vocal.wav"
    timings["rvc"] = run_rvc(args, applio_dir, python_env, masked_vocal, converted_vocal, pth, index)
    metal_drums = work_dir / "metal_drums.wav"
    tempo, timings["metal_arrangement"] = analyze_and_generate_metal_drums(stems["drums"], metal_drums, args.seed)
    master = work_dir / "metal_master.wav"
    timings["mix_master"] = render_master(stems, converted_vocal, metal_drums, master, duration)
    output = output_dir / Path(args.output).name
    timings["mp3_encode"] = encode_mp3(master, output, args.title, args.model)
    metadata, peak, timings["verification"] = verify_output(output)
    if peak is None or peak > -1.0:
        raise SystemExit(f"[!] Peak không đạt yêu cầu: {peak} dB. Giữ WAV master để chỉnh lại.")
    timings["total"] = time.monotonic() - total_started
    report = {
        "output": str(output),
        "source": str(audio),
        "model": args.model,
        "pitch": args.pitch,
        "tempo": tempo,
        "vocal_intervals": intervals,
        "peak_db": peak,
        "probe": metadata,
        "timings_seconds": {key: round(value, 2) for key, value in timings.items()},
        "synthetic_voice_notice": "AI-generated RVC voice; not an authentic singer recording",
    }
    report_path = output.with_suffix(".report.json")
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print("="*64)
    print(f"[+] HOÀN THÀNH: {output}")
    print(f"[+] Peak: {peak:.1f} dB | Tổng thời gian: {timings['total']/60:.2f} phút")
    print(f"[+] Báo cáo: {report_path}")


if __name__ == "__main__":
    main()
