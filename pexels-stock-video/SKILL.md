---
name: pexels-stock-video
description: Tự động tìm kiếm, tải về và cắt gọt stock video miễn phí bản quyền từ Pexels API (9:16 portrait, 16:9 landscape, 1:1 square) để tích hợp trực tiếp vào Nhà Máy Sản Xuất Video (/root/Apps/04_Nha_May_San_Xuat_Video) và các bài dựng HyperFrames/FFmpeg. Dùng khi người dùng muốn chèn b-roll, background video, video minh họa công nghệ, thiên nhiên, văn phòng, robot, hoặc cắt ngắn video stock cho Reels/Shorts/TikTok.
---

# Pexels Stock Video Skill

Skill cho phép AI Agent tương tác với Pexels Video API để tìm kiếm và sử dụng kho stock video HD/4K miễn phí bản quyền cho các dự án video ngắn, Reels, Shorts, TikTok và HyperFrames composition.

## Cấu Hình API Key

API Key được nạp tự động từ file `/root/Apps/04_Nha_May_San_Xuat_Video/.env`:

```env
PEXELS_API_KEY=Ht00...
```

Chủ động kiểm tra `.env` hoặc truyền biến môi trường `PEXELS_API_KEY` khi gọi script.

## Sử Dụng Tool Fetch Video

Tool nằm tại: `/root/Apps/04_Nha_May_San_Xuat_Video/scripts/fetch_pexels_video.py`.

### Các Lệnh Phổ Biến

#### 1. Tải Video Portrait (9:16 - Reels/Shorts/TikTok) dài 10 giây
```bash
python3 /root/Apps/04_Nha_May_San_Xuat_Video/scripts/fetch_pexels_video.py \
  --query "artificial intelligence robot" \
  --orientation portrait \
  --quality hd \
  --trim 10 \
  --output input/pexels_ai_10s.mp4
```

#### 2. Tải Video Landscape (16:9 - YouTube Standard)
```bash
python3 /root/Apps/04_Nha_May_San_Xuat_Video/scripts/fetch_pexels_video.py \
  --query "developer coding laptop" \
  --orientation landscape \
  --output input/pexels_coding_landscape.mp4
```

#### 3. Tải Video Vuông (1:1 - Facebook Post/Instagram Feed)
```bash
python3 /root/Apps/04_Nha_May_San_Xuat_Video/scripts/fetch_pexels_video.py \
  --query "city night lights" \
  --orientation square \
  --trim 15 \
  --output input/pexels_city_square.mp4
```

## Tham Số Chi Tiết CLI

| Tham số | Ngắn | Mặc định | Mô tả |
| --- | --- | --- | --- |
| `--query` | `-q` | `technology` | Từ khóa tìm kiếm (tiếng Anh) |
| `--orientation` | `-o` | `portrait` | Tỷ lệ khung hình: `portrait` (9:16), `landscape` (16:9), `square` (1:1) |
| `--quality` | `-k` | `hd` | Chất lượng ưu tiên: `hd`, `sd`, `1080p`, `720p` |
| `--min-duration` | | `5` | Độ dài tối thiểu của video stock (giây) |
| `--max-duration` | | `60` | Độ dài tối đa của video stock (giây) |
| `--output` | `-out` | `input/pexels_<query>_<id>.mp4` | Đích lưu file |
| `--trim` | `-t` | (None) | Cắt thời lượng bằng FFmpeg về số giây chỉ định (VD: `--trim 10`) |

## Tích Hợp Vào Composition HyperFrames

Khi đã tải video về `input/<filename>.mp4`, chèn vào `index.html` của HyperFrames:

```html
<video
  src="input/pexels_demo_10s.mp4"
  id="bg-video"
  data-start="0"
  data-duration="10"
  data-track-index="0"
  muted
  playsinline
  class="clip"
  style="position: absolute; width: 100%; height: 100%; object-fit: cover;"
></video>
```

> **Lưu ý quan trọng:**
> 1. Sử dụng `object-fit: cover;` để video tự lấp đầy khung hình composition 1080x1920.
> 2. Đặt `muted` và `playsinline` cho thẻ `<video>` để trình duyệt render đúng.
> 3. Luôn chạy `npx hyperframes check` để xác minh composition trước khi render MP4.
