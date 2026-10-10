---
name: core-openclaw-telegram
description: Skill chính điều phối quyền, recovery, delivery và audit cho OpenClaw Telegram.
---

Dùng skill chuyên biệt phù hợp:
- Quyền full exec/auto approval: `core-openclaw-telegram-permissions`
- Group recovery/migrate/context: `openclaw-telegram-group-recovery`, `openclaw-telegram-group-migrate`, `openclaw-telegram-context-guard`
- Delivery/task handoff: `openclaw-telegram-task-delivery`
- Latency/slow reply: `openclaw-telegram-latency-audit`, `openclaw-telegram-slow-reply-recovery`
- Cài tool/lệnh gửi QR Zalo cho mọi Telegram owner đã cấu hình: `telegram-zalo-owner-login`; thao tác gửi QR: `openclaw-telegram-zalo-qr-delivery`.
