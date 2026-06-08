---
name: skill_chuan_alt
description: Kiểm tra và chuẩn hóa dự án theo chuẩn ALT (đường dẫn tương đối, cấu hình .env, metadata chuẩn).
---

# Hướng Dẫn Kiểm Tra Dự Án Theo Chuẩn "Anh Lập Trình" (Skill Chuẩn ALT)

Skill này được thiết kế để bạn (AI) sử dụng khi người dùng yêu cầu "kiểm tra skill" hoặc "chuẩn hóa dự án". Mục tiêu là đảm bảo mọi dự án automation (Python) đều tuân thủ các quy tắc nhất quán, giúp mã nguồn linh hoạt, dễ chia sẻ và không yêu cầu người dùng cuối can thiệp vào code.

## 📋 CÁC TIÊU CHÍ BẮT BUỘC (CHECKLIST)

Khi tiến hành kiểm tra một dự án/skill, hãy lần lượt quét qua các tiêu chí sau:

### 0. Chuẩn Website ALT - Mặc Định Dùng Python Django
- Khi người dùng yêu cầu tạo website, tạo domain/subdomain, tạo landing page, brochure, website khóa học hoặc website chương trình đào tạo trong `/root/10Web_BH`, **mặc định phải triển khai bằng Python Django**, không dùng HTML tĩnh/Nginx tĩnh trừ khi người dùng yêu cầu rõ.
- Mẫu kỹ thuật mặc định để tham khảo/copy cấu trúc là `/root/10Web_BH/03_domain_oplw`:
  - Có `manage.py`, `mysite/`, app Django, `templates/`, `static/`, `requirements.txt`, `Dockerfile`, `docker-compose.yml`.
  - `docker-compose.yml` chạy service Django bằng `python manage.py runserver 0.0.0.0:8000`, gắn Traefik `Host(\`PROJECT_DOMAIN\`)`, service/container/router/middleware theo subdomain.
  - `mysite/settings.py` phải có domain mới trong `CSRF_TRUSTED_ORIGINS`, `ALLOWED_HOSTS`, `STATIC_URL`, timezone/language phù hợp.
  - Template chính đặt trong app Django, ví dụ `app/templates/app/index.html`; CSS/JS/ảnh đặt trong `app/static/app/...` và template phải dùng `{% load static %}`.
- Font chữ mặc định cho website tiếng Việt là `Be Vietnam Pro`:
  - Import trong template/base HTML bằng Google Fonts:
    ```html
    <link href="https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:wght@300;400;500;600;700;800;900&family=Inter:wght@400;500;600;700;800&display=swap&subset=vietnamese" rel="stylesheet">
    ```
  - CSS nền tảng:
    ```css
    body {
      font-family: "Be Vietnam Pro", Inter, Arial, sans-serif;
    }
    h1, h2, h3, .page-title, .main-title {
      font-family: "Be Vietnam Pro", Inter, Arial, sans-serif;
    }
    ```
  - Không dùng `Montserrat` làm font mặc định cho website tiếng Việt mới, trừ khi người dùng yêu cầu rõ hoặc dự án cũ đã có nhận diện riêng.
- Mẫu dữ liệu Second Brain mặc định để tham khảo là `/root/Second_Brain/01_chuong_trinh_dao_tao/03_domain_oplw`:
  - Tạo folder cùng mã dự án trong `/root/Second_Brain/01_chuong_trinh_dao_tao/[PROJECT_CODE]`.
  - Ưu tiên cấu trúc có `00_moc_...md`, `00_tong_quan_chuong_trinh/`, `02_lo_trinh_dao_tao/`, `03_q_a_va_xu_ly_phan_doi/`, `05_bai_quang_cao_va_content/`, `06_prompt_va_workflow_mau/`, `07_case_study_va_vi_du/`, `08_tai_lieu_ky_thuat/`, `10_post_trang_ca_nhan_quang_cao/`, `11_doi_tuong_khach_hang_huong_toi/`, `01_du_lieu_website_chatbot_[domain]/`, `99_ghi_chu_tong_hop/`.
  - Folder `01_du_lieu_website_chatbot_[domain]/` phải có tối thiểu dữ liệu chatbot/website tương tự mẫu `03_domain_oplw`.
- Sau khi tạo website Django, bắt buộc kiểm tra:
  - `python manage.py check`
  - `python manage.py test` nếu đã có test hoặc logic mới
  - `docker compose up -d --build`
  - `curl -I http://localhost:[PORT]`
  - `curl -I -H 'Host: PROJECT_DOMAIN' http://127.0.0.1`
  - `curl -k -I https://PROJECT_DOMAIN` khi đã gắn Traefik/SSL.

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

### 4. Khử Token/API/Secret Trước Khi Đưa Lên GitHub - Bắt Buộc
- **Skill chuyên trách**: Nếu skill `khu-token-api-secret` có sẵn, phải dùng skill đó cho toàn bộ bước quét/khử secret khi tạo, cập nhật, chuẩn hóa hoặc chuẩn bị đưa bất kỳ skill/dự án nào lên GitHub.
- **Nguyên tắc**: Trước khi hoàn tất bất kỳ skill/dự án nào, AI phải tự quét và thay toàn bộ thông tin nhạy cảm bằng placeholder, không chờ người dùng nhắc.
- **Placeholder chuẩn**:
  - API key, bot token, auth token, access token, refresh token, secret: `Nhap_API_Cua_Ban`
  - Email cá nhân trong ví dụ/log: `email_cua_ban@example.com`
  - Password/mật khẩu mẫu: `Nhap_Mat_Khau_Cua_Ban`
  - ID/cấu hình riêng tư nếu không cần công khai: `Nhap_Gia_Tri_Cua_Ban`
- **Các giá trị phải thay**:
  - OpenAI/API key dạng `sk-...`, `sk-proj-...`
  - Telegram bot token dạng `123456789:ABC...`
  - Google API key dạng `AIza...`
  - GitHub token dạng `ghp_...`, `github_pat_...`
  - Slack/Discord/Zalo/webhook token, bearer token, cookie/session, client secret
  - Email, số điện thoại, URL quản trị, account đăng nhập xuất hiện trong file mẫu hoặc log
- **Các file/thư mục nhạy cảm phải chặn bằng `.gitignore`**:
  - `.env`, `.env.*` (trừ `.env.example` nếu đã dùng placeholder)
  - `credentials.json`, `client_secret*.json`, service account JSON thật
  - `*token*`, `*secret*`, `*credential*` nếu là dữ liệu thật
  - Chrome/browser profile: `**/zalo-chrome-profile/`, `**/chrome-profile/`, `**/user-data-dir/`
  - Browser data: `Cookies`, `Login Data`, `Local Storage`, `IndexedDB`, `Session Storage`, `Secure Preferences`
  - Log chạy thật: `*.log`, `auto_register_log.txt` nếu chứa email/token/session
  - Cache/build local: `__pycache__/`, `*.pyc`, `venv/`
- **Nếu file nhạy cảm đã bị Git track**: dùng `git rm --cached` để gỡ khỏi Git index nhưng giữ file local. Không xóa file local của người dùng nếu không được yêu cầu.
- **Quét bắt buộc trước khi báo xong**:
  ```powershell
  rg -uuu -n --glob '!**/.git/**' --glob '!**/zalo-chrome-profile/**' "(sk-proj-[A-Za-z0-9_-]+|sk-[A-Za-z0-9_-]{20,}|AIza[0-9A-Za-z_-]{25,}|gh[pousr]_[0-9A-Za-z_]{20,}|github_pat_[A-Za-z0-9_]+|xox[baprs]-[0-9A-Za-z-]{10,}|[0-9]{7,}:[A-Za-z0-9_-]{25,})" .
  git ls-files | rg -i "zalo-chrome-profile|chrome-profile|user-data-dir|cookies|login data|local storage|indexeddb|session storage|secure preferences|__pycache__|\.pyc$|\.env$"
  ```
- **Kiểm tra history nếu chuẩn bị push GitHub**: Nếu repo đã có commit cũ, phải nhắc người dùng rằng secret có thể còn trong lịch sử Git. Khi cần sạch tuyệt đối, tạo repo mới sạch hoặc rewrite history trước khi push.

### 5. Môi Trường Ảo Python (venv) - Không Bắt Buộc.
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
4. **Khử token/API/secret trước khi GitHub**:
   - Quét toàn bộ file text/code/config bằng `rg` để tìm API key, bot token, auth token, secret, bearer token, webhook, email/log thật.
   - Thay giá trị thật bằng placeholder chuẩn: `Nhap_API_Cua_Ban`, `email_cua_ban@example.com`, `Nhap_Mat_Khau_Cua_Ban`.
   - Kiểm tra `.gitignore` và bổ sung các dòng chặn `.env`, log thật, credentials thật, browser profile, cache, `venv/`, `__pycache__/`.
   - Nếu thấy Chrome/browser profile, cookie, `Login Data`, `Local Storage`, `IndexedDB`, `Session Storage` đang được Git track → dùng `git rm --cached` để gỡ khỏi index và giữ file local.
   - Quét lại staged/current tree. Nếu repo đã có commit cũ chứa secret, báo rõ rủi ro history trước khi push GitHub.
5. **Kiểm tra venv**:
   - Thư mục `venv/` có tồn tại ở thư mục gốc dự án không? Nếu chưa → chạy `python -m venv venv` ngay.
   - Lệnh chạy trong `SKILL.md` có dùng `.\venv\Scripts\python.exe` không? Nếu không → cập nhật.
   - File `.gitignore` có dòng `venv/` không? Nếu không → bổ sung.
6. **Báo cáo và Đề xuất**: Liệt kê các lỗi vi phạm và đề xuất cách sửa (hoặc trực tiếp sửa bằng tool code edit nếu người dùng cho phép).

---
*Ghi chú: Chuẩn này được xây dựng dựa trên sự thống nhất cấu trúc của các dự án:*
- `D:\100.Skills\Skills_V00\skill_post_facebook_personal`
- `D:\100.Skills\Skills_V00\skill_post_fanpage`
- `D:\100.Skills\Skills_V00\skill_zalo_mes_personal`
