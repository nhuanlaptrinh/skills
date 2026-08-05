#!/usr/bin/env python3
"""Create a reusable /root/_Second_AI_Brain skeleton without overwriting files."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path


ROOT_FILES = {
    "AGENTS.md": """# Quy tắc làm việc trên VPS này

Trước khi sửa bất kỳ project nào trên VPS này, AI/Codex phải đọc:

1. `/root/_Second_AI_Brain/START_HERE.md`
2. `/root/_Second_AI_Brain/01_Ban_Do_VPS.md`
3. `/root/_Second_AI_Brain/02_Danh_Sach_Project.md`
4. File project note liên quan trong `/root/_Second_AI_Brain/projects/` nếu có
5. Checklist `/root/_Second_AI_Brain/checklists/truoc_khi_sua_production.md` nếu sửa production

Nguyên tắc an toàn:
- Không ghi API key, token, cookie, mật khẩu hoặc private key thật vào tài liệu/câu trả lời.
- Không xóa folder/file quan trọng nếu chưa có yêu cầu rõ ràng.
- Không sửa `.env`, credential, Chrome/Selenium profile nếu task không yêu cầu.
- Trước khi sửa cron/nginx/docker-compose/production config, nên backup file gốc vào `/root/_Backups`.
- Nếu thư mục project có `AGENTS.md` riêng, phải đọc và ưu tiên hướng dẫn gần file hơn.
- Sau thay đổi quan trọng, cập nhật `/root/_Second_AI_Brain/06_Nhat_Ky_Thay_Doi.md`.

Cấu trúc chuẩn cho project:
- `/root/Apps` cho website, web app, N8N, video factory.
- `/root/Automation` cho bot/script tự động.
- `/root/Data` cho dữ liệu và tài liệu.
- `/root/AI_Runtime` cho công cụ AI.
- `/root/_Infra` cho ghi chú/cấu hình hạ tầng.
- `/root/_Backups` cho backup thủ công trước khi sửa.
- `/root/_Archive` cho project cũ không còn chạy.

Vùng cần cẩn trọng đặc biệt:
- `/root/.ssh`
- `/root/.codex`
- `/root/.agents`
- `/root/.env` hoặc file `.env` trong project
- Browser/Selenium profile folders
- Credential JSON files

Không tự di chuyển folder production cũ nếu chưa có yêu cầu rõ ràng và kế hoạch migrate trong `/root/_Second_AI_Brain/09_Ke_Hoach_Chuan_Hoa_Folder.md`.
""",
}

CORE_FILES = {
    "START_HERE.md": """# START HERE - AI làm việc trên VPS này

Đọc file này trước khi làm bất kỳ việc gì trên VPS.

## Quy trình nhanh

1. Xác định task thuộc nhóm nào: `Apps`, `Automation`, `Data`, `AI_Runtime`, hay `_Infra`.
2. Đọc `/root/_Second_AI_Brain/01_Ban_Do_VPS.md`.
3. Đọc `/root/_Second_AI_Brain/02_Danh_Sach_Project.md`.
4. Nếu sửa production, đọc `/root/_Second_AI_Brain/checklists/truoc_khi_sua_production.md`.
5. Nếu có project note trong `/root/_Second_AI_Brain/projects/`, đọc trước khi sửa.
6. Sau thay đổi quan trọng, ghi vào `/root/_Second_AI_Brain/06_Nhat_Ky_Thay_Doi.md`.

## Nguyên tắc vàng

- Không làm lộ secret, token, cookie, mật khẩu, private key.
- Không xóa dữ liệu/folder production nếu chưa được yêu cầu rõ.
- Không tự ý gửi tin nhắn/bài đăng thật từ automation social.
- Không sửa `.env`, credential, browser profile nếu task không yêu cầu.
- Project có `AGENTS.md` riêng thì đọc file đó trước khi sửa.
""",
    "README.md": """# Second AI Brain VPS

Bộ não vận hành VPS cho AI/Codex: bản đồ folder, registry project, dịch vụ đang chạy, checklist an toàn và nhật ký thay đổi.

Bắt đầu tại `START_HERE.md`.
""",
    "00_overview.md": """# 00 - Tổng quan VPS

Cập nhật thông tin tổng quan, mục đích VPS, nguyên tắc vận hành và các liên hệ nội bộ nếu cần. Không ghi secret.
""",
    "01_Ban_Do_VPS.md": """# 01 - Bản đồ VPS

Cập nhật: {date} UTC.

| Nhóm | Đường dẫn | Dùng cho |
|---|---|---|
| Bộ não AI | `/root/_Second_AI_Brain` | Tài liệu vận hành, registry, checklist, lịch sử sửa |
| Apps | `/root/Apps` | Website, web app, N8N, video factory |
| Automation | `/root/Automation` | Bot, crawler, Selenium, social automation |
| Data | `/root/Data` | Dữ liệu, tài liệu, file đồng bộ |
| AI Runtime | `/root/AI_Runtime` | Công cụ AI và workspace an toàn |
| Infra | `/root/_Infra` | Nginx, cron, Docker notes, system notes |
| Backup | `/root/_Backups` | Backup trước khi sửa production |
| Archive | `/root/_Archive` | Project cũ/ngưng chạy |
""",
    "02_Danh_Sach_Project.md": """# 02 - Danh sách project / registry

Cập nhật: {date} UTC.

| Nhóm | Project | Đường dẫn hiện tại | Trạng thái | Ghi chú |
|---|---|---|---|---|
| Apps | TODO | `/root/Apps/...` | unknown | Bổ sung sau khi khảo sát |
""",
    "03_Dich_Vu_Dang_Chay.md": "# 03 - Dịch vụ đang chạy\n\nGhi Docker, systemd, cron, nginx domain và port. Không ghi token/secret.\n",
    "04_Lenh_Van_Hanh.md": "# 04 - Lệnh vận hành\n\nGhi các lệnh an toàn để kiểm tra, start/stop/restart, backup và debug. Không ghi secret.\n",
    "05_Canh_Bao_Bao_Mat.md": "# 05 - Cảnh báo bảo mật\n\n- Không in `.env`, credential JSON, cookie, private key.\n- Không commit browser profile, log nhạy cảm, token hoặc secret.\n",
    "06_Nhat_Ky_Thay_Doi.md": "# 06 - Nhật ký thay đổi\n\n## {timestamp} - Tạo Second AI Brain skeleton\n\n- Đã tạo cấu trúc tài liệu vận hành VPS.\n",
    "07_Su_Co_Da_Gap.md": "# 07 - Sự cố đã gặp\n\nGhi sự cố, nguyên nhân, cách xử lý và cách tránh lặp lại.\n",
    "08_Quy_Uoc_Lam_Viec.md": "# 08 - Quy ước làm việc\n\nGhi quy ước đặt tên, backup, kiểm thử, triển khai và cập nhật tài liệu.\n",
    "09_Ke_Hoach_Chuan_Hoa_Folder.md": "# 09 - Kế hoạch chuẩn hóa folder\n\nKhông tự di chuyển production nếu chưa có kế hoạch và xác nhận rõ.\n",
    "10_ai_workflow.md": "# 10 - AI workflow\n\nQuy trình AI/Codex đọc tài liệu, kiểm tra project, backup, sửa, test và cập nhật nhật ký.\n",
}

EXTRA_FILES = {
    "checklists/truoc_khi_sua_production.md": """# Checklist - Trước khi sửa production

- [ ] Đã xác định đúng project/folder.
- [ ] Đã đọc `/root/_Second_AI_Brain/START_HERE.md`.
- [ ] Đã đọc file project note liên quan nếu có.
- [ ] Đã đọc `AGENTS.md` trong project nếu có.
- [ ] Đã biết file nào chứa secret và không in/lộ nội dung secret.
- [ ] Đã backup file cấu hình quan trọng nếu chuẩn bị sửa.
- [ ] Đã xác định lệnh kiểm tra sau khi sửa.
- [ ] Không chạy lệnh gửi tin/đăng bài thật nếu chưa được yêu cầu.
- [ ] Không di chuyển folder production nếu chưa có kế hoạch migrate.
""",
    "services/cron.md": "# Cron\n\nGhi snapshot cron đã khử secret và lịch chạy quan trọng.\n",
    "services/docker.md": "# Docker\n\nGhi container, compose project, port, volume quan trọng. Không ghi secret.\n",
    "services/nginx.md": "# Nginx\n\nGhi domain, config path, upstream/port. Không ghi private key.\n",
    "templates/project_profile.md": """# Project: TEN_PROJECT

## Tổng quan

- Đường dẫn: `/root/...`
- Nhóm: Apps/Automation/Data/AI_Runtime/Infra
- Trạng thái: production/dev/automation/archive/unknown
- Chủ đích:

## Thành phần chính

- Runtime:
- Entry point:
- Config nhạy cảm: chỉ ghi tên file, không ghi giá trị thật.
- Dữ liệu quan trọng:

## Lệnh vận hành

```bash
# Lệnh an toàn, không kèm token/secret
```

## Lưu ý an toàn

- File cần backup trước khi sửa:
- Việc không làm nếu chưa xác nhận:
""",
}

ROOT_DIRS = ["Apps", "Automation", "Data", "AI_Runtime", "_Infra", "_Backups", "_Archive"]
BRAIN_DIRS = ["checklists", "projects", "services", "templates", "inventories", "backups"]


def write_file(path: Path, content: str, *, force: bool, dry_run: bool) -> str:
    if path.exists() and not force:
        return "skip"
    if not dry_run:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    return "write" if not path.exists() or force else "write"


def main() -> None:
    parser = argparse.ArgumentParser(description="Create /root/_Second_AI_Brain skeleton safely.")
    parser.add_argument("--root", default="/root", help="VPS root directory, default: /root")
    parser.add_argument("--force", action="store_true", help="Overwrite existing template files")
    parser.add_argument("--dry-run", action="store_true", help="Print actions without writing")
    args = parser.parse_args()

    root = Path(args.root).expanduser().resolve()
    brain = root / "_Second_AI_Brain"
    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    for dirname in ROOT_DIRS:
        path = root / dirname
        print(f"mkdir {'DRY ' if args.dry_run else ''}{path}")
        if not args.dry_run:
            path.mkdir(parents=True, exist_ok=True)

    for dirname in BRAIN_DIRS:
        path = brain / dirname
        print(f"mkdir {'DRY ' if args.dry_run else ''}{path}")
        if not args.dry_run:
            path.mkdir(parents=True, exist_ok=True)

    for relative_path, template in ROOT_FILES.items():
        content = template.format(date=date, timestamp=timestamp)
        path = root / relative_path
        action = write_file(path, content, force=args.force, dry_run=args.dry_run)
        print(f"{action}: {path}")

    all_files = {**CORE_FILES, **EXTRA_FILES}
    for relative_path, template in all_files.items():
        content = template.format(date=date, timestamp=timestamp)
        path = brain / relative_path
        action = write_file(path, content, force=args.force, dry_run=args.dry_run)
        print(f"{action}: {path}")


if __name__ == "__main__":
    main()
