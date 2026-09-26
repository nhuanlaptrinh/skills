---
name: di-chuyen-tro-ly-openclaw-vps-moi
description: Đóng gói bản sao lưu sạch (Clean Export) và khôi phục Trợ lý AI OpenClaw sang VPS mới, giữ nguyên 100% phần đào tạo (Identity, Soul, Memory, User, Rules, Skills, Scripts, Supervisor, Nginx) và loại bỏ hoàn toàn dữ liệu chat cũ, sqlite cache và media rác.
---

# Di chuyển Trợ lý AI OpenClaw sang VPS Mới (Clean Migration)

Sử dụng skill này khi cần chuyển một Trợ lý OpenClaw (từ Member VPS Docker hoặc Standalone host) sang một VPS mới mà **không muốn kéo theo các dữ liệu chat cũ, database sqlite phình to, hoặc các tệp media/test rác**, đồng thời **giữ nguyên 100% nhân cách, trí nhớ dài hạn, quy tắc làm việc và các công cụ/skills đã huấn luyện**.

---

## 1. Thành phần kịch bản (Scripts)

- **Script đóng gói trên VPS cũ:**
  `/root/.agents/skills/di-chuyen-tro-ly-openclaw-vps-moi/scripts/export_clean_assistant.sh`
- **Script khôi phục trên VPS mới:**
  `/root/.agents/skills/di-chuyen-tro-ly-openclaw-vps-moi/scripts/restore_clean_assistant.sh`

---

## 2. Quy trình đóng gói trên VPS cũ (Export)

### A. Kiểm tra trước (Dry-run)
```bash
/root/.agents/skills/di-chuyen-tro-ly-openclaw-vps-moi/scripts/export_clean_assistant.sh \
  --source /root/Apps/member_vps/docker-users/data/<ten-member> \
  --container user-<ten-member> \
  --dry-run
```

### B. Chạy thật (Apply)
```bash
/root/.agents/skills/di-chuyen-tro-ly-openclaw-vps-moi/scripts/export_clean_assistant.sh \
  --source /root/Apps/member_vps/docker-users/data/<ten-member> \
  --container user-<ten-member> \
  --apply
```
*Kết quả xuất ra file nén tại `/root/_Backups/<ten-member>_clean_export_<timestamp>.tar.gz` (dung lượng thông thường chỉ 15–25 MB).*

---

## 3. Chuyển file sang VPS mới

Từ máy tính hoặc VPS cũ, dùng `scp` chuyển file:
```bash
scp /root/_Backups/<ten-member>_clean_export_<timestamp>.tar.gz root@<IP_VPS_MOI>:/root/
```

---

## 4. Quy trình khôi phục trên VPS mới (Restore)

### A. Tùy chọn 1: Cài đặt tự động toàn bộ (kèm dependencies)
Nếu VPS mới là VPS trắng Ubuntu chưa cài đặt OpenClaw:
```bash
/root/.agents/skills/di-chuyen-tro-ly-openclaw-vps-moi/scripts/restore_clean_assistant.sh \
  --tarball /root/<ten-member>_clean_export_<timestamp>.tar.gz \
  --target-home /root \
  --install-deps \
  --apply
```

### B. Tùy chọn 2: Khôi phục vào môi trường đã có sẵn Node/OpenClaw
```bash
/root/.agents/skills/di-chuyen-tro-ly-openclaw-vps-moi/scripts/restore_clean_assistant.sh \
  --tarball /root/<ten-member>_clean_export_<timestamp>.tar.gz \
  --target-home /root \
  --apply
```

---

## 5. Danh mục các thành phần được giữ lại & loại bỏ

### Giữ lại (100% Training & Config):
1. **Phần đào tạo & Nhân cách:**
   - `IDENTITY.md` (Tên trợ lý, vibe, tính cách)
   - `SOUL.md` (Triết lý phục vụ, ranh giới, thái độ)
   - `USER.md` (Thông tin người vận hành, quy tắc nhóm riêng)
   - `MEMORY.md` (Bộ nhớ dài hạn: bảng giá, khóa học, chính sách, hướng dẫn)
   - `memory/*.md` (Nhật ký học hỏi hằng ngày)
   - `AGENTS.md` (Quy tắc hành vi, heartbeat, rules gửi file Zalo/Telegram)
   - `TOOLS.md` (Ghi chú cấu hình thiết bị/tool)
   - `profiles/*.md` (Hồ sơ huấn luyện doanh nghiệp & cá nhân)
   - Secondary Agent: `workspace-facebook-anvi/` (toàn bộ tri thức cho bot Fanpage)
2. **Skills & Scripts tự xây dựng:**
   - `workspace/skills/` (Audio Whisper/Edge-TTS, Zalo buffer, Zalo reminder...)
   - `workspace/scripts/` (Scripts vẽ poster, banner, infographic...)
   - `workshop-skills/` và `proposals/`
   - `.local/bin/gan-domain` và `cloudflared`
3. **Cấu hình hệ thống:**
   - `openclaw.json` (Agents, model 9Router, channels Telegram, Zalo)
   - Supervisor: `member-vps.conf` và `facebook-fanpage-auto-reply.conf`
   - Nginx: `openclaw-nginx.conf`

### Loại bỏ (Dữ liệu rác):
- Session chat cũ trong `.openclaw/agents/*/sessions/`
- Database sqlite chat runtime `openclaw-agent.sqlite*`
- Ảnh chụp màn hình test, video/audio render thử, tệp excel tạm
- Các thư mục tạm: `tmp/`, `output/`, `outputs/`, `uploads/`, `outbox/`

---

## 6. Kiểm tra nghiệm thu sau khi khôi phục

1. **Kiểm tra tiến trình:**
   ```bash
   supervisorctl status
   ```
   Đảm bảo `openclaw-gateway` và `nginx` ở trạng thái `RUNNING`.

2. **Kiểm tra Telegram:**
   - Nhắn tin trực tiếp tới bot Telegram: Bot phải trả lời với đúng tên và nhân cách đã đào tạo.

3. **Kiểm tra Zalo Personal:**
   - Mở trình duyệt vào `http://<IP_VPS>/openclaw-qr.png`.
   - Dùng Zalo trên điện thoại quét mã QR để kích hoạt lại phiên đăng nhập.

---

## 7. Quy tắc an toàn

- Không ghi trực tiếp API key, secret token hay mật khẩu vào file skill này.
- Khi chia sẻ file nén export, lưu ý file `openclaw.json` bên trong có thể chứa botToken Telegram và 9Router key hiện tại của trợ lý. Cần bảo mật file `.tar.gz`.
