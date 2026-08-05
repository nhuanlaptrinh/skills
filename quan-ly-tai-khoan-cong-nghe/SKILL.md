---
name: quan-ly-tai-khoan-cong-nghe
description: Quản lý kho tài khoản công nghệ cá nhân trên VPS bằng CSV plaintext tại /root/Data/private_accounts. Use khi người dùng muốn thêm, tìm, liệt kê, hoặc lấy email/mật khẩu/SĐT tài khoản ChatGPT, Gemini, Claude, hosting, domain, VPS, API, phần mềm.
---

# Quản Lý Tài Khoản Công Nghệ

## Khi nào dùng

Dùng skill này khi người dùng yêu cầu:
- Thêm tài khoản công nghệ mới.
- Tìm tài khoản ChatGPT/Gemini/Claude/email/hosting/domain/VPS/API.
- Lấy email, username, mật khẩu, SĐT, email khôi phục, ghi chú đăng nhập.
- Liệt kê các tài khoản theo nhóm hoặc dịch vụ.

## Đường dẫn

- Folder chính: `/root/Data/private_accounts`
- File CSV chính: `/root/Data/private_accounts/accounts.csv`
- Script CLI: `/root/Data/private_accounts/scripts/accounts_cli.py`
- Backup thủ công: `/root/Data/private_accounts/backups`

## Cấu trúc CSV

```csv
id,nhom,dich_vu,link_dang_nhap,email,username,mat_khau,so_dien_thoai,email_khoi_phuc,ghi_chu,cap_nhat_lan_cuoi
```

## Lệnh đọc/tìm

Liệt kê ngắn gọn:

```bash
/root/Data/private_accounts/scripts/accounts_cli.py list
```

Tìm không hiện mật khẩu:

```bash
/root/Data/private_accounts/scripts/accounts_cli.py find ChatGPT
```

Tìm và hiện mật khẩu khi người dùng yêu cầu rõ:

```bash
/root/Data/private_accounts/scripts/accounts_cli.py find ChatGPT --show-password
```

## Lệnh thêm tài khoản

```bash
/root/Data/private_accounts/scripts/accounts_cli.py add \
  --nhom AI \
  --dich-vu ChatGPT \
  --link-dang-nhap https://chatgpt.com \
  --email email_cua_ban@example.com \
  --username username_neu_co \
  --mat-khau 'Nhap_Mat_Khau_Cua_Ban' \
  --so-dien-thoai '+84...' \
  --email-khoi-phuc email_khoi_phuc@example.com \
  --ghi-chu 'Ghi chú'
```

## Quy tắc an toàn

- `accounts.csv` là file plaintext có thể chứa mật khẩu thật; không copy nội dung thật vào skill, README công khai, GitHub, hoặc câu trả lời nếu người dùng không yêu cầu rõ.
- Khi người dùng yêu cầu rõ mật khẩu, có thể dùng `--show-password` và trả đúng thông tin cần thiết.
- Không in toàn bộ file CSV nếu người dùng chỉ hỏi một tài khoản.
- Trước khi sửa nhiều dòng, backup CSV vào `/root/Data/private_accounts/backups`.
- Không sửa `.env`, credential hệ thống, Chrome/Selenium profile khi làm việc với kho này.

## Output mong muốn

Khi trả thông tin cho người dùng, ưu tiên format ngắn:

```text
Dịch vụ: ChatGPT
Email: ...
Username: ...
Mật khẩu: ...
SĐT: ...
Link: ...
Ghi chú: ...
```
