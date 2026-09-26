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
*Kết quả xuất ra file nén sạch tại `/root/_Backups/<ten-member>_clean_export_<timestamp>.tar.gz` (dung lượng chỉ ~19 MB).*

---

## 3. Chuyển file sang VPS mới

Từ máy tính hoặc VPS cũ, dùng `scp` chuyển file:
```bash
scp /root/_Backups/<ten-member>_clean_export_<timestamp>.tar.gz root@<IP_VPS_MOI>:/root/
```

---

## 4. Quy trình khôi phục trên VPS mới (Restore)

### Trường hợp 1: VPS mới ĐÃ CÀI SẴN OpenClaw (Khuyên dùng - Phổ biến nhất)
Vì VPS mới đã có sẵn Node.js và OpenClaw, ta chỉ cần giải nén đè dữ liệu đào tạo và cài đặt những công cụ phụ trợ còn thiếu.

#### Cách A (Dùng script 1 lệnh duy nhất):
```bash
/root/restore_clean_assistant.sh \
  --tarball /root/anhlaptrinhthu_clean_export_20260926.tar.gz \
  --target-home /root \
  --send-zalo-qr <TELEGRAM_USER_ID> \
  --apply
```
*Script sẽ tự động: cài ffmpeg/libreoffice/rapidocr nếu chưa có, giải nén toàn bộ nhân cách & skills, sửa đường dẫn `/home/anhlaptrinh` -> `/root` trong `openclaw.json`, khởi động lại Gateway, và tự động tạo mã QR Zalo Personal gửi thẳng vào tin nhắn Telegram của chủ sở hữu.*

#### Cách B (Bung thủ công không cần script - 3 bước):
```bash
# 1. Giải nén vào thư mục tạm và copy vào thư mục OpenClaw của VPS mới:
mkdir -p /tmp/restore_bot
tar -xzf /root/anhlaptrinhthu_clean_export_20260926.tar.gz -C /tmp/restore_bot/
cp -a /tmp/restore_bot/home/. /root/
sed -i 's|/home/anhlaptrinh|/root|g' /root/.openclaw/openclaw.json
rm -rf /tmp/restore_bot

# 2. Cài đặt các thư viện phụ trợ còn thiếu (chỉ OCR và media tools):
apt update && apt install -y ffmpeg libreoffice
pip install rapidocr-onnxruntime onnxruntime opencv-python mutagen yt-dlp

# 3. Khởi động lại OpenClaw:
openclaw gateway restart
```

---

### Trường hợp 2: VPS mới là MÁY TRẮNG hoàn toàn (chưa có OpenClaw)
Nếu VPS mới chưa cài đặt Node, OpenClaw hay bất kỳ thư viện nào, chạy lệnh:
```bash
/root/restore_clean_assistant.sh \
  --tarball /root/<ten-member>_clean_export_<timestamp>.tar.gz \
  --target-home /root \
  --install-deps \
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
   # hoặc:
   openclaw status
   ```
   Đảm bảo `openclaw-gateway` ở trạng thái `RUNNING / Connected`.

2. **Kiểm tra Telegram:**
   - Nhắn tin trực tiếp tới bot Telegram: Bot phải trả lời với đúng tên và nhân cách đã đào tạo.

3. **Đăng nhập Zalo Personal bằng QR:**
   - **Cách 1 (Gửi thẳng vào Telegram Owner - Khuyên dùng, nhanh nhất):**
     ```bash
     node /root/.agents/skills/openclaw-zalo-qr-login/scripts/send_zalo_qr_to_telegram_owner.mjs \
       --target <TELEGRAM_USER_ID> \
       --apply
     ```
     *Script sẽ tự động sinh QR mới, đóng gói ảnh và gửi thẳng vào tin nhắn Telegram của chủ sở hữu. Chỉ cần mở điện thoại quét ảnh là xong.*
   - **Cách 2 (Mở ảnh qua Web URL):**
     Truy cập `http://<IP_VPS>/openclaw-qr.png` (hoặc cổng web của Member VPS, ví dụ `http://<IP_VPS>:3025/openclaw-qr.png`).
   - **Cách 3 (Chạy lệnh terminal trực tiếp):**
     ```bash
     openclaw channels login --channel zalouser
     ```

---

## 7. Quy tắc an toàn

- Không ghi trực tiếp API key, secret token hay mật khẩu vào file skill này.
- Khi chia sẻ file nén export, lưu ý file `openclaw.json` bên trong có thể chứa botToken Telegram và 9Router key hiện tại của trợ lý. Cần bảo mật file `.tar.gz`.
