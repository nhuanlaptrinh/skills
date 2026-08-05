---
name: video-to-fanpage-alt-sheet
description: Create or rerender an Anh Lập Trình vertical video from a transcript, generate MagicVoice/HuggingFace audio, align exact captions, render via video factory, copy the MP4 to /root/Automation/facebook/05_skill_facebook_zalo/images, and append the media to Google Sheet fanpage_alt with status PA. Use when the user asks OpenClaw/Codex to tạo video đưa vào Fanpage ALT, lưu vào sheet fanpage_alt, copy video sang 05_skill_facebook_zalo/images, or tạo lại video giữ nguyên tên file.
---

# Video To Fanpage ALT Sheet

Use this skill when the user wants to create a video for the Fanpage ALT content queue, or rerender an existing queued video while keeping the same MP4 filename.

## Project

Pipeline folder:

```bash
/root/Automation/content_pipeline/05_Facebook_Youtube_Zalo_GGS/04_video_to_fanpage_alt_sheet
```

Main script:

```bash
create_video_to_fanpage_alt.py
```

Run from the pipeline folder with its local venv:

```bash
cd /root/Automation/content_pipeline/05_Facebook_Youtube_Zalo_GGS/04_video_to_fanpage_alt_sheet
.venv/bin/python create_video_to_fanpage_alt.py --transcript-file /path/to/transcript.txt
```

## Required Workflow

The script performs this sequence:

1. Read transcript from `--transcript`, `--transcript-file`, or stdin.
2. Create a short hook title and exactly 5 hashtags for Sheet column A. Hashtags are for the post/Sheet only; do not render hashtags inside the video visuals.
3. Generate voice audio using MagicVoice/HuggingFace at `/root/Apps/huggingface_audio` with `Nhuan Voice V2`, then speed the final narration audio to `1.15x` before caption alignment unless the user explicitly requests a different speed.
4. Save source files under video factory input:
   - `input/<slug>_transcript.txt`
   - `input/<slug>_voice.wav`
   - `input/<slug>_captions_exact.json`
5. Apply `transcript-centered-video-render`: generate and validate exact captions before render.
6. Render with `/root/Apps/video_factory/10.Nha_May_San_Xuat_Video`.
7. Save final MP4 to `output/<slug>/<slug>.mp4`.
8. Copy final MP4 to `/root/Automation/facebook/05_skill_facebook_zalo/images/<slug>.mp4`.
9. Append Google Sheet `fanpage_alt` with status `PA`.

## Audio And Caption Rules

Always preserve this source-of-truth chain:

```text
transcript -> MagicVoice audio -> captions_exact.json -> video composition
```

Default narration speed:

- Always use `1.15x` audio speed for newly created videos unless the user explicitly asks for another speed.
- Apply speed-up after generating the MagicVoice WAV and before creating `captions_exact.json`.
- Keep a backup of the original normal-speed WAV when manually adjusting, e.g. `input/<slug>_voice_original_normal_speed.wav`.
- After changing speed, regenerate `captions_exact.json` and run validation. Never reuse captions from the old speed.

Example manual speed adjustment:

```bash
cp input/<slug>_voice.wav input/<slug>_voice_original_normal_speed.wav
ffmpeg -y -i input/<slug>_voice_original_normal_speed.wav \
  -filter:a "atempo=1.15" \
  input/<slug>_voice.wav
```

The pipeline must use:

```bash
.venv_align/bin/python scripts/align_clean_transcript_captions.py \
  --video input/<slug>_voice.wav \
  --transcript input/<slug>_transcript.txt \
  --out input/<slug>_captions_exact.json \
  --model small

python3 /root/.agents/skills/transcript-centered-video-render/scripts/validate_exact_captions.py \
  --audio input/<slug>_voice.wav \
  --transcript input/<slug>_transcript.txt \
  --captions input/<slug>_captions_exact.json
```

Do not split captions evenly by duration. Caption timing and highlighted words must come from `captions_exact.json`.

## Google Sheet Output

Sheet target:

```text
Spreadsheet ID: 1txOKAVBAJhWyWNr4rxjs7zn5GKJvJKrQDmISNur-TVg
Worksheet: fanpage_alt
```

The script reads local configuration/credentials from:

```text
/root/Automation/facebook/05_skill_facebook_zalo/skill_post_fanpage_alt/.env
/root/Automation/facebook/05_skill_facebook_zalo/skill_post_fanpage_alt/googlesheetcn.json
```

Never print, edit, or copy secrets from these files.

Sheet columns:

| Column | Value |
|---|---|
| A `Tiêu Đề` | Short curiosity hook + exactly 5 hashtags |
| B `Ebook` | Blank unless user provides `--ebook` |
| C `Hình ảnh Hoặc Video` | MP4 filename only, no full path |
| D `Status` | `PA` |

Hashtags: always include `#anhlaptrinh`; choose 4 more based on transcript, such as `#aiautomation`, `#ai`, `#python`, `#openclaw`, `#codex`, `#obsidian`, `#antigravity`, `#claude`. Hashtags must only appear in Sheet/post text, never inside rendered video image text, overlays, headlines, badges, or captions.

## Create New Video

If user provides transcript text, save it to a temporary `.txt` file first, then run:

```bash
cd /root/Automation/content_pipeline/05_Facebook_Youtube_Zalo_GGS/04_video_to_fanpage_alt_sheet
.venv/bin/python create_video_to_fanpage_alt.py \
  --transcript-file /path/to/transcript.txt
```

Optional custom title:

```bash
.venv/bin/python create_video_to_fanpage_alt.py \
  --title "Bạn đang dùng AI quá thủ công?" \
  --transcript-file /path/to/transcript.txt
```

Optional ebook/link:

```bash
.venv/bin/python create_video_to_fanpage_alt.py \
  --transcript-file /path/to/transcript.txt \
  --ebook "https://drive.google.com/file/d/FILE_ID/view"
```

## Rerender Existing Video Without Renaming

Use when the user says the current video is not satisfactory and wants to create it again while keeping the same Sheet/media filename.

```bash
cd /root/Automation/content_pipeline/05_Facebook_Youtube_Zalo_GGS/04_video_to_fanpage_alt_sheet
.venv/bin/python create_video_to_fanpage_alt.py \
  --rerender-media 123_ten_video_720x1280.mp4 \
  --transcript-file /path/to/transcript_moi.txt
```

Rerender behavior:

- Keeps the same slug and MP4 filename.
- Regenerates MagicVoice audio from the new transcript.
- Regenerates and validates `captions_exact.json`.
- Overwrites both:
  - `/root/Apps/video_factory/10.Nha_May_San_Xuat_Video/output/<slug>/<slug>.mp4`
  - `/root/Automation/facebook/05_skill_facebook_zalo/images/<slug>.mp4`
- Does not append a new Sheet row by default.
- Backs up existing MP4 files to `/root/_Backups/video_to_fanpage_alt_sheet/<slug>_<timestamp>/` before overwriting.

Only use `--append-sheet-on-rerender` if the user explicitly wants a new Sheet row for the same media filename.

## Dry Run

Before a real run, especially when OpenClaw is unsure, run:

```bash
.venv/bin/python create_video_to_fanpage_alt.py \
  --transcript-file /path/to/transcript.txt \
  --dry-run
```

Dry-run must not render, copy MP4, or write Google Sheet.

## Safety

- Do not auto-post Facebook; this pipeline only queues content with status `PA`.
- Do not modify cron.
- Do not edit `.env`, credentials, Chrome/Selenium profiles, or tokens.
- Do not print secrets.
- Read `/root/Apps/video_factory/10.Nha_May_San_Xuat_Video/AGENTS.md` before changing video factory files.
- For actual renders, follow `video-factory-render-checklist` and `transcript-centered-video-render`.
- After important changes, update `/root/_Second_AI_Brain/06_Nhat_Ky_Thay_Doi.md`.
