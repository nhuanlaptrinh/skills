---
name: skill_chuan_alt
description: Kiểm tra và chuẩn hóa dự án theo chuẩn ALT (đường dẫn tương đối, cấu hình .env, metadata chuẩn).
---

# Hướng Dẫn Kiểm Tra Dự Án Theo Chuẩn "Anh Lập Trình" (Skill Chuẩn ALT)

Skill này được thiết kế để bạn (AI) sử dụng khi người dùng yêu cầu "kiểm tra skill" hoặc "chuẩn hóa dự án". Mục tiêu là đảm bảo mọi dự án automation (Python) đều tuân thủ các quy tắc nhất quán, giúp mã nguồn linh hoạt, dễ chia sẻ và không yêu cầu người dùng cuối can thiệp vào code.

## 📋 CÁC TIÊU CHÍ BẮT BUỘC (CHECKLIST)

Khi tiến hành kiểm tra một dự án/skill, hãy lần lượt quét qua các tiêu chí sau:

### 1. Metadata của Skill (File `SKILL.md`)
- **`name`**: Bắt buộc viết liền không dấu, không có khoảng trắng. Nên dùng dấu gạch nối (`-`) hoặc gạch dưới (`_`). VD: `skill_post_fanpage`, `zalo-auto-message`.
- **`description`**: Phải mô tả đầy đủ chức năng và tác dụng của skill, không được ngắn cộc lốc.

### 2. Đường Dẫn Tương Đối (Relative Paths)
- **Quy tắc cốt lõi**: Dự án phải linh hoạt, copy sang máy tính khác (hoặc thư mục khác) vẫn phải chạy được ngay.
- **Tuyệt đối KHÔNG** sử dụng đường dẫn cứng/tuyệt đối trong code (Ví dụ: cấm dùng `D:\100.Skills\...` hay `C:\Users\...`).
- **Cách làm đúng**: Sử dụng `os` hoặc `pathlib` để xác định đường dẫn động.
  ```python
  import os
  # Lấy thư mục chứa script hiện tại
  BASE_DIR = os.path.dirname(os.path.abspath(__file__))
  file_path = os.path.join(BASE_DIR, 'googlesheetcn.json')
  ```

### 3. Tách Biệt Cấu Hình (.env) - Không Can Thiệp Code
- **Nguyên tắc**: Người dùng chỉ cần thiết lập thông số bên ngoài (file cấu hình), tuyệt đối không mở code ra để sửa biến.
- **Quy tắc Google Sheets**:
  - `SPREADSHEET_ID`: Bắt buộc nằm trong file `.env`.
  - `WORKSHEET_NAME` (Tên sheet con): Bắt buộc nằm trong file `.env`.
  - Tên file chứng chỉ (Service Account): Khuyến nghị chuẩn hóa là `googlesheetcn.json` và gọi bằng đường dẫn tương đối.
- Code phải sử dụng `python-dotenv` để load các biến môi trường này:
  ```python
  from dotenv import load_dotenv
  import os
  
  load_dotenv()
  SPREADSHEET_ID = os.getenv('SPREADSHEET_ID')
  WORKSHEET_NAME = os.getenv('WORKSHEET_NAME')
  ```

### 4. Môi Trường Ảo Python (venv) - Bắt Buộc
- **Nguyên tắc**: Mỗi dự án phải có môi trường ảo riêng để tránh xung đột thư viện giữa các project.
- **Tạo venv** (chỉ làm 1 lần trên mỗi máy):
  ```powershell
  python -m venv venv
  ```
  > ⚠️ Dùng `python -m venv` (không dùng `py -m venv`) để đảm bảo tương thích.
- **Cài thư viện** vào đúng venv của dự án:
  ```powershell
  .\venv\Scripts\Activate.ps1
  pip install --upgrade pip
  pip install <các-thư-viện-cần-thiết>
  ```
- **Lệnh chạy script** phải dùng python trong venv (không dùng `python` hệ thống):
  ```powershell
  .\venv\Scripts\python.exe .agent\skills\scripts\<TenScript>.py
  ```
- **Gitignore**: Thư mục `venv/` phải được liệt kê trong `.gitignore`.
- **Kiểm tra vi phạm**: Nếu SKILL.md ghi lệnh chạy là `python script.py` hoặc `py script.py` (không qua venv) → coi là vi phạm chuẩn.

---

## 🛠 QUY TRÌNH THỰC HIỆN CỦA AI

Khi người dùng gọi skill này để kiểm tra một thư mục dự án, bạn hãy:
1. **Kiểm tra `SKILL.md`**: Đọc file này (thường nằm ở root hoặc thư mục `.agents/skills/...`), phân tích phần frontmatter (yaml) xem `name` và `description` đã chuẩn chưa.
2. **Tìm kiếm lỗi Hardcode**: Dùng công cụ (như `grep_search`) quét các file `.py` tìm `C:\`, `D:\`, `SPREADSHEET_ID = "..."` (hardcode string).
3. **Kiểm tra `.env`**: Xác nhận sự tồn tại của file `.env` và các biến môi trường cần thiết có được khai báo ở đó không.
4. **Kiểm tra venv**:
   - Thư mục `venv/` có tồn tại ở thư mục gốc dự án không? Nếu chưa → chạy `python -m venv venv` ngay.
   - Lệnh chạy trong `SKILL.md` có dùng `.\venv\Scripts\python.exe` không? Nếu không → cập nhật.
   - File `.gitignore` có dòng `venv/` không? Nếu không → bổ sung.
5. **Báo cáo và Đề xuất**: Liệt kê các lỗi vi phạm và đề xuất cách sửa (hoặc trực tiếp sửa bằng tool code edit nếu người dùng cho phép).

---
*Ghi chú: Chuẩn này được xây dựng dựa trên sự thống nhất cấu trúc của các dự án:*
- `D:\100.Skills\Skills_V00\skill_post_facebook_personal`
- `D:\100.Skills\Skills_V00\skill_post_fanpage`
- `D:\100.Skills\Skills_V00\skill_zalo_mes_personal`
