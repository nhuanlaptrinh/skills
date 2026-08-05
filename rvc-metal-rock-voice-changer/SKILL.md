---
name: rvc-metal-rock-voice-changer
description: Đổi riêng giọng hát sang model damvinhhung_vietnamese đi kèm skill bằng Applio RVC, giữ và phối lại bốn stem Demucs thành metal rock, tạo Auto Vocal Mask, trống metal theo BPM, master MP3 256 kbps 48 kHz stereo và kiểm định đầu ra. Dùng trên VPS đã có source Applio.
---

# RVC Metal Rock Voice Changer

Dùng skill này khi người dùng muốn tải một bài hát từ YouTube hoặc dùng audio cục bộ, chỉ đổi phần giọng hát qua model RVC và phối nhạc nền thành metal rock. VPS đích được giả định đã có Applio hoạt động tại `/root/Applio` hoặc đường dẫn khai báo bằng `APPLIO_DIR`.

## Kết quả pipeline

Script `scripts/rvc_metal_pipeline.py` thực hiện tuần tự:

1. Tải audio YouTube bằng `yt-dlp`, cookies và proxy do người vận hành cung cấp.
2. Dùng Demucs `htdemucs` tách `vocals`, `drums`, `bass`, `other`.
3. Tạo Auto Vocal Mask theo năng lượng vocal và tỷ lệ vocal/nhạc nền.
4. Chạy `core.py infer` của Applio với RMVPE và model `.pth/.index` đã có.
5. Phân tích BPM/beat từ stem trống.
6. Tạo kick, double kick, snare, hi-hat và crash tổng hợp bám nhịp.
7. Parallel compression trống, bass drive, guitar distortion stereo từ stem `other`.
8. Mix/master WAV float, sau đó mã hóa MP3 256 kbps, 48 kHz, stereo đúng một lần.
9. Kiểm tra metadata, giải mã toàn bộ và đo peak không vượt `-1 dB`.
10. Tạo báo cáo JSON gồm BPM, vùng vocal, peak và thời gian từng công đoạn.

## Model giọng mặc định bắt buộc

Skill đóng gói sẵn model đã tải ngày **16/07/2026**:

```text
assets/models/damvinhhung_vietnamese.pth
assets/models/damvinhhung_vietnamese.index
```

Khi chạy, nếu `/root/Applio/input` chưa có hai file này, script tự chép model từ skill sang Applio. Model duy nhất được CLI chấp nhận là `damvinhhung_vietnamese`; nếu bỏ tham số `--model`, script tự dùng model này.

## Nguyên tắc bắt buộc

- Skill này được chủ sở hữu yêu cầu nhúng cứng proxy Proxy-Seller mặc định để có thể copy sang VPS khác và chạy ngay.
- Ưu tiên proxy từ tham số `--proxy`, sau đó `YTDLP_PROXY`; nếu cả hai không được cung cấp thì dùng proxy Proxy-Seller đã nhúng trong script.
- Đọc cookies từ `YTDLP_COOKIES` hoặc tham số `--cookies`.
- Không chuyển toàn bộ nhạc nền qua RVC; chỉ stem vocal đã qua Auto Vocal Mask được chuyển giọng.
- Giọng đầu ra bắt buộc sử dụng model `damvinhhung_vietnamese` đi kèm skill.
- Nếu Applio chưa có model, script tự cài cả `.pth` và `.index` từ `assets/models`.
- Luôn giữ thông báo metadata rằng đây là giọng tổng hợp AI/RVC, không phải bản thu thật của ca sĩ.
- Nếu peak MP3 lớn hơn `-1 dB`, script dừng với lỗi và giữ WAV master để chỉnh lại; không báo hoàn thành sai.

## Yêu cầu VPS đích

Kiểm tra các file và lệnh:

```bash
test -f /root/Applio/core.py
test -x /root/Applio/.venv/bin/python
test -x /root/Applio/.venv/bin/yt-dlp
ffmpeg -version
ffprobe -version
/root/Applio/.venv/bin/python -c "import torch, librosa, soundfile, numpy, demucs"
```

Sau lần chạy đầu tiên, model được tự chép vào:

```text
/root/Applio/input/damvinhhung_vietnamese.pth
/root/Applio/input/damvinhhung_vietnamese.index
```

## Cài skill sang VPS khác

Copy nguyên thư mục này vào thư mục skills của Codex/agent:

```bash
mkdir -p /root/.agents/skills
cp -a rvc-metal-rock-voice-changer /root/.agents/skills/
chmod +x /root/.agents/skills/rvc-metal-rock-voice-changer/scripts/rvc_metal_pipeline.py
```

Không cần copy script vào source Applio. Script tự gọi `/root/Applio/core.py` và virtualenv của Applio.

## Cấu hình cookies và proxy

Proxy Proxy-Seller HTTP/HTTPS cổng `50100` đã được cấu hình mặc định trong script theo yêu cầu của chủ sở hữu. Chỉ cần cấu hình cookies:

```bash
export YTDLP_COOKIES=/root/cookies.txt
export APPLIO_DIR=/root/Applio
```

Khi proxy mặc định hết hạn hoặc cần thay proxy khác, ghi đè bằng biến môi trường:

```bash
export YTDLP_PROXY='http://username:password@ip:port'
```

Không in nguyên URL proxy có mật khẩu vào báo cáo chạy hoặc câu trả lời cho người dùng.

## Chạy với YouTube

```bash
cd /root/.agents/skills/rvc-metal-rock-voice-changer
./scripts/rvc_metal_pipeline.py \
  --url 'https://www.youtube.com/watch?v=VIDEO_ID' \
  --source-id VIDEO_ID \
  --title 'Tên bài hát' \
  --pitch 0 \
  --output damvinhhung_metal_rock.mp3
```

Output được đặt trong:

```text
/root/Applio/output/damvinhhung_metal_rock.mp3
/root/Applio/output/damvinhhung_metal_rock.report.json
```

## Chạy với audio cục bộ

```bash
cd /root/.agents/skills/rvc-metal-rock-voice-changer
./scripts/rvc_metal_pipeline.py \
  --audio '/root/Applio/input/bai_hat.wav' \
  --title 'Tên bài hát' \
  --pitch 0 \
  --output damvinhhung_metal_rock.mp3
```

## Tùy chỉnh Auto Vocal Mask

Mặc định phù hợp đa số bài pop/ballad:

```text
--vocal-threshold-db -38
--vocal-ratio-db -14
--vocal-padding 0.45
--vocal-min-duration 1.3
```

Nếu mất câu hát nhỏ, giảm `--vocal-threshold-db` xuống `-42` hoặc giảm `--vocal-ratio-db` xuống `-17`.

Nếu intro/nhạc cụ bị nhận nhầm thành vocal, tăng `--vocal-threshold-db` lên `-34`, tăng `--vocal-ratio-db` lên `-10`, hoặc tăng `--vocal-min-duration`.

## Kiểm tra sau khi chạy

Đọc báo cáo JSON trước, sau đó xác nhận trực tiếp:

```bash
FILE=/root/Applio/output/damvinhhung_metal_rock.mp3
ffprobe -v error \
  -show_entries format=duration,size,bit_rate:stream=codec_name,sample_rate,channels,channel_layout \
  -of default=noprint_wrappers=1 "$FILE"
ffmpeg -v error -i "$FILE" -f null -
ffmpeg -hide_banner -i "$FILE" -af volumedetect -f null - 2>&1 | grep -E 'mean_volume|max_volume'
```

Điều kiện đạt:

- `codec_name=mp3`
- `sample_rate=48000`
- `channels=2`
- `channel_layout=stereo`
- bitrate xấp xỉ `256000`
- giải mã toàn bộ không có lỗi
- `max_volume` không lớn hơn `-1.0 dB`

## Báo cáo cho người dùng

Sau khi hoàn thành, báo:

- Đường dẫn MP3 và report JSON.
- Tên bài, model, pitch.
- BPM phân tích và BPM metal.
- Số vùng Auto Vocal Mask cùng thời điểm bắt đầu/kết thúc.
- Thời lượng, bitrate, sample rate, stereo và peak.
- Thời gian tải, Demucs, RVC, phối/master, kiểm định và tổng thời gian.
- Nêu rõ đây là bản giọng tổng hợp AI/RVC.

Không khẳng định bản phối là bản thu thật của ca sĩ hoặc ban nhạc.
