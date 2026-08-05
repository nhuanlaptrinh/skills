---
name: zalo-silent-group-archive
description: Lưu tin nhắn của một Zalo Personal group vào JSONL theo ngày nhưng không tạo session AI và không gửi phản hồi vào group.
---

# Zalo Silent Group Archive

## Khi nào dùng

- Chủ tài khoản muốn OpenClaw theo dõi/lưu lịch sử một group Zalo nhưng bot phải im lặng tuyệt đối.
- Cần đọc hoặc tổng hợp lại lịch sử group từ Telegram mà không gửi bất kỳ nội dung nào về group Zalo.

## Đường dẫn

- Patch script: `/root/Automation/openclaw_member_assistant/scripts/patch_zalouser_silent_archive.py`
- Member hiện tại: `/root/Apps/member_vps/docker-users/data/anhlaptrinhthu`
- Archive trong container: `/home/anhlaptrinh/.openclaw/workspace/data/zalo_silent_archive/<GROUP_ID>/YYYY-MM-DD.jsonl`
- Archive trên host: `/root/Apps/member_vps/docker-users/data/anhlaptrinhthu/.openclaw/workspace/data/zalo_silent_archive/<GROUP_ID>/YYYY-MM-DD.jsonl`

## Dry-run

```bash
python3 /root/Automation/openclaw_member_assistant/scripts/patch_zalouser_silent_archive.py \
  --member-data-dir /root/Apps/member_vps/docker-users/data/anhlaptrinhthu \
  --group-id 5098372907433048709
```

## Chạy thật

```bash
python3 /root/Automation/openclaw_member_assistant/scripts/patch_zalouser_silent_archive.py \
  --member-data-dir /root/Apps/member_vps/docker-users/data/anhlaptrinhthu \
  --group-id 5098372907433048709 \
  --apply
docker exec user-anhlaptrinhthu bash -lc 'kill -TERM "$(pgrep -f "^openclaw-gateway$" | head -1)"'
```

## Input/Output

- Input: member data directory và numeric Zalo group ID.
- Mỗi tin text được append thành một JSON object gồm timestamp, group ID, sender ID/tên, message ID và content.
- Hook chạy sau delivery/seen acknowledgement nhưng trước group policy, session recording, model dispatch, typing và reply delivery.
- Group vẫn nên giữ `enabled: false` trong `openclaw.json` làm fail-safe: nếu plugin update làm mất patch thì group bị drop, không thể phản hồi ngoài ý muốn.

## Đọc archive

```bash
tail -n 100 /home/anhlaptrinh/.openclaw/workspace/data/zalo_silent_archive/5098372907433048709/$(date -u +%F).jsonl
```

Khi lệnh đọc được yêu cầu từ Telegram, chỉ đọc/tóm tắt archive và trả lời trên Telegram. Tuyệt đối không gọi helper gửi Zalo cho group im lặng.

## Rerun

- Plugin update sẽ tạo generation folder mới và có thể làm mất hook; chạy lại dry-run sau mỗi lần `openclaw plugins update zalouser`.
- Script tự tìm monitor bundle mới nhất, tạo backup cạnh bundle, chèn marker idempotent và chạy `node --check`.
- Nếu dry-run báo `alreadyPatched: true`, không cần apply lại.

## An toàn

- Backup `openclaw.json`, workspace `AGENTS.md` và plugin monitor bundle trước khi áp dụng.
- Không lưu credential, cookie, API key hoặc nội dung file credential vào archive.
- Không gửi tin test thật vào group im lặng.
- Nếu archive ghi lỗi, hook vẫn dừng dispatch để ưu tiên không phản hồi.

