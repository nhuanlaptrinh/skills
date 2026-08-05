---
skill_name: auto-register-web
description: Tự động đăng ký tài khoản trên website (Voomly và các nền tảng tương tự) sử dụng Selenium WebDriver với Python.
version: "2.0"
author: AI Assistant
tags: [automation, registration, selenium, web, python]
---

# 🌐 Skill: Auto Register Web Account

## Mô tả

Skill này tự động hóa quy trình đăng ký tài khoản trên các website (mặc định là Voomly) bằng **Selenium WebDriver** + **Python**. AI sẽ cập nhật trực tiếp file `scripts/auto_register.py` với thông tin người dùng, chạy luôn từ đó, ghi log và báo cáo kết quả — **không tạo file tạm, không dọn dẹp**.

---

## Khi nào kích hoạt (Triggers)

Kích hoạt skill khi người dùng yêu cầu bất kỳ điều gì sau đây:

| Trigger | Ví dụ |
|---------|-------|
| Đăng ký tài khoản web | *"Đăng ký tài khoản Voomly cho tôi"* |
| Đăng ký với mã coupon | *"Đăng ký với coupon DAMUATL"* |
| Tạo tài khoản tự động | *"Tự động tạo tài khoản trên tl1.anhlaptrinh.vn"* |
| Automation đăng ký | *"Chạy script đăng ký web"* |

---

## Thông tin bắt buộc từ người dùng

Trước khi thực thi, **phải thu thập đủ 4 thông tin** sau. Nếu thiếu, hỏi lại người dùng:

| Tham số | Mô tả | Ví dụ |
|---------|--------|-------|
| `URL` | Link trang đăng ký | `https://tl1.anhlaptrinh.vn/` |
| `COUPON` | Mã coupon giảm giá | `DAMUATL` |
| `FULL_NAME` | Họ tên đầy đủ | `Nguyễn Văn Nhuần` |
| `EMAIL` | Địa chỉ email | `email_cua_ban@example.com` |

---

## Quy trình thực thi (Step-by-step)

### Bước 1 — Cập nhật thông tin vào script

Dùng tool `multi_replace_file_content` để chỉnh sửa **đúng 4 dòng** biến cấu hình trong file `scripts/auto_register.py`:

```
.agents/skills/auto-register-web/scripts/auto_register.py
```

Thay thế 4 dòng sau (giữ nguyên phần còn lại của file):

```python
# TRƯỚC (placeholder)
URL       = "{{URL}}"
COUPON    = "{{COUPON}}"
FULL_NAME = "{{FULL_NAME}}"
EMAIL     = "{{EMAIL}}"

# SAU (thông tin thực)
URL       = "https://tdhcvp1.anhlaptrinh.vn/"
COUPON    = "DAMUANC"
FULL_NAME = "Nguyễn Văn Nhuần"
EMAIL     = "email_cua_ban@example.com"
```

> ⚠️ **Lưu ý:** Chỉ thay 4 dòng biến cấu hình, KHÔNG sửa bất kỳ phần nào khác của script.

### Bước 2 — Chạy script trực tiếp

Chạy lệnh sau từ thư mục gốc của dự án:

```powershell
python .agents/skills/auto-register-web/scripts/auto_register.py
```

Hoặc dùng đường dẫn tuyệt đối nếu cần. Script sẽ mở Chrome, tự động điền form và hoàn tất đăng ký.

> 💡 Dùng flag `-u` để output không bị buffer: `python -u .agents/...`

### Bước 3 — Đọc kết quả & báo cáo

Kiểm tra output terminal **và** file `scripts/auto_register_log.txt` để xác định trạng thái:

- ✅ **Thành công:** Nếu log chứa `HOÀN TẤT ĐĂNG KÝ THÀNH CÔNG!`
- ❌ **Thất bại:** Nếu log chứa `LỖI:` — đọc traceback và báo cáo nguyên nhân

**Báo cáo cho người dùng** theo format:

```
📋 KẾT QUẢ ĐĂNG KÝ
━━━━━━━━━━━━━━━━━━
• Trạng thái: ✅ Thành công / ❌ Thất bại
• Website: [URL]
• Tên: [FULL_NAME]
• Email: [EMAIL]
• Coupon: [COUPON]
• URL sau đăng ký: [URL cuối từ log]
```

### Bước 4 — Reset placeholder (tuỳ chọn)

Sau khi hoàn tất, có thể reset 4 dòng biến về placeholder để script luôn sạch:

```python
URL       = "{{URL}}"
COUPON    = "{{COUPON}}"
FULL_NAME = "{{FULL_NAME}}"
EMAIL     = "{{EMAIL}}"
```

> Bước này **không bắt buộc** — chỉ thực hiện nếu người dùng yêu cầu.

---

## Yêu cầu môi trường

| Phần mềm | Yêu cầu |
|-----------|----------|
| Python | >= 3.8 |
| Chrome Browser | Đã cài đặt |
| ChromeDriver | Tương thích phiên bản Chrome |
| Selenium | `pip install selenium` |

> 💡 Nếu thiếu `selenium`, tự động cài trước khi chạy: `pip install selenium`

---

## Xử lý lỗi thường gặp

| Lỗi | Nguyên nhân | Cách xử lý |
|-----|-------------|------------|
| `WebDriverException` | ChromeDriver không tương thích | Cập nhật ChromeDriver |
| `TimeoutException` | Phần tử không xuất hiện | Kiểm tra URL, tăng timeout |
| `ElementNotInteractableException` | Form bị overlay | Thêm scroll hoặc wait |
| Coupon không áp dụng được | Coupon hết hạn/sai | Kiểm tra lại mã coupon |
| Chrome không mở | Chrome chưa cài | Cài đặt Google Chrome |
| `UnicodeEncodeError` | Terminal Windows không hỗ trợ UTF-8 | Script đã xử lý tự động bằng `io.TextIOWrapper` |

---

## Cấu trúc thư mục Skill

```
.agents/skills/auto-register-web/
├── SKILL.md                          # File hướng dẫn chính (file này)
├── scripts/
│   ├── auto_register.py              # ⭐ Script chính — Agent cập nhật & chạy trực tiếp
│   └── auto_register_log.txt         # Log tự động ghi sau mỗi lần chạy
├── examples/
│   └── example_usage.md              # Ví dụ sử dụng thực tế
└── resources/
    └── sample_log.txt                # Mẫu log đăng ký thành công
```

---

## Ghi chú

- Script sử dụng Chrome ở chế độ **có giao diện** (không headless) để người dùng có thể quan sát quá trình.
- Thời gian chờ mặc định cho mỗi phần tử là **20 giây**, riêng coupon là **50 giây**.
- Log được ghi vào `scripts/auto_register_log.txt` — mỗi lần chạy sẽ ghi đè log cũ.
- Script có thể mở rộng cho các website khác bằng cách điều chỉnh CSS selector bên trong `auto_register.py`.
- **Không cần tạo/xóa file tạm** — flow v2.0 hoạt động trực tiếp trên file cố định.
