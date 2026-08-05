---
name: video-clone-ytb
description: "Dựng reel HyperFrames dọc từ YouTube URL hoặc Google Sheet queue bằng pipeline video-clone-ytb. Use when Codex needs to đọc Google Sheet Status=Run, lấy transcript YouTube bằng youtube-transcript-api qua Tor, tải audio/phụ đề bằng yt-dlp khi có cookies/proxy, giữ narration.mp3 giọng cố định, cập nhật templates/video-clone-ytb, validate, render MP4, và có thể publish Facebook Page."
---

# Video Clone YTB

## Tổng Quan

Dùng skill này cho pipeline `video-clone-ytb`. Workflow chuẩn hiện tại:

1. Đọc YouTube URL từ Google Sheet queue hoặc từ lệnh một URL.
2. Lấy transcript ưu tiên bằng `youtube-transcript-api` qua Tor proxy `socks5://127.0.0.1:9050`.
3. Lưu transcript thô để kiểm tra: `transcript_raw_api.json` và `transcript_raw_api.txt`.
4. Convert transcript sang word-level timing trong `transcript.json`.
5. Giữ nguyên `assets/narration.mp3` nếu file đã có sẵn; đây là giọng bắt buộc.
6. Dùng `yt-dlp` để tải audio/phụ đề/metadata khi proxy/cookies dùng được; nếu fail thì vẫn tiếp tục bằng transcript API và narration có sẵn.
7. Cập nhật composition bằng `automation/update_composition_from_transcript.py`.
8. Validate HyperFrames rồi render MP4.

Skill này thay cho tên cũ `claude-cowork-reel`. Nếu gặp tên cũ trong output/file, ưu tiên đổi sang `video-clone-ytb`.

## Yêu Cầu Môi Trường

Cần có:

```bash
python3 -m pip install -U youtube-transcript-api requests[socks] yt-dlp
```

Tor proxy cần chạy ở:

```text
socks5://127.0.0.1:9050
```

Kiểm tra Tor:

```bash
ss -ltnp | grep 9050
curl -x socks5://127.0.0.1:9050 -I https://www.youtube.com
```

Biến môi trường khuyến nghị:

```bash
export YT_DLP_PROXY=socks5://127.0.0.1:9050
export YT_DLP_COOKIES=/root/cookies.txt
```

Cookie không bắt buộc cho transcript API. Cookie chỉ giúp `yt-dlp` tải metadata/audio/subtitle khi YouTube chặn bot. Không commit hoặc copy public cookie/credential.

## Quy Trình Queue Google Sheet

Lệnh chính trong bundle:

```bash
cd /root/hyperframes/video-clone-ytb-bundle
YT_DLP_PROXY=socks5://127.0.0.1:9050 YT_DLP_COOKIES=/root/cookies.txt python3 automation/google_sheet_queue.py
```

Luồng bắt buộc:

1. Đọc Google Sheet tab `Post`, tìm dòng đầu tiên có `Status = Run`.
2. Đổi `Status` thành `Pro` trước khi xử lý để tránh chạy trùng.
3. Chạy `automation/youtube_reel_pipeline.py` với URL YouTube:
   - Gọi `yt-dlp` với `--proxy` và `--cookies` nếu có.
   - Nếu `assets/narration.mp3` tồn tại, không ghi đè file này; tải audio nguồn thành `source_audio.mp3` nếu tải được.
   - Tải VTT bằng `yt-dlp` nếu có.
   - Nếu VTT/yt-dlp fail, gọi `automation/transcript_pipeline.py` để lấy transcript bằng `youtube-transcript-api` qua Tor.
   - Tạo/cập nhật `transcript.json`, `script.short.txt`, `pipeline-meta.json`.
   - Lưu bản kiểm tra transcript API vào `transcript_raw_api.json` và `transcript_raw_api.txt`.
4. Chạy `automation/update_composition_from_transcript.py`.
5. Chạy `npx hyperframes validate templates/video-clone-ytb`.
6. Render MP4 ra `output/video-clone-ytb-<videoId>.mp4`.
7. Nếu `META_PUBLISH_ENABLED=true`, publish Facebook Page và tạo first comment.
8. Ghi kết quả về Google Sheet, đổi `Status` thành `Success` hoặc `Error: ...`.

## Chạy Một URL YouTube

```bash
cd /root/hyperframes/video-clone-ytb-bundle
YT_DLP_PROXY=socks5://127.0.0.1:9050 YT_DLP_COOKIES=/root/cookies.txt \
  python3 automation/youtube_reel_pipeline.py "YOUTUBE_URL" --project-dir templates/video-clone-ytb
python3 automation/update_composition_from_transcript.py --project-dir templates/video-clone-ytb
npx hyperframes validate templates/video-clone-ytb
npx hyperframes render templates/video-clone-ytb --output output/video-clone-ytb-VIDEO_ID.mp4
```

Nếu chỉ muốn kiểm tra transcript API:

```bash
cd /root/hyperframes/video-clone-ytb-bundle
YT_DLP_PROXY=socks5://127.0.0.1:9050 \
  python3 automation/transcript_pipeline.py "YOUTUBE_URL" --project-dir templates/video-clone-ytb
```

## File Đầu Ra Chính

Trong `templates/video-clone-ytb/assets/`:

- `narration.mp3`: giọng bắt buộc, không được ghi đè nếu đã tồn tại.
- `source_audio.mp3`: audio YouTube tải bằng `yt-dlp` để tham khảo nếu tải được.
- `transcript_raw_api.json`: transcript thô từ `youtube-transcript-api`.
- `transcript_raw_api.txt`: full text transcript để người dùng kiểm tra.
- `transcript.json`: word-level transcript dùng cho caption.
- `script.short.txt`: script rút gọn để cập nhật scene text.
- `pipeline-meta.json`: metadata URL, videoId, renderDuration, wordCount.
- `thumbnail.jpg`: thumbnail nếu tải được.

MP4 cuối nằm trong:

```text
output/video-clone-ytb-<videoId>.mp4
```

## Quy Tắc Narration

- Luôn ưu tiên `templates/video-clone-ytb/assets/narration.mp3` làm audio chính.
- Không để `yt-dlp` ghi đè `narration.mp3` khi file đã tồn tại.
- Khi cần tải audio YouTube, lưu thành `source_audio.mp3` hoặc `input/video-clone-ytb/<videoId>.mp3` để tham khảo.
- Render duration nên lấy theo duration của `narration.mp3` nếu file tồn tại.

## Quy Tắc Transcript

- Ưu tiên `youtube-transcript-api` qua Tor để lấy transcript vì ổn định hơn khi `yt-dlp` bị YouTube chặn bot.
- Luôn lưu raw transcript để kiểm tra tải về được hay không:
  - `assets/transcript_raw_api.json`
  - `assets/transcript_raw_api.txt`
- Convert segment transcript thành word-level timing trong `assets/transcript.json`.
- Nếu transcript API fail, mới fallback sang VTT từ `yt-dlp` hoặc title fallback.

## Quy Tắc Composition

- Composition chính nằm trong `templates/video-clone-ytb/index.html`.
- Mỗi visual block có timing riêng phải là clip HyperFrames đúng chuẩn.
- Dùng `data-start`, `data-duration`, và `data-track-index`.
- Nếu dùng GSAP, timeline phải paused và đăng ký trên `window.__timelines`.
- Không dùng `Date.now()`, unseeded `Math.random()`, hoặc fetch network lúc render.
- Scene đầu phải có thông tin chính hiển thị ngay tại `t=0s`.
- Caption text lấy từ transcript hiện tại, không giữ nội dung job cũ.

## Sync Guard

Trước render, kiểm tra:

- `pipeline-meta.json` đúng URL/video hiện tại.
- `script.short.txt` đúng nội dung hiện tại.
- `transcript.json` có word timing hợp lệ.
- `transcript_raw_api.txt` có nội dung nếu dùng transcript API.
- `index.html` đã được updater ghi lại.
- Không còn text, brand, hoặc chủ đề của job trước.
- Frame `t=0s` không bị trống.

Nếu transcript hoặc subtitle đã đổi nhưng scene text chưa đổi theo, phải fail trước render.

## Publish Facebook Page

Publish chỉ chạy khi:

```text
META_PUBLISH_ENABLED=true
```

Các biến môi trường cần có:

```text
META_GRAPH_API_VERSION=v23.0
META_PAGE_ID=
META_PAGE_ACCESS_TOKEN=
META_POST_MESSAGE=
META_FIRST_COMMENT=
```

Không commit token hoặc credential vào repo/bundle portable.

## Google Sheet Env

Các biến thường dùng:

| Variable | Ghi chú |
|---|---|
| `GOOGLE_SERVICE_ACCOUNT_JSON` | File credential service account |
| `GOOGLE_SHEETS_SPREADSHEET_ID` | Spreadsheet ID |
| `GOOGLE_SHEETS_SHEET_NAME` | Tab name, mặc định `Post` |
| `GOOGLE_SHEETS_LINK_COLUMN` | Cột URL, mặc định `LinkYoutube` |
| `GOOGLE_SHEETS_STATUS_COLUMN` | Cột trạng thái, mặc định `Status` |
| `GOOGLE_SHEETS_STATUS_RUN` | Trạng thái chờ xử lý, mặc định `Run` |
| `GOOGLE_SHEETS_STATUS_INPROGRESS` | Trạng thái đang xử lý, mặc định `Pro` |
| `GOOGLE_SHEETS_STATUS_SUCCESS` | Trạng thái hoàn tất, mặc định `Success` |
| `GOOGLE_SHEETS_STATUS_ERROR` | Trạng thái lỗi, mặc định `Error` |

## Checklist Trước Render

1. Tor proxy `127.0.0.1:9050` chạy được.
2. `youtube-transcript-api` import được.
3. `yt-dlp --version` chạy được.
4. `templates/video-clone-ytb/assets/narration.mp3` tồn tại nếu cần giữ giọng cố định.
5. `templates/video-clone-ytb/assets/transcript_raw_api.txt` có text nếu dùng transcript API.
6. `templates/video-clone-ytb/assets/transcript.json` có word timing hợp lệ.
7. `templates/video-clone-ytb/assets/script.short.txt` đúng nội dung hiện tại.
8. `templates/video-clone-ytb/index.html` đã được updater ghi lại.
9. `npx hyperframes validate templates/video-clone-ytb` pass 0 errors.
10. Output dùng tên `output/video-clone-ytb-<videoId>.mp4`.
