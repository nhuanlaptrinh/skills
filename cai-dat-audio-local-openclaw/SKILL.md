---
name: cai-dat-audio-local-openclaw
description: "Cài đặt bổ sung khả năng đọc voice Telegram/Zalo cho OpenClaw bằng faster-whisper local, không dùng API transcription trả phí. Use cho member VPS Docker gọi Shared Local STT trên VPS chính hoặc VPS riêng cài model local độc lập; bao gồm backup, dry-run, apply, test, đo CPU/RAM và rollback."
---

# Cài Audio Local OpenClaw

Skill này bổ sung speech-to-text tiếng Việt cho OpenClaw bằng `faster-whisper small`, CPU INT8. Khi cần bot trả thêm voice, kết hợp với `/root/.agents/skills/cai-dat-tra-loi-audio-openclaw/SKILL.md`.

## Hai Trường Hợp Triển Khai

1. **VPS thành viên Docker:** ưu tiên gọi Shared Local STT trên VPS chính. Với outbound TTS, config có thể nằm trên bind mount hoặc nằm legacy trong container; dùng installer tương ứng của skill `cai-dat-tra-loi-audio-openclaw`.
2. **VPS riêng hoặc OpenClaw VPS chính:** dùng Shared Local STT nếu service đã có trên cùng VPS, hoặc cài standalone local nếu máy độc lập. Outbound TTS patch trực tiếp `openclaw.json` trên host.

Ba lệnh bên dưới là các biến thể kỹ thuật thuộc hai trường hợp triển khai này, không phải ba loại VPS khác nhau.

## Chọn Chế Độ

- **Member VPS Docker:** dùng `member-shared`. Container chỉ cài client nhỏ và gọi Shared Local STT tại VPS chính. Đây là chế độ ưu tiên khi VPS chính đã có `/root/AI_Runtime/shared_local_stt`.
- **OpenClaw trên VPS chính:** dùng `host-shared`. Runtime `/root/.openclaw` gọi Shared Local STT trên cùng VPS, áp dụng toàn bộ bot dùng chung `tools.media.audio`.
- **VPS riêng:** dùng `standalone-local`. Cài venv, thư viện và model ngay trên VPS đó; không phụ thuộc VPS chính.

Không cấu hình provider `gpt-4o-mini-transcribe` hoặc paid fallback khi yêu cầu là STT không tốn API.

## Điều Kiện Chung

- Linux x86_64, Python 3, `ffmpeg`, `ffprobe`, `jq` và `curl`.
- Khuyến nghị từ 4 vCPU, 4 GB RAM và 2 GB disk trống.
- Lần cài/model đầu cần Internet; sau khi model cache xong có thể phiên âm offline.
- Audio mặc định tối đa 20 MB và 10 phút.
- Backup production trước khi apply; không in `.env`, token, cookie hoặc credential.

## Member VPS Dùng Shared STT

Trước khi chạy installer, xác định config thật. Nếu gateway chạy `HOME=/root` và config chỉ tồn tại tại `/root/.openclaw/openclaw.json` bên trong container, đây là **runtime legacy**: không dùng installer host-bind bên dưới và không `docker restart`. Backup bằng `docker cp`, cài client/config trực tiếp trong container, sau đó chỉ respawn gateway bằng:

```bash
docker exec user-member \
  tmux respawn-pane -k -t openclaw 'HOME=/root openclaw gateway run'
```

Sau respawn, phải kiểm tra startup log và kết nối Telegram. Cấu hình trong filesystem container có thể mất nếu container bị recreate; cần lưu bản backup bên ngoài tại `/root/_Backups`.

Dry-run:

```bash
bash /root/.agents/skills/cai-dat-audio-local-openclaw/scripts/install_member_shared.sh \
  --container user-member \
  --member-root /root/Apps/member_vps/docker-users/data/member \
  --member-id member \
  --container-openclaw-home /home/member/.openclaw \
  --dry-run
```

Apply:

```bash
bash /root/.agents/skills/cai-dat-audio-local-openclaw/scripts/install_member_shared.sh \
  --container user-member \
  --member-root /root/Apps/member_vps/docker-users/data/member \
  --member-id member \
  --container-openclaw-home /home/member/.openclaw \
  --apply
```

Mặc định installer dùng endpoint `http://172.17.0.1:18080`, đọc token từ `/root/AI_Runtime/shared_local_stt/.env`, copy token vào credential member, tạo client workspace, patch `tools.media.audio.models`, test health và restart container. Luôn truyền đúng `--container-openclaw-home`; tên project/member có thể khác username bên trong container.

## VPS Riêng Cài Local

Dry-run:

```bash
bash /root/.agents/skills/cai-dat-audio-local-openclaw/scripts/install_standalone_local.sh \
  --openclaw-home /root/.openclaw \
  --dry-run
```

Apply:

```bash
bash /root/.agents/skills/cai-dat-audio-local-openclaw/scripts/install_standalone_local.sh \
  --openclaw-home /root/.openclaw \
  --apply
```

Installer tạo venv tại `<openclaw-home>/tools/local-stt-venv`, model cache tại `~/.cache/faster-whisper`, copy script vào workspace, cài `faster-whisper`, warm model `small`, rồi patch audio CLI local. Installer không tự đoán/cài lại OpenClaw và không sửa provider/model chat.

## OpenClaw VPS Chính Dùng Shared STT

```bash
bash /root/.agents/skills/cai-dat-audio-local-openclaw/scripts/install_host_shared.sh \
  --openclaw-home /root/.openclaw \
  --member-id openclaw-main \
  --dry-run
```

Đổi thành `--apply` sau khi dry-run đạt. Installer patch một cấu hình `tools.media.audio` toàn cục nên tất cả Telegram/Zalo bot trong runtime đó cùng chuyển sang Shared Local STT.

## Kiểm Tra

Shared member:

```bash
docker exec user-member curl -fsS http://172.17.0.1:18080/health
docker exec user-member python3 /home/member/.openclaw/workspace/skills/openclaw-shared-voice-stt/scripts/transcribe_shared.py /path/to/audio.ogg
```

Standalone:

```bash
/root/.openclaw/tools/local-stt-venv/bin/python \
  /root/.openclaw/workspace/skills/openclaw-local-voice-stt/scripts/transcribe_local.py \
  /path/to/audio.ogg
```

## Input Và Output

- Input: container/member root hoặc OpenClaw home, cùng file audio khi test.
- Output: OpenClaw tự thay voice bằng transcript; script CLI chỉ in transcript trên stdout.
- Metrics local: `<openclaw-home>/logs/local-stt-metrics.jsonl`.
- Metrics shared: `/root/AI_Runtime/shared_local_stt/logs/metrics.jsonl`.
- Không ghi transcript text vào metrics, skill hoặc change log.

## CPU Và RAM

- Mặc định giới hạn bốn CPU threads và một transcription hoạt động.
- `400% CPU` của tiến trình tương đương bốn core; trên VPS 8 vCPU là khoảng 50% tổng CPU trong thời gian phiên âm.
- Model `small` thường giữ khoảng 500–800 MB RSS; cần benchmark lại trên từng VPS.
- Shared service nên giữ `CPUQuota=400%`, `MemoryMax=3G`, queue tối đa 20.

## Rollback

- Installer luôn backup config vào `/root/_Backups` trước khi apply.
- Member shared: phục hồi `openclaw.json` backup, credential backup nếu có, rồi restart container.
- Standalone: phục hồi `openclaw.json` backup; venv/model có thể giữ lại để dùng sau, không cần xóa ngay.
- Không xóa model cache, venv hoặc transcript khi chưa có yêu cầu rõ.

## An Toàn

- Đọc quy trình VPS, project note, AGENTS và production checklist trước khi apply.
- Shared endpoint chỉ bind Docker gateway và chỉ allow subnet Docker bằng firewall.
- Token phải nằm trong `.env`/credential mode `600`, không ghi inline vào JSON hay script.
- Không gửi audio ra Internet, không thêm paid fallback và không log nội dung người nói.
- Sau thay đổi production, cập nhật `/root/_Second_AI_Brain/06_Nhat_Ky_Thay_Doi.md`.

Chi tiết kiến trúc và checklist xem `references/architecture.md`.
