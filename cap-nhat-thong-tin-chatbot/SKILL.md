---
name: cap-nhat-thong-tin-chatbot
description: Cập nhật thông tin hàng loạt (học phí, tài khoản ngân hàng, thông tin liên hệ, hoặc thay thế văn bản bất kỳ) cho website/chatbot của các chương trình đào tạo của Anh Lập Trình trong Second_Brain.
---

# Skill: Cập Nhật Thông Tin Website & Chatbot Đào Tạo

Skill này giúp tự động hóa việc tìm kiếm và thay thế hoặc cập nhật hàng loạt thông tin của website và chatbot tư vấn (các file CSV, XLSX, MD) cho tất cả các chương trình đào tạo thuộc hệ thống **Anh Lập Trình** trong `/root/Second_Brain/01_chuong_trinh_dao_tao`.

## Các chức năng hỗ trợ:
1.  **Thay thế văn bản tự do:** Thay thế bất kỳ từ hoặc cụm từ cũ nào bằng cụm từ mới trên toàn bộ các file của chatbot.
2.  **Cập nhật học phí theo mẫu:** Tự động định dạng lại câu trả lời học phí của AI/Chatbot theo mẫu kịch bản tư vấn học phí mới.
3.  **Phím tắt cập nhật nhanh:** Các thông tin nhạy cảm thường thay đổi như Số tài khoản ngân hàng, Tên ngân hàng, Chủ tài khoản, Số điện thoại Zalo kích hoạt, Hotline, Email hỗ trợ.

---

## Cách thực thi

Chạy script Python nằm trong folder script của skill này:
```bash
python /root/.agents/skills/cap-nhat-thong-tin-chatbot/scripts/update_chatbot_info.py [các tham số]
```

### Các tham số tùy chọn (Arguments):
*   `--domain <ma_domain>`: Chỉ áp dụng cho một domain cụ thể (ví dụ: `--domain 03_domain_oplw`). Nếu bỏ qua, sẽ áp dụng cho tất cả các domain đang hoạt động.
*   `--summary <duong_dan_file>`: Thay đổi đường dẫn file summary chứa thông tin các khóa học (mặc định là `/root/Second_Brain/01_chuong_trinh_dao_tao/00_bang_tong_hop_thong_tin_cac_chuong_trinh.md`).

#### 1. Các tham số cho Thay thế văn bản tự do:
*   `--search "<van_ban_cu>"`: Văn bản cần tìm kiếm.
*   `--replace "<van_ban_moi>"`: Văn bản mới thay thế vào.

#### 2. Các tham số cho Cập nhật học phí:
*   `--tuition`: Bật chế độ cập nhật học phí (đồng bộ hóa kịch bản trả lời của chatbot và cập nhật các dòng hiển thị).
*   `--price-override <gia_K>`: Ghi đè giá thủ công (ví dụ: `1.460K`), nếu không truyền sẽ tự động lấy từ summary.
*   `--template-override "<kich_ban_mau>"`: Đổi cấu trúc câu trả lời của AI. Dùng `{price_K}` để tự động chèn giá của từng khóa học.

#### 3. Các phím tắt cập nhật nhanh thông tin chung (Hệ thống sẽ tự động tìm kiếm các giá trị cũ mặc định và thay bằng giá trị mới):
*   `--bank-acc <so_tk_moi>`: Cập nhật Số tài khoản (thay cho tài khoản mặc định cũ `19034464432011`).
*   `--bank-name <ten_nh_moi>`: Cập nhật Tên ngân hàng (thay cho `Techcombank`).
*   `--bank-owner "<ten_chu_tk_moi>"`: Cập nhật Tên chủ tài khoản (thay cho `Lê Thị Thu Nhi`).
*   `--zalo <so_zalo_moi>`: Cập nhật Số Zalo hỗ trợ/kích hoạt (thay cho `0854838394`).
*   `--hotline <hotline_moi>`: Cập nhật Hotline hỗ trợ (thay cho `0914972102`).
*   `--email <email_moi>`: Cập nhật Email hỗ trợ (thay cho `contact@anhlaptrinh.com`).

---

## Ví dụ sử dụng thực tế

### 1. Thay thế một từ hoặc link bất kỳ trên tất cả các file
Thay thế link website cũ bằng link mới:
```bash
python /root/.agents/skills/cap-nhat-thong-tin-chatbot/scripts/update_chatbot_info.py --search "http://old-link.com" --replace "https://new-link.com"
```

### 2. Cập nhật số tài khoản ngân hàng mới
Hệ thống sẽ tự tìm kiếm số TK cũ `19034464432011` trong các file CSV, XLSX, MD của tất cả khóa học và đổi thành số TK mới:
```bash
python /root/.agents/skills/cap-nhat-thong-tin-chatbot/scripts/update_chatbot_info.py --bank-acc "9999999999" --bank-owner "NGUYEN VAN A"
```

### 3. Cập nhật số Zalo hỗ trợ mới cho một khóa học duy nhất (`20_domain_anob`)
```bash
python /root/.agents/skills/cap-nhat-thong-tin-chatbot/scripts/update_chatbot_info.py --domain 20_domain_anob --zalo "0988888888"
```

### 4. Đồng bộ kịch bản trả lời học phí của chatbot cho tất cả khóa học
```bash
python /root/.agents/skills/cap-nhat-thong-tin-chatbot/scripts/update_chatbot_info.py --tuition
```
