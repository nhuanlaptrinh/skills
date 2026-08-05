---
name: gan-domain-openclaw-member-vps
description: Gắn hoặc sửa domain Cloudflare, Nginx reverse proxy WebSocket và SSL Let's Encrypt cho OpenClaw chạy trong member VPS Docker dưới /root/Apps/member_vps/docker-users/data. Use khi người dùng yêu cầu gắn tên miền/subdomain cho OpenClaw member VPS, public OpenClaw Control UI qua HTTPS, đổi domain đã gắn, sửa lỗi domain không vào được dashboard, hoặc đặt lại gateway auth token trong lúc triển khai domain.
---

# Gắn Domain OpenClaw Member VPS

## Đường dẫn

- Member manager: `/root/Apps/member_vps/docker-users/manage-user.sh`
- Member data: `/root/Apps/member_vps/docker-users/data/<member>`
- Script: `scripts/setup_member_openclaw_domain.sh`
- Host Nginx: `/etc/nginx/sites-available/<domain>`
- Backup: `/root/_Backups/member_openclaw_domain_<member>_<timestamp>`
- Nhật ký: `/root/_Second_AI_Brain/06_Nhat_Ky_Thay_Doi.md`

## Kiến trúc chuẩn

Giữ OpenClaw bind loopback trong container:

`Domain HTTPS -> Nginx host -> 127.0.0.1:<member_web_port> -> Nginx container:80 -> 127.0.0.1:18789`

Không đổi gateway sang `0.0.0.0` và không public trực tiếp cổng `18789`.

## Biến môi trường

- `CLOUDFLARE_API_TOKEN`: bắt buộc khi `--apply`, token có quyền DNS Edit cho zone.
- `OPENCLAW_GATEWAY_TOKEN`: tùy chọn; chỉ đặt khi người dùng yêu cầu đổi token gateway.

Không truyền token trực tiếp trên command line. Không ghi token vào SKILL.md, log, nhật ký hoặc câu trả lời.

## Dry-run

```bash
bash /root/.agents/skills/gan-domain-openclaw-member-vps/scripts/setup_member_openclaw_domain.sh \
  --member anhlaptrinh \
  --domain anhlaptrinh.anhlaptrinh.vn \
  --zone anhlaptrinh.vn \
  --ip 187.127.177.163 \
  --dry-run
```

Dry-run kiểm tra container, data folder, cổng web, gateway và in kế hoạch; không cần Cloudflare token và không sửa production.

## Chạy thật

Nạp secret vào environment từ nơi lưu riêng, sau đó chạy:

```bash
export CLOUDFLARE_API_TOKEN='Nhap_API_Cua_Ban'
export OPENCLAW_GATEWAY_TOKEN='Nhap_API_Cua_Ban'

bash /root/.agents/skills/gan-domain-openclaw-member-vps/scripts/setup_member_openclaw_domain.sh \
  --member anhlaptrinh \
  --domain anhlaptrinh.anhlaptrinh.vn \
  --zone anhlaptrinh.vn \
  --ip 187.127.177.163 \
  --apply

unset CLOUDFLARE_API_TOKEN OPENCLAW_GATEWAY_TOKEN
```

Nếu không cần đổi gateway token, không export `OPENCLAW_GATEWAY_TOKEN`.

## Script thực hiện

1. Xác nhận root, dependency, container `user-<member>` và data folder.
2. Tự lấy host web port đang map vào container port 80.
3. Backup `openclaw.json`, Nginx container và Nginx host nếu có.
4. Thêm HTTPS domain vào `gateway.controlUi.allowedOrigins`.
5. Đặt `gateway.trustedProxies` chỉ gồm loopback.
6. Chỉ đổi `gateway.auth.token` khi có `OPENCLAW_GATEWAY_TOKEN`.
7. Cấu hình Nginx container proxy WebSocket vào `127.0.0.1:18789`.
8. Cấu hình Nginx host proxy domain vào host web port của member.
9. Tạo hoặc cập nhật Cloudflare A record bằng API token từ environment.
10. Validate/reload Nginx, validate/restart OpenClaw gateway.
11. Chờ DNS public rồi cấp SSL Certbot và bật HTTP redirect.
12. Kiểm tra HTTPS, gateway và channel status.

## Kiểm tra sau khi chạy

```bash
curl -I https://<domain>/
docker exec user-<member> sh -lc 'HOME=/home/<member> openclaw gateway status'
docker exec user-<member> sh -lc 'HOME=/home/<member> openclaw channels status --probe'
nginx -t
certbot certificates
```

Kết quả đúng:

- HTTPS trả `200` và trang có tiêu đề `OpenClaw Control`.
- HTTP chuyển `301` sang HTTPS.
- Gateway connectivity `ok`.
- Các channel trước đó vẫn `running`/`works`.

## Rerun và sửa lỗi

- Script có thể chạy lại với cùng member/domain; Cloudflare record được cập nhật thay vì tạo trùng.
- Nếu DNS chưa lan truyền, kiểm tra bằng `dig +short <domain> @1.1.1.1` rồi chạy lại.
- Nếu local resolver cache chưa cập nhật, kiểm tra HTTPS bằng `curl --resolve <domain>:443:<ip> https://<domain>/`.
- Nếu container được tạo lại và mất `/etc/nginx`, copy lại file nguồn `<member-data>/openclaw-nginx.conf` vào `/etc/nginx/sites-available/default`, rồi reload Nginx container.
- Khi đổi domain, chạy skill với domain mới; kiểm tra và gỡ domain/Nginx cũ riêng nếu người dùng yêu cầu rõ.

## An toàn

- Đọc tài liệu Second AI Brain và checklist production trước khi sửa.
- Không in hoặc lưu Cloudflare token, gateway token, bot token hay API key.
- Không sửa model, channel, `.env`, credential hoặc dữ liệu member ngoài phạm vi domain/token được yêu cầu.
- Không mở thêm firewall port cho gateway; dùng host web port đã tồn tại.
- Backup trước mọi thay đổi và cập nhật nhật ký sau khi hoàn tất.
