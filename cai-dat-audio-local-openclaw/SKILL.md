---
name: cai-dat-audio-local-openclaw
description: "Cai dat, van hanh, kiem tra, sua loi hoac rollback toan bo audio cho OpenClaw tren Telegram va Zalo: nhan mic/voice bang faster-whisper local hoac Shared Local STT, xu ly URL voice Zalo zdn.vn AAC, va tra loi bang text kem voice Microsoft Edge TTS. Use cho VPS chinh, VPS rieng hoac member Docker; bao gom backup, dry-run, gioi han pham vi agent/account, test CPU/RAM va bao ve credential."
---

# Cai Dat Audio OpenClaw

Dung mot skill nay cho toan bo luong audio Telegram/Zalo. Khong can goi rieng cac skill cu `openclaw-local-voice-stt`, `openclaw-shared-voice-stt`, `zalo-voice-transcription` hoac `cai-dat-tra-loi-audio-openclaw`.

## Chon Luong

| Nhu cau | Luong can dung |
|---|---|
| Telegram/Zalo gui file voice vao bot | STT local hoac shared |
| Zalo Personal dua vao URL `zdn.vn/*.aac` | Tai URL an toan, sau do goi shared STT |
| Telegram bot tra text kem voice | Microsoft Edge TTS theo agent |
| Van han dich vu faster-whisper dung chung | Dung them skill `shared-local-stt-service` |

Khong bat TTS khi nguoi dung chi can bot hieu mic. Khong them provider STT tra phi khi yeu cau la local/khong ton API.

## Kiem Tra Truoc Khi Sua

1. Doc quy dinh VPS, project note, `AGENTS.md` gan project va checklist production.
2. Xac dinh config that nam tren host, bind mount hay chi nam trong container.
3. Xac dinh dung agent/account Telegram va cac channel dung chung runtime.
4. Chay dry-run, backup config vao `/root/_Backups`, sau do moi apply.
5. Khong in `.env`, token, cookie, credential hoac noi dung transcript.

## Cai STT Cho Member Docker

Uu tien Shared Local STT tren VPS chinh. Voi member co config persistent theo layout chuan, chay dry-run:

```bash
bash /root/.agents/skills/cai-dat-audio-local-openclaw/scripts/install_member_shared.sh \
  --container user-member \
  --member-root /root/Apps/member_vps/docker-users/data/member \
  --member-id member \
  --container-openclaw-home /home/member/.openclaw \
  --dry-run
```

Doi `--dry-run` thanh `--apply` sau khi endpoint health, config path va owner deu dung. Script validate candidate bang CLI cua chinh container va mac dinh chi restart `openclaw-gateway` qua Supervisor; dung `--restart-mode none` de gom nhieu thay doi truoc mot lan restart, hoac `container` chi khi deployment bat buoc. Installer tao client tai `workspace/skills/cai-dat-audio-local-openclaw/scripts/transcribe_shared.py`.

## Cai STT Cho OpenClaw Host

Neu host goi Shared Local STT:

```bash
bash /root/.agents/skills/cai-dat-audio-local-openclaw/scripts/install_host_shared.sh \
  --openclaw-home /root/.openclaw \
  --member-id openclaw-main \
  --dry-run
```

Neu VPS doc lap va can model local:

```bash
bash /root/.agents/skills/cai-dat-audio-local-openclaw/scripts/install_standalone_local.sh \
  --openclaw-home /root/.openclaw \
  --dry-run
```

Installer standalone tao venv trong `<openclaw-home>/tools/local-stt-venv`, warm model `small`, va cau hinh CLI local. Lan dau can Internet; sau khi model da cache co the phien am offline.

## Xu Ly Voice URL Zalo

Khi plugin `zalouser` dua vao mot URL HTTPS `zdn.vn` ket thuc bang `.aac` thay vi media attachment, chay:

```bash
python3 /root/.openclaw/workspace/skills/cai-dat-audio-local-openclaw/scripts/transcribe_zalo_voice.py '<URL_VOICE_ZALO>'
```

Script chi chap nhan `zdn.vn` va subdomain, gioi han 25 MB, dung thu muc tam, goi client shared cung skill va xoa audio sau khi xong. Dung stdout lam noi dung nguoi dung da noi; khong tra lai URL neu phien am thanh cong.

## Bat Bot Tra Loi Bang Voice

Voi config tren host, giu TTS global `off` va chi bat agent Telegram can dung:

```bash
bash /root/.agents/skills/cai-dat-audio-local-openclaw/scripts/enable_edge_tts_agent.sh \
  --config /root/.openclaw/openclaw.json \
  --agent main \
  --voice vi-VN-NamMinhNeural \
  --auto-mode inbound \
  --dry-run
```

Voi member legacy co config that trong container:

```bash
bash /root/.agents/skills/cai-dat-audio-local-openclaw/scripts/enable_edge_tts_container.sh \
  --container user-member \
  --config-path /home/member/.openclaw/openclaw.json \
  --agent main \
  --auto-mode inbound \
  --dry-run
```

- `inbound`: chi tra voice khi input la voice.
- `always`: ca input chu va voice deu tra text kem voice.
- Giong nam: `vi-VN-NamMinhNeural`.
- Giong nu: `vi-VN-HoaiMyNeural`.
- Neu runtime co nhieu agent/channel, khong bat `always` toan cuc.
- OpenClaw `2026.8.1+` dung `tts` o top-level va `agents.entries.<id>.tts`; khong ghi schema cu `messages.tts` hoac `agents.list`.

Doc `references/telegram-scope.md` truoc khi bat TTS tren runtime dung chung Telegram va Zalo.

## Kiem Tra

Chay cac test phu hop, khong gui tin that neu chua duoc phep:

```bash
curl -fsS http://172.17.0.1:18080/health
python3 /root/.openclaw/workspace/skills/cai-dat-audio-local-openclaw/scripts/transcribe_shared.py /path/to/audio.ogg
/root/.openclaw/tools/local-stt-venv/bin/python \
  /root/.openclaw/workspace/skills/cai-dat-audio-local-openclaw/scripts/transcribe_local.py \
  /path/to/audio.ogg
```

Sau apply:

1. Validate `openclaw.json` bang CLI cua runtime.
2. Respawn/restart dung gateway, khong mac dinh restart ca container legacy.
3. Kiem tra startup log, Telegram/Zalo channel status va Microsoft plugin neu dung TTS.
4. Test bang fixture audio noi bo; chi test mic that khi duoc phep.
5. Xac nhan bot/channel khac khong bi bat TTS ngoai y muon.

## Gioi Han Tai Nguyen

- Audio STT mac dinh toi da 20 MB va 10 phut; Zalo URL toi da 25 MB truoc khi gui STT.
- Local STT dung `faster-whisper small`, CPU INT8, bon CPU threads va mot transcription dong thoi.
- `400% CPU` cua process tuong duong bon core; model thuong can khoang 500-1000 MB RSS tuy may.
- Shared service giu `CPUQuota=400%`, `MemoryMax=3G`, mot worker va queue toi da 20 tru khi da benchmark lai.
- Metrics chi ghi thoi gian, CPU/RAM va do dai transcript; khong ghi noi dung noi.

## Rollback

- Khoi phuc `openclaw.json` va credential tu backup, validate, sau do restart/respawn gateway bang cach dang dung cua runtime.
- Voi TTS, khoi phuc config va xac nhan text reply van hoat dong.
- Co the giu venv/model cache de rollback nhanh; khong xoa audio, transcript, model hoac credential neu chua co yeu cau ro.
- Neu token shared bi lo, dung quy trinh rotate trong skill `shared-local-stt-service`; khong in token ra terminal/log.

Chi tiet kien truc va validation xem `references/architecture.md`.
