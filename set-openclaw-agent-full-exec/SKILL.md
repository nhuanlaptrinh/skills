---
name: set-openclaw-agent-full-exec
description: Bật, kiểm tra hoặc sửa Full Exec không hỏi duyệt cho một agent OpenClaw trên VPS Linux hoặc member VPS Docker. Use khi cần đặt phần Tools Exec của một agent thành Host gateway, Mode full, Security full, Ask off và tắt Strict inline eval; áp dụng lại cho main hoặc agent khác; kiểm tra vì Control UI chỉ lưu một phần; hoặc rollback cấu hình Exec mà không sửa token, model, bot, binding, workspace hay toolsBySender.
---

# Set OpenClaw Agent Full Exec

## Trạng thái đích

Script `scripts/set_openclaw_agent_full_exec.sh` đặt đúng:

```text
Host: gateway
Mode: full
Security: full
Ask: off
Strict inline eval: false
```

Ba giá trị Host/Mode/Strict nằm trong `openclaw.json`. Security/Ask và fallback tương ứng nằm trong `exec-approvals.json`. Giữ nguyên allowlist cũ và mọi policy `toolsBySender`.

## Quy trình bắt buộc

1. Đọc tài liệu Second AI Brain, project note, `AGENTS.md` gần project và checklist production.
2. Xác định đúng member/OpenClaw root và agent ID. Không đoán agent khi có nhiều agent.
   OpenClaw 2026.8 lưu approval trong `state/openclaw.sqlite` (bảng
   `exec_approvals_config`); helper `scripts/native_approvals.py` được đồng bộ
   cùng skill để đọc/backup/restore backend này. Bản OpenClaw cũ dùng
   `exec-approvals.json` và vẫn được hỗ trợ.
3. Chạy dry-run:

```bash
bash scripts/set_openclaw_agent_full_exec.sh \
  --member <member> \
  --agent <agent-id> \
  --dry-run
```

4. Áp dụng:

```bash
bash scripts/set_openclaw_agent_full_exec.sh \
  --member <member> \
  --agent <agent-id> \
  --apply
```

5. Kiểm tra lại độc lập:

```bash
bash scripts/set_openclaw_agent_full_exec.sh \
  --member <member> \
  --agent <agent-id> \
  --check
```

6. Với production, cập nhật project note và `/root/_Second_AI_Brain/06_Nhat_Ky_Thay_Doi.md`; không ghi secret.

## Chọn target

Member VPS chuẩn:

```bash
--member nguyenpho --agent main
```

Shortcut này dùng:

- OpenClaw root host: `/root/Apps/member_vps/docker-users/data/<member>/root/.openclaw`
- Container: `user-<member>`
- Runtime HOME trong container: `/root`

OpenClaw root tùy chọn:

```bash
bash scripts/set_openclaw_agent_full_exec.sh \
  --openclaw-root /duong/dan/.openclaw \
  --container user-example \
  --runtime-home /root \
  --agent main \
  --dry-run
```

- Bỏ `--container` cho OpenClaw chạy trực tiếp trên host.
- Dùng `--no-restart` khi chỉ muốn ghi file rồi tự restart sau maintenance window.
- Dùng `--backup-dir /root/_Backups/thu-muc-rieng` để đổi thư mục backup gốc.

## Script thực hiện

1. Xác nhận agent tồn tại đúng một lần và `openclaw.json` hợp lệ; approval
   được đọc từ native SQLite hoặc legacy JSON tùy backend đang hoạt động.
2. Chỉ tạo candidate cho `agents.entries.<agent-id>.tools.exec` (hoặc legacy
   `agents.list[].tools.exec`) của agent đích và `agents[agent-id]` trong approval policy.
3. Dry-run chỉ in các field Exec an toàn; không in toàn bộ config, token hoặc socket credential.
4. Apply tạo backup root-only, ghi config atomic và cập nhật approval native qua
   `openclaw approvals set --stdin --json` (không tạo file legacy dai dẳng); với
   backend cũ vẫn ghi JSON atomic và giữ owner/mode.
5. Chạy `openclaw config validate`; tự rollback file nếu validation lỗi.
6. Với member VPS, chỉ signal riêng `openclaw-gateway` khi parent là Supervisor; không restart/recreate container.
7. Kiểm tra runtime Gateway approval, connectivity và channel probe mà không gửi tin nhắn thật.

## Input và output

Input:

- `openclaw.json` có agent đích.
- `exec-approvals.json`; nếu chưa có, script tạo cấu trúc tối thiểu quyền `0600`.
- Một action: `--dry-run`, `--apply` hoặc `--check`.

Output:

- Config Exec và approval policy khớp đủ năm giá trị.
- Backup timestamped chứa config cùng SQLite snapshot (hoặc legacy JSON) trước
  thay đổi và checksum; metadata ghi backend/locator đã khử secret.
- Báo cáo validation/restart đã khử secret.

Backup mặc định:

```text
/root/_Backups/openclaw-agent-full-exec/<target>/<timestamp>/
```

## Rerun và rollback

- Script idempotent: apply lại khi đã đúng không ghi file hoặc restart Gateway.
- Rollback bằng config và snapshot approval trong backup gần nhất, giữ nguyên
  socket token/native state, validate rồi respawn riêng Gateway.
- Nếu restart lỗi sau khi validation đạt, không restart cả container; kiểm tra Supervisor/Gateway và dùng backup để rollback có kiểm soát.

## Quy tắc an toàn

- Đây là policy quyền cao: agent/sender có tool Exec sẽ chạy lệnh trên Gateway mà không hỏi duyệt.
- Không tự xóa `toolsBySender`, sender policy, owner policy hoặc deny list. Sender đang bị deny runtime vẫn không được mở quyền bởi skill này.
- Không sửa `tools.profile`, token, API key, model, channel, binding, workspace, session, `.env` hoặc credential.
- Không in/copy toàn bộ `openclaw.json` hay `exec-approvals.json`.
- Không gửi tin Telegram/Zalo thật để kiểm thử.
- Không dùng cho agent/user không được chủ VPS cho phép quyền thực thi không duyệt.
