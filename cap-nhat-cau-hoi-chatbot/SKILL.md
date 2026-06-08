---
name: cap-nhat-cau-hoi-chatbot
description: Cập nhật nội dung câu hỏi và câu trả lời đồng bộ vào cả 4 file dữ liệu (CSV, XLSX, Chatbot MD, Website MD) của một chương trình đào tạo tùy chọn.
---

# Skill: Cập Nhật Câu Hỏi & Câu Trả Lời Chatbot & Website

Skill này giúp tự động hóa việc tìm kiếm và cập nhật đồng bộ câu trả lời cho một câu hỏi cụ thể trong toàn bộ dữ liệu của một chương trình đào tạo thuộc hệ thống **Anh Lập Trình** trong thư mục `/root/Second_Brain/01_chuong_trinh_dao_tao`.

Khi chạy, skill sẽ tự động quét và sửa đổi cả 4 file sau:
1. `*_nap_ai_fanpage.csv` (Dữ liệu nạp chatbot)
2. `*_nap_ai_fanpage.xlsx` (Dữ liệu Excel nạp chatbot)
3. `*_chatbot_tu_van.md` (Cơ sở dữ liệu kịch bản chatbot)
4. `*_lam_website.md` (Dữ liệu câu hỏi FAQ hiển thị trên website)

---

## Cách thực thi

Chạy script Python nằm trong folder script của skill này:
```bash
python /root/.agents/skills/cap-nhat-cau-hoi-chatbot/scripts/update_qa.py --domain <ký_hiệu_domain> --key "<từ_khóa_câu_hỏi>" --answer "<nội_dung_câu_trả_lời_mới>"
```

### Các tham số bắt buộc (Arguments):
*   `--domain <ký_hiệu_domain>`: Ký hiệu của khóa học/domain muốn cập nhật (ví dụ: `ancl`, `alt`, `oplw`, `vibepython`, `opcl`). Hệ thống sẽ tự động tìm thư mục phù hợp.
*   `--key "<từ_khóa_câu_hỏi>"`: Từ khóa hoặc một cụm từ độc nhất trong câu hỏi để tìm kiếm và khớp (ví dụ: `"tài khoản AI trả phí"` hoặc `"tốn nhiều tiền"`).
*   `--answer "<nội_dung_câu_trả_lời_mới>"`: Nội dung câu trả lời mới muốn thay thế hoàn toàn cho câu cũ.

---

## Ví dụ sử dụng thực tế

### 1. Cập nhật câu hỏi về chi phí token/API cho khóa ANCL
```bash
python /root/.agents/skills/cap-nhat-cau-hoi-chatbot/scripts/update_qa.py \
  --domain ancl \
  --key "tốn nhiều tiền" \
  --answer "Dạ anh yên tâm, việc này hoàn toàn không tốn nhiều token đâu anh nhé. Mới đầu học bên em khuyên khích anh em dùng miễn phí trước..."
```

### 2. Cập nhật câu hỏi về mua tài khoản trả phí cho khóa ALT
```bash
python /root/.agents/skills/cap-nhat-cau-hoi-chatbot/scripts/update_qa.py \
  --domain alt \
  --key "tài khoản AI trả phí" \
  --answer "Dạ không cần bắt đầu bằng tư duy phải mua tài khoản đắt đỏ đâu anh nhé. Mới đầu học mình cứ dùng các gói miễn phí..."
```
