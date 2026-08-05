#!/root/Applio/.venv/bin/python
import argparse
import math
import os
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

APPLIO_VENV_PYTHON = Path("/root/Applio/.venv/bin/python")
if Path(__file__).resolve().parent == Path("/root/Applio") and APPLIO_VENV_PYTHON.exists():
    if Path(sys.executable).resolve() != APPLIO_VENV_PYTHON.resolve():
        os.execv(str(APPLIO_VENV_PYTHON), [str(APPLIO_VENV_PYTHON), *sys.argv])

MODEL_REGISTRY = {
    "default": {
        "pth": "https://huggingface.co/PhoenixStormJr/RVC-V2-default-voice/resolve/main/default.pth",
        "index": "https://huggingface.co/PhoenixStormJr/RVC-V2-default-voice/resolve/main/added_IVF511_Flat_nprobe_1_default_v2.index",
        "note": "Model mẫu nhỏ gọn để test nhanh.",
    },
    "suara_wanita_1": {
        "pth": "https://huggingface.co/fahmifauzi/rvc-malaysian-voices/resolve/main/suara_wanita_1.pth",
        "index": "https://huggingface.co/fahmifauzi/rvc-malaysian-voices/resolve/main/suara_wanita_1.index",
        "note": "Voice model nữ public.",
    },
    "kurumi_vietnamese": {
        "pth": "https://huggingface.co/Uchiha2026/Kurumi-RVC-v2-VietNamese/resolve/main/Kurumi.pth",
        "index": "https://huggingface.co/Uchiha2026/Kurumi-RVC-v2-VietNamese/resolve/main/added_IVF8533_Flat_nprobe_1_v1.index",
        "note": "Model RVC VietNamese/Kurumi public, repo khai báo Apache-2.0.",
    },
}
DEFAULT_MODEL_NAME = "kurumi_vietnamese"
AUDIO_EXTENSIONS = {".wav", ".mp3", ".flac", ".m4a", ".ogg", ".aac"}
REQUIRED_IMPORTS = ["torch", "librosa", "soundfile", "numpy", "faiss"]
PREREQUISITE_FILES = [
    "rvc/models/predictors/rmvpe.pt",
    "rvc/models/embedders/contentvec/pytorch_model.bin",
]


def run_command(command, description, cwd=None):
    print(f"\n[*] {description}...")
    print("Lệnh chạy:", " ".join(str(item) for item in command))
    result = subprocess.run(command, cwd=cwd, text=True)
    if result.returncode != 0:
        print(f"[!] Lỗi khi thực hiện: {description}")
        sys.exit(result.returncode)
    print(f"[+] Hoàn thành: {description}")


def download_file(url, output_path):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists() and output_path.stat().st_size > 1024 * 1024:
        print(f"[+] Đã có {output_path.name}, bỏ qua tải lại.")
        return
    print(f"[*] Đang tải {output_path.name}...")
    urllib.request.urlretrieve(url, output_path)
    print(f"[+] Đã tải: {output_path}")


def list_registry_models():
    print("Các model có link tải sẵn trong script:")
    for name, config in MODEL_REGISTRY.items():
        print(f"- {name}: {config.get('note', '')}")


def install_registry_model(input_dir, model_name):
    if model_name not in MODEL_REGISTRY:
        print(f"[!] Không có model '{model_name}' trong registry.")
        list_registry_models()
        sys.exit(1)
    config = MODEL_REGISTRY[model_name]
    download_file(config["pth"], input_dir / f"{model_name}.pth")
    if config.get("index"):
        download_file(config["index"], input_dir / f"{model_name}.index")
    print(f"[+] Đã sẵn sàng model: {model_name}")


def check_ffmpeg():
    if shutil.which("ffmpeg"):
        print("[+] FFmpeg: đã có")
        return
    print("[*] Không tìm thấy FFmpeg. Đang tiến hành cài đặt tự động...")
    try:
        if shutil.which("apt-get"):
            subprocess.run(["apt-get", "update"], check=True)
            subprocess.run(["apt-get", "install", "-y", "ffmpeg"], check=True)
            if shutil.which("ffmpeg"):
                print("[+] Đã tự động cài đặt FFmpeg thành công!")
                return
    except Exception as e:
        print(f"[!] Không thể tự động cài đặt FFmpeg: {e}")
    print("[!] FFmpeg bắt buộc để convert/mix MP3 nhưng chưa có trong PATH")
    print("    Cài trên Ubuntu/Debian: apt-get update && apt-get install -y ffmpeg")
    sys.exit(1)


def check_python_imports(python_env):
    check_code = """
import importlib.util
import sys
packages = sys.argv[1:]
missing = [package for package in packages if importlib.util.find_spec(package) is None]
if missing:
    print("MISSING:" + ",".join(missing))
    sys.exit(1)
print("OK")
"""
    result = subprocess.run([str(python_env), "-c", check_code, *REQUIRED_IMPORTS], capture_output=True, text=True)
    if result.returncode == 0:
        print("[+] Python packages: đã đủ gói cơ bản")
        return
    output = (result.stdout + result.stderr).strip()
    missing = output.replace("MISSING:", "") if "MISSING:" in output else output
    print(f"[!] Python packages: thiếu hoặc không import được: {missing}")
    print("    Hãy chạy lại cài đặt Applio:")
    print("    cd /root/Applio && export PATH=\"/root/.local/bin:$PATH\" && bash run-install.sh")
    sys.exit(1)


def check_prerequisites(applio_dir, python_env, core_script):
    missing_files = [relative for relative in PREREQUISITE_FILES if not (applio_dir / relative).exists()]
    if not missing_files:
        print("[+] Applio prerequisites: đã có model phụ trợ cơ bản")
        return
    print("[!] Applio prerequisites: thiếu model phụ trợ:")
    for relative in missing_files:
        print(f"    - {relative}")
    run_command([
        str(python_env), str(core_script), "prerequisites",
        "--pretraineds_hifigan", "True",
        "--models", "True",
        "--exe", "True",
    ], "Tải Applio prerequisites", cwd=applio_dir)


def install_package(python_env, package_name):
    # Thử sử dụng uv trước vì nó rất nhanh và hoạt động trên venv không có pip
    uv_bin = Path("/root/.local/bin/uv")
    if uv_bin.exists():
        print(f"[*] Đang cài đặt {package_name} bằng uv...")
        try:
            subprocess.run([str(uv_bin), "pip", "install", "--python", str(python_env), package_name], check=True)
            return True
        except Exception as e:
            print(f"[*] Cài đặt bằng uv thất bại: {e}. Thử phương án dự phòng...")
    
    # Phương án dự phòng dùng pip tiêu chuẩn
    print(f"[*] Đang cài đặt {package_name} bằng pip...")
    try:
        subprocess.run([str(python_env), "-m", "pip", "install", package_name], check=True)
        return True
    except Exception as e:
        print(f"[!] Cài đặt bằng pip thất bại: {e}")
        return False


def check_demucs(applio_dir, python_env):
    demucs_bin = applio_dir / ".venv" / "bin" / "demucs"
    if demucs_bin.exists():
        print("[+] Demucs: đã có")
        return demucs_bin
    print("[*] Không tìm thấy Demucs trong virtualenv. Đang tự động cài đặt...")
    if install_package(python_env, "demucs"):
        if demucs_bin.exists():
            print("[+] Tự động cài đặt Demucs thành công!")
            return demucs_bin
    print("[!] Demucs bắt buộc vì skill này xử lý bài nhạc có nhạc nền + giọng hát.")
    print("    Cài: export PATH=\"/root/.local/bin:$PATH\" && uv pip install --python /root/Applio/.venv/bin/python demucs")
    sys.exit(1)


def check_yt_dlp(python_env):
    try:
        result = subprocess.run([str(python_env), "-c", "import yt_dlp"], capture_output=True, text=True)
        if result.returncode == 0:
            print("[+] yt-dlp: đã có trong virtualenv")
            return
    except Exception:
        pass
    print("[*] Không tìm thấy yt-dlp trong virtualenv. Đang tự động cài đặt...")
    if install_package(python_env, "yt-dlp"):
        print("[+] Tự động cài đặt yt-dlp thành công!")
        return
    print("[!] Lỗi khi tự động cài đặt yt-dlp.")
    print("    Vui lòng cài đặt thủ công: .venv/bin/python -m pip install yt-dlp")
    sys.exit(1)


def check_environment(applio_dir, python_env, core_script):
    print("=" * 60)
    print("[*] BƯỚC 0: KIỂM TRA MÔI TRƯỜNG")
    print("=" * 60)
    if not core_script.exists():
        print(f"[!] Không tìm thấy {core_script}. Hãy copy script này vào thư mục gốc Applio.")
        sys.exit(1)
    print("[+] core.py: đã có")
    if not python_env.exists():
        print(f"[!] Không tìm thấy virtualenv: {python_env}")
        sys.exit(1)
    print("[+] .venv python: đã có")
    check_ffmpeg()
    check_python_imports(python_env)
    check_prerequisites(applio_dir, python_env, core_script)
    check_yt_dlp(python_env)
    return check_demucs(applio_dir, python_env)


def find_audio(input_dir, preferred_name=None):
    audio_files = sorted(path for path in input_dir.rglob("*") if path.is_file() and path.suffix.lower() in AUDIO_EXTENSIONS)
    if preferred_name:
        for path in audio_files:
            if preferred_name.lower() in path.name.lower() or preferred_name.lower() == path.stem.lower():
                return path
        print(f"[!] Không tìm thấy audio khớp tên: {preferred_name}")
        sys.exit(1)
    if not audio_files:
        print(f"[!] Không tìm thấy file audio trong {input_dir}")
        sys.exit(1)
    if len(audio_files) > 1:
        print("[!] Có nhiều file audio, script sẽ chọn file đầu tiên:")
        for path in audio_files:
            print(f"    - {path.relative_to(input_dir)}")
        print("    Gợi ý: dùng --audio <tên_file>.")
    return audio_files[0]


def find_model(input_dir, model_name=None):
    pth_files = sorted(path for path in input_dir.rglob("*.pth") if path.is_file())
    if not pth_files:
        print(f"[!] Chưa có voice model RVC trong input. Tự tải model mẫu {DEFAULT_MODEL_NAME}...")
        install_registry_model(input_dir, DEFAULT_MODEL_NAME)
        pth_files = [input_dir / f"{DEFAULT_MODEL_NAME}.pth"]
    
    # Nếu không truyền model_name, ưu tiên chọn DEFAULT_MODEL_NAME nếu file đó tồn tại
    if not model_name:
        default_pth = input_dir / f"{DEFAULT_MODEL_NAME}.pth"
        if default_pth.exists():
            model_name = DEFAULT_MODEL_NAME
            
    if model_name:
        matched = [path for path in pth_files if model_name.lower() in path.stem.lower()]
        if not matched:
            print(f"[!] Không tìm thấy model khớp tên: {model_name}")
            print("    Các model hiện có:")
            for path in pth_files:
                print(f"    - {path.stem}")
            sys.exit(1)
        pth_file = matched[0]
    else:
        if len(pth_files) > 1:
            print("[!] Có nhiều model, script sẽ chọn model đầu tiên:")
            for path in pth_files:
                print(f"    - {path.stem}")
            print("    Gợi ý: dùng --model <tên_model>.")
        pth_file = pth_files[0]
    index_candidates = sorted(path for path in input_dir.rglob("*.index") if path.is_file())
    same_stem_index = pth_file.with_suffix(".index")
    if same_stem_index.exists():
        index_file = same_stem_index
    else:
        related = [path for path in index_candidates if pth_file.stem.lower() in path.stem.lower()]
        index_file = related[0] if related else None
    return pth_file, index_file


def find_demucs_stem(work_dir, stem_name):
    matches = sorted(path for path in work_dir.rglob(f"{stem_name}.wav") if path.is_file())
    if not matches:
        print(f"[!] Không tìm thấy stem Demucs: {stem_name}.wav trong {work_dir}")
        sys.exit(1)
    return matches[0]


def separate_audio_with_demucs(demucs_bin, audio_file, work_dir):
    if work_dir.exists():
        shutil.rmtree(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)
    run_command([
        str(demucs_bin),
        "--two-stems=vocals",
        "-d", "cpu",
        str(audio_file),
        "-o", str(work_dir),
    ], "Tách vocal và nhạc nền bằng Demucs CPU")
    return find_demucs_stem(work_dir, "vocals"), find_demucs_stem(work_dir, "no_vocals")


def apply_auto_vocal_mask(vocal_file, music_file, output_file, threshold_db, ratio_db, padding, min_duration):
    import numpy as np
    import soundfile as sf

    vocal_audio, sample_rate = sf.read(vocal_file, always_2d=True, dtype="float32")
    music_audio, music_sample_rate = sf.read(music_file, always_2d=True, dtype="float32")
    if sample_rate != music_sample_rate:
        print("[!] Auto vocal mask yêu cầu hai stem cùng sample rate.")
        sys.exit(1)

    sample_count = min(len(vocal_audio), len(music_audio))
    vocal_audio = vocal_audio[:sample_count]
    music_audio = music_audio[:sample_count]
    vocal_mono = np.mean(vocal_audio, axis=1)
    music_mono = np.mean(music_audio, axis=1)

    frame_seconds = 0.25
    hop_seconds = 0.10
    frame_size = max(1, int(sample_rate * frame_seconds))
    hop_size = max(1, int(sample_rate * hop_seconds))
    frame_starts = np.arange(0, sample_count, hop_size)
    vocal_rms = np.empty(len(frame_starts), dtype=np.float32)
    music_rms = np.empty(len(frame_starts), dtype=np.float32)

    for index, start in enumerate(frame_starts):
        end = min(sample_count, start + frame_size)
        vocal_frame = vocal_mono[start:end]
        music_frame = music_mono[start:end]
        vocal_rms[index] = math.sqrt(float(np.mean(vocal_frame * vocal_frame)) + 1e-12)
        music_rms[index] = math.sqrt(float(np.mean(music_frame * music_frame)) + 1e-12)

    vocal_level_db = 20.0 * np.log10(vocal_rms + 1e-8)
    relative_level_db = 20.0 * np.log10((vocal_rms + 1e-8) / (music_rms + 1e-8))
    noise_floor_db = float(np.percentile(vocal_level_db, 30))
    adaptive_threshold_db = max(float(threshold_db), min(noise_floor_db + 10.0, -24.0))
    active = (vocal_level_db >= adaptive_threshold_db) & (relative_level_db >= float(ratio_db))

    padding_frames = max(0, int(round(padding / hop_seconds)))
    if padding_frames:
        active_indices = np.flatnonzero(active)
        padded = np.zeros_like(active)
        for index in active_indices:
            start = max(0, index - padding_frames)
            end = min(len(active), index + padding_frames + 1)
            padded[start:end] = True
        active = padded

    minimum_frames = max(1, int(round(min_duration / hop_seconds)))
    intervals = []
    start_index = None
    for index, is_active in enumerate(np.append(active, False)):
        if is_active and start_index is None:
            start_index = index
        elif not is_active and start_index is not None:
            if index - start_index >= minimum_frames:
                start_time = frame_starts[start_index] / sample_rate
                end_frame = min(index - 1, len(frame_starts) - 1)
                end_time = min(sample_count / sample_rate, (frame_starts[end_frame] + frame_size) / sample_rate)
                intervals.append((start_time, end_time))
            start_index = None

    mask = np.zeros(sample_count, dtype=np.float32)
    fade_samples = max(1, int(sample_rate * 0.08))
    for start_time, end_time in intervals:
        start_sample = max(0, int(start_time * sample_rate))
        end_sample = min(sample_count, int(end_time * sample_rate))
        mask[start_sample:end_sample] = 1.0
        fade_length = min(fade_samples, max(0, (end_sample - start_sample) // 2))
        if fade_length:
            fade = np.linspace(0.0, 1.0, fade_length, dtype=np.float32)
            mask[start_sample:start_sample + fade_length] = fade
            mask[end_sample - fade_length:end_sample] = fade[::-1]

    masked_audio = vocal_audio * mask[:, None]
    sf.write(output_file, masked_audio, sample_rate, subtype="PCM_16")

    print(f"[+] Auto vocal mask: noise floor {noise_floor_db:.1f} dB, ngưỡng {adaptive_threshold_db:.1f} dB, tỷ lệ vocal/nền >= {ratio_db:.1f} dB")
    if intervals:
        print(f"[+] Phát hiện {len(intervals)} vùng có vocal:")
        for start_time, end_time in intervals:
            print(f"    - {start_time:07.2f}s -> {end_time:07.2f}s")
    else:
        print("[!] Không phát hiện vùng vocal. Hãy giảm --vocal-threshold-db hoặc --vocal-ratio-db.")
        sys.exit(1)
    return output_file


def run_rvc(python_env, core_script, pitch, input_audio, output_wav, pth_file, index_file, no_split, applio_dir):
    rvc_cmd = [
        str(python_env), str(core_script), "infer",
        "--pitch", str(pitch),
        "--index_rate", "0.7",
        "--volume_envelope", "1.0",
        "--protect", "0.33",
        "--f0_method", "rmvpe",
        "--input_path", str(input_audio.resolve()),
        "--output_path", str(output_wav.resolve()),
        "--pth_path", str(pth_file.resolve()),
        "--index_path", str(index_file.resolve()) if index_file else "",
        "--export_format", "WAV",
    ]
    if not no_split:
        rvc_cmd.extend(["--split_audio", "True"])
    run_command(rvc_cmd, "Chạy RVC đổi giọng vocal ra WAV tạm", cwd=applio_dir)



def mix_vocal_with_music(converted_vocal, music_file, mp3_file):
    run_command([
        "ffmpeg", "-y",
        "-i", str(converted_vocal),
        "-i", str(music_file),
        "-filter_complex", "[0:a]volume=1.0[v];[1:a]volume=1.0[m];[v][m]amix=inputs=2:duration=longest:dropout_transition=2",
        "-vn",
        "-codec:a", "libmp3lame",
        "-b:a", "192k",
        str(mp3_file),
    ], "Mix giọng đã đổi với nhạc nền và xuất MP3")


import re

def sanitize_filename(name):
    # Loại bỏ các ký tự không hợp lệ cho hệ thống file (\ / : * ? " < > |)
    # Giữ lại khoảng trắng và chữ tiếng Việt có dấu
    name = re.sub(r'[\\/*?:"<>|]', "", name)
    # Loại bỏ các ký tự đặc biệt nguy hiểm cho shell hoặc rút gọn khoảng trắng thừa
    name = re.sub(r'\s+', ' ', name).strip()
    # Thay thế các ký tự có thể gây lỗi shell đặc biệt bằng dấu gạch dưới hoặc bỏ qua
    name = name.replace("$", "").replace("`", "").replace("'", "").replace('"', "")
    return name if name else "youtube_audio"


def get_youtube_title(url, python_env, proxy=None, cookies_path=None):
    cmd = [
        str(python_env), "-m", "yt_dlp", 
        "--no-playlist", 
        "--js-runtimes", "node", 
        "--remote-components", "ejs:github", 
        "--get-title", 
        url
    ]
    if proxy:
        cmd.extend(["--proxy", proxy])
    if cookies_path and Path(cookies_path).exists():
        cmd.extend(["--cookies", str(cookies_path)])
    try:
        print("[*] Đang lấy tiêu đề video từ YouTube...")
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"[!] Lỗi khi lấy tiêu đề: {e.stderr or e.stdout}")
        return "youtube_audio"


def download_youtube_audio(url, input_dir, python_env, proxy=None, cookies_path=None):
    title = get_youtube_title(url, python_env, proxy, cookies_path)
    safe_title = sanitize_filename(title)
    output_path = input_dir / f"{safe_title}.wav"
    
    print(f"[*] Tiêu đề video: {title}")
    print(f"[*] File tải về dự kiến: {output_path.name}")
    
    # Lệnh tải nhạc từ YouTube dạng wav
    cmd = [
        str(python_env), "-m", "yt_dlp", 
        "--no-playlist", 
        "--js-runtimes", "node", 
        "--remote-components", "ejs:github", 
        "-x",
        "--audio-format", "wav",
        "--audio-quality", "0",
        "-o", str(output_path),
        url
    ]
    if proxy:
        cmd.extend(["--proxy", proxy])
    if cookies_path and Path(cookies_path).exists():
        cmd.extend(["--cookies", str(cookies_path)])
        
    run_command(cmd, f"Tải nhạc YouTube: {title}")
    
    if not output_path.exists():
        print(f"[!] Lỗi: Không tìm thấy file âm thanh sau khi tải về tại {output_path}")
        sys.exit(1)
        
    return output_path


def parse_args():
    parser = argparse.ArgumentParser(description="Đổi giọng bài nhạc audio có nhạc nền + giọng hát bằng Applio RVC, output cuối bắt buộc MP3.")
    parser.add_argument("pitch", nargs="?", type=int, default=0, help="Độ lệch pitch, mặc định 0")
    parser.add_argument("--audio", help="Tên file audio trong input cần xử lý")
    parser.add_argument("--model", help="Tên model RVC cần dùng, ví dụ default hoặc kurumi_vietnamese")
    parser.add_argument("--install-model", help="Tải model có sẵn trong registry rồi thoát")
    parser.add_argument("--list-models", action="store_true", help="Liệt kê model có link tải sẵn rồi thoát")
    parser.add_argument("--output", help="Tên file output .mp3 trong output")
    parser.add_argument("--no-split", action="store_true", help="Tắt split_audio nếu máy đủ RAM")
    parser.add_argument("--url", help="Đường dẫn (URL) video/audio YouTube cần tải")
    parser.add_argument("--proxy", default="http://quocdattranhuu1606:iQVzmppt6C@74.0.101.207:50100", help="Proxy để tải YouTube (mặc định: http://quocdattranhuu1606:iQVzmppt6C@74.0.101.207:50100)")
    parser.add_argument("--tor", action="store_true", help="Tự động sử dụng proxy Tor tại socks5://127.0.0.1:9050")
    parser.add_argument("--cookies", help="Đường dẫn file cookies cho yt-dlp (mặc định: /root/cookies.txt nếu tồn tại)")
    parser.add_argument("--auto-vocal-mask", action="store_true", help="Tự tắt các đoạn stem vocal không có giọng hát trước khi chạy RVC")
    parser.add_argument("--vocal-threshold-db", type=float, default=-38.0, help="Ngưỡng âm lượng vocal tối thiểu, mặc định -38 dB")
    parser.add_argument("--vocal-ratio-db", type=float, default=-14.0, help="Tỷ lệ vocal so với nhạc nền tối thiểu, mặc định -14 dB")
    parser.add_argument("--vocal-padding", type=float, default=0.45, help="Khoảng đệm trước/sau vùng hát, mặc định 0.45 giây")
    parser.add_argument("--vocal-min-duration", type=float, default=1.3, help="Độ dài vùng hát tối thiểu, mặc định 1.3 giây để loại tiếng rò ngắn")
    return parser.parse_args()


def main():
    args = parse_args()
    applio_dir = Path(__file__).resolve().parent
    input_dir = applio_dir / "input"
    output_dir = applio_dir / "output"
    work_dir = output_dir / "_rvc_work"
    python_env = applio_dir / ".venv" / "bin" / "python"
    core_script = applio_dir / "core.py"

    print("=" * 60)
    print("[*] RVC AUDIO-ONLY VOICE CHANGER -> MP3")
    print("=" * 60)

    demucs_bin = check_environment(applio_dir, python_env, core_script)

    input_dir.mkdir(exist_ok=True)
    output_dir.mkdir(exist_ok=True)

    if args.list_models:
        list_registry_models()
        return
    if args.install_model:
        install_registry_model(input_dir, args.install_model)
        return

    # Xử lý tải YouTube nếu có --url
    if args.url:
        proxy = "socks5://127.0.0.1:9050" if args.tor else args.proxy
        cookies_path = None
        if args.cookies:
            cookies_path = Path(args.cookies)
        else:
            default_cookies = Path("/root/cookies.txt")
            if default_cookies.exists():
                try:
                    content = default_cookies.read_text().strip()
                    non_comments = [line for line in content.splitlines() if line.strip() and not line.strip().startswith("#")]
                    if non_comments:
                        cookies_path = default_cookies
                except Exception:
                    pass
        audio_file = download_youtube_audio(args.url, input_dir, python_env, proxy, cookies_path)
    else:
        audio_file = find_audio(input_dir, args.audio)
        
    pth_file, index_file = find_model(input_dir, args.model)
    output_name = args.output or f"{audio_file.stem}_rvc_{pth_file.stem}.mp3"
    if not output_name.lower().endswith(".mp3"):
        output_name = f"{Path(output_name).stem}.mp3"
    output_file = output_dir / output_name
    temp_vocal_wav = output_dir / f".{Path(output_name).stem}.converted_vocal.tmp.wav"
    masked_vocal_wav = output_dir / f".{Path(output_name).stem}.masked_vocal.tmp.wav"

    print(f"[+] Audio đầu vào: {audio_file}")
    print(f"[+] Model PTH: {pth_file}")
    print(f"[+] Model Index: {index_file if index_file else 'Không có'}")
    print(f"[+] Output MP3 cuối: {output_file}")

    print("[*] Chế độ bài nhạc: tách vocal/nhạc nền, đổi giọng vocal, rồi mix nhạc nền lại.")
    vocal_wav, music_wav = separate_audio_with_demucs(demucs_bin, audio_file, work_dir)
    rvc_input_wav = vocal_wav
    if args.auto_vocal_mask:
        rvc_input_wav = apply_auto_vocal_mask(
            vocal_wav,
            music_wav,
            masked_vocal_wav,
            args.vocal_threshold_db,
            args.vocal_ratio_db,
            args.vocal_padding,
            args.vocal_min_duration,
        )
    run_rvc(python_env, core_script, args.pitch, rvc_input_wav, temp_vocal_wav, pth_file, index_file, args.no_split, applio_dir)
    mix_vocal_with_music(temp_vocal_wav, music_wav, output_file)

    if temp_vocal_wav.exists():
        temp_vocal_wav.unlink()
    if masked_vocal_wav.exists():
        masked_vocal_wav.unlink()
    print("\n" + "=" * 60)
    print("[+] HOÀN THÀNH")
    print(f"[+] File MP3 kết quả: {output_file}")
    print("=" * 60)


if __name__ == "__main__":
    main()
