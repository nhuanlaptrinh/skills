---
name: cloudflare-subdomain
description: Tạo Cloudflare DNS A record cho domain hoặc subdomain bằng CLI local, dùng IP mặc định legacy hoặc IPv4 được chỉ định. Use khi người dùng yêu cầu tạo tên miền con, thêm A record Cloudflare, trỏ subdomain về VPS, hoặc khi skill triển khai website cần tạo DNS trước SSL.
---

# Cloudflare Subdomain Manager

## Description
Skill này giúp Agent tự động hóa việc tạo subdomain (A record) trên Cloudflare bằng các script đã được tích hợp tại `/root/.agents/skills/cloudflare-subdomain`.

## Capabilities
- Hỗ trợ IP mặc định legacy (`187.127.177.163`), nhưng workflow mới phải truyền IPv4 đã xác nhận rõ ràng.
- Tạo subdomain tự động trên Cloudflare với IP tuỳ chỉnh.
- Quản lý tự động virtual environment, nếu chưa có sẽ tự cài đặt.

## Pre-requisites
- API token ưu tiên đọc từ file `/root/.cloudflare_subdomain_token` có quyền `600`; biến `CLOUDFLARE_API_TOKEN` chỉ dùng làm fallback.
- Không ghi token thật vào skill, source code, log hoặc câu trả lời.
- Tool wrapper tự kích hoạt môi trường Python.

## How to use / Instructions cho AI
Khi user yêu cầu tạo một tên miền con (subdomain), hãy thực thi bash command trỏ trực tiếp đến script `tao_ten_mien` của hệ thống.

### Lệnh legacy với IP mặc định (`187.127.177.163`)
```bash
/root/.agents/skills/cloudflare-subdomain/tao_ten_mien <tên_subdomain>
```
*Ví dụ:*
```bash
/root/.agents/skills/cloudflare-subdomain/tao_ten_mien auth.anhlaptrinh.vn
```

### Lệnh chạy với IP tuỳ chỉnh
```bash
/root/.agents/skills/cloudflare-subdomain/tao_ten_mien <tên_subdomain> <địa_chỉ_ip>
```
*Ví dụ:*
```bash
/root/.agents/skills/cloudflare-subdomain/tao_ten_mien api.anhlaptrinh.vn 192.168.1.100
```

Ưu tiên lệnh có IP tuỳ chỉnh sau khi xác nhận public IPv4 của VPS. Không suy luận IP từ tài liệu cũ.

## Useful Information & Paths
- **Thư mục gốc:** `/root/.agents/skills/cloudflare-subdomain`
- **CLI Shell Wrapper:** `/root/.agents/skills/cloudflare-subdomain/tao_ten_mien`
- **Python Script chính:** `/root/.agents/skills/cloudflare-subdomain/cloudflare_dns.py`
- **Web Interface (Streamlit):** Giao diện UI nằm ở `app.py`, chạy ở port `8501` bằng lệnh `streamlit run app.py`
- **Credential:** `/root/.cloudflare_subdomain_token`, mode `600`

## Troubleshooting
- Nếu báo lỗi "Command not found", hãy kiểm tra quyền thực thi `chmod +x /root/.agents/skills/cloudflare-subdomain/tao_ten_mien`.
- Đảm bảo tên miền (domain) gốc hiện đang được quản lý bởi tài khoản chứa API Key mặc định.
