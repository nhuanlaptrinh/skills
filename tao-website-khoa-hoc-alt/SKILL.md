---
name: tao-website-khoa-hoc-alt
description: Tạo website khóa học/chương trình theo chuẩn ALT: tạo folder code trong /root/10Web_BH, đặt tên theo subdomain, gắn tên miền nếu có, tạo dữ liệu cùng tên trong Second Brain chương trình đào tạo, và đưa chương trình vào cổng /root/10Web_BH/28_domain_alt. Cũng dùng khi cần đặt tên/đổi tên folder chuẩn ALT.
---

# Tạo Website Khóa Học ALT

Skill này được thiết kế để bạn (AI) sử dụng khi người dùng yêu cầu:
- "Dùng skill tao-website-khoa-hoc-alt"
- "Tạo website khóa học ALT"
- "Đặt tên thư mục chuẩn ALT"
- "Đổi tên các folder dự án cho dễ nhớ và chuyên nghiệp"
- "Chuẩn hóa tên folder dựa theo tên miền"
- "Tạo folder website chuẩn Anh Lập Trình/ALT"
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

### Bước A - Xác định tên chuẩn và nguồn dữ liệu

- Tìm số thứ tự tiếp theo còn trống trong `/root/10Web_BH`.
- Nếu có subdomain, đặt folder theo dạng `[Số]_domain_[subdomain]`, ví dụ `pytd.anhlaptrinh.vn` -> `25_domain_pytd`.
- Nếu người dùng đưa link nguồn/nội dung mẫu, đọc link hoặc file đó, rồi biên tập thành nội dung website/chương trình mới. Không sao chép dài nguyên văn từ nguồn bên ngoài khi không cần thiết.
- Nếu người dùng nêu rõ tên miền, ghi lại:
  - `PROJECT_CODE`: tên folder chuẩn, ví dụ `25_domain_pytd`.
  - `PROJECT_DOMAIN`: ví dụ `pytd.anhlaptrinh.vn`.
  - `PROJECT_URL`: ví dụ `https://pytd.anhlaptrinh.vn/`.
  - `COURSE_TITLE`: tên chương trình/khóa học hiển thị.

### Bước B - Tạo folder website trong `/root/10Web_BH`

- Tạo folder `/root/10Web_BH/[PROJECT_CODE]`.
- Ưu tiên clone/copy cấu trúc từ website mẫu phù hợp:
  - Website khóa học có Django, đăng ký, thanh toán, chatbot: tham khảo `/root/10Web_BH/19_domain_ancl`.
  - Website cổng/portal: tham khảo `/root/10Web_BH/28_domain_alt`.
- Không copy runtime/private files từ mẫu: `.env` thật, `db.sqlite3`, `output.log`, `__pycache__/`, `*.pyc`.
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

`/root/Second_Brain/01Chuong_Trinh_Dao_Tao/01 - Chương trình đào tạo/[PROJECT_CODE]`

Tạo cấu trúc chuẩn tương tự các chương trình hiện có:

```text
[PROJECT_CODE]/
├── 00 - MOC - [COURSE_TITLE].md
├── 01 - Tổng quan chương trình/
│   └── 00 - Tổng hợp - Tổng quan chương trình.md
├── 02 - Lộ trình đào tạo/
│   ├── 00 - Tổng hợp - Kích hoạt và onboarding.md
│   └── 00 - Tổng hợp - Lộ trình đào tạo.md
├── 03 - Q&A và xử lý phản đối/
│   └── 00 - Tổng hợp - Q&A và xử lý phản đối.md
├── 05 - Bài quảng cáo và content/
│   ├── 00 - Tổng hợp - Bài quảng cáo và content.md
│   └── Noi_Dung_Trang_Website_Ban_Hang.md
├── 06 - Prompt và workflow mẫu/
│   └── 00 - Tổng hợp - Prompt và workflow mẫu.md
├── 07 - Case study và ví dụ/
│   └── 00 - Tổng hợp - Case study và ví dụ.md
├── 08 - Tài liệu kỹ thuật/
│   └── 00 - Tổng hợp - Tài liệu kỹ thuật.md
├── 10 - Post trang cá nhân quảng cáo/
│   └── 00 - Tổng hợp - Post trang cá nhân quảng cáo.md
├── 11 - Đối tượng khách hàng hướng tới/
│   └── 00 - Tổng hợp - Đối tượng khách hàng hướng tới.md
├── 12 - Dữ liệu làm website [PROJECT_DOMAIN]/
│   └── 00 - Thông tin website và link đăng ký.md
├── 13 - Dữ liệu đào tạo Business AI Fanpage Facebook/
│   ├── 00 - Hướng dẫn sử dụng dữ liệu.md
│   ├── 01 - Thông tin công ty và chương trình.md
│   └── 03 - FAQ đào tạo AI Fanpage.md
└── 99 - Ghi chú tổng hợp/
    └── 00 - Tổng hợp - Ghi chú tổng hợp.md
```

Yêu cầu nội dung tối thiểu:

- MOC có frontmatter, định vị ngắn, link wiki tới từng nhóm.
- `12 - Dữ liệu làm website.../00 - Thông tin website và link đăng ký.md` phải có `Mã chương trình`, `Tên chương trình`, `Website đăng ký chính thức`, `Link tư vấn/đăng ký`, học phí nếu có, và nội dung public đã biên tập/trích xuất từ website.
- Các file tổng hợp phải đủ thông tin để chatbot tư vấn đọc được qua `course_advisor`: tổng quan, lộ trình, onboarding, Q&A, đối tượng khách hàng, dữ liệu website.

### Bước E - Đưa chương trình vào dự án ALT portal

Luôn cập nhật dự án `/root/10Web_BH/28_domain_alt` để cổng ALT biết khóa mới:

- Trong `website/views.py`:
  - Thêm `PROJECT_CODE` vào `COURSE_FOLDERS`.
  - Thêm `PROJECT_CODE: (PROJECT_CODE, PROJECT_URL)` vào `COURSE_PROJECT_META`.
- Trong `script.js` và `website/static/website/js/script.js`:
  - Thêm object mới vào `advisorCourses` với các trường: `id`, `code`, `title`, `tag`, `level`, `tools`, `url`, `short`, `fit`, `outcome`, `keywords`.
  - Nếu trang courses/home render từ `advisorCourses`, object này sẽ tự xuất hiện trên cổng.
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
