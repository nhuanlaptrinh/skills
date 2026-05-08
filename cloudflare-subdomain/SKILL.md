# Cloudflare Subdomain Manager

## Description
Skill này giúp Agent tự động hóa việc tạo subdomain (A record) trên Cloudflare bằng các script đã được tích hợp tại `/root/.agents/skills/cloudflare-subdomain`.

## Capabilities
- Tạo subdomain tự động trên Cloudflare với IP mặc định (194.59.165.104).
- Tạo subdomain tự động trên Cloudflare với IP tuỳ chỉnh.
- Quản lý tự động virtual environment, nếu chưa có sẽ tự cài đặt.

## Pre-requisites
- Hệ thống hoạt động dựa trên script và API Key mặc định (JWqJlR2cFxzDt6U0_hhGeEn6kpNepgk6cwVKWHv8) nằm trong dự án gốc.
- Không cần cấu hình thêm, tool wrapper tự lo việc activate venv.

## How to use / Instructions cho AI
Khi user yêu cầu tạo một tên miền con (subdomain), hãy thực thi bash command trỏ trực tiếp đến script `tao_ten_mien` của hệ thống.

### Lệnh chạy với IP mặc định (194.59.165.104)
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

## Useful Information & Paths
- **Thư mục gốc:** `/root/.agents/skills/cloudflare-subdomain`
- **CLI Shell Wrapper:** `/root/.agents/skills/cloudflare-subdomain/tao_ten_mien`
- **Python Script chính:** `/root/.agents/skills/cloudflare-subdomain/cloudflare_dns.py`
- **Web Interface (Streamlit):** Giao diện UI nằm ở `app.py`, chạy ở port `8501` bằng lệnh `streamlit run app.py`

## Troubleshooting
- Nếu báo lỗi "Command not found", hãy kiểm tra quyền thực thi `chmod +x /root/.agents/skills/cloudflare-subdomain/tao_ten_mien`.
- Đảm bảo tên miền (domain) gốc hiện đang được quản lý bởi tài khoản chứa API Key mặc định.
