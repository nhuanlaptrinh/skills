---
name: tao-website-khoa-hoc-alt
description: Tạo website khóa học/chương trình theo chuẩn ALT khi người dùng nói "tạo folder website với tên miền", "tạo website khóa học", "gắn tên miền/subdomain", hoặc đưa một khóa học mới cần dựng giống mẫu OPLW: tạo folder code trong /root/10Web_BH, đặt tên theo subdomain, gắn tên miền nếu có, viết lại nội dung theo giọng Anh Lập Trình từ nguồn tham khảo, tạo dữ liệu cùng tên trong Second Brain, và cập nhật cổng ALT khi phù hợp. Cũng dùng khi cần đặt tên/đổi tên folder chuẩn ALT.
---

# Tạo Website Khóa Học ALT

Skill này được thiết kế để bạn (AI) sử dụng khi người dùng yêu cầu:
- "Dùng skill tao-website-khoa-hoc-alt"
- "Tạo website khóa học ALT"
- "Đặt tên thư mục chuẩn ALT"
- "Đổi tên các folder dự án cho dễ nhớ và chuyên nghiệp"
- "Chuẩn hóa tên folder dựa theo tên miền"
- "Tạo folder website chuẩn Anh Lập Trình/ALT"
- "Tạo folder website với tên miền ..."
- "Tạo một folder trong /root/10Web_BH khóa học ... rồi gắn tên miền ..."
- "Tạo website theo mẫu /root/10Web_BH/03_domain_oplw"
- "Tạo website mới trong `/root/10Web_BH` và gắn domain/subdomain"
- "Tạo chương trình đào tạo/Second Brain cùng tên với website"
- "Đưa chương trình/khóa học vào trang ALT"

Mục tiêu là đảm bảo cấu trúc thư mục của toàn bộ hệ sinh thái dự án (mã nguồn web, backup, ghi chép học tập) đều tuân thủ các quy tắc nhất quán, dễ nhớ và tự động hóa cao.

---

## 📋 TIÊU CHUẨN ĐẶT TÊN FOLDER CHUẨN ALT

Khi tiến hành kiểm tra hoặc đề xuất đặt tên cho thư mục, bạn bắt buộc phải tuân theo 4 quy tắc cốt lõi sau:

### 1. Tiền tố bắt buộc bằng Số thứ tự (2 chữ số)
- Tên thư mục luôn bắt đầu bằng số thứ tự tăng dần có hai chữ số (ví dụ: `01_`, `02_`, `03_`, ..., `23_`, `24_`).
- Số thứ tự giúp sắp xếp các dự án theo mức độ quan trọng hoặc nhóm chức năng để quản lý khoa học.

### 2. Viết thường nối bằng dấu gạch dưới `_`
- Tất cả chữ cái trong tên thư mục đều viết thường.
- Không dùng khoảng trắng hay ký tự đặc biệt khác. Các từ phải được phân cách nhau bằng dấu gạch dưới `_` (snake_case).
- Ví dụ đúng: `02_domain_tlai`, `05_domain_vibepython`.
- Ví dụ sai: `02-domain-tlai`, `02 domain tlai`, `02DomainTlai`.

### 3. Ưu tiên đặt theo Tên miền (Subdomain)
- Nếu thư mục là một dự án chạy website có gắn tên miền (hoặc subdomain), **bắt buộc phải ưu tiên đặt tên folder theo tên miền/subdomain đó** để dễ nhớ.
- Cấu trúc chuẩn: `[Số]_[Loại]_[Subdomain]`
  - Ví dụ: Thư mục dự án của trang `tlai.anhlaptrinh.vn` -> đặt tên là `02_domain_tlai`.
  - Ví dụ: Thư mục dự án của trang `fbs.anhlaptrinh.vn` -> đặt tên là `13_domain_fbs`.
  - Ví dụ: Thư mục tài liệu của trang `anob.anhlaptrinh.vn` -> đặt tên là `20_domain_anob`.

### 4. Đơn giản, ngắn gọn (Dưới 5 từ)
- Tên thư mục phải cực kỳ súc tích, **không được vượt quá 4 từ**.
- Loại bỏ các từ thừa thãi để tập trung vào từ khóa chính của dự án.
- Ví dụ đúng: `12_domain_wast`, `24_backup_oplw`.

---

## QUY TRÌNH TẠO WEBSITE/CHƯƠNG TRÌNH MỚI (BẮT BUỘC KHI USER YÊU CẦU TẠO FOLDER)

Khi người dùng yêu cầu tạo một website/chương trình mới theo chuẩn ALT, luôn làm đủ chuỗi sau trong cùng lượt nếu không bị chặn:

### Nguyên tắc mặc định

- Website mới trong `/root/10Web_BH` **mặc định phải dùng Python Django**, kể cả khi người dùng chỉ đưa HTML/brochure/landing page tĩnh. Chỉ dùng HTML tĩnh hoặc Nginx tĩnh nếu người dùng yêu cầu rõ.
- Mẫu code Django mặc định để tham khảo là `/root/10Web_BH/03_domain_oplw`.
- Mẫu dữ liệu Second Brain mặc định để tham khảo là `/root/Second_Brain/01_chuong_trinh_dao_tao/03_domain_oplw`.
- Font chữ mặc định cho website tiếng Việt mới là `Be Vietnam Pro`, fallback `Inter`, `Arial`, `sans-serif`.
- Template/base HTML phải import Google Fonts:
  ```html
  <link href="https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:wght@300;400;500;600;700;800;900&family=Inter:wght@400;500;600;700;800&display=swap&subset=vietnamese" rel="stylesheet">
  ```
- CSS nền tảng phải đặt:
  ```css
  body {
    font-family: "Be Vietnam Pro", Inter, Arial, sans-serif;
  }
  h1, h2, h3, .page-title, .main-title {
    font-family: "Be Vietnam Pro", Inter, Arial, sans-serif;
  }
  ```
- Không dùng `Montserrat` làm font mặc định cho website tiếng Việt mới, trừ khi người dùng yêu cầu rõ hoặc đang sửa dự án có nhận diện cũ cần giữ.
- Khi người dùng đưa HTML có sẵn:
  - Đưa HTML vào template Django, ví dụ `[app]/templates/[app]/index.html`.
  - Đưa CSS/JS/ảnh vào static Django, ví dụ `[app]/static/[app]/css/...`.
  - Template phải dùng `{% load static %}` và link asset bằng `{% static '...' %}`.
  - Không để website mới chỉ chạy bằng file HTML mở trực tiếp hoặc Nginx tĩnh.

### Bước A - Xác định tên chuẩn và nguồn dữ liệu

- Tìm số thứ tự tiếp theo còn trống trong `/root/10Web_BH`.
- Nếu có subdomain, đặt folder theo dạng `[Số]_domain_[subdomain]`, ví dụ `pytd.anhlaptrinh.vn` -> `25_domain_pytd`.
- Nếu người dùng đưa link nguồn/nội dung mẫu, đọc link hoặc file đó, rồi biên tập thành nội dung website/chương trình mới. Không sao chép dài nguyên văn từ nguồn bên ngoài khi không cần thiết.
- Nếu người dùng yêu cầu "viết lại theo Anh Lập Trình", chuyển nội dung nguồn sang giọng thực chiến, gần gũi, ưu tiên "cứ ứng dụng vào công việc trước, vướng thì gỡ", không bê nguyên văn câu chữ/claim của nguồn tham khảo.
- Nếu người dùng nêu rõ tên miền, ghi lại:
  - `PROJECT_CODE`: tên folder chuẩn, ví dụ `25_domain_pytd`.
  - `PROJECT_DOMAIN`: ví dụ `pytd.anhlaptrinh.vn`.
  - `PROJECT_URL`: ví dụ `https://pytd.anhlaptrinh.vn/`.
  - `COURSE_TITLE`: tên chương trình/khóa học hiển thị.

### Bước B - Tạo folder website trong `/root/10Web_BH`

- Tạo folder `/root/10Web_BH/[PROJECT_CODE]`.
- Ưu tiên clone/copy cấu trúc từ website mẫu phù hợp:
  - Mặc định cho mọi website khóa học/chương trình/landing page/brochure: tham khảo `/root/10Web_BH/03_domain_oplw`.
  - Website khóa học có Django, đăng ký, thanh toán, chatbot nâng cao: vẫn ưu tiên bắt đầu từ `/root/10Web_BH/03_domain_oplw`, rồi chỉ bổ sung phần cần thiết từ `/root/10Web_BH/19_domain_ancl` nếu chức năng đó thật sự cần.
  - Website cổng/portal: tham khảo `/root/10Web_BH/28_domain_alt`.
- Không copy runtime/private files từ mẫu: `.env` thật, `db.sqlite3`, `output.log`, `__pycache__/`, `*.pyc`.
- Nếu mẫu có API key, SePay secret, webhook secret, email cá nhân hoặc token trong code/config, dùng skill `khu-token-api-secret` để chuyển sang `.env` hoặc placeholder trước khi báo xong.
- Với website mới có chatbot tư vấn, sau khi tạo `.env` từ `.env.example`, copy các biến vận hành nội bộ `DEEPSEEK_API_KEY`, `DEEPSEEK_MODEL`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` từ `.env` của mẫu `/root/10Web_BH/03_domain_oplw/.env` sang `.env` thật của dự án mới nếu mẫu có giá trị hợp lệ. Không in giá trị secret ra log/final answer, không đưa secret thật vào `.env.example`, tài liệu, Second Brain, hoặc skill.
- Cập nhật các file quan trọng:
  - `docker-compose.yml`: service/container/router/middleware/service name theo subdomain; Traefik `Host(\`PROJECT_DOMAIN\`)`.
  - `.env.example` và `.env`: `COURSE_CODE`, `COURSE_FOLDER`, `COURSE_TITLE`, `PROJECT_PUBLIC_URL`, `PROJECT_FOLDER_NAME`.
  - `mysite/settings.py`: `CSRF_TRUSTED_ORIGINS` có domain mới.
  - `views.py`, `course_advisor.py`, `sepay.py`: tên khóa, học phí, public URL, fallback host.
  - template landing page: cập nhật nội dung theo câu lệnh/link nguồn của người dùng.

### Bước C - Gắn tên miền nếu có

- Nếu yêu cầu có domain/subdomain/tên miền con, tự động dùng skill `cloudflare-subdomain` để tạo A record khi DNS chưa có hoặc cần gắn tên miền. Người dùng không cần gọi rõ tên skill Cloudflare.
- Mặc định dùng IP của skill Cloudflare nếu người dùng không đưa IP riêng.
- Sau khi cấu hình Docker/Traefik, chạy:
  - `python3 manage.py check`
  - `python3 manage.py migrate` nếu là Django có database.
  - `docker compose up -d --build`
  - `curl -I -H 'Host: PROJECT_DOMAIN' http://127.0.0.1`
  - `curl -I https://PROJECT_DOMAIN`
- Nếu HTTPS mới cấp chứng chỉ chậm, kiểm tra thêm bằng `curl -k -I` và `openssl s_client`.

### Bước D - Tạo folder cùng tên trong Second Brain

Luôn tạo folder:

`/root/Second_Brain/01_chuong_trinh_dao_tao/[PROJECT_CODE]`

Tạo cấu trúc chuẩn tương tự chương trình mẫu:

`/root/Second_Brain/01_chuong_trinh_dao_tao/03_domain_oplw`

Nếu chưa có lý do đặc biệt, dùng cấu trúc thư mục và kiểu file tổng hợp của `03_domain_oplw` làm chuẩn mặc định:

```text
[PROJECT_CODE]/
├── 00_moc_[slug_khoa_hoc].md
├── 00_tong_quan_chuong_trinh/
│   └── 00_tong_hop_tong_quan_chuong_trinh.md
├── 02_lo_trinh_dao_tao/
│   ├── 00_tong_hop_kich_hoat_va_onboarding.md
│   └── 00_tong_hop_lo_trinh_dao_tao.md
├── 03_q_a_va_xu_ly_phan_doi/
│   └── 00_tong_hop_q_a_va_xu_ly_phan_doi.md
├── 05_bai_quang_cao_va_content/
│   ├── 00_tong_hop_bai_quang_cao_va_content.md
│   └── Noi_Dung_Trang_Website_Ban_Hang.md
├── 06_prompt_va_workflow_mau/
│   └── 00_tong_hop_prompt_va_workflow_mau.md
├── 07_case_study_va_vi_du/
│   └── 00_tong_hop_case_study_va_vi_du.md
├── 08_tai_lieu_ky_thuat/
│   └── 00_tong_hop_tai_lieu_ky_thuat.md
├── 10_post_trang_ca_nhan_quang_cao/
│   └── 00_tong_hop_post_trang_ca_nhan_quang_cao.md
├── 11_doi_tuong_khach_hang_huong_toi/
│   └── 00_tong_hop_doi_tuong_khach_hang_huong_toi.md
├── 01_du_lieu_website_chatbot_[PROJECT_DOMAIN]/
│   ├── 01_du_lieu_nap_ai_fanpage.csv
│   ├── 02_du_lieu_nap_ai_fanpage.xlsx
│   ├── 03_du_lieu_chatbot_tu_van.md
│   └── 04_du_lieu_lam_website.md
└── 99_ghi_chu_tong_hop/
    └── 00_tong_hop_ghi_chu_tong_hop.md
```

Yêu cầu nội dung tối thiểu:

- MOC có frontmatter, định vị ngắn, link wiki tới từng nhóm.
- `01_du_lieu_website_chatbot.../01_du_lieu_nap_ai_fanpage.csv` là dữ liệu hỏi đáp để nạp cho AI/Fanpage.
- `01_du_lieu_website_chatbot.../02_du_lieu_nap_ai_fanpage.xlsx` là bản Excel cùng nội dung với CSV để người vận hành đọc/sửa dễ hơn.
- `01_du_lieu_website_chatbot.../03_du_lieu_chatbot_tu_van.md` phải có thông tin công ty, chương trình, học phí, link đăng ký, FAQ, quy tắc trả lời và giọng tư vấn để chatbot đọc.
- `01_du_lieu_website_chatbot.../04_du_lieu_lam_website.md` phải có dữ liệu dựng website: tên chương trình, headline, offer, học phí, CTA, lợi ích, đối tượng phù hợp và nội dung public đã biên tập/trích xuất từ website.
- Không tạo thêm thư mục `13_du_lieu_dao_tao_business_ai_fanpage_facebook` nữa.
- Các file tổng hợp phải đủ thông tin để chatbot tư vấn đọc được qua `course_advisor`: tổng quan, lộ trình, onboarding, Q&A, đối tượng khách hàng, dữ liệu website.

### Bước E - Đưa chương trình vào dự án ALT portal

Luôn cập nhật dự án `/root/10Web_BH/28_domain_alt` để cổng ALT biết khóa mới:

- Trong `website/views.py`:
  - Thêm `PROJECT_CODE` vào `COURSE_FOLDERS`.
  - Thêm `PROJECT_CODE: (PROJECT_CODE, PROJECT_URL)` vào `COURSE_PROJECT_META`.
- Trong `script.js` và `website/static/website/js/script.js`:
  - Thêm object mới vào `advisorCourses` với các trường: `id`, `code`, `title`, `tag`, `level`, `tools`, `url`, `short`, `fit`, `outcome`, `keywords`.
  - Đặt object khóa mới ở đầu mảng `advisorCourses` để khóa mới xuất hiện ngay trong danh sách khóa học và nhóm khóa nổi bật trên trang chủ, vì homepage thường chỉ render một số khóa đầu tiên.
  - Nếu trang courses/home render từ `advisorCourses`, object này sẽ tự xuất hiện trên cổng.
- Bump query version cho static JS/CSS trong template ALT, ví dụ đổi `?v=...` sang ngày/mã mới như `?v=20260607-anns`, để trình duyệt không giữ danh sách khóa học cũ.
- Nếu dự án dùng HTML tĩnh cũ (`courses.html`) hoặc CSS image class riêng, thêm card hoặc class ảnh tương ứng khi cần.
- Kiểm tra API tư vấn với `PROJECT_CODE`; nếu trả `invalid_course`, nghĩa là thiếu cập nhật `COURSE_FOLDERS`.

### Bước F - Kiểm thử cuối

- `rg` trong website mới để chắc không còn domain/tên khóa mẫu cũ.
- `python3 manage.py check` ở website mới và ở `/root/10Web_BH/28_domain_alt` nếu đã sửa portal Django.
- `curl -I` domain mới.
- Test đọc context:

```bash
COURSE_CODE=[PROJECT_CODE] COURSE_FOLDER=[PROJECT_CODE] python3 - <<'PY'
from pathlib import Path
import os
os.chdir('/root/10Web_BH/[PROJECT_CODE]')
from trolyai.course_advisor import _read_course_context
text = _read_course_context('[PROJECT_CODE]')
print(len(text))
print(text[:300])
PY
```

---

## QUY TRÌNH ĐỔI TÊN/CHUẨN HÓA FOLDER ĐANG CÓ (BẮT BUỘC)

Việc đổi tên thư mục cha có thể phá vỡ các cấu hình liên kết. Do đó, khi triển khai kỹ năng này, bạn phải thực hiện đầy đủ các bước an toàn sau để **đảm bảo mọi thứ vẫn chạy mượt mà**:

### Bước 1: Quét & Đề xuất Mapping
- Quét danh sách các thư mục hiện có.
- Tra cứu tệp tin cấu hình (`docker-compose.yml`, `nginx.conf`, file metadata hoặc file list trang web) để tìm ra subdomain chính xác của từng dự án.
- Lập bảng đề xuất mapping chuyển đổi gửi cho người dùng phê duyệt trước khi đổi tên.

### Bước 2: Thực thi Đổi tên Vật lý
- Sử dụng công cụ lệnh hoặc script Python để thực hiện `os.rename` đổi tên thư mục vật lý.

### Bước 3: Đồng bộ hóa cấu hình & Liên kết (Refactoring)
- **Nếu là dự án Web (Docker Compose/Nginx):**
  - Quét nội dung các tệp tin cấu hình (`docker-compose.yml`, `nginx.conf`, script hướng dẫn chạy, biến `.env`) trong thư mục vừa được đổi tên.
  - Tìm và thay thế các đường dẫn tuyệt đối dạng `/root/10Web_BH/[Tên_Cũ]` thành `/root/10Web_BH/[Tên_Mới]` để tránh lỗi đường dẫn.
- **Nếu là tài liệu Obsidian (Second_Brain):**
  - Quét toàn bộ tệp tin `.md` trong toàn bộ Obsidian Vault.
  - Tự động tìm kiếm và cập nhật tất cả các wiki-links bị đổi tên (ví dụ: Thay thế `[[01 - Python Antigravity]]` thành `[[05_domain_vibepython]]`) để bảo toàn sơ đồ liên kết của người dùng.

### Bước 4: Kiểm thử hoạt động của Container và Web
- Chạy `docker ps` để kiểm tra các container của dự án vẫn chạy bình thường.
- Chạy `curl -I` kiểm tra phản hồi HTTP (mã `200 OK`) của các website chính sau khi đổi tên để đảm bảo không bị gián đoạn.
