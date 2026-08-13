---
name: ai-website-telegram-manager
description: Quản lý, vận hành, kiểm thử và bảo trì hệ thống AI Tạo & Quản Lý Website qua Telegram (ai_website_telegram) trên VPS Hostinger với Nginx, Traefik, SQLite và Token Codex LLM. Dùng khi người dùng yêu cầu kiểm tra bot, restart bot, dọn dữ liệu test, hoặc kiểm tra router tên miền.
---

# Skill: Quản Lý & Vận Hành Hệ Thống AI Website qua Telegram

## 🎯 Mục đích & Phạm vi
Skill này hướng dẫn quy trình quản lý, khởi động lại, xóa dữ liệu test và kiểm thử hệ thống AI Website Telegram tại `/root/Apps/ai_website_telegram`.

---

## 🛠️ Cấu trúc hệ thống (`/root/Apps/ai_website_telegram`)

| File / Folder | Chức năng chính |
| :--- | :--- |
| `config.py` | Cấu hình DB, Base domain (`devoverflow.xyz`), Token Codex API |
| `models.py` | 6 SQLite ORM models (`Customer`, `TelegramIdentity`, `Package`, `Hosting`, `Website`, `AuditLog`) |
| `policy_engine.py` | Thực thi quy tắc 1 site/1 Telegram, chặn Denylist & tenant isolation |
| `hosting_manager.py` | Quản lý hosting, sinh mã nguồn HTML5/CSS3 qua Token Codex LLM, backup/rollback |
| `ai_agent_tools.py` | 9 Tool APIs chính thức cho AI Agent Engine |
| `bot_handler.py` | Bộ tiếp nhận tin nhắn Telegram, router intent & xác nhận 2 bước |
| `run_bot.py` | Daemon lắng nghe tin nhắn Telegram 24/7 với hiệu ứng Progress Loading % |
| `test_suite.py` | Bộ kiểm thử tự động 10/10 test cases nghiệm thu (T01 - T10) |

---

## 🚀 Các lệnh vận hành chuẩn

### 1. Kiểm tra trạng thái Bot Service (systemd)
```bash
systemctl status ai_website_telegram_bot.service
journalctl -u ai_website_telegram_bot.service -n 20 --no-pager
```

### 2. Khởi động lại Bot Service
```bash
systemctl restart ai_website_telegram_bot.service
```

### 3. Dọn dẹp toàn bộ dữ liệu test cũ & Reset hệ thống sạch 100%
```bash
systemctl stop ai_website_telegram_bot.service
rm -f /root/Apps/ai_website_telegram/ai_website_system.db
rm -rf /root/Apps/ai_website_telegram/hosting_data/sites/* /root/Apps/ai_website_telegram/hosting_data/domains/* /root/Apps/ai_website_telegram/hosting_data/backups/*
python3 -c "from models import init_db; init_db(); print('Clean DB Initialized!')"
systemctl restart ai_website_telegram_bot.service
```

### 4. Chạy bộ kiểm thử tự động (T01 - T10)
```bash
python3 /root/Apps/ai_website_telegram/test_suite.py
```

---

## 🔒 Quy tắc bảo mật
- Không in Token Telegram hoặc Token Codex API Key ra output chat hay tài liệu.
- Lưu credential trong `/root/Apps/ai_website_telegram/.env` với quyền `chmod 600`.
