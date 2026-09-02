---
name: openclaw-zalo-qr-login
description: Hướng dẫn đăng nhập lại Zalo Personal cho OpenClaw bằng QR trên VPS/headless, gửi QR trực tiếp tới Telegram owner hoặc đồng bộ ra web, và giữ nguyên cấu hình không liên quan. Use when Codex needs to regenerate expired Zalo QR, authorize an owner-triggered Telegram QR workflow, onboard/re-login OpenClaw Zalo Personal, or configure dmPolicy/groupPolicy safely.
---

# OpenClaw Zalo QR Login

Skill này dùng để đăng nhập lại kênh **Zalo Personal** của OpenClaw trên VPS không có màn hình, bằng cách tạo QR mới rồi đưa ảnh QR ra một URL web để người vận hành quét bằng điện thoại.

## Nguyên tắc an toàn

- Chỉ xử lý đăng nhập QR Zalo Personal; không đổi model, provider, web search, skills, hooks, workspace, token, `.env`, hoặc cấu hình không liên quan.
- Trước khi sửa `~/.openclaw/openclaw.json`, backup vào `/root/_Backups` nếu thư mục tồn tại; nếu không, backup vào `~/.openclaw/backups`.
- Không in token, cookie, bot token, gateway token, QR raw payload, hoặc nội dung secret ra câu trả lời.
- Nếu đang ở VPS production, đọc quy tắc/AGENTS/checklist của máy trước khi sửa và ghi nhật ký thay đổi nếu máy có cơ chế nhật ký.
- Ưu tiên giữ giá trị hiện có khi wizard hỏi các bước không liên quan.

## Quyền Telegram owner bắt buộc

Khi user muốn ra lệnh từ Telegram để tạo và nhận QR Zalo, ID Telegram đó phải xuất hiện đồng thời trong các lớp quyền sau:

- `channels.telegram.allowFrom`: được nhắn trực tiếp với bot.
- `commands.ownerAllowFrom`: dùng dạng `telegram:<user_id>` để nhận quyền owner command.
- `tools.elevated.allowFrom.telegram`: được phép gọi công cụ elevated từ Telegram.
- `channels.telegram.execApprovals.approvers`: được bấm duyệt hoặc từ chối exec approval.
- `approvals.plugin.targets`: định tuyến plugin approval tới DM Telegram của owner nếu hệ thống dùng plugin approval.

Không thêm wildcard `"*"` vào owner, elevated hoặc approver allowlist. Không gửi QR vào group hoặc tới một ID chỉ được chuyển tiếp qua lời nhắn của người khác.

## Policy Zalo sau khi liên kết

Khi owner yêu cầu Zalo Personal nhận tin trong group mà không cần mention, cấu hình
channel phải dùng `groupPolicy: "open"` và nhóm wildcard phải có
`groups["*"].enabled: true` cùng `requireMention: false`. Chỉ đưa các ID Zalo
đã xác minh vào `allowFrom` cho DM; không ghi các ID riêng tư vào skill hoặc tài liệu
dùng chung. Giữ binding account `default` về agent `main` và chạy `openclaw config validate`
sau khi thay đổi.

## Gửi QR trực tiếp qua Telegram owner

Helper dùng cho workflow không tương tác:

- Global: `/root/.agents/skills/openclaw-zalo-qr-login/scripts/send_zalo_qr_to_telegram_owner.mjs`
- Trong member workspace: `<workspace>/skills/openclaw-zalo-qr-login/scripts/send_zalo_qr_to_telegram_owner.mjs`

Helper chạy lệnh chính thức `openclaw channels login --channel zalouser`, theo dõi file QR mà CLI tạo, giữ Telegram tiếp tục chạy để gửi ảnh, chờ quét, rồi để CLI bật lại Zalo khi thành công. Cách này tương thích plugin Zalo cài ngoài trên OpenClaw 2026.8.x, nơi Gateway có thể không công bố `web.login.*`. Không restart container và không đổi model/provider/token/policy.

Helper dùng khóa `~/.openclaw/state/zalo-qr-owner-login.lock` để từ chối lượt chạy chồng nhau, gửi qua đúng Telegram account đã khai báo trong plugin approval target, và chỉ coi là đã gửi khi CLI trả về `messageId` cùng destination khớp.

Với OpenClaw 2026.7.x, receipt direct-send có thể nằm trong `payload.result`; với 2026.8.x, destination của plugin Telegram có thể nằm ở `payload.chatId` thay vì `payload.to`. Helper hỗ trợ các dạng receipt này và vẫn yêu cầu `messageId` thật cùng đúng destination.

Dry-run bắt buộc trước:

```bash
node /path/to/send_zalo_qr_to_telegram_owner.mjs \
  --target <telegram_user_id> \
  --dry-run
```

Chạy thật chỉ khi owner đã yêu cầu đăng nhập lại hoặc gửi QR mới:

```bash
node /path/to/send_zalo_qr_to_telegram_owner.mjs \
  --target <telegram_user_id> \
  --apply
```

Input/output:

- Input: Telegram user ID đã có đủ các lớp quyền trên; account Zalo mặc định là `default`; timeout mặc định 180 giây.
- Output: ảnh QR được stage tạm trong `~/.openclaw/media/outbound/` rồi gửi vào DM Telegram của owner; helper vẫn tạo QR khi Zalo đã `stopped` sau lỗi listener, sau khi quét kênh Zalo được start lại.
- Backup: `~/.openclaw/backups/zalo-qr-<timestamp>/` với mode riêng tư; không in nội dung credential.
- Rerun: nếu QR hết hạn, chạy lại lệnh `--apply`; mỗi lượt tạo QR mới và xóa ảnh tạm sau khi kết thúc.
- Concurrent rerun: nếu một lượt còn chờ quét, helper trả lỗi `already running` mà không tạo hoặc gửi QR thứ hai. Lock stale được tự dọn khi PID cũ không còn chạy.
- An toàn: `--apply` sẽ thay phiên Zalo hiện tại, vì vậy không chạy khi owner chỉ muốn kiểm tra trạng thái.

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

Ví dụ cho phép một ID Zalo đã xác minh nhắn DM, đồng thời mở mọi group và không
yêu cầu mention. Dùng placeholder hoặc biến môi trường, không ghi ID thật vào skill:

```bash
export VERIFIED_ZALO_ID='<zalo_user_id>'
python3 - <<'PY'
import json
import os
from pathlib import Path
p = Path('/root/.openclaw/openclaw.json')
data = json.loads(p.read_text())
zalouser = data.setdefault('channels', {}).setdefault('zalouser', {})
zalouser.update({
    'enabled': True,
    'dmPolicy': 'allowlist',
    'allowFrom': [os.environ['VERIFIED_ZALO_ID']],
    'groupPolicy': 'open',
    'groupAllowFrom': ['*'],
    'groups': {'*': {'enabled': True, 'requireMention': False}},
})
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
