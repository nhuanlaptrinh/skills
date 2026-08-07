# Đổi tên hoặc copy từ VPS thành viên cũ

## Khi dùng

Dùng khi thư mục host đã đổi tên nhưng container mới chưa tồn tại, bind source của container cũ không còn đúng, hoặc cần tạo member mới dựa trên runtime/image của member đang hoạt động. Luôn phân loại một trong hai mode:

- `rename-same-member`: vẫn là cùng khách hàng/member; có thể giữ state sau backup và phải rotate/cập nhật mọi secret, đường dẫn, account, binding, port và label liên quan.
- `copy-new-member`: là member mới; chỉ tái sử dụng image/runtime/package/skill sạch, không copy dữ liệu riêng hoặc secret của source.

## Input và output

- Input: source member/folder, destination name, mode, email Token Codex, Telegram account/token/group nếu có, SSH/web port và image nguồn đã xác minh.
- Output host: `/root/Apps/member_vps/docker-users/data/<destination>/root`, `home`, build context không chứa secret và container `user-<destination>`.
- Backup: `/root/_Backups/openclaw/<destination>/<UTC_TIMESTAMP>/`.
- Private API output: `/root/Data/private_accounts/token_codex/`, directory `700`, file `600`.
- Không ghi Sheet. Không ghi full API key, bot token, Gateway token hoặc mật khẩu vào skill, Git, nhật ký hay câu trả lời.

## Dry-run và preflight

```bash
BASE=/root/Apps/member_vps/docker-users
SOURCE='<source>'
DEST='<destination>'

docker ps -a --format '{{.Names}}|{{.ID}}|{{.Image}}|{{.Status}}|{{.Ports}}' | sort
docker inspect "user-${SOURCE}" --format 'name={{.Name}} image={{.Config.Image}} hostname={{.Config.Hostname}} mounts={{json .Mounts}} ports={{json .NetworkSettings.Ports}}' 2>/dev/null || true
docker inspect "user-${DEST}" >/dev/null 2>&1 && echo 'destination container exists'
find "$BASE/data/$DEST" -maxdepth 3 -mindepth 1 -printf '%y|%m|%u:%g|%p\n' 2>/dev/null | sort
ss -ltn
```

Nếu source container đang chạy và bind source trên host vừa bị đổi tên, không restart. Docker có thể giữ inode cũ cho tới restart nhưng lần khởi động sau có thể tạo folder source cũ rỗng. Backup trước, sau đó đưa đúng inode dữ liệu về source path đang hiện trong `docker inspect` hoặc lập kế hoạch recreate riêng.

`docker rename user-old user-new` chỉ đổi tên container. Nó không đổi hostname, user, home, bind mount source/destination, port, label, OpenClaw account, Telegram binding hoặc secret path; không dùng như migration hoàn chỉnh.

## Backup bắt buộc

```bash
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
BACKUP="/root/_Backups/openclaw/<destination>/$STAMP"
mkdir -p "$BACKUP"
chmod 700 "$BACKUP"
cp -a "/root/Apps/member_vps/docker-users/data/<destination>" "$BACKUP/data.before"
docker ps -a --filter 'name=^user-' --format '{{.Names}}|{{.ID}}|{{.Image}}|{{.Status}}|{{.Ports}}' | sort > "$BACKUP/member-containers.before.tsv"
```

Không lưu full `docker inspect` dùng chung nếu container có secret trong environment. Chỉ lưu các field cần kiểm tra hoặc file backup root-only.

## Mode `rename-same-member`

1. Xác minh không còn container đích hoặc container cũ đã được nhận diện chính xác.
2. Backup nguyên folder và config private trước khi đổi cấu trúc.
3. Nếu folder legacy chứa `.openclaw` ở top-level và runtime mới yêu cầu root volume, tạo `<destination>/root` và `<destination>/home`, sau đó move/copy state legacy vào `root/.openclaw` chỉ sau backup.
4. Dùng root volume thật `<destination>/root:/root`; không dùng symlink `/root/.openclaw` sang `/home`.
5. Tạo image/container đích với hostname, username, home, labels, SSH/web port và disk guard riêng.
6. Rotate hoặc tạo mới API key, Telegram token file, Gateway token, dashboard token; cập nhật account ID, group, binding và allowed origins.
7. Chỉ giữ state/history nếu chắc chắn đây là cùng member. Không mang token/config source cũ vào runtime mới.

## Mode `copy-new-member`

Mặc định chỉ copy runtime/image/package và skill. Không copy các path sau từ source:

```text
/root/.openclaw/openclaw.json
/root/.openclaw/*.env
/root/.openclaw/*.token
/root/.openclaw/credentials/
/root/.openclaw/identity/
/root/.openclaw/agents/
/root/.openclaw/state/
/root/.openclaw/logs/
/root/.openclaw/workspace-memory/
/root/.openclaw_dashboard_token
/root/.ssh/
/home/<source>/
```

Nếu cần copy skeleton workspace, dry-run với exclude rõ ràng và chỉ lấy file công khai đã duyệt:

```bash
rsync -aHAXn \
  --exclude '.git/' \
  --exclude 'node_modules/' \
  --exclude '__pycache__/' \
  --exclude '*.pyc' \
  --exclude '*.env' \
  --exclude '*.token' \
  --exclude 'credentials/' \
  --exclude 'identity/' \
  --exclude 'agents/' \
  --exclude 'state/' \
  --exclude 'logs/' \
  '<source-workspace>/' '<destination-workspace>/'
```

Sau khi xem dry-run, bỏ `-n` mới chạy thật. Không copy khi source đang ghi SQLite/WAL; dừng đúng process nguồn hoặc dùng snapshot nhất quán nếu thực sự cần dữ liệu cùng-member.

Khi dùng image member cũ làm base, kiểm tra trước:

```bash
docker run --rm --entrypoint sh '<source-image>' -lc '
  test ! -e /root/.openclaw
  test ! -e /root/.ssh
  find /home -mindepth 1 -maxdepth 2 -type f -print -quit | grep -q . && exit 1 || true
'
```

Image đích phải loại user/home nguồn, không chứa secret, pin đúng OpenClaw, thêm package tài liệu và dùng build context có `.dockerignore` loại `root`, `home`, `*.env`, `*.token`, SQLite và credential.

## Chạy thật

1. Tạo hoặc xác minh tài khoản Token Codex bằng dry-run rồi chạy backend thật; lưu output private một lần.
2. Tạo root/home persistent, config mới và secret files quyền `600`.
3. Đồng bộ toàn bộ skill, chạy `--check`, `openclaw skills check` và `openclaw config validate` bằng container tạm.
4. Chọn cổng chưa dùng; tạo đúng một container `user-<destination>` với giới hạn CPU/RAM/swap/PID chuẩn và restart policy `unless-stopped`.
5. Mở đúng SSH/web port trong firewall, không restart container khác.
6. Kiểm tra model catalog, cả ba model chat, vision smoke-test, Gateway, Telegram, dashboard HTTP, SSH/web listener, document modules và disk guard.
7. Snapshot sau thay đổi; so sánh ID/trạng thái các member cũ với snapshot trước.

## Rerun và rollback

- Nếu preflight/container tạm fail: sửa image/config/root volume trước; không tạo production container.
- Nếu container mới fail nhưng source member không bị sửa: stop đúng container đích, giữ dữ liệu để điều tra và không chạm member khác.
- Nếu source path active bị đổi nhầm: restore đúng inode/folder về bind source cũ từ backup trước khi restart.
- Nếu cần rollback cùng-member: dùng backup root-only, restore config/data đúng destination và validate trước khi start Gateway.
- Không chạy `docker system prune`, không xóa image/container/source folder cũ khi chưa có yêu cầu rõ và chưa xác minh backup.

## Secret scan trước bàn giao

Quét đúng skill/build context public, không in secret hit ra terminal dùng chung:

```bash
rg -l -i 'api[_-]?key|bot[_-]?token|password|private key|BEGIN .* PRIVATE KEY' \
  /root/.agents/skills/tao-tro-ly-openclaw-windows-macos-linux \
  /root/Apps/member_vps/docker-users/data/<destination>/build
```

Review từng file hit để xác nhận chỉ là placeholder/quy tắc. Không quét rồi in nội dung file private `.env`, token, credential hoặc database.
