# Cấu trúc Website Django Chuẩn

## Profile standalone

```text
/root/Apps/websites/<project-name>/
├── AGENTS.md
├── .dockerignore
├── .env.example
├── .gitignore
├── Dockerfile
├── README.md
├── docker-compose.yml
├── manage.py
├── requirements.txt
├── config/
├── website/
├── templates/website/
├── static/website/css/
├── static/website/img/logo-anh-lap-trinh.png
├── staticfiles/
├── data/
├── deploy/nginx.conf.example
└── scripts/prepare_env.sh
```

## Profile course

Destination:

```text
/root/Apps/course_websites/10Web_BH/<NN>_domain_<subdomain>/
```

Giữ cùng cấu trúc Django, Docker và Nginx. Logic nội dung khóa học, Second Brain, payment, chatbot và ALT portal phải theo skill chuyên biệt tương ứng.

## Kiến trúc runtime

```text
Cloudflare A record
  -> HTTPS :443
  -> Nginx host
  -> 127.0.0.1:<host-port>
  -> Docker container :8000
  -> Gunicorn
  -> Django
```

## Environment

`.env.example` chỉ chứa placeholder:

- `DJANGO_SECRET_KEY`
- `DJANGO_DEBUG`
- `DJANGO_ALLOWED_HOSTS`
- `DJANGO_CSRF_TRUSTED_ORIGINS`

`.env` được tạo bằng `scripts/prepare_env.sh`, đặt mode `600`, nằm ngoài Git và không được in ra log/tài liệu.

## Dữ liệu

- SQLite mặc định: `data/db.sqlite3`.
- Static production: `staticfiles/`.
- Hai thư mục được bind mount để không mất dữ liệu khi rebuild container.
- Nếu chuyển sang PostgreSQL, thêm biến môi trường và volume riêng; không ghi credential vào Compose.

## Domain

- A record được tạo qua skill `/root/.agents/skills/cloudflare-subdomain`.
- Nginx chỉ proxy tới loopback.
- Certbot quản lý certificate và redirect HTTPS.
- Khi DNS đã tồn tại nhưng không đúng IP, dừng để xác minh thay vì tự động ghi đè.
