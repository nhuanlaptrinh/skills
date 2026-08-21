---
name: openclaw-local-voice-stt
description: Install, operate, benchmark, or repair offline Telegram/OpenClaw voice transcription using faster-whisper on CPU without a paid transcription API. Use for local STT setup, CPU/RAM measurement, model changes, or rollback to provider transcription.
---

# OpenClaw Local Voice STT

For the production member `anhlaptrinhthu`, the active path is now the shared host service documented in `/root/.agents/skills/shared-local-stt-service/SKILL.md`. The member-local venv remains installed only as a tested rollback option.

## Project Paths

- Member data: `/root/Apps/member_vps/docker-users/data/anhlaptrinhthu`
- Container: `user-anhlaptrinhthu`
- Venv rollback: `/home/anhlaptrinh/.openclaw/tools/local-stt-venv`
- Workspace script: `/home/anhlaptrinh/.openclaw/workspace/skills/openclaw-local-voice-stt/scripts/transcribe_local.py`
- Metrics: `/home/anhlaptrinh/.openclaw/logs/local-stt-metrics.jsonl`
- Model cache: `/home/anhlaptrinh/.cache/faster-whisper`

## Install

```bash
docker exec user-anhlaptrinhthu bash -lc 'python3 -m venv /home/anhlaptrinh/.openclaw/tools/local-stt-venv && /home/anhlaptrinh/.openclaw/tools/local-stt-venv/bin/pip install --upgrade pip && /home/anhlaptrinh/.openclaw/tools/local-stt-venv/bin/pip install faster-whisper'
```

For a new isolated member, configure `tools.media.audio.models` with a CLI entry calling the venv Python and `{{MediaPath}}`. For production members, prefer the shared service skill. Do not retain a provider entry when the requirement is zero transcription API cost.

## Dry Run

```bash
docker exec user-anhlaptrinhthu bash -lc '/home/anhlaptrinh/.openclaw/tools/local-stt-venv/bin/python /home/anhlaptrinh/.openclaw/workspace/skills/openclaw-local-voice-stt/scripts/transcribe_local.py --help'
```

## Run

```bash
docker exec user-anhlaptrinhthu bash -lc '/home/anhlaptrinh/.openclaw/tools/local-stt-venv/bin/python /home/anhlaptrinh/.openclaw/workspace/skills/openclaw-local-voice-stt/scripts/transcribe_local.py /path/to/audio.ogg'
```

## Input And Output

- Input: local audio path from OpenClaw `{{MediaPath}}`, maximum 20 MB and 10 minutes.
- Output stdout: transcript only, suitable for OpenClaw media understanding.
- Output stderr: short failures and library diagnostics.
- Metrics JSONL records duration, wall time, CPU-time equivalent percentage, peak RSS and transcript length; it never records transcript text.
- The default model is `small`, language `vi`, CPU INT8, four CPU threads and one concurrent transcription.
- Initial VPS benchmark on 2026-07-19: a 3.2-second Vietnamese clip took 8.95 seconds while downloading/loading the model, used 79.1% one-core equivalent and peaked at 770 MB RSS. With the model cached, a 32-second clip completed in 3.01 seconds, used 297.9% process CPU equivalent, sampled at up to 395.55% container CPU (about four of eight VPS CPUs), and used about 1.0 GB container memory.

## Resource Reading

- `cpu_percent_equivalent=100` means roughly one CPU core fully used during that transcription.
- The script can report up to about `400%` because it is capped at four worker threads.
- Relative to this 8-vCPU VPS, `400%` process CPU is about 50% of total host CPU capacity.
- Inspect the latest measurement without exposing transcript content:

```bash
docker exec user-anhlaptrinhthu tail -n 5 /home/anhlaptrinh/.openclaw/logs/local-stt-metrics.jsonl
```

## Rerun And Rollback

- Rerun the same command with the same local audio file; model files remain cached.
- Change model temporarily with `LOCAL_STT_MODEL=base` or `LOCAL_STT_MODEL=medium`.
- Roll back by restoring the backed-up `openclaw.json` and restarting the container.

## Safety

- Backup `openclaw.json` before changing media models.
- Do not log transcript text, Telegram files, tokens, cookies or credentials.
- Keep audio temporary; the script removes normalized WAV files automatically.
- Do not configure automatic paid-provider fallback when zero API cost is required.
