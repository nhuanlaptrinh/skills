---
name: old-data-cleanup
description: Rà soát và xóa từng đợt video, audio, PDF, Word, Excel và backup cũ trên VPS sau khi chủ hệ thống yêu cầu dọn dung lượng; không dọn hệ thống, database production hoặc thư viện tri thức.
---

# Dọn dữ liệu cũ theo manifest

## Phạm vi

Script: `/root/Automation/maintenance/old_data_cleanup.py`, chỉ Python standard library và Docker/systemd đang sẵn có trên VPS. Đọc Second AI Brain và AGENTS.md liên quan trước khi xóa. Đây là thao tác thủ công được người dùng cho phép, không phải lịch dọn tự động.

Nhóm `backups` gồm file trong `/root/_Backups`, bản runtime cũ `/root/AI_Runtime/9router_backup`, archive backup trong `/root/Data` và các thư mục backup OpenClaw. Nhóm `host-media` gồm media/workspace OpenClaw chính và thư mục tài liệu cá nhân. Nhóm `member-media` chỉ gồm media/workspace OpenClaw dưới bind data member. Nhóm `video-data` gồm input/output/renders/snapshots của video factory và workspace pipeline video cũ.

## Dry-run

Tạo một thư mục báo cáo riêng tư mới dưới `/root/_Infra/maintenance/`, rồi tạo plan cho từng nhóm:

```bash
python3 /root/Automation/maintenance/old_data_cleanup.py --days 7 --group backups --plan /root/_Infra/maintenance/NEW_RUN/backups.json
```

Thay `backups` bằng `host-media`, `member-media` hoặc `video-data` để rà soát nhóm khác. Không dùng lại tên plan cũ: script từ chối ghi đè. Dry-run chỉ stat metadata, không đọc nội dung tài liệu. Có thể dùng `--inventory PATH` nếu inventory có schema `cutoff_ns` và `files` với metadata tương ứng.

## Chạy thật

Sau khi xem manifest, đọc hướng dẫn riêng của thư mục được chọn, xác minh không nằm trong thư mục đồng bộ và không phải tài sản được website/queue/composition hiện tại tham chiếu, chạy lần lượt:

```bash
ionice -c 3 nice -n 10 python3 /root/Automation/maintenance/old_data_cleanup.py --apply-plan /root/_Infra/maintenance/NEW_RUN/backups.json
```

Chỉ xóa file trong manifest có cả mtime và ctime cũ hơn mốc đủ bảy ngày. Recheck device/inode/size/timestamps ngay trước unlink; bỏ qua file bị sửa, hardlink, file đang mở hoặc memory-mapped, thư mục có marker `.stfolder`; không theo symlink. Mỗi 200 file kiểm tra lại service/container so với đầu lượt và dừng khi phát hiện dịch vụ đang chạy bị dừng hoặc container mới unhealthy. Không restart/stop dịch vụ. Kiểm tra HTTP và đối chiếu trạng thái với baseline trước/sau toàn đợt bằng thao tác riêng; script không tự kiểm tra HTTP hay queue/composition references.

Nếu một service đã được chứng minh đang lỗi trước đợt dọn và không liên quan thao tác này, có thể ghi rõ service đó bằng một hoặc nhiều cờ `--ignore-service NAME.service`; không dùng cờ này để che lỗi mới hoặc bỏ qua Docker/container.

## Input/output và rerun

- Input: group, số ngày tối thiểu 7, manifest hoặc inventory đã duyệt.
- Output: plan JSON, `*.deleted.jsonl` ghi intent và kết quả từng file, `*.result.json` tổng số byte/file và skip; quyền file 0600.
- Báo cáo đợt đầu: `/root/_Infra/maintenance/cleanup-20261015T082609Z/`.
- Không ghi Google Sheet/API, không upload, không gửi tin và không render/rerender.
- Rerun: tạo plan mới và kiểm tra lại; không tái dùng tên log/manifest cũ. Xóa thật không có rollback nội dung; không tạo bản backup dữ liệu sắp xóa vì mục đích giải phóng đĩa.

## An toàn

Giữ nguyên credential/.env/private key, Chrome/Selenium profile, node_modules/venv đang dùng, source code `.mts`/`.ts`, cấu hình và database production, Second Brain, báo cáo tài chính, kiến thức/reference/template/assets/model dùng chung. Snapshot backup cũ có thể chứa bản sao package/code/database và được xóa theo yêu cầu backup; không xóa plugin source dưới `.tmp/plugins` hoặc Git metadata. Không xóa folder, Docker image/volume/container, swap, log hệ thống, session database đang chạy, cron/nginx/Compose. Không lan thao tác xóa vào thư mục đồng bộ vì có thể xóa từ xa. Lưu báo cáo riêng tư chỉ metadata, không đọc/in secret. Nếu phải xem journal bot, redact trước khi xuất vì exception xác thực có thể chứa credential. Quét skill không chứa secret và cập nhật nhật ký Second AI Brain sau thao tác.
