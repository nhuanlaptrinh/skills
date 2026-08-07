#!/usr/bin/env python3

import argparse
import os
import re
import shutil
import socket
import sys
import textwrap
from pathlib import Path


PROJECT_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")
DOMAIN_RE = re.compile(
    r"^(?=.{4,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scaffold a production-ready Django website")
    parser.add_argument("--project-name", required=True)
    parser.add_argument("--domain", required=True)
    parser.add_argument("--port", required=True, type=int)
    parser.add_argument("--profile", required=True, choices=("standalone", "course"))
    parser.add_argument("--number", type=int)
    parser.add_argument("--title", required=True)
    parser.add_argument("--destination", type=Path)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--apply", action="store_true")
    return parser.parse_args()


def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def validate(args: argparse.Namespace) -> None:
    args.project_name = args.project_name.lower()
    args.domain = args.domain.lower()
    if not PROJECT_RE.fullmatch(args.project_name):
        fail("project-name must contain lowercase letters, numbers, or hyphens")
    if not DOMAIN_RE.fullmatch(args.domain):
        fail("domain must be a valid fully qualified domain name")
    if not 1024 <= args.port <= 65535:
        fail("port must be between 1024 and 65535")
    if args.profile == "course":
        if args.number is None or not 1 <= args.number <= 99:
            fail("course profile requires --number between 1 and 99")
    elif args.number is not None:
        fail("--number is only valid with --profile course")


def destination_for(args: argparse.Namespace) -> Path:
    if args.destination:
        return args.destination.expanduser().resolve()
    if args.profile == "course":
        folder_name = f"{args.number:02d}_domain_{args.project_name.replace('-', '_')}"
        return Path("/root/Apps/course_websites/10Web_BH") / folder_name
    return Path("/root/Apps/websites") / args.project_name


def port_is_available(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind(("127.0.0.1", port))
        except OSError:
            return False
    return True


def render(template: str, replacements: dict[str, str]) -> str:
    content = textwrap.dedent(template).lstrip()
    for key, value in replacements.items():
        content = content.replace(f"__{key}__", value)
    return content


def project_files(args: argparse.Namespace) -> dict[str, str]:
    replacements = {
        "PROJECT_NAME": args.project_name,
        "DOMAIN": args.domain,
        "PORT": str(args.port),
        "TITLE": args.title,
        "PROFILE": args.profile,
    }
    templates = {
        "AGENTS.md": """
            # Project Instructions

            - Đọc `/root/_Second_AI_Brain/START_HERE.md` và project note trước khi sửa production.
            - Không in hoặc commit `.env`, database, token, password hay credential.
            - Backup Nginx/Compose/config quan trọng vào `/root/_Backups` trước khi sửa production.
            - Giữ Docker bind `127.0.0.1:__PORT__:8000`; không public trực tiếp cổng Django.
            - Chạy `python manage.py check`, tests liên quan, `docker compose config` và `nginx -t` sau thay đổi.
            - Ghi thay đổi quan trọng vào `/root/_Second_AI_Brain/06_Nhat_Ky_Thay_Doi.md`.
        """,
        ".dockerignore": """
            .env
            .git
            __pycache__
            *.py[cod]
            data
            staticfiles
        """,
        ".env.example": """
            DJANGO_SECRET_KEY=CHANGE_ME_GENERATE_AT_DEPLOY
            DJANGO_DEBUG=0
            DJANGO_ALLOWED_HOSTS=__DOMAIN__,localhost,127.0.0.1
            DJANGO_CSRF_TRUSTED_ORIGINS=https://__DOMAIN__
        """,
        ".gitignore": """
            .env
            .venv/
            __pycache__/
            *.py[cod]
            data/db.sqlite3
            staticfiles/*
            !staticfiles/.gitkeep
        """,
        "Dockerfile": """
            FROM python:3.12-slim

            ENV PYTHONDONTWRITEBYTECODE=1 \\
                PYTHONUNBUFFERED=1

            WORKDIR /app

            COPY requirements.txt .
            RUN pip install --no-cache-dir -r requirements.txt

            COPY . .

            EXPOSE 8000

            CMD ["sh", "-c", "python manage.py migrate --noinput && python manage.py collectstatic --noinput && gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 3 --timeout 120"]
        """,
        "README.md": """
            # __TITLE__

            Django website profile `__PROFILE__` for `__DOMAIN__`.

            ## Chuẩn bị

            ```bash
            bash scripts/prepare_env.sh
            docker compose config
            docker compose run --rm web python manage.py check
            docker compose run --rm web python manage.py test
            ```

            ## Chạy

            ```bash
            docker compose up -d --build
            docker compose ps
            docker compose logs --tail=120
            ```

            App chỉ lắng nghe tại `127.0.0.1:__PORT__`; domain public đi qua Nginx và HTTPS.
        """,
        "docker-compose.yml": """
            services:
              web:
                build: .
                container_name: __PROJECT_NAME__-django
                restart: unless-stopped
                env_file:
                  - .env
                ports:
                  - "127.0.0.1:__PORT__:8000"
                volumes:
                  - ./data:/app/data
                  - ./staticfiles:/app/staticfiles
                healthcheck:
                  test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/', timeout=5)"]
                  interval: 30s
                  timeout: 10s
                  retries: 3
                  start_period: 20s
        """,
        "manage.py": """
            #!/usr/bin/env python3
            import os
            import sys


            def main():
                os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
                from django.core.management import execute_from_command_line

                execute_from_command_line(sys.argv)


            if __name__ == "__main__":
                main()
        """,
        "requirements.txt": """
            Django==5.2.4
            gunicorn==23.0.0
        """,
        "config/__init__.py": "",
        "config/asgi.py": """
            import os

            from django.core.asgi import get_asgi_application

            os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
            application = get_asgi_application()
        """,
        "config/settings.py": """
            import os
            from pathlib import Path

            BASE_DIR = Path(__file__).resolve().parent.parent

            DEBUG = os.getenv("DJANGO_DEBUG", "0") == "1"
            SECRET_KEY = os.getenv("DJANGO_SECRET_KEY")
            if not SECRET_KEY:
                if DEBUG:
                    SECRET_KEY = "django-insecure-local-development-only"
                else:
                    raise RuntimeError("DJANGO_SECRET_KEY is required when DJANGO_DEBUG=0")

            ALLOWED_HOSTS = [
                item.strip()
                for item in os.getenv(
                    "DJANGO_ALLOWED_HOSTS", "__DOMAIN__,localhost,127.0.0.1"
                ).split(",")
                if item.strip()
            ]
            CSRF_TRUSTED_ORIGINS = [
                item.strip()
                for item in os.getenv(
                    "DJANGO_CSRF_TRUSTED_ORIGINS", "https://__DOMAIN__"
                ).split(",")
                if item.strip()
            ]

            INSTALLED_APPS = [
                "django.contrib.admin",
                "django.contrib.auth",
                "django.contrib.contenttypes",
                "django.contrib.sessions",
                "django.contrib.messages",
                "django.contrib.staticfiles",
                "website",
            ]

            MIDDLEWARE = [
                "django.middleware.security.SecurityMiddleware",
                "django.contrib.sessions.middleware.SessionMiddleware",
                "django.middleware.common.CommonMiddleware",
                "django.middleware.csrf.CsrfViewMiddleware",
                "django.contrib.auth.middleware.AuthenticationMiddleware",
                "django.contrib.messages.middleware.MessageMiddleware",
                "django.middleware.clickjacking.XFrameOptionsMiddleware",
            ]

            ROOT_URLCONF = "config.urls"

            TEMPLATES = [
                {
                    "BACKEND": "django.template.backends.django.DjangoTemplates",
                    "DIRS": [BASE_DIR / "templates"],
                    "APP_DIRS": True,
                    "OPTIONS": {
                        "context_processors": [
                            "django.template.context_processors.request",
                            "django.contrib.auth.context_processors.auth",
                            "django.contrib.messages.context_processors.messages",
                        ],
                    },
                }
            ]

            WSGI_APPLICATION = "config.wsgi.application"

            DATABASES = {
                "default": {
                    "ENGINE": "django.db.backends.sqlite3",
                    "NAME": BASE_DIR / "data" / "db.sqlite3",
                }
            }

            AUTH_PASSWORD_VALIDATORS = [
                {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
                {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
                {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
                {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
            ]

            LANGUAGE_CODE = "vi"
            TIME_ZONE = "Asia/Ho_Chi_Minh"
            USE_I18N = True
            USE_TZ = True

            STATIC_URL = "/static/"
            STATICFILES_DIRS = [BASE_DIR / "static"]
            STATIC_ROOT = BASE_DIR / "staticfiles"

            DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
            SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
            SESSION_COOKIE_SECURE = not DEBUG
            CSRF_COOKIE_SECURE = not DEBUG
            X_FRAME_OPTIONS = "DENY"
        """,
        "config/urls.py": """
            from django.contrib import admin
            from django.urls import include, path

            urlpatterns = [
                path("admin/", admin.site.urls),
                path("", include("website.urls")),
            ]
        """,
        "config/wsgi.py": """
            import os

            from django.core.wsgi import get_wsgi_application

            os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
            application = get_wsgi_application()
        """,
        "website/__init__.py": "",
        "website/admin.py": "",
        "website/apps.py": """
            from django.apps import AppConfig


            class WebsiteConfig(AppConfig):
                default_auto_field = "django.db.models.BigAutoField"
                name = "website"
        """,
        "website/models.py": "",
        "website/tests.py": """
            from django.test import TestCase
            from django.urls import reverse


            class HomePageTests(TestCase):
                def test_home_page_returns_success(self):
                    response = self.client.get(
                        reverse("website:home"), HTTP_HOST="__DOMAIN__"
                    )
                    self.assertEqual(response.status_code, 200)
        """,
        "website/urls.py": """
            from django.urls import path

            from . import views

            app_name = "website"

            urlpatterns = [
                path("", views.home, name="home"),
            ]
        """,
        "website/views.py": """
            from django.shortcuts import render


            def home(request):
                return render(request, "website/home.html", {"site_title": "__TITLE__"})
        """,
        "templates/website/home.html": """
            {% load static %}
            <!doctype html>
            <html lang="vi">
            <head>
              <meta charset="utf-8">
              <meta name="viewport" content="width=device-width, initial-scale=1">
              <title>{{ site_title }}</title>
              <meta name="description" content="Website Django tại __DOMAIN__">
              <link rel="preconnect" href="https://fonts.googleapis.com">
              <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
              <link href="https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:wght@400;500;600;700;800&display=swap&subset=vietnamese" rel="stylesheet">
              <link rel="stylesheet" href="{% static 'website/css/style.css' %}">
            </head>
            <body>
              <main class="hero">
                <p class="eyebrow">Django Website</p>
                <h1>{{ site_title }}</h1>
                <p>Website đã sẵn sàng để phát triển nội dung và tính năng.</p>
                <a class="button" href="/admin/">Mở trang quản trị</a>
              </main>
            </body>
            </html>
        """,
        "static/website/css/style.css": """
            :root {
              color-scheme: light;
              font-family: "Be Vietnam Pro", Arial, sans-serif;
              background: #f5f7fb;
              color: #14213d;
            }

            * {
              box-sizing: border-box;
            }

            body {
              margin: 0;
              min-height: 100vh;
              display: grid;
              place-items: center;
              background: radial-gradient(circle at top, #ffffff, #e8eef9);
            }

            .hero {
              width: min(760px, calc(100% - 32px));
              padding: 64px 48px;
              border: 1px solid #dce5f3;
              border-radius: 28px;
              background: rgba(255, 255, 255, 0.92);
              box-shadow: 0 24px 80px rgba(20, 33, 61, 0.12);
              text-align: center;
            }

            .eyebrow {
              color: #2563eb;
              font-weight: 700;
              letter-spacing: 0.12em;
              text-transform: uppercase;
            }

            h1 {
              margin: 12px 0 16px;
              font-size: clamp(2.2rem, 8vw, 4.6rem);
              line-height: 1.05;
            }

            .button {
              display: inline-block;
              margin-top: 20px;
              padding: 14px 22px;
              border-radius: 999px;
              background: #2563eb;
              color: #ffffff;
              font-weight: 700;
              text-decoration: none;
            }
        """,
        "deploy/nginx.conf.example": """
            server {
                listen 80;
                listen [::]:80;
                server_name __DOMAIN__;

                location / {
                    proxy_pass http://127.0.0.1:__PORT__;
                    proxy_http_version 1.1;
                    proxy_set_header Host $host;
                    proxy_set_header X-Real-IP $remote_addr;
                    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
                    proxy_set_header X-Forwarded-Proto $scheme;
                    proxy_set_header X-Forwarded-Host $host;
                    proxy_set_header X-Forwarded-Port $server_port;
                }
            }
        """,
        "scripts/prepare_env.sh": """
            #!/usr/bin/env bash
            set -euo pipefail

            PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
            ENV_FILE="$PROJECT_DIR/.env"
            EXAMPLE_FILE="$PROJECT_DIR/.env.example"

            if [[ -e "$ENV_FILE" ]]; then
                echo ".env already exists; refusing to overwrite" >&2
                exit 1
            fi

            umask 077
            DJANGO_GENERATED_SECRET="$(python3 -c 'import secrets; print(secrets.token_urlsafe(64))')" \
                python3 - "$EXAMPLE_FILE" "$ENV_FILE" <<'PY'
            import os
            import sys
            from pathlib import Path

            source = Path(sys.argv[1]).read_text(encoding="utf-8")
            secret = os.environ["DJANGO_GENERATED_SECRET"]
            Path(sys.argv[2]).write_text(
                source.replace("CHANGE_ME_GENERATE_AT_DEPLOY", secret),
                encoding="utf-8",
            )
            PY
            chmod 600 "$ENV_FILE"
            echo "Created $ENV_FILE with mode 600"
        """,
        "data/.gitkeep": "",
        "staticfiles/.gitkeep": "",
    }
    return {path: render(template, replacements) for path, template in templates.items()}


def write_project(destination: Path, files: dict[str, str]) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = destination.parent / f".{destination.name}.tmp-{os.getpid()}"
    if staging.exists():
        fail(f"temporary path already exists: {staging}")
    try:
        for relative_path, content in files.items():
            target = staging / relative_path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
        (staging / "manage.py").chmod(0o755)
        (staging / "scripts/prepare_env.sh").chmod(0o755)
        staging.replace(destination)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def main() -> None:
    args = parse_args()
    validate(args)
    destination = destination_for(args)
    if destination.exists():
        fail(f"destination already exists: {destination}")
    if not port_is_available(args.port):
        fail(f"port is already in use: 127.0.0.1:{args.port}")

    files = project_files(args)
    print(f"Mode: {'apply' if args.apply else 'dry-run'}")
    print(f"Profile: {args.profile}")
    print(f"Destination: {destination}")
    print(f"Domain: {args.domain}")
    print(f"Loopback port: 127.0.0.1:{args.port}")
    print(f"Files: {len(files)}")

    if args.dry_run:
        for relative_path in sorted(files):
            print(f"  - {relative_path}")
        return

    write_project(destination, files)
    print(f"Created Django website scaffold at {destination}")
    print(f"Next: cd {destination} && bash scripts/prepare_env.sh")


if __name__ == "__main__":
    main()
