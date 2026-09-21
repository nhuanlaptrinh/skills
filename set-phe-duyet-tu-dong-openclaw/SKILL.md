---
name: set-phe-duyet-tu-dong-openclaw
description: Cấu hình tự động phê duyệt (không hỏi duyệt Telegram/Zalo, "ask":"off", "mode":"full") cho agent OpenClaw trên VPS Linux hoặc Member VPS Docker, kèm tùy chọn cấp toàn quyền chủ sở hữu / đồng chủ sở hữu (co-owner) qua Telegram và Zalo Personal. Dùng khi người dùng hoặc bot không muốn phải bấm duyệt từng lệnh terminal/tool (extract pdf, txt2docx, python script, bash...).
---

# Set Phê Duyệt Tự Động OpenClaw (Full Exec & Auto-Approval)

Dùng skill này khi:
- Người dùng không muốn mỗi lần bot OpenClaw chạy lệnh terminal/script (như trích xuất PDF, tạo Word docx, chạy code Python...) lại phải bấm nút xác nhận **"Allowed once"** trên Telegram/Zalo.
- Cần cấp toàn quyền đồng chủ sở hữu (co-owner) cho Telegram ID hoặc Zalo ID và tự động duyệt lệnh không cần hỏi ("ask": "off").
- Cần cho phép ID Telegram hoặc Zalo nói chuyện riêng (DM) và ra lệnh toàn quyền cho bot.

## Trạng thái đích sau khi chạy

1. **Trong `openclaw.json` (agent `main`)**:
   ```json
   "tools": {
     "exec": {
       "host": "gateway",
       "mode": "full",
       "strictInlineEval": false
     }
   }
   ```
2. **Trong chính sách phê duyệt SQLite native (`state/openclaw.sqlite` hoặc legacy `exec-approvals.json`)**:
   ```json
   "agents": {
     "main": {
       "security": "full",
       "ask": "off",
       "askFallback": "full",
       "autoAllowSkills": true
     }
   }
   ```
3. **Khi kèm tùy chọn Telegram ID đồng chủ sở hữu (`--telegram-id <ID>`)**:
   - Thêm vào `commands.ownerAllowFrom: ["telegram:<ID>"]`
   - Thêm vào `approvals.exec.targets` và `approvals.plugin.targets`
   - Thêm vào `tools.elevated.allowFrom.telegram`
   - Cấp full profile trong `toolsBySender: {"channel:telegram:<ID>": {}}`
   - Thêm vào `allowFrom` và `groupAllowFrom` của tài khoản Telegram
4. **Khi kèm tùy chọn Zalo ID đồng chủ sở hữu (`--zalo-id <ID>`)**:
   - Thêm vào `channels.zalouser.allowFrom: ["<ID>"]` (cho phép nói chuyện riêng DM)
   - Thêm vào `channels.zalouser.groupAllowFrom: ["<ID>"]` (nếu có cấu hình groupAllowFrom)
   - Thêm vào `commands.ownerAllowFrom: ["zalouser:<ID>"]`
   - Thêm vào `tools.elevated.allowFrom.zalouser: ["<ID>"]`
   - Cấp full profile trong `toolsBySender: {"channel:zalouser:<ID>": {}}`

---

## Cách sử dụng

Script thực thi nằm tại:
`/root/.agents/skills/set-phe-duyet-tu-dong-openclaw/scripts/set_auto_approval.py`

### 1. Cho Member VPS Docker

Script tự động phát hiện đường dẫn runtime:
- Dạng legacy home: `/root/Apps/member_vps/docker-users/data/<member>/.openclaw` (HOME: `/home/<member>`)
- Dạng root home: `/root/Apps/member_vps/docker-users/data/<member>/root/.openclaw` (HOME: `/root`)

- **Kiểm tra trạng thái (Check)**:
  ```bash
  python3 /root/.agents/skills/set-phe-duyet-tu-dong-openclaw/scripts/set_auto_approval.py \
    --member <member> \
    --zalo-id <ZALO_ID> \
    --check
  ```

- **Chạy thử trước (Dry-run)**:
  ```bash
  python3 /root/.agents/skills/set-phe-duyet-tu-dong-openclaw/scripts/set_auto_approval.py \
    --member <member> \
    --zalo-id <ZALO_ID> \
    --dry-run
  ```

- **Áp dụng chính thức (Apply)**:
  ```bash
  python3 /root/.agents/skills/set-phe-duyet-tu-dong-openclaw/scripts/set_auto_approval.py \
    --member <member> \
    --zalo-id <ZALO_ID> \
    --apply
  ```
  *(Có thể truyền cả `--telegram-id <TELEGRAM_ID>` và `--zalo-id <ZALO_ID>` đồng thời nếu muốn cấp cho cả hai nền tảng).*

---

### 2. Cho Standalone VPS Linux (Host chính)

- **Chạy kiểm tra**:
  ```bash
  python3 /root/.agents/skills/set-phe-duyet-tu-dong-openclaw/scripts/set_auto_approval.py \
    --openclaw-root /root/.openclaw \
    --check
  ```

- **Áp dụng**:
  ```bash
  python3 /root/.agents/skills/set-phe-duyet-tu-dong-openclaw/scripts/set_auto_approval.py \
    --openclaw-root /root/.openclaw \
    --telegram-id <TELEGRAM_ID> \
    --zalo-id <ZALO_ID> \
    --apply
  ```

---

## Input và Output

- **Input**:
  - File cấu hình `openclaw.json` của runtime OpenClaw.
  - Cơ sở dữ liệu native approvals `state/openclaw.sqlite` (hoặc legacy `exec-approvals.json`).
  - Tùy chọn `--telegram-id` và/hoặc `--zalo-id` để đồng bộ toàn quyền đồng chủ sở hữu.
- **Output**:
  - Tự động sao lưu snapshot trước khi sửa vào `/root/_Backups/openclaw-auto-approval/<member_or_host>/<timestamp>/`.
  - Cập nhật an toàn atomic `openclaw.json` và SQLite native table `exec_approvals_config`.
  - Tự động chạy `openclaw config validate` để kiểm tra tính hợp lệ (tự rollback nếu lỗi).
  - Khởi động lại `openclaw-gateway` dưới Supervisor (không kill cả container VPS).

---

## An toàn & Rollback

- **Quyền bảo vệ**: Chỉ những Telegram/Zalo ID nằm trong `allowFrom` / `commands.ownerAllowFrom` mới được phép ra lệnh cho bot. Không mở quyền cho người lạ.
- **Rollback**: Nếu cần khôi phục lại cấu hình trước khi sửa, sao chép file từ thư mục backup tương ứng:
  ```bash
  cp /root/_Backups/openclaw-auto-approval/<target>/<timestamp>/openclaw.json /path/to/.openclaw/openclaw.json
  cp /root/_Backups/openclaw-auto-approval/<target>/<timestamp>/openclaw.sqlite /path/to/.openclaw/state/openclaw.sqlite
  # Restart gateway
  ```
