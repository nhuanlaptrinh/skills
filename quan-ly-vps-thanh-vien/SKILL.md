---
name: quan-ly-vps-thanh-vien
description: Quản lý & Vận hành VPS Thành Viên toàn diện (Docker Container Member VPS): tạo mới, giới hạn 10 GiB, cấp dải port 3001-3999, mở port TCP, gắn domain Cloudflare, SSL Let's Encrypt, Cloudflare Tunnel, tự động đồng bộ AGENTS.md, skills và _Second_AI_Brain, tự động trả về IP Public thật và mật khẩu cho khách hàng. Use when creating member VPS, opening ports, managing member domains, configuring member Cloudflare tunnels, or checking member resources.
---

# Quản Lý & Vận Hành VPS Thành Viên Toàn Diện

Skill này là **chuẩn duy nhất** để khởi tạo, cấp tài nguyên, mở port, gắn domain, cài Cloudflare Tunnel và vận hành toàn bộ các VPS Thành Viên (Docker container member VPS) trên máy chủ chính.

---

## 🚀 PHẦN 1: KHỞI TẠO & QUẢN LÝ THÀNH VIÊN

### 📌 Source Of Truth
- Project: `/root/Apps/member_vps/docker-users`
- Script quản lý: `/root/Apps/member_vps/docker-users/manage-user.sh`
- Dữ liệu persistent: `/root/Apps/member_vps/docker-users/data/<username>`
- Image base: `vps-user-env`
- Disk guard config: `/root/Apps/member_vps/docker-users/member-vps-disk-guard.conf`

### 🎯 Giới Hạn Mặc Định
Container tạo mới mặc định có:
- CPU: `2 cores`
- RAM: `4g` (`6g` gồm swap)
- Mutable disk guard: `10 GiB`
- Restart policy: `unless-stopped`
- OpenClaw Gateway loopback port: `18789`

### 📋 Quy Trình 7 Bước Bắt Buộc Khi Tạo Mới Thành Viên
1. **Kiểm tra cổng port:** Đảm bảo cổng SSH & Web dự định cấp chưa bị chiếm (`ss -tlnp`).
2. **Khởi tạo container:** Chạy `manage-user.sh create <username> <password> <ssh_port> <web_port>`.
3. **Kiểm tra firewall:** Mở rule UFW tương ứng.
4. **Xác minh giới hạn tài nguyên:** CPU 2 cores, RAM 4GB, Swap 6GB.
5. **Trả về thông tin kết nối kèm IP Public thật (BẮT BUỘC):** AI tự động lấy IP Public (`curl -s https://api.ipify.org`) và xuất sẵn khung thông tin copy gửi ngay cho khách hàng (gồm Username, Password, SSH Port, Lệnh SSH kèm IP, Web Port, Website URL `http://<IP>:<web_port>`).
6. **Disk guard:** Giới hạn mặc định `10 GiB` cho container `user-<username>`.
7. **Đồng bộ Quy tắc & Bộ Não Thứ 2 vào Container:** Tự động sao chép tệp quy tắc `AGENTS.md` và cấu trúc Bộ Não Thứ 2 (`_Second_AI_Brain`) vào bên trong container VPS thành viên tại `/home/<username>/` và `/root/` (lưu ý: không copy skill quản lý host `quan-ly-vps-thanh-vien` vào bên trong container thành viên vì container không có quyền quản trị máy chủ chính).

### 🛠 Các Lệnh Quản Lý Chính
```bash
# Liệt kê tất cả VPS thành viên
/root/Apps/member_vps/docker-users/manage-user.sh list

# Tạo thành viên mới (Tự lấy IP Public và trả về khung kết nối gửi khách hàng)
/root/Apps/member_vps/docker-users/manage-user.sh create <username> <password> <ssh_port> <web_port>

# Xem thông số live & IP của thành viên
/root/Apps/member_vps/docker-users/manage-user.sh show <username>

# Báo cáo dung lượng đĩa Disk Guard
/root/Apps/member_vps/docker-users/manage-user.sh disk-status
```

---

## 🌐 PHẦN 2: CẤP PORT (3001-3999) & NGINX SUBDOMAIN ROUTING

### 🛠 Cấu Trúc Auto-Subdomain Engine (`/root/Apps/member_vps_subdomain_port`)
- Dải port cấp tự động: `3001-3999`.
- Cơ sở dữ liệu SQLite: `member_websites`.
- Blacklist port cấm: Tránh đụng độ port hệ thống (18789, 2225, 3025...).

```bash
# Kiểm thử tự động 10/10 kịch bản
python3 /root/Apps/member_vps_subdomain_port/test_suite.py 2>/dev/null || true

# Gọi Tool tạo Website mới cấp port tự động
python3 -c "from ai_agent_tools import create_website; res = create_website('<subdomain>'); print(res['report'])" 2>/dev/null || true

# Liệt kê website hiện có
python3 -c "from ai_agent_tools import list_websites; print(list_websites())" 2>/dev/null || true
```

---

## 🔌 PHẦN 3: MỞ PORT FIREWALL & DOCKER MAPPING

### Quy Tắc Mở Port TCP
- Khi người dùng yêu cầu "mở port <PORT>" hoặc "mở cổng <PORT>", mặc định hiểu là **Port Application/Web** (không phải SSH trừ khi yêu cầu rõ).
- Quy trình 3 lớp mở port:
  1. Kiểm tra ứng dụng trong container đang lắng nghe `0.0.0.0:<PORT>`.
  2. Mở UFW host: `ufw allow <PORT>/tcp`.
  3. Cấu hình DNAT/iptables hoặc Docker proxy map port public ra container:
     ```bash
     /usr/local/sbin/open-member-port.sh <host_port> <container_name> [container_port] 2>/dev/null || true
     ```

---

## 🔒 PHẦN 4: GẮN DOMAIN CLOUDFLARE, NGINX WEBSOCKET & SSL

### Kiến Trúc Proxy Chuẩn
`Domain HTTPS -> Nginx Host -> 127.0.0.1:<web_port> -> Nginx Container:80 -> 127.0.0.1:18789 (OpenClaw/Web)`

### Thao Tác Gắn Domain
```bash
# Dry-run kiểm tra cấu hình
bash /root/.agents/skills/gan-domain-openclaw-member-vps/scripts/setup_member_openclaw_domain.sh \
  --member <member> \
  --domain <subdomain.domain.com> \
  --zone <domain.com> \
  --ip <public_ip> \
  --dry-run 2>/dev/null || true

# Áp dụng thật (cần CLOUDFLARE_API_TOKEN)
export CLOUDFLARE_API_TOKEN='Nhap_API_Cua_Ban'
bash /root/.agents/skills/gan-domain-openclaw-member-vps/scripts/setup_member_openclaw_domain.sh \
  --member <member> \
  --domain <subdomain.domain.com> \
  --zone <domain.com> \
  --ip <public_ip> \
  --apply 2>/dev/null || true
unset CLOUDFLARE_API_TOKEN
```

---

## 🛡 PHẦN 5: TRIỂN KHAI CLOUDFLARE TUNNEL CHO VPS THÀNH VIÊN

### Kiến Trúc Tunnel Cách Ly
`Domain -> Cloudflare HTTPS -> cloudflared in container -> Nginx localhost:80 -> App internal`

### Thao Tác Triển Khai
```bash
# Triển khai connector cloudflared vào container thành viên
bash /root/.agents/skills/member-vps-cloudflare-tunnel/scripts/setup_member_cloudflare_tunnel.sh \
  --container user-<member> \
  --data-dir /root/Apps/member_vps/docker-users/data/<member> \
  --member-home /home/<member> \
  --origin http://127.0.0.1:80 \
  --apply 2>/dev/null || true

# Thêm domain nội bộ bằng gan-domain trong container
docker exec user-<member> sudo gan-domain add example.com --port 8000 2>/dev/null || true
```

---

## 🔒 QUY TẮC AN TOÀN VÀ BẢO MẬT BẮT BUỘC

1. **Không in hoặc ghi lộ Mật khẩu/Token thật** vào tệp nhật ký thay đổi (`/root/_Second_AI_Brain/06_Nhat_Ky_Thay_Doi.md`), log hệ thống hay các kho skill public. Dùng placeholder khi làm tài liệu.
2. **Luôn trả về đầy đủ khung đăng nhập kèm IP thật và Mật khẩu** trong kết quả phản hồi cuối cùng cho người dùng khi tạo VPS thành viên mới.
3. **Mỗi member VPS dùng riêng một thư mục persistent:** `/root/Apps/member_vps/docker-users/data/<username>`, không mount chồng chéo giữa các member.
4. **Sau mọi thay đổi quan trọng trên production**, luôn cập nhật vào `/root/_Second_AI_Brain/06_Nhat_Ky_Thay_Doi.md`.
