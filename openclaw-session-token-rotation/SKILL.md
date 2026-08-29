---
name: openclaw-session-token-rotation
description: Tự động kiểm tra và xoay session OpenClaw theo ngưỡng token an toàn, dùng Gateway RPC chính thức, giữ transcript reset archive và tránh reset session đang hoạt động. Dùng để ngăn session Telegram dài bị phình context.
---

# OpenClaw Session Token Rotation

## Khi dùng

Dùng khi một bot OpenClaw có session Telegram dài, nhiều toolResult hoặc compaction chậm, và cần xoay session trước khi chạm giới hạn context. Skill này chỉ áp dụng trên VPS chính nếu người vận hành yêu cầu; không tự động đụng member VPS.

## Project và script

- Project: `/root/Automation/openclaw/session_maintenance`
- Script: `/root/Automation/openclaw/session_maintenance/rotate_sessions_by_tokens.py`
- Wrapper có `flock`: `/root/Automation/openclaw/session_maintenance/run_rotate_sessions.sh`
- Log cron: `/root/Automation/openclaw/session_maintenance/logs/rotate_sessions.log`
- Config OpenClaw: `/root/.openclaw/openclaw.json`
- Session store của bot tài chính: `/root/.openclaw/agents/quanlychitieugd/sessions`

## Dry-run

```bash
/root/Automation/openclaw/session_maintenance/run_rotate_sessions.sh --dry-run
```

Kiểm tra bot khác hoặc prefix khác:

```bash
/root/Automation/openclaw/session_maintenance/run_rotate_sessions.sh \
  --agent <agent-id> \
  --key-prefix 'agent:<agent-id>:telegram:' \
  --threshold 50000 \
  --dry-run
```

## Chạy thật

```bash
/root/Automation/openclaw/session_maintenance/run_rotate_sessions.sh
```

Mặc định script kiểm tra mọi session Telegram của `quanlychitieugd` và xoay ở `50.000` token. Session được cập nhật trong `3` phút gần nhất được bỏ qua để tránh can thiệp lượt đang chạy.

Reset dùng Gateway RPC `sessions.reset` không kèm reason tùy biến để tương thích schema Gateway hiện hành, không gửi tin Telegram. OpenClaw giữ transcript cũ dưới dạng `*.jsonl.reset.<timestamp>` theo cơ chế archive của runtime.

## Lịch

Cron production chạy mỗi 5 phút:

```cron
*/5 * * * * /root/Automation/openclaw/session_maintenance/run_rotate_sessions.sh --threshold 50000 >> /root/Automation/openclaw/session_maintenance/logs/rotate_sessions.log 2>&1
```

## Input và output

- Input: session metadata do `openclaw sessions --agent ... --json` trả về.
- Điều kiện: key khớp prefix Telegram của agent, `totalTokens` đạt ngưỡng và session không nằm trong cửa sổ hoạt động.
- Output: log tổng số session, số candidate, số reset hoặc skip; không ghi nội dung hội thoại.
- Transcript archive: do OpenClaw tự giữ trong session directory.

## Kiểm tra và rerun

```bash
openclaw config validate
/root/Automation/openclaw/session_maintenance/run_rotate_sessions.sh --dry-run
openclaw sessions --agent quanlychitieugd --json --limit all
```

Rerun an toàn vì session vừa reset sẽ có token thấp và không đạt ngưỡng. Nếu reset lỗi, kiểm tra `openclaw-gateway.service` và chạy lại dry-run trước khi chạy thật.

## Quy tắc an toàn

- Không in, sao chép hoặc ghi bot token, API key, cookie, mật khẩu, private key hay nội dung `.env`.
- Không reset session đang hoạt động trong cửa sổ bảo vệ.
- Không ghép session theo chat ID nếu thiếu agent/account; dùng full agent/channel session-key prefix.
- Backup `openclaw.json`, session store và crontab trước khi bật lịch production.
- Không gửi tin Telegram thử thật trong quá trình kiểm tra.
