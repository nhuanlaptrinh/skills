---
name: tao-website-django-cloudflare
description: Tạo, scaffold, triển khai hoặc chuẩn hóa website Python Django theo cấu trúc VPS ALT trong /root/Apps, chạy bằng Docker bind loopback, Nginx reverse proxy và HTTPS; tự tích hợp skill cloudflare-subdomain để tạo tên miền con/A record khi người dùng yêu cầu website kèm domain hoặc subdomain. Use khi người dùng nói tạo website Django, tạo web mới theo cấu trúc VPS, dựng landing page Django, tạo website kèm tên miền con, deploy Django lên subdomain, hoặc tạo course website mới nhưng chưa yêu cầu logic chuyên ngành cụ thể.
---

# Tạo Website Django + Cloudflare

## Phạm vi

- Website độc lập mới: `/root/Apps/websites/<project-name>`.
- Website khóa học ALT: `/root/Apps/course_websites/10Web_BH/<NN>_domain_<subdomain>`.
- Stack mặc định: Django, Gunicorn, Docker Compose, host Nginx, Certbot.
- App chỉ publish `127.0.0.1:<host-port>:8000`; không public trực tiếp cổng Django.
- Khi có domain/subdomain, bắt buộc dùng skill `cloudflare-subdomain` qua CLI `/root/.agents/skills/cloudflare-subdomain/tao_ten_mien` thay vì tự viết lại Cloudflare API.

## Nhận diện mặc định

- Dùng logo Anh Lập Trình chuẩn tại `/logo-anh-lap-trinh.png` cho website/web app Django mới, trừ khi người dùng yêu cầu nhận diện khác.
- Scaffold tự chép logo vào `static/website/img/logo-anh-lap-trinh.png`; template phải tham chiếu asset bằng `{% static %}` thay vì đường dẫn filesystem.
- Giữ logo ngang đúng tỉ lệ: `width:auto`, chiều cao cố định và `object-fit:contain`; không ép cặp kích thước vuông.

Nếu yêu cầu là website khóa học ALT có nội dung, Second Brain, thanh toán hoặc cập nhật ALT portal, dùng thêm skill `tao-website-khoa-hoc-alt`. Skill này phụ trách scaffold Django và hạ tầng chung, không thay thế logic khóa học chuyên biệt.

## Đọc trước khi làm

1. `/root/_Second_AI_Brain/START_HERE.md`
2. `/root/_Second_AI_Brain/01_Ban_Do_VPS.md`
3. `/root/_Second_AI_Brain/02_Danh_Sach_Project.md`
4. Project note liên quan trong `/root/_Second_AI_Brain/projects/`
5. `/root/_Second_AI_Brain/checklists/truoc_khi_sua_production.md` nếu deploy hoặc sửa production
6. `AGENTS.md` gần project nhất nếu có

## Input bắt buộc

- `project-name`: slug viết thường, dùng chữ, số và dấu `-`.
- `domain`: FQDN, ví dụ `demo.anhlaptrinh.vn`.
- `host-port`: cổng loopback chưa được sử dụng.
- `profile`: `standalone` hoặc `course`.
- `title`: tên hiển thị của website.
- `ip`: public IPv4 đã xác nhận của VPS khi tạo DNS; không đoán hoặc dùng IP cũ từ tài liệu.
- Với `course`: thêm `number` hai chữ số chưa dùng.

## Tạo scaffold

Luôn chạy dry-run trước:

```bash
python3 /root/.agents/skills/tao-website-django-cloudflare/scripts/scaffold_django_site.py \
  --project-name demo \
  --domain demo.anhlaptrinh.vn \
  --port 8022 \
  --profile standalone \
  --title "Website Demo" \
  --dry-run
```

Tạo thật sau khi đã xác nhận destination và port:

```bash
python3 /root/.agents/skills/tao-website-django-cloudflare/scripts/scaffold_django_site.py \
  --project-name demo \
  --domain demo.anhlaptrinh.vn \
  --port 8022 \
  --profile standalone \
  --title "Website Demo" \
  --apply
```

Profile khóa học:

```bash
python3 /root/.agents/skills/tao-website-django-cloudflare/scripts/scaffold_django_site.py \
  --project-name demo \
  --domain demo.anhlaptrinh.vn \
  --port 8022 \
  --profile course \
  --number 36 \
  --title "Khóa Học Demo" \
  --apply
```

Script không ghi đè destination đã tồn tại. Dùng `--destination /tmp/...` khi cần test scaffold ngoài `/root/Apps`.

## Hoàn thiện code

1. Đọc `README.md` và `AGENTS.md` vừa sinh.
2. Sửa nội dung trong `templates/website/home.html` và `static/website/css/style.css`; giữ logo mặc định trong `static/website/img/logo-anh-lap-trinh.png`.
3. Thêm model/view/form theo yêu cầu; không đưa secret vào source.
4. Chạy `bash scripts/prepare_env.sh`; script tạo `.env` mode `600` và không in secret.
5. Chạy kiểm tra trước deploy:

```bash
python3 -m compileall -q config website
docker compose config
docker compose run --rm web python manage.py check
docker compose run --rm web python manage.py test
```

## Deploy và tạo subdomain

Dry-run hạ tầng:

```bash
bash /root/.agents/skills/tao-website-django-cloudflare/scripts/setup_django_domain.sh \
  --project-dir /root/Apps/websites/demo \
  --domain demo.anhlaptrinh.vn \
  --port 8022 \
  --ip 203.0.113.10 \
  --dry-run
```

Chạy thật:

```bash
bash /root/.agents/skills/tao-website-django-cloudflare/scripts/setup_django_domain.sh \
  --project-dir /root/Apps/websites/demo \
  --domain demo.anhlaptrinh.vn \
  --port 8022 \
  --ip 203.0.113.10 \
  --certbot-email admin@example.com \
  --apply
```

Không truyền Cloudflare token trên command line. Script gọi skill `cloudflare-subdomain`, skill đó tự đọc credential riêng. Dùng `--skip-dns` nếu A record đã được quản trị đúng ở nơi khác; dùng `--skip-ssl` chỉ khi người dùng yêu cầu HTTP tạm thời.

## Script deploy thực hiện

1. Kiểm tra project, `.env`, Docker Compose, port, Nginx và Cloudflare helper.
2. Build/start container và kiểm tra HTTP trực tiếp trên loopback.
3. Backup Nginx cũ vào `/root/_Backups/django_site_domain_<domain>_<timestamp>`.
4. Tạo Nginx reverse proxy, chạy `nginx -t`, rồi reload.
5. Gọi `/root/.agents/skills/cloudflare-subdomain/tao_ten_mien <domain> <ip>` khi DNS chưa có.
6. Chờ DNS trỏ đúng IP, cấp SSL bằng Certbot và bật redirect HTTPS.
7. Kiểm tra HTTP, HTTPS, container health và Nginx.

## Output và tài liệu

- Source code trong destination đã chọn.
- Nginx host: `/etc/nginx/sites-available/<domain>`.
- Symlink: `/etc/nginx/sites-enabled/<domain>`.
- Backup: `/root/_Backups/django_site_domain_<domain>_<timestamp>`.
- DNS A record trong Cloudflare do skill `cloudflare-subdomain` tạo.
- SSL do Certbot quản lý.

Sau deploy production:

- Tạo/cập nhật project note trong `/root/_Second_AI_Brain/projects/`.
- Cập nhật `/root/_Second_AI_Brain/02_Danh_Sach_Project.md` nếu đây là project mới chính thức.
- Ghi thay đổi vào `/root/_Second_AI_Brain/06_Nhat_Ky_Thay_Doi.md`.

## Rerun và sửa lỗi

- Scaffold không rerun trên folder đã có; sửa code trực tiếp hoặc tạo destination mới.
- Script domain có thể rerun. Nếu DNS đã trỏ đúng IP, script bỏ qua bước tạo record.
- Nếu DNS tồn tại nhưng trỏ IP khác, dừng và xác minh record; không tự ghi đè mù.
- Nếu Certbot lỗi, giữ HTTP/Nginx đã kiểm tra, sửa DNS rồi rerun cùng tham số.
- Nếu Nginx config mới không hợp lệ, script khôi phục bản backup hoặc gỡ file mới.
- Kiểm tra bằng `docker compose ps`, `docker compose logs --tail=120`, `nginx -t`, `dig +short <domain> @1.1.1.1`, và `curl -I https://<domain>/`.

## An toàn

- Không copy `.env`, database, log, `__pycache__`, credential hoặc secret từ website mẫu.
- Không in nội dung `.env`, Cloudflare token, API key, cookie, password hoặc private key.
- Không dùng Django `runserver` cho production.
- Không expose app trên `0.0.0.0:<host-port>`.
- Không sửa/xóa Nginx, DNS hoặc project cũ ngoài domain được yêu cầu.
- Không chạy payment, chatbot, webhook, gửi tin hoặc đăng bài thật để test.
- Xem cấu trúc chi tiết tại `references/project_structure.md` khi cần.
