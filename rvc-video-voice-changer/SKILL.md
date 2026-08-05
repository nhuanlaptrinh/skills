---
name: rvc-video-voice-changer
description: Đổi giọng bài nhạc audio có nhạc nền + giọng hát bằng RVC qua Applio CPU: tách vocal/nhạc nền bằng Demucs, đổi giọng vocal, mix nhạc nền lại và xuất MP3; kiểm tra/cài model nếu thiếu.
---

# RVC Audio Voice Changer (Đổi Giọng Audio Bằng Applio)

Skill này dùng khi người dùng muốn **bỏ 1 file bài nhạc audio có nhạc nền + giọng hát vào và đổi giọng phần vocal bằng RVC**. Quy trình không xử lý video nặng: script tách vocal/nhạc nền bằng Demucs, đổi giọng vocal, rồi mix nhạc nền lại. Output cuối **bắt buộc là MP3** để dễ mở trên mọi máy.

## Khi nào sử dụng

Dùng skill này khi người dùng muốn:

- Đổi giọng một file audio `.wav`, `.mp3`, `.flac`, `.m4a`, `.ogg`, `.aac` bằng Applio/RVC.
- Giữ nhạc nền cho bài hát bằng cách tách vocal/nhạc nền bằng Demucs rồi mix lại MP3.
- Chạy RVC bằng CLI, không mở Web UI.
- Kiểm tra có voice model `.pth/.index` chưa; nếu chưa có thì tải model mẫu.
- Copy script `automate_rvc.py` của skill vào `/root/Applio` rồi xử lý trong thư mục Applio.

Không ưu tiên dùng cho video. Nếu input là video, hãy nhắc người dùng tách audio trước hoặc chỉ xử lý audio đã tách.

---

## 1. Nguyên tắc bắt buộc

- **Chỉ xử lý audio**: bỏ video ra khỏi quy trình mặc định vì video nặng.
- **Giữ nhạc nền cho bài nhạc**: script luôn chạy Demucs để tách vocal và `no_vocals`, sau đó mix lại MP3.
- **Script phải nằm trong Applio**: trước khi chạy, copy script mẫu từ skill vào `/root/Applio/automate_rvc.py`.
- **Luôn chạy tại Applio**: dùng `cd /root/Applio` rồi chạy `./automate_rvc.py`.
- **Luôn check voice model**: nếu đã có `.pth` thì dùng; nếu chưa có thì script tự tải model mẫu `default.pth/default.index`.
- **Có link tải model sẵn**: script có registry model public để khách clone source về có thể tải bằng `--install-model`.
- **Luôn check thư viện**: script kiểm tra `ffmpeg`, import package cơ bản trong `.venv`, `core.py`, và model phụ trợ của Applio trước khi chạy.
- **Ưu tiên CPU-safe**: script mặc định truyền `--split_audio True` khi gọi `core.py infer` để giảm rủi ro OOM/RAM khi chạy CPU.

---

## 2. Kiểm tra & khởi tạo môi trường

### Bước 1: Kiểm tra source Applio

Nếu chưa có `/root/Applio`, clone source:

```bash
git clone https://github.com/IAHispano/Applio.git /root/Applio
```

### Bước 2: Cài Applio và virtualenv

```bash
cd /root/Applio
export PATH="/root/.local/bin:$PATH"
bash run-install.sh
```

### Bước 3: Tải prerequisites của Applio

```bash
cd /root/Applio
/root/Applio/.venv/bin/python core.py prerequisites --pretraineds_hifigan True --models True --exe True
```

Demucs là bắt buộc vì skill này xử lý bài nhạc có nhạc nền + giọng hát. Không dùng video, nhưng vẫn phải tách vocal/nhạc nền để giữ nhạc nền sau khi đổi giọng.

### Bước 4: FFmpeg bắt buộc có

Workflow bài nhạc audio **bắt buộc cần FFmpeg** vì script luôn xuất MP3 cuối và dùng FFmpeg để mix vocal đã đổi với nhạc nền.

Nếu thiếu FFmpeg, cài bằng:

```bash
apt-get update && apt-get install -y ffmpeg
```

Script sẽ check `ffmpeg` trước khi chạy. Nếu chưa có, script dừng và đưa lệnh cài đặt.

### Bước 5: Các package/prerequisites script tự kiểm tra

Khi chạy `/root/Applio/automate_rvc.py`, script tự kiểm tra:

- `/root/Applio/core.py` có tồn tại không.
- `/root/Applio/.venv/bin/python` có tồn tại không.
- `ffmpeg` có trong `PATH` không.
- Các import cơ bản trong `.venv`: `torch`, `librosa`, `soundfile`, `numpy`, `faiss`.
- Model phụ trợ Applio: `rvc/models/predictors/rmvpe.pt` và `rvc/models/embedders/contentvec/pytorch_model.bin`.
- Demucs trong `.venv` để tách vocal/nhạc nền.
- Voice model `.pth`; nếu thiếu thì tự tải model mẫu `default.pth/default.index`.

Nếu thiếu package Python cơ bản, script sẽ dừng và yêu cầu chạy lại:

```bash
cd /root/Applio
export PATH="/root/.local/bin:$PATH"
bash run-install.sh
```

---

## 3. Copy script xử lý bài nhạc vào Applio

Script trong skill chỉ là bản mẫu. Khi chạy thật, bắt buộc copy vào thư mục gốc Applio:

```bash
cp /root/.agents/skills/rvc-video-voice-changer/scripts/automate_rvc.py /root/Applio/automate_rvc.py
chmod +x /root/Applio/automate_rvc.py
```

Sau đó mọi lệnh xử lý chạy tại:

```bash
cd /root/Applio
```

---

## 4. Chuẩn bị input audio và voice model

Tạo/chọn thư mục input:

```bash
mkdir -p /root/Applio/input /root/Applio/output
```

Bỏ vào `/root/Applio/input/`:

- **1 file audio cần đổi giọng**: ví dụ `voice.wav`, `audio.mp3`, `recording.m4a`.
- **Voice model RVC** nếu đã có:
  - `<model>.pth` bắt buộc.
  - `<model>.index` khuyên dùng.

Ví dụ:

```bash
/root/Applio/input/my_audio.wav
/root/Applio/input/default.pth
/root/Applio/input/default.index
```

Nếu chưa có model `.pth`, script sẽ tự tải model mẫu:

- `default.pth`
- `default.index`

### Model registry có sẵn trong script

Script `/root/Applio/automate_rvc.py` có sẵn link tải một số model public. Xem danh sách:

```bash
cd /root/Applio
./automate_rvc.py --list-models
```

Các model registry hiện có:

| Tên model | Nguồn tải |
|---|---|
| `default` | `https://huggingface.co/PhoenixStormJr/RVC-V2-default-voice` |
| `suara_wanita_1` | `https://huggingface.co/fahmifauzi/rvc-malaysian-voices` |
| `kurumi_vietnamese` | `https://huggingface.co/Uchiha2026/Kurumi-RVC-v2-VietNamese` |

Tải model cụ thể về `/root/Applio/input`:

```bash
cd /root/Applio
./automate_rvc.py --install-model default
./automate_rvc.py --install-model suara_wanita_1
./automate_rvc.py --install-model kurumi_vietnamese
```

Nếu khách tải source từ Git/GitHub về mà chưa có model, cách nhanh nhất là:

```bash
cd /root/Applio
./automate_rvc.py --install-model default
```

Hoặc cứ chạy đổi giọng bình thường; nếu script không thấy file `.pth` nào trong `input`, nó sẽ tự tải `default`.

---

## 5. Chạy đổi giọng audio

### Cách 1: Sử dụng file audio cục bộ (có sẵn trong `input`)

Chạy mặc định với file audio có sẵn, pitch `0`:

```bash
cd /root/Applio
./automate_rvc.py 0
```

Lệnh này dành cho **bài nhạc có nhạc nền + giọng hát**: script tách vocal/nhạc nền, đổi giọng vocal, rồi mix lại thành MP3.

Chọn audio cụ thể khi có nhiều file audio:

```bash
cd /root/Applio
./automate_rvc.py 0 --audio my_audio.wav
```

### Cách 2: Tải nhạc trực tiếp từ YouTube

Thay vì tải lên thủ công, bạn có thể truyền link YouTube trực tiếp bằng tham số `--url`. Script sẽ tự động lấy tiêu đề video (giữ nguyên tiếng Việt có dấu), tải âm thanh `.wav` về thư mục `input/` và xử lý:

```bash
cd /root/Applio
./automate_rvc.py 0 --url "https://www.youtube.com/watch?v=xxxx"
```

*Mặc định, script đã được tích hợp sẵn proxy trả phí của Proxy Seller (`http://quocdattranhuu1606:iQVzmppt6C@74.0.101.207:50100`) nên bạn không cần nhập thông số proxy khi chạy.*

#### Sử dụng Proxy Tor hoặc Proxy tùy chỉnh khác
Nếu muốn chuyển đổi sang sử dụng cổng Tor nội bộ thay thế cho proxy mặc định:

```bash
./automate_rvc.py 0 --url "https://www.youtube.com/watch?v=xxxx" --tor
```

Hoặc chỉ định proxy khác tùy ý:

```bash
./automate_rvc.py 0 --url "https://www.youtube.com/watch?v=xxxx" --proxy "socks5://127.0.0.1:9050"
```

#### Sử dụng Cookies (Bắt buộc để xác minh bot)
YouTube thường yêu cầu đăng nhập/xác thực tài khoản. Script sẽ tự động tìm kiếm cookies ở file `/root/cookies.txt`. Đảm bảo đã xuất cookies của bạn bằng tiện ích "Get cookies.txt LOCALLY" và dán vào file này. Bạn cũng có thể chỉ định file cookie tùy chỉnh khác:

```bash
./automate_rvc.py 0 --url "https://www.youtube.com/watch?v=xxxx" --cookies /path/to/custom_cookies.txt
```

---

### Các tham số tùy chọn chung khác

Chọn model cụ thể khi có nhiều model:

```bash
cd /root/Applio
./automate_rvc.py 0 --model kurumi_vietnamese
```

Tự phát hiện vùng có giọng hát và tắt tiếng rò trong stem vocal trước khi chạy RVC:

```bash
./automate_rvc.py 0 --audio my_audio.wav --model kurumi_vietnamese --auto-vocal-mask
```

Chế độ này phân tích tương quan âm lượng giữa `vocals.wav` và `no_vocals.wav`, loại các vùng rò ngắn, thêm khoảng đệm và fade ở đầu/cuối câu hát. Có thể điều chỉnh bằng `--vocal-threshold-db`, `--vocal-ratio-db`, `--vocal-padding` và `--vocal-min-duration`.

Đặt tên output MP3:

```bash
cd /root/Applio
./automate_rvc.py 0 --audio my_audio.wav --model default --output my_audio_rvc.mp3
```

Đổi pitch:

```bash
./automate_rvc.py 12
./automate_rvc.py -12
```

Gợi ý pitch:

- `0`: giữ nguyên tone.
- `12`: tăng 1 quãng tám.
- `-12`: giảm 1 quãng tám.

---

## 6. Kết quả đầu ra

File audio sau khi đổi giọng được lưu tại dạng **MP3**:

```bash
/root/Applio/output/<ten_audio>_rvc_<ten_model>.mp3
```

Ví dụ:
 
```bash
/root/Applio/output/my_audio_rvc_default.mp3
```

RVC vẫn cần xuất WAV nội bộ, nên script tạo file vocal WAV tạm trong `output`, mix với nhạc nền sang MP3 bằng FFmpeg, rồi tự xóa file WAV tạm.

---

## 7. Lệnh RVC chạy ngầm

Với bài hát, script chạy ngầm 3 bước:

1. Demucs tách audio thành `vocals.wav` và `no_vocals.wav`.
2. Applio/RVC đổi giọng `vocals.wav` thành WAV tạm.
3. FFmpeg mix vocal đã đổi với `no_vocals.wav` và xuất MP3.

Lệnh Applio CLI tạo WAV tạm:

```bash
/root/Applio/.venv/bin/python /root/Applio/core.py infer \
  --pitch [PITCH] \
  --index_rate 0.7 \
  --volume_envelope 1.0 \
  --protect 0.33 \
  --f0_method rmvpe \
  --input_path [AUDIO_PATH] \
  --output_path [OUTPUT_WAV] \
  --pth_path [PTH_PATH] \
  --index_path [INDEX_PATH] \
  --export_format WAV \
  --split_audio True
```

Sau đó mix nhạc nền lại:

```bash
ffmpeg -y -i [CONVERTED_VOCAL_WAV] -i [NO_VOCALS_WAV] \
  -filter_complex "[0:a]volume=1.0[v];[1:a]volume=1.0[m];[v][m]amix=inputs=2:duration=longest:dropout_transition=2" \
  -vn -codec:a libmp3lame -b:a 192k [OUTPUT_MP3]
```

Có thể tắt chia nhỏ audio nếu máy đủ RAM:

```bash
./automate_rvc.py 0 --no-split
```

---

## 8. Lưu ý vận hành

- Mỗi lần chạy nên để **1 audio chính** trong `input`, hoặc dùng `--audio` để chọn đúng file.
- Nếu có nhiều model `.pth`, dùng `--model <tên_model>` để tránh chọn nhầm.
- `.index` không bắt buộc nhưng nên có để chất lượng tốt hơn.
- Script tự kiểm tra `/root/Applio/core.py`, `/root/Applio/.venv/bin/python`, `ffmpeg`, package Python cơ bản, prerequisites, và voice model.
- Không xử lý video trong quy trình mặc định. Video làm workflow nặng và không phù hợp yêu cầu hiện tại.

---

## 9. Checklist nhanh

```bash
# 1) Copy script vào Applio
cp /root/.agents/skills/rvc-video-voice-changer/scripts/automate_rvc.py /root/Applio/automate_rvc.py
chmod +x /root/Applio/automate_rvc.py

# 2) Bỏ 1 audio vào input
ls -lh /root/Applio/input

# 3) Chạy đổi giọng
cd /root/Applio
./automate_rvc.py 0

# 4) Lấy output
ls -lh /root/Applio/output
```
