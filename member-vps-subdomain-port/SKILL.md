---
name: member-vps-subdomain-port
description: Vận hành, kiểm thử, quản lý và bảo trì hệ thống AI Agent Tự Động Cấp Port (3001-3999), Nginx Proxy Routing và Cloudflare Wildcard Tunnel cho VPS Thành Viên tại /root/Apps/member_vps_subdomain_port. Dùng khi người dùng hoặc AI Agent cần tạo website mới, kiểm tra port, chạy bộ test T01-T10, hoặc bảo trì hệ thống subdomain member VPS.
---

# Skill: Member VPS Auto-Subdomain & Port Allocation Engine

## 🎯 Mục đích & Phạm vi
Skill này hướng dẫn quy trình vận hành, khởi tạo website tự động, chạy bộ kiểm thử nghiệm thu 10/10 test cases và bảo trì hệ thống tự động cấp Port (3001-3999) + Nginx Routing + Cloudflare Wildcard Tunnel tại `/root/Apps/member_vps_subdomain_port`.

---

## 🛠️ Cấu trúc hệ thống (`/root/Apps/member_vps_subdomain_port`)

| File / Folder | Chức năng chính |
| :--- | :--- |
| `config.py` | Cấu hình dải Port (3001-3999), Blacklist port cấm, Tenant ID, Base domain |
| `models.py` | Quản lý bảng SQLite `member_websites` với đầy đủ indexes (`idx_tenant`, `idx_port`, `idx_full_domain`) |
| `port_manager.py` | Quét socket OS, DB registry, Blacklist & SQLite Transaction Lock (`BEGIN EXCLUSIVE`) |
| `nginx_manager.py` | Sinh cấu hình Nginx proxy_pass trỏ `subdomain` ➔ `http://127.0.0.1:<port>`, test `nginx -t` & reload an toàn |
| `app_launcher.py` | Khởi chạy Backend Application trên port được cấp và thực hiện Healthcheck nội bộ |
| `cloudflare_manager.py` | Tự động quản lý Cloudflare Wildcard Tunnel config (`.cloudflared/config.yml`) & kiểm tra HTTPS External |
| `ai_agent_tools.py` | Đóng gói Tool `create_website` 10 bước chuẩn hóa cho AI Agent kèm `list_websites` và `check_website` |
| `test_suite.py` | Script kiểm thử tự động 10/10 kịch bản kỹ thuật nghiệm thu (T01 - T10) |
| `.cloudflared/` | Chứa file cấu hình Cloudflare Tunnel (`config.yml`) và `tunnel-token` mode `600` |

---

## 🚀 Các lệnh vận hành chuẩn

### 1. Chạy bộ kiểm thử tự động (T01 - T10)
```bash
python3 /root/Apps/member_vps_subdomain_port/test_suite.py
```

### 2. Gọi Tool tạo Website mới qua Python
```bash
python3 -c "from ai_agent_tools import create_website; res = create_website('noithat'); print(res['report'])"
```

### 3. Liệt kê danh sách Website hiện có
```bash
python3 -c "from ai_agent_tools import list_websites; print(list_websites())"
```

### 4. Kiểm tra sức khỏe 1 website cụ thể
```bash
python3 -c "from ai_agent_tools import check_website; print(check_website('noithat'))"
```

### 5. Kiểm tra trạng thái Cloudflare Tunnel Service (systemd)
```bash
systemctl status cloudflared
```

---

## 🔒 Quy tắc an toàn & Cách ly

1. **Cam kết "3 Không":**
   - AI Agent trong VPS thành viên không giữ SSH key VPS chính.
   - Không mount Docker socket (`/var/run/docker.sock`) của VPS chính.
   - Không can thiệp, không đọc/ghi và không restart bất kỳ dịch vụ nào ở VPS chính.
2. **Quy tắc bảo mật Token:**
   - Không in Tunnel Token ra màn hình log, chat hay tài liệu công khai. Tệp token phải được phân quyền `chmod 600`.
3. **Rollback Engine:**
   - Nếu khởi chạy backend thất bại hoặc cú pháp Nginx lỗi (`nginx -t` fail), hệ thống bắt buộc tự động Rollback giải phóng Port và xóa bản ghi DB dở dang để bảo vệ các website khác 100% online.
