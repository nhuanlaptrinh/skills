---
name: shared-local-stt-service
description: Operate, benchmark, repair, extend, or connect member OpenClaw containers to the shared faster-whisper CPU service on the main VPS for Telegram or Zalo voice transcription without paid STT APIs.
---

# Shared Local STT Service

## Paths

- Project: `/root/AI_Runtime/shared_local_stt`
- App: `/root/AI_Runtime/shared_local_stt/app.py`
- Venv: `/root/AI_Runtime/shared_local_stt/venv`
- Model cache: `/root/AI_Runtime/shared_local_stt/model-cache`
- Metrics: `/root/AI_Runtime/shared_local_stt/logs/metrics.jsonl`
- Service: `/etc/systemd/system/shared-local-stt.service`
- Health timer: `shared-local-stt-healthcheck.timer`
- Internal endpoint: `http://172.17.0.1:18080/v1/audio/transcriptions`
- Canonical member client: `<openclaw-home>/workspace/skills/cai-dat-audio-local-openclaw/scripts/transcribe_shared.py`
- Existing deployments may retain the legacy `openclaw-shared-voice-stt/scripts/transcribe_shared.py` path until a separately tested migration.

## Architecture

The host service keeps `faster-whisper small` warm in RAM, runs CPU INT8 with four threads, processes one transcription at a time, and allows at most 20 active/waiting requests. It binds only to Docker gateway `172.17.0.1`, uses a bearer token stored outside documentation, and has no paid-provider fallback. Both Docker members and the main `/root/.openclaw` runtime can use the same service through separate CLI clients.

## Dry Run

```bash
curl -fsS http://172.17.0.1:18080/health
systemctl is-active shared-local-stt.service
systemctl is-active shared-local-stt-healthcheck.timer
```

## Run And Test

```bash
systemctl restart shared-local-stt.service
docker exec user-member python3 /home/member/.openclaw/workspace/skills/cai-dat-audio-local-openclaw/scripts/transcribe_shared.py /path/to/audio.ogg
```

## Input And Output

- Input: authenticated multipart audio from Docker member containers, maximum 20 MB and 10 minutes.
- Output: JSON `text` to the client; the OpenClaw CLI client prints transcript only.
- Metrics contain member ID, durations, CPU, peak RSS, transcript length and error type; they never contain transcript text or audio.
- No Sheet, external API or paid transcription service is used.

## Rerun And Rollback

- Restart the service with `systemctl restart shared-local-stt.service`.
- If the shared credential is exposed, discover every active `shared-local-stt.token`, back up the service env and all client tokens, then rotate them together. The current helper `/root/Automation/openclaw_member_assistant/scripts/rotate_shared_local_stt_token.sh` updates `openclaw-main`, `anhlaptrinhthu`, and `nguyendinhtan`; extend its explicit allowlist before running if another client exists. It restarts only this service and waits for health without printing the new token.
- Inspect recent metrics with `tail -n 10 /root/AI_Runtime/shared_local_stt/logs/metrics.jsonl`.
- Roll a member back by restoring its backed-up `openclaw.json` local CLI entry.
- Keep each member token in its credential folder and the matching service token in `.env`; never print either token.

## Safety

- Backup app, unit, UFW rules and member config before production changes.
- Keep port `18080` restricted to `docker0` and `172.17.0.0/16`; never allow it publicly.
- Do not log transcripts, audio, Telegram/Zalo credentials or bearer tokens.
- Keep `CPUQuota=400%`, `MemoryMax=3G`, one uvicorn worker and one active transcription unless capacity has been re-benchmarked.
- Do not add a paid STT fallback without explicit user approval.
