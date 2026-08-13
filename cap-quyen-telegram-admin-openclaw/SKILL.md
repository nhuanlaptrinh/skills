---
name: cap-quyen-telegram-admin-openclaw
description: Grant or verify a Telegram user ID as a full guarded OpenClaw/VPS owner on the existing canonical agent and workspace for that bot, without creating a separate admin agent or DM-only workspace. Use when adding an owner, synchronizing Telegram owner/exec/plugin approval rights, repairing incomplete owner access, or checking that one bot still routes both DMs and groups through one agent/workspace.
---

# Cấp Quyền Telegram Admin OpenClaw

## Nguyên Tắc

- Cấp owner trên agent đang phục vụ toàn bộ Telegram account, thường là `main`.
- Owner là quyền của sender trên `main`, không phải một agent; DM/group của owner vẫn dùng `/root/.openclaw/workspace` như mọi cuộc trò chuyện của bot đó.
- Không tạo `owner-admin`, workspace mới hoặc direct peer binding chỉ để thêm owner.
- Chỉ tạo agent/workspace mới khi thực sự tạo bot/account thứ hai.
- Nếu account đang route tới nhiều agent hoặc có peer-specific binding, dùng `unify-openclaw-bot-workspace` trước.
- Giữ DM allowlist, owner commands, exec approvers, plugin approval targets, elevated allowlist và sender policy đồng bộ.
- Owner exact Telegram ID kế thừa `tools.profile: full`; sender khác bị chặn runtime, filesystem, memory, browser, messaging, automation, nodes, plugins và session/admin tools.
- Exec dùng `host=gateway`, `mode=auto`, `strictInlineEval=true`; host approvals dùng `allowlist/on-miss/deny`.
- Không mở wildcard owner, không in credential và không gửi tin thật khi kiểm thử tự động.
- Không thêm field ngoài schema như `channels.telegram.commands.enforceOwnerForCommands`; dùng `commands.ownerAllowFrom` làm nguồn owner.

## Dry-Run

```bash
python3 /root/.agents/skills/cap-quyen-telegram-admin-openclaw/scripts/grant_telegram_admin.py \
  --telegram-id <TELEGRAM_USER_ID> \
  --openclaw-root <HOST_OPENCLAW_ROOT> \
  --runtime-openclaw-root /root/.openclaw \
  --account-id <TELEGRAM_ACCOUNT_ID> \
  --agent-id main
```

Đọc danh sách thay đổi đã làm sạch. Nếu script báo account route nhiều agent hoặc có peer binding, dừng và gộp bằng skill `unify-openclaw-bot-workspace`.

## Apply

Backup production trước, sau đó chạy:

```bash
python3 /root/.agents/skills/cap-quyen-telegram-admin-openclaw/scripts/grant_telegram_admin.py \
  --telegram-id <TELEGRAM_USER_ID> \
  --openclaw-root <HOST_OPENCLAW_ROOT> \
  --runtime-openclaw-root /root/.openclaw \
  --account-id <TELEGRAM_ACCOUNT_ID> \
  --agent-id main \
  --backup-dir /root/_Backups/openclaw \
  --apply
```

Script backup `openclaw.json` và `exec-approvals.json` khi cần, ghi atomically và giữ socket token không đổi.

## Check

```bash
python3 /root/.agents/skills/cap-quyen-telegram-admin-openclaw/scripts/grant_telegram_admin.py \
  --telegram-id <TELEGRAM_USER_ID> \
  --openclaw-root <HOST_OPENCLAW_ROOT> \
  --runtime-openclaw-root /root/.openclaw \
  --account-id <TELEGRAM_ACCOUNT_ID> \
  --agent-id main \
  --check
```

Tiếp tục chạy `openclaw config validate`, xem binding, restart đúng Gateway process manager, probe channel và kiểm tra effective exec policy. Yêu cầu owner tự thử lệnh chỉ đọc trong DM/group; không tự deliver tin nhắn.

## Thu Hồi

Backup trước rồi xóa ID đồng bộ khỏi channel/account allowlist, `commands.ownerAllowFrom`, exec approvers, plugin targets, elevated allowlist và exact `toolsBySender`. Không xóa agent/workspace vì việc thu hồi một owner không thay đổi bot architecture.

## Tài Liệu

- Đọc `references/security-model.md` trước khi sửa policy.
- Dùng `unify-openclaw-bot-workspace` khi cấu hình legacy đã có agent/workspace admin riêng.
- Chạy `scripts/test_grant_telegram_admin.py` sau khi sửa script.
