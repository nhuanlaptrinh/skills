---
name: cap-nhat-chuong-trinh-alt-portal
description: Cập nhật các chương trình/khóa học mới từ /root/Second_Brain/01_chuong_trinh_dao_tao vào cổng ALT /root/10Web_BH/28_domain_alt, bao gồm danh sách khóa học frontend, whitelist chatbot backend, metadata Telegram/domain và kiểm thử API tư vấn.
---

# Cập Nhật Chương Trình ALT Portal

Use this skill when the user asks to:
- cập nhật khóa học/chương trình mới vào website ALT
- đưa chương trình mới trong Second Brain lên `/root/10Web_BH/28_domain_alt`
- cập nhật cổng `anhlaptrinh.vn` / `28_domain_alt`
- thêm khóa mới vào chatbot tư vấn khóa học ALT

## Sources

- Portal project: `/root/10Web_BH/28_domain_alt`
- Training data root: `/root/Second_Brain/01_chuong_trinh_dao_tao`
- Frontend course list files:
  - `/root/10Web_BH/28_domain_alt/script.js`
  - `/root/10Web_BH/28_domain_alt/website/static/website/js/script.js`
- Backend chatbot whitelist:
  - `/root/10Web_BH/28_domain_alt/website/views.py`

## Workflow

1. Discover new course folders.
   - List folders under `/root/Second_Brain/01_chuong_trinh_dao_tao`.
   - Compare against `advisorCourses` in both JS files and `COURSE_FOLDERS` in `website/views.py`.
   - Treat missing numbered `*_domain_*` folders as candidates to add.

2. Extract course metadata.
   - Prefer markdown inside `01_du_lieu_website_chatbot*`, especially:
     - `03_du_lieu_chatbot_tu_van.md`
     - `04_du_lieu_lam_website.md`
   - Also inspect overview/Q&A files when needed:
     - `00_tong_quan_chuong_trinh/00_tong_hop_tong_quan_chuong_trinh.md`
     - `02_lo_trinh_dao_tao/00_tong_hop_lo_trinh_dao_tao.md`
     - `03_q_a_va_xu_ly_phan_doi/00_tong_hop_q_a_va_xu_ly_phan_doi.md`
   - Build one JS course object per new course with:
     `id`, `code`, `title`, `tag`, `level`, `tools`, `url`, `short`, `fit`, `outcome`, `keywords`.
   - Infer URL from markdown if present. If missing, infer `https://<subdomain>.anhlaptrinh.vn/` from folder name like `31_domain_anvi`.

3. Update backend whitelist.
   - In `website/views.py`, add each code to `COURSE_FOLDERS`.
   - Add each code to `COURSE_PROJECT_META` with `(PROJECT_CODE, PROJECT_URL)`.
   - Keep keys sorted by numeric folder order where practical.

4. Update frontend course arrays.
   - Add the same course objects to both:
     - root `script.js`
     - `website/static/website/js/script.js`
   - Keep both files identical for the `advisorCourses` data block.
   - Add objects before the closing `];` of `advisorCourses`.

5. Verify.
   - Run in `/root/10Web_BH/28_domain_alt`:
     - `python3 manage.py check`
     - `docker compose config --quiet`
   - Test backend API for every added course:
     ```bash
     curl -sS -k --resolve anhlaptrinh.vn:443:127.0.0.1 \
       -X POST -H 'Content-Type: application/json' \
       https://anhlaptrinh.vn/api/course-advisor/ \
       -d '{"course_code":"PROJECT_CODE","course_title":"COURSE_TITLE","question":"cho tôi xin link đăng ký"}'
     ```
   - Expected: not `invalid_course`; if DeepSeek key is present, expect `configured: true`.

6. Deploy.
   - Recreate portal container:
     ```bash
     cd /root/10Web_BH/28_domain_alt
     docker compose up -d --force-recreate
     ```
   - Confirm public HTML contains new course titles:
     ```bash
     curl -sS https://anhlaptrinh.vn/courses/ | rg "COURSE_TITLE|PROJECT_CODE"
     ```

## Safety

- Do not print real `.env` values.
- Do not edit unrelated legacy course cards unless the rendered portal depends on them.
- Before final response, scan touched project/skill files for obvious secret patterns.
