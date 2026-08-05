---
name: openclaw-zalo-qr-login
description: Hướng dẫn thao tác đăng nhập lại Zalo Personal cho OpenClaw bằng QR trên VPS/headless, đồng bộ QR ra link web công khai, giữ nguyên các cấu hình khác ở mặc định hoặc giá trị hiện có để tránh ảnh hưởng production. Use when Codex needs to regenerate expired Zalo QR, onboard/re-login OpenClaw Zalo Personal, configure dmPolicy/groupPolicy safely, or reproduce the QR login workflow on another VPS.
---

# OpenClaw Zalo QR Login

Skill này dùng để đăng nhập lại kênh **Zalo Personal** của OpenClaw trên VPS không có màn hình, bằng cách tạo QR mới rồi đưa ảnh QR ra một URL web để người vận hành quét bằng điện thoại.

## Nguyên tắc an toàn

- Chỉ xử lý đăng nhập QR Zalo Personal; không đổi model, provider, web search, skills, hooks, workspace, token, `.env`, hoặc cấu hình không liên quan.
- Trước khi sửa `~/.openclaw/openclaw.json`, backup vào `/root/_Backups` nếu thư mục tồn tại; nếu không, backup vào `~/.openclaw/backups`.
- Không in token, cookie, bot token, gateway token, QR raw payload, hoặc nội dung secret ra câu trả lời.
- Nếu đang ở VPS production, đọc quy tắc/AGENTS/checklist của máy trước khi sửa và ghi nhật ký thay đổi nếu máy có cơ chế nhật ký.
- Ưu tiên giữ giá trị hiện có khi wizard hỏi các bước không liên quan.

## Link QR chuẩn cần dùng

Mặc định workflow dùng:

- Nguồn QR OpenClaw: `/tmp/openclaw/openclaw-zalouser-qr-default.png`
- File web public: `/var/www/html/openclaw-qr.png`
- URL public dạng: `https://<domain>/openclaw-qr.png`

Nếu VPS chưa có Nginx route, thêm location tương đương vào domain đang dùng:

```nginx
location = /openclaw-qr.png {
    auth_basic off;
    alias /var/www/html/openclaw-qr.png;
    etag off;
    expires -1;
    add_header Cache-Control "no-store, no-cache, must-revalidate, max-age=0" always;
    add_header Pragma "no-cache" always;
}
```

Sau khi sửa Nginx, kiểm tra và reload:

```bash
nginx -t && systemctl reload nginx
```

## Bước 1: Bật đồng bộ QR ra web

Nếu VPS có skill `openclaw-qr-sync`, dùng script có sẵn:

```bash
chmod +x /root/.agents/skills/openclaw-qr-sync/scripts/sync_qr.sh
nohup /root/.agents/skills/openclaw-qr-sync/scripts/sync_qr.sh \
  /tmp/openclaw/openclaw-zalouser-qr-default.png \
  /var/www/html/openclaw-qr.png \
  >/tmp/openclaw-qr-sync.log 2>&1 &
```

Nếu không có script, dùng vòng lặp tạm:

```bash
mkdir -p /var/www/html
while true; do
  if [ -f /tmp/openclaw/openclaw-zalouser-qr-default.png ]; then
    cp -f /tmp/openclaw/openclaw-zalouser-qr-default.png /var/www/html/openclaw-qr.png
    chmod 644 /var/www/html/openclaw-qr.png
  fi
  sleep 1
done
```

Chỉ để tiến trình sync chạy trong lúc quét QR; tắt sau khi đăng nhập thành công.

## Bước 2: Chạy OpenClaw onboard

Chạy:

```bash
openclaw onboard
```

Trong wizard, chọn như sau:

1. `I understand... Continue?` → chọn `Yes`.
2. `Setup mode` → chọn `QuickStart`.
3. Nếu có `Existing config detected` → chọn `Keep current values`.
4. `Model/auth provider` → chọn `Skip for now`, trừ khi user yêu cầu đổi provider.
5. `Default model` → chọn `Keep current (...)`.
6. `Select channel` → tìm và chọn `Zalo (Personal Account)`.
7. `Login via QR code now?` → chọn `Yes`.
8. Khi thấy `QR image saved to: /tmp/openclaw/openclaw-zalouser-qr-default.png`, yêu cầu user mở URL public và quét QR bằng Zalo.
9. Sau khi user nói đã quét và approve trên điện thoại, chọn `Yes` ở câu `Did you scan and approve the QR on your phone?`.

Nếu QR hết hạn, chạy lại từ bước `Login via QR code now?` hoặc chạy lại `openclaw onboard` để tạo ảnh mới.

## Bước 3: Giữ mặc định các phần không liên quan

Sau khi `Login successful`, wizard có thể hỏi thêm. Chọn theo nguyên tắc không làm thay đổi ngoài yêu cầu:

- `Zalo Personal DM policy`: giữ lựa chọn hiện có nếu user không yêu cầu đổi.
- Nếu user yêu cầu DM pairing: chọn `Pairing (recommended)` và bỏ `allowFrom` nếu đang sửa trực tiếp config.
- Nếu user yêu cầu DM allowlist: chọn `Allowlist` và chỉ nhập user ID do user cung cấp hoặc giá trị đang có sẵn.
- `Configure Zalo groups access?`: chọn theo yêu cầu user; nếu không có yêu cầu thì chọn `No` hoặc giữ nguyên hiện có.
- `Search provider`: chọn `Skip for now`.
- `Configure skills now?`: chọn `No`.
- `Enable hooks?`: chọn `Skip for now`.
- `Gateway service already installed`: chọn `Restart` để nạp phiên đăng nhập mới.
- `How do you want to hatch your agent?`: chọn `Hatch later` để không mở chat hoặc phiên mới.

## Bước 4: Kiểm tra và dọn dẹp

Kiểm tra file QR đã được publish khi cần:

```bash
ls -l /tmp/openclaw/openclaw-zalouser-qr-default.png /var/www/html/openclaw-qr.png
```

Tắt sync QR sau khi đăng nhập thành công:

```bash
for pid in $(pgrep -f 'sync_qr\.sh' || true); do kill "$pid" 2>/dev/null || true; done
```

Kiểm tra gateway user service:

```bash
XDG_RUNTIME_DIR=/run/user/0 systemctl --user is-active openclaw-gateway.service
XDG_RUNTIME_DIR=/run/user/0 systemctl --user status openclaw-gateway.service --no-pager -l
```

Nếu hệ thống không dùng user service, kiểm tra process/cổng:

```bash
ps aux | rg '[o]penclaw|[g]ateway'
ss -ltnp | rg '18789|openclaw|node'
```

## Sửa nhanh policy bằng config nếu được yêu cầu

Chỉ dùng khi user yêu cầu đổi policy rõ ràng. Backup trước:

```bash
TS=$(date -u '+%Y%m%dT%H%M%SZ')
BACKUP_DIR="/root/_Backups/openclaw_zalouser_policy_$TS"
mkdir -p "$BACKUP_DIR"
cp -a /root/.openclaw/openclaw.json "$BACKUP_DIR/openclaw.json.before"
```

Ví dụ đổi DM về pairing và group open:

```bash
python3 - <<'PY'
import json
from pathlib import Path
p = Path('/root/.openclaw/openclaw.json')
data = json.loads(p.read_text())
zalouser = data.setdefault('channels', {}).setdefault('zalouser', {})
zalouser['dmPolicy'] = 'pairing'
zalouser.pop('allowFrom', None)
zalouser['groupPolicy'] = 'open'
p.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
PY
openclaw config validate
XDG_RUNTIME_DIR=/run/user/0 systemctl --user restart openclaw-gateway.service
```

Không dùng đoạn sửa config này nếu chỉ cần quét QR đăng nhập lại.

## Câu trả lời mẫu cho user

Khi QR đã tạo xong:

```text
QR mới đã được tạo. Anh/chị mở link https://<domain>/openclaw-qr.png, nhấn F5 nếu còn ảnh cũ, quét bằng Zalo và bấm xác nhận trên điện thoại. Sau khi quét xong, nhắn “đã quét” để em xác nhận tiếp trong OpenClaw.
```

Khi hoàn tất:

```text
Xong rồi. OpenClaw báo Login successful, Zalo Personal đã configured, gateway đã restart và đang chạy. Em đã tắt tiến trình sync QR tạm để khỏi chạy nền mãi.
```
