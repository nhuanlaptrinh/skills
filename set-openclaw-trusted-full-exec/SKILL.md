---
name: set-openclaw-trusted-full-exec
description: Bật, kiểm tra hoặc sửa Full Exec không hỏi duyệt cho toàn bộ agent OpenClaw, đồng thời khóa Telegram group để chỉ sender đã được phép DM, pairing hoặc owner mới dùng được bot. Use khi cần áp dụng host gateway, mode/security full, ask off, askFallback full, strict inline eval false cho nhiều agent; đồng bộ trusted sender giữa DM và group; tránh wildcard sender; hoặc kiểm tra/khôi phục policy trên VPS Linux chính và member VPS Docker.
---

# Set OpenClaw Trusted Full Exec

## Trạng thái đích

Cho mọi agent trong runtime:

```text
Host: gateway
Mode: full
Security: full
Ask: off
Ask fallback: full
Strict inline eval: false
```

Cho mỗi Telegram account:

- Giữ DM ở `pairing` và ghi rõ tập trusted sender vào account `allowFrom`.
- Tập trusted sender là effective DM allowFrom hiện có, pairing store của account và Telegram owner; loại wildcard sender `*`.
- Đặt `groupPolicy=allowlist`, đồng bộ tập trusted sender vào `groupAllowFrom`, `groups["*"].allowFrom`, mọi group cụ thể và topic đã cấu hình.
- `groups["*"]` chỉ mở phạm vi group; `allowFrom` không bao giờ là wildcard.
- Pairing mới sau này phải rerun skill để được đồng bộ sang group.

## Quy trình bắt buộc

1. Đọc Second AI Brain, project note, `AGENTS.md` gần runtime và checklist production.
2. Xác định đúng OpenClaw root và cơ chế chạy Gateway; không đoán member/container.
3. Chạy dry-run:

```bash
bash scripts/set_openclaw_trusted_full_exec.sh \
  --openclaw-root /root/.openclaw \
  --dry-run
```

4. Chỉ apply khi chủ hệ thống đã cho phép quyền Full Exec cho toàn bộ trusted sender:

```bash
bash scripts/set_openclaw_trusted_full_exec.sh \
  --openclaw-root /root/.openclaw \
  --apply
```

5. Kiểm tra độc lập:

```bash
bash scripts/set_openclaw_trusted_full_exec.sh \
  --openclaw-root /root/.openclaw \
  --check
```

6. Với production, cập nhật project note và `/root/_Second_AI_Brain/06_Nhat_Ky_Thay_Doi.md`; không ghi token hoặc Telegram ID.

## Member VPS Docker

```bash
bash scripts/set_openclaw_trusted_full_exec.sh \
  --member <member> \
  --dry-run
```

Shortcut `--member` dùng:

- OpenClaw root host: `/root/Apps/member_vps/docker-users/data/<member>/root/.openclaw`
- Container: `user-<member>`
- Runtime home: `/root`

Dùng `--no-restart` chỉ khi có maintenance/restart riêng. Khi dùng tùy chọn này, runtime approval và channel connectivity không được coi là đã nghiệm thu.

## Script thực hiện

1. Xác nhận JSON hợp lệ, agent ID không trùng, account ID an toàn và trusted sender không rỗng.
2. Tạo candidate cho toàn bộ agent, Telegram account và host approval trong một transaction.
3. Dry-run chỉ in tên agent/account, số trusted sender và trạng thái thay đổi; không in sender ID, token hoặc toàn bộ config.
4. Apply tạo backup root-only, ghi file atomic, validate config, restart Gateway đúng một lần và kiểm tra runtime approval.
5. Check tạo lại candidate từ state hiện tại; pairing mới chưa đồng bộ sẽ làm check fail và yêu cầu rerun apply.
6. Probe Telegram chỉ yêu cầu account đang `enabled` và `configured` phải `running, connected`; account disabled hoặc chưa cấu hình token được báo là inactive và không làm fail connectivity.
7. Giữ nguyên token, model, binding, workspace, plugin approval, sender tool policy, allowlist lệnh cũ và cấu hình ngoài phạm vi.

Backup mặc định:

```text
/root/_Backups/openclaw-trusted-full-exec/<target>/<timestamp>/
```

## An toàn và rollback

- Đây là quyền rất cao: mọi trusted sender có thể khiến agent chạy lệnh trên Gateway mà không hỏi duyệt.
- Không dùng khi các trusted sender không cùng một ranh giới tin cậy. Tách Gateway/OS user nếu họ không tin cậy lẫn nhau.
- Không xóa `toolsBySender`, deny list hoặc owner policy; deny hiện có vẫn có thể chặn tool dù Exec là full/off.
- Không tự gửi tin Telegram thật. Channel probe chỉ kiểm tra Gateway/polling.
- Rollback bằng đúng cặp `openclaw.json` và `exec-approvals.json` trong một backup timestamp, validate rồi restart Gateway.
