# Ví dụ sử dụng Skill: Auto Register Web

## Ví dụ 1 — Đăng ký tài khoản Voomly cơ bản

**Người dùng nói:**
> Đăng ký tài khoản Voomly cho tôi với thông tin sau:
> - URL: https://tl1.anhlaptrinh.vn/
> - Coupon: DAMUATL
> - Tên: Nguyễn Văn A
> - Email: nguyenvana@gmail.com

**AI thực hiện:**

1. Tạo file `temp_register.py` với nội dung từ template, thay thế:
   - `{{URL}}` → `https://tl1.anhlaptrinh.vn/`
   - `{{COUPON}}` → `DAMUATL`
   - `{{FULL_NAME}}` → `Nguyễn Văn A`
   - `{{EMAIL}}` → `nguyenvana@gmail.com`

2. Chạy: `python temp_register.py`

3. Đọc log và báo cáo:
```
📋 KẾT QUẢ ĐĂNG KÝ
━━━━━━━━━━━━━━━━━━
• Trạng thái: ✅ Thành công
• Website: https://tl1.anhlaptrinh.vn/
• Tên: Nguyễn Văn A
• Email: nguyenvana@gmail.com
• Coupon: DAMUATL
• URL sau đăng ký: https://tl1.anhlaptrinh.vn/thank-you
```

4. Xóa file `temp_register.py`

---

## Ví dụ 2 — Người dùng cung cấp thiếu thông tin

**Người dùng nói:**
> Đăng ký Voomly cho tôi, email là test@gmail.com

**AI phản hồi:**
> Để đăng ký tài khoản, tôi cần thêm các thông tin sau:
> 1. **URL** đăng ký (ví dụ: https://tl1.anhlaptrinh.vn/)
> 2. **Mã coupon** (ví dụ: DAMUATL)
> 3. **Họ tên đầy đủ**
>
> Bạn vui lòng cung cấp thêm nhé!

---

## Ví dụ 3 — Xử lý lỗi

**Khi script gặp lỗi TimeoutException:**

```
📋 KẾT QUẢ ĐĂNG KÝ
━━━━━━━━━━━━━━━━━━
• Trạng thái: ❌ Thất bại
• Lỗi: TimeoutException - Không tìm thấy nút "Đăng Ký Ngay" sau 20 giây
• Nguyên nhân có thể:
  - Website đang bảo trì hoặc thay đổi giao diện
  - Kết nối mạng chậm
• Đề xuất: Thử lại sau hoặc kiểm tra URL có chính xác không
```

---

## Ví dụ 4 — Đăng ký hàng loạt (nâng cao)

**Người dùng nói:**
> Đăng ký 3 tài khoản Voomly cho tôi:
> - URL: https://tl1.anhlaptrinh.vn/
> - Coupon: DAMUATL
> - Tài khoản 1: Nguyễn Văn A / a@gmail.com
> - Tài khoản 2: Trần Văn B / b@gmail.com
> - Tài khoản 3: Lê Thị C / c@gmail.com

**AI thực hiện:** Lặp quy trình 3 lần, mỗi lần thay thông tin tương ứng, báo cáo kết quả tổng hợp sau khi hoàn tất tất cả.
