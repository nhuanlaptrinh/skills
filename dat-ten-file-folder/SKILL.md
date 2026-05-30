---
name: dat-ten-file-folder
description: Chuẩn hóa tên file và folder theo quy tắc bắt đầu bằng số, dùng dấu gạch dưới, không dấu tiếng Việt, lowercase; dùng khi người dùng muốn đổi tên thư mục/file trong vault Obsidian hoặc cây tài liệu và cần cập nhật link Markdown/Obsidian liên quan.
---

# Dat Ten File Folder

## Quy Tac

Áp dụng cho file và folder nội dung:

- Tên luôn bắt đầu bằng số.
- Phần số và phần chữ ngăn bằng `_`.
- Chữ thường, không dấu tiếng Việt.
- Từ ngăn bằng `_`.
- Ký tự đặc biệt, khoảng trắng, dấu gạch ngang được đổi thành `_`.
- Giữ extension cuối của file, ví dụ `.md`, `.pdf`, `.json`, `.csv`, `.png`.
- Nếu tên chưa bắt đầu bằng số, thêm tiền tố `00_`.
- Giữ nguyên thư mục/file hệ thống ẩn như `.git`, `.obsidian`, `.stfolder`, dotfile.

Ví dụ:

```text
01_chuong_trinh_dao_tao -> 01_chuong_trinh_dao_tao
02_facebook_ca_nhan -> 02_facebook_ca_nhan
Template - Ý tưởng.md -> 00_template_y_tuong.md
2026-05-22 - Ghi chú.md -> 2026_05_22_ghi_chu.md
data -> 00_data hoặc 01_data nếu người dùng muốn đánh số thủ công
```

## Workflow

1. Chạy dry-run để xem trước số lượng đổi tên và conflict:

```bash
python3 /root/.agents/skills/dat-ten-file-folder/scripts/normalize_names.py /duong/dan/thu_muc --dry-run
```

2. Nếu không có conflict, chạy thật:

```bash
python3 /root/.agents/skills/dat-ten-file-folder/scripts/normalize_names.py /duong/dan/thu_muc
```

3. Kiểm tra lại:

```bash
python3 /root/.agents/skills/dat-ten-file-folder/scripts/normalize_names.py /duong/dan/thu_muc --check
```

## Khi La Obsidian Vault

Script sẽ cập nhật các link phổ biến trong Markdown:

- Wiki link: `[[folder/note|alias]]`, `[[note]]`
- Markdown link nội bộ: `[text](folder/file.md)`
- Code span chứa đường dẫn khớp file cũ: `` `folder/file.md` ``

Không sửa nội dung đọc tự nhiên, title, category, hoặc alias nếu không cần thiết.

## Luu Y

- Luôn xem dry-run trước khi chạy thật trên vault lớn.
- Nếu có conflict, dừng lại và xử lý tên trùng trước.
- Với repo git, đọc `git status --short` sau khi chạy để nắm thay đổi.
