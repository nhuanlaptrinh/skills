---
name: member-cache-guard
description: Dọn snapshot SQLite tạm của OpenClaw member và cảnh báo dung lượng host thấp.
---

# Member cache guard

## Khi dùng

Dùng khi OpenClaw báo `ENOSPC`, `database or disk is full`, hoặc cần kiểm tra cache snapshot tạm của member VPS.

## Script

- `/root/Automation/watchdog/member_cache_guard.sh`
- Chỉ áp dụng member lehuynhphong khi Supervisor FATAL/STOPPED và không có process Node/OpenClaw. Chỉ xử lý thư mục có tên `.cache/openclaw/openclaw-sqlite-readonly-*` cũ hơn 6 giờ.
- Không chạm session database, credential, workspace hay file cấu hình.

## Dry-run/kiểm tra

```bash
find /root/Apps/member_vps/docker-users/data -type d -path '*/.cache/openclaw/openclaw-sqlite-readonly-*' -mmin +360 -print
```

## Chạy thật

```bash
/root/Automation/watchdog/member_cache_guard.sh
```

Mặc định cảnh báo khi host còn dưới 30 GiB; đổi ngưỡng bằng `MIN_FREE_GIB=40` nếu cần.

## An toàn

Chỉ xóa snapshot tạm đã quá 6 giờ; mọi thay đổi được ghi tại `/root/Automation/watchdog/member_cache_guard.log`.
