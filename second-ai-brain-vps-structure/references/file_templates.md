# Second AI Brain File Templates

Use these templates for `/root/AGENTS.md` and `/root/_Second_AI_Brain`. Replace placeholders with sanitized, VPS-specific information.

## /root/AGENTS.md

```markdown
# Quy tắc làm việc trên VPS này

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
```

## START_HERE.md

```markdown
# START HERE - AI làm việc trên VPS này

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
```

## 01_Ban_Do_VPS.md

```markdown
# 01 - Bản đồ VPS

Cập nhật: YYYY-MM-DD UTC.

## Nhóm chuẩn

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

## Vùng cần cẩn trọng

- `/root/.ssh`
- `/root/.codex`
- `/root/.agents`
- `/root/.env` hoặc file `.env` trong project
- Browser/Selenium profile folders
```

## 02_Danh_Sach_Project.md

```markdown
# 02 - Danh sách project / registry

Cập nhật: YYYY-MM-DD UTC.

| Nhóm | Project | Đường dẫn hiện tại | Trạng thái | Ghi chú |
|---|---|---|---|---|
| Apps | Ten project | `/root/Apps/example` | production/dev/unknown | Ghi chú ngắn |
| Automation | Ten bot | `/root/Automation/example` | automation | Ghi chú ngắn |
```

## checklists/truoc_khi_sua_production.md

```markdown
# Checklist - Trước khi sửa production

- [ ] Đã xác định đúng project/folder.
- [ ] Đã đọc `/root/_Second_AI_Brain/START_HERE.md`.
- [ ] Đã đọc file project note liên quan nếu có.
- [ ] Đã đọc `AGENTS.md` trong project nếu có.
- [ ] Đã biết file nào chứa secret và không in/lộ nội dung secret.
- [ ] Đã backup file cấu hình quan trọng nếu chuẩn bị sửa.
- [ ] Đã xác định lệnh kiểm tra sau khi sửa.
- [ ] Không chạy lệnh gửi tin/đăng bài thật nếu chưa được yêu cầu.
- [ ] Không di chuyển folder production nếu chưa có kế hoạch migrate.
```

## templates/project_profile.md

```markdown
# Project: TEN_PROJECT

## Tổng quan

- Đường dẫn: `/root/...`
- Nhóm: Apps/Automation/Data/AI_Runtime/Infra
- Trạng thái: production/dev/automation/archive/unknown
- Chủ đích: Mô tả ngắn.

## Thành phần chính

- Runtime:
- Entry point:
- Config nhạy cảm: Không ghi giá trị thật, chỉ ghi tên file như `.env`.
- Dữ liệu quan trọng:

## Lệnh vận hành

```bash
# Chỉ ghi lệnh an toàn, không kèm token/secret
```

## Lưu ý an toàn

- Những việc không được làm nếu chưa xác nhận.
- File cần backup trước khi sửa.
```

## 06_Nhat_Ky_Thay_Doi.md

```markdown
# 06 - Nhật ký thay đổi

## YYYY-MM-DD HH:MM UTC - Tiêu đề thay đổi

- Đã làm:
- Đường dẫn liên quan:
- Kiểm tra sau thay đổi:
- Ghi chú an toàn:
```
