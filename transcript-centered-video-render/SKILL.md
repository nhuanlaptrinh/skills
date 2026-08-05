---
name: transcript-centered-video-render
description: Render or rerender Anh Lập Trình/video-factory videos with captions synchronized to MagicVoice/OmniVoice audio generated from a transcript. Use when creating videos from Google Sheet transcript columns, running the RS audio/video pipeline, fixing caption/audio mismatch, rerendering row videos, generating `captions_exact.json`, or ensuring `input/{slug}_transcript.txt`, `input/{slug}_voice.wav`, and `input/{slug}_captions_exact.json` stay the timing source of truth.
---

# Transcript-Centered Video Render

Use this skill for `/root/Apps/video_factory/10.Nha_May_San_Xuat_Video` and the RS audio/video pipeline at:

`/root/Automation/content_pipeline/05_Facebook_Youtube_Zalo_GGS/03_google_sheet_rs_audio_video_pipeline`

## Principle

Transcript is the source of truth. MagicVoice audio is generated from that transcript, so captions and scene timing must be derived from the transcript-aligned audio timestamps, not from evenly splitting duration.

## Required Workflow

1. Keep the source transcript at `input/<slug>_transcript.txt`.
2. Generate or reuse voice audio at `input/<slug>_voice.wav`.
3. Generate exact captions:
   ```bash
   cd /root/Apps/video_factory/10.Nha_May_San_Xuat_Video
   .venv_align/bin/python scripts/align_clean_transcript_captions.py \
     --video input/<slug>_voice.wav \
     --transcript input/<slug>_transcript.txt \
     --out input/<slug>_captions_exact.json \
     --model small
   ```
4. Build or patch `index.html` so captions are loaded from `captions_exact.json`:
   - Use each caption's `start`, `end`, `text`, and `wordStarts`.
   - Highlight words using `wordStarts`, not an even interval.
   - Do not rewrite captions away from the source transcript.
5. Align scene/headline timing to the same caption groups. Scene text can be summarized, but it must describe the same idea being read at that time.
6. Validate before final render:
   ```bash
   python3 scripts/check_logo_ratio_css.py
   npm run check
   python3 /root/.agents/skills/transcript-centered-video-render/scripts/validate_exact_captions.py \
     --audio input/<slug>_voice.wav \
     --transcript input/<slug>_transcript.txt \
     --captions input/<slug>_captions_exact.json
   ```
7. Render and copy output:
   ```bash
   npm run render
   cp renders/<new-render>.mp4 output/<slug>/<slug>.mp4
   cp output/<slug>/<slug>.mp4 output/00_output_trend_ai_tintuc/<slug>.mp4
   ```
8. Check final MP4:
   ```bash
   ffprobe -v error -select_streams v:0 -show_entries stream=width,height,duration -of default=nw=1 output/<slug>/<slug>.mp4
   ffprobe -v error -show_entries stream=index,codec_type,codec_name -of csv=p=0 output/<slug>/<slug>.mp4
   ```
9. Extract at least two frames, one near the start and one near the middle, to visually inspect logo and caption meaning.
10. Send Telegram notification only after final MP4 has been copied to the output folder.

## Acceptance Rules

- `captions_exact.json` must exist before render.
- `match_ratio` should be `1.0` when possible; investigate if below `0.95`.
- Caption end must not exceed audio duration by more than `0.35s`.
- Each caption should normally be `1–4.8s`; prefer `1–3s` for short social videos, but allow longer when Vietnamese clauses are naturally connected.
- Captions must cover the transcript in order and use original words.
- `npm run check` must have `0 error`; warnings can be reported if not blocking.
- MP4 must be `720x1280`, contain audio, and be copied to both output locations.
- Logo must not be forced square; `.brand img` must use `width:auto`, fixed `height`, and `object-fit:contain`.

## Pipeline Rule

For future RS/OpenClaw pipeline runs, after MagicVoice creates `input/<slug>_voice.wav`, run `align_clean_transcript_captions.py` immediately and mention this file in the OpenClaw prompt as mandatory timing input. OpenClaw must not split captions by equal duration.

## Rerender Existing Video

Before overwriting an existing video:

1. Backup `index.html`, `styles.css`, and both MP4 outputs into `/root/_Backups/video_rerender_<slug>_<timestamp>`.
2. Generate or refresh `input/<slug>_captions_exact.json`.
3. Patch `index.html` to use exact caption timing.
4. Render, copy over both MP4 outputs, and validate with `ffprobe`.
5. Update `/root/_Second_AI_Brain/06_Nhat_Ky_Thay_Doi.md`.
