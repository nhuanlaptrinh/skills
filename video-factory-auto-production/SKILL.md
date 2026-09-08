---
name: video-factory-auto-production
description: Quy trình tự động hóa sản xuất video ngắn (Reels, TikTok, Shorts 15-60s) trên hệ thống Video Factory dùng HyperFrames, ElevenLabs TTS (eleven_v3 với word timestamps) và Pexels API B-roll chuyển cảnh mỗi 3-6s.
---

# Video Factory Auto Production (HyperFrames + ElevenLabs + Pexels B-Roll)

Skill này dùng để tự động hóa toàn bộ quy trình sản xuất video dạng ngắn (15s – 60s) trên VPS, ứng dụng công nghệ kết hợp:
1. **Giọng đọc AI (TTS)**: Tạo giọng đọc tiếng Việt chân thực qua **ElevenLabs API** (model `eleven_v3` hoặc `eleven_multilingual_v2`) hoặc **Edge-TTS**, trích xuất trực tiếp mốc thời gian từng từ (`word_timestamps`) để chạy hiệu ứng chữ karaoke đồng bộ.
2. **Hình ảnh nền động (B-roll)**: Tự động tìm kiếm, tải và chuẩn hóa video cảnh quay chân thực từ **Pexels API** (`1280x720`, 30fps H.264), chuyển cảnh mượt mà cứ mỗi **3–6 giây một video**.
3. **Đồ họa & Dựng khung hình**: Sử dụng engine **HyperFrames** + **GSAP** tạo chuyển động mượt mà, phân lớp độ tương phản điện ảnh (Vignette overlay), hiệu ứng chữ nổi bật và thanh tiến trình.
4. **Xuất video**: Render bằng Headless Chrome pipeline ra file MP4 chuẩn xác, tích hợp 2 track âm thanh (Voiceover 1.0 + BGM 0.10).

---

## 1. Cấu hình & Biến môi trường (`.env`)

Mỗi thư mục Video Factory (ví dụ: `/root/Apps/member_vps/docker-users/data/<member>/04_Nha_May_San_Xuat_Video`) cần có file `.env`:

```env
ELEVANLABS_API_KEY=sk_...
PEXELS_API_KEY=prb...
ELEVENLABS_MODEL_ID=eleven_v3
ELEVENLABS_VOICE_THANG=I17U3AyPj7ZvX0kSQB9n
```

> [!IMPORTANT]
> - Tuyệt đối không in API Key ra màn hình hoặc ghi vào log / commit git.
> - Nếu sử dụng `eleven_v3` cho tiếng Việt, không truyền thêm tham số `language_code="vi"` trong payload gọi API để tránh timeout; model `eleven_v3` tự động nhận diện ngôn ngữ tiếng Việt từ nội dung văn bản.

---

## 2. Quy ước thư mục I/O (Bắt buộc theo AGENTS.md)

- **Đầu vào (`input/`)**: Chứa file kịch bản, âm thanh thuyết minh (`*_voice.mp3`), phụ đề (`.vtt`, `*_words.json`) và video thô tải về.
- **Tài nguyên chung (`assets/`)**:
  - `assets/music/`: Chứa file nhạc nền (ví dụ: `bgm-motivational.mp3`).
  - `assets/videos/`: Chứa các video B-roll đã chuẩn hóa `1280x720 30fps`.
  - `assets/fonts/`: Chứa font chữ tiếng Việt (ví dụ: `BeVietnamPro`).
- **Thành phẩm bàn giao (`output/<project-folder>/`)**:
  - **Quy tắc bắt buộc**: Không lưu file video trực tiếp tại gốc `output/`. Luôn tạo thư mục con theo tên dự án: `output/<tên-dự-án>/<tên-dự-án>.mp4`.
  - Đính kèm: kịch bản (`.txt`), audio độc lập (`.mp3`) và thư mục ảnh chụp trích xuất (`preview/`).

---

## 3. Quy trình 5 bước thực hiện chi tiết

### Bước 1: Soạn kịch bản theo mục tiêu thời lượng

Tốc độ đọc của ElevenLabs `eleven_v3` là khoảng **3.8 – 4.2 từ/giây**:
- **Video 15 giây**: 50 – 58 từ (3 cảnh).
- **Video 20 giây**: 68 – 76 từ (4 cảnh).
- **Video 30 giây**: 105 – 115 từ (5-6 cảnh).

Mỗi kịch bản nên gồm 4 phần:
1. **Hook**: Nêu vấn đề hoặc câu hỏi gây tò mò (3–4s).
2. **Warning / Problem**: Chỉ ra sai lầm phổ biến (3–4s).
3. **Strategy / Solution**: Đưa ra giải pháp/quy trình 3 bước (5–7s).
4. **Action / CTA**: Tư duy thực chiến & Kêu gọi hành động (4–6s).

---

### Bước 2: Sinh giọng đọc ElevenLabs có Word Timestamps

Sử dụng endpoint `/v1/text-to-speech/{voice_id}/with-timestamps` để nhận đồng thời file âm thanh MP3 và mảng `alignment` ký tự:

```bash
curl -s -X POST "https://api.elevenlabs.io/v1/text-to-speech/$VOICE_ID/with-timestamps" \
  -H "xi-api-key: $ELEVENLABS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Nội dung thuyết minh tiếng Việt...",
    "model_id": "eleven_v3"
  }' -o /tmp/eleven_response.json
```

Trích xuất mốc thời gian bắt đầu của từng từ (`word_starts`) để đưa vào timeline HyperFrames. Đo thời lượng thực tế bằng:
```bash
ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 input/<tên>_voice.mp3
```

---

### Bước 3: Tìm kiếm & Tải B-roll từ Pexels API (Mỗi 3–6s đổi cảnh)

1. **Tìm kiếm qua API**:
   ```bash
   curl -s "https://api.pexels.com/videos/search?query=artificial+intelligence&per_page=5&orientation=landscape" \
     -H "Authorization: $PEXELS_API_KEY"
   ```
2. **Lọc video 720p hoặc HD** (`width=1280` hoặc `height=720`).
3. **Chuẩn hóa bằng ffmpeg** (bảo đảm khớp tỷ lệ, không giật lag và không sparse keyframe):
   ```bash
   ffmpeg -y -i raw.mp4 -t <thời_lượng> \
     -vf "scale=1280:720:force_original_aspect_ratio=increase,crop=1280:720,fps=30" \
     -c:v libx264 -preset fast -crf 20 -r 30 -g 30 -keyint_min 30 -movflags +faststart -an \
     assets/videos/clip1.mp4
   ```

---

### Bước 4: Dựng Timeline HyperFrames (`index.html` & `styles.css`)

#### Nguyên tắc phân tầng Z-Index (Cực kỳ quan trọng)
Để chữ và đồ họa hiển thị rực rỡ, sắc nét trên nền video live-action:
- `video.bg-video`: `z-index: 0` (Nền video Pexels chuyển động)
- `.video-overlay`: `z-index: 1` (Lớp phủ tối `radial-gradient` làm nổi bật nội dung)
- `.grid-bg`, `.orb`: `z-index: 2` & `3` (Đồ họa không gian neon mờ)
- `.scene`: `z-index: 10` (Khung cảnh, tiêu đề, thẻ card, icon)
- `.brand`: `z-index: 40` (Logo thương hiệu)
- `.caption-layer`: `z-index: 50` (Phụ đề karaoke chạy theo giọng đọc)
- `.progress`: `z-index: 60` (Thanh tiến trình chạy ở cạnh dưới cùng)

#### Khai báo thẻ Video trong HTML
Mỗi thẻ `<video>` **bắt buộc phải có thuộc tính `id` riêng biệt** để trình render không bị đóng băng (freeze frame):
```html
<video id="bg-clip-1" class="clip bg-video" src="assets/videos/clip1.mp4" data-start="0" data-duration="4.0" data-track-index="1" muted playsinline></video>
<video id="bg-clip-2" class="clip bg-video" src="assets/videos/clip2.mp4" data-start="4.0" data-duration="4.5" data-track-index="2" muted playsinline></video>
```

#### Hai Track Âm Thanh Đồng Thời
```html
<audio id="bgm" class="clip" src="assets/music/bgm-motivational.mp3" data-start="0" data-duration="20.0" data-track-index="6" data-volume="0.10"></audio>
<audio id="voice" class="clip" src="input/hoc_ai_20s_voice.mp3" data-start="0" data-duration="20.0" data-track-index="7" data-volume="1.0"></audio>
```

---

### Bước 5: Kiểm tra Linter & Render Video MP4

1. **Chạy linter bắt buộc**:
   ```bash
   npx --yes hyperframes@0.6.96 lint
   ```
   *Phải bảo đảm `0 error(s)` trước khi render.*

2. **Render video ra đúng thư mục thành phẩm**:
   ```bash
   npx --yes hyperframes@0.6.96 render --low-memory-mode -o output/<tên_dự_án>/<tên_dự_án>.mp4
   ```
   *Cờ `--low-memory-mode` giúp render an toàn, bỏ qua bước hiệu chuẩn BeginFrame 30s và sử dụng phương pháp screenshot streaming mượt mà.*

3. **Kiểm tra thông số kỹ thuật file xuất**:
   ```bash
   ffprobe -v error -show_entries format=duration,size:stream=codec_name,width,height,r_frame_rate,sample_rate,channels -of default=noprint_wrappers=1 output/<tên_dự_án>/<tên_dự_án>.mp4
   ```

4. **Trích xuất ảnh chụp phân cảnh để đối soát**:
   ```bash
   ffmpeg -y -ss 00:00:02 -i output/<tên_dự_án>/<tên_dự_án>.mp4 -vframes 1 output/<tên_dự_án>/preview/frame_scene1.jpg
   ```

---

## 4. Sử dụng Helper Script có sẵn trong Skill

Skill cung cấp sẵn công cụ dòng lệnh thực thi tự động tại:
`/root/.agents/skills/video-factory-auto-production/scripts/generate_video.py`

### Cách dùng:
```bash
python3 /root/.agents/skills/video-factory-auto-production/scripts/generate_video.py \
  --project-dir /root/Apps/member_vps/docker-users/data/nv6_taovideo4/04_Nha_May_San_Xuat_Video \
  --output-name "hoc_ai_20s" \
  --text "Bạn muốn học A.I nhưng bị ngợp trước quá nhiều công cụ mới? Đừng cố nhồi nhét lý thuyết hay chạy theo mọi tool trên mạng. Cách nhanh nhất là chọn đúng một việc thực tế bạn đang làm, rồi ứng dụng A.I tự động hóa từng bước. Vướng đâu gỡ đó, tư duy thực chiến liên tục mới tạo ra kết quả đột phá. Bắt tay vào làm ngay hôm nay!" \
  --queries "ai technology" "coding developer" "robot automation" "future digital"
```

Script sẽ tự động:
1. Đọc API Key ElevenLabs & Pexels từ file `.env`.
2. Gọi ElevenLabs tạo audio và xuất word timestamps.
3. Tìm kiếm và tải 4 video B-roll Pexels, normalize về `1280x720`.
4. Hướng dẫn lệnh HyperFrames render ra thành phẩm.
