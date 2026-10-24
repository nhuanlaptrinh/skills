---
name: nang-openclaw-member-6-10
description: Nâng OpenClaw Docker member VPS lên bản stable 6.10 (2026.10.6), nâng Node khi cần, backup và nghiệm thu Telegram/model; dùng lại quy trình đã chạy trên Minh Vương.
---

# Nâng OpenClaw member lên 6.10

## Phạm vi và công cụ

- Chạy từ **VPS host**, không chạy script host từ terminal bên trong member.
- Project: `/root/Apps/member_vps/docker-users`.
- Driver: `/root/Automation/openclaw/member_sequential_upgrade/upgrade_2026_10_6.py`.
- Driver dùng chung helper trong `upgrade_2026_9_9.py` cùng thư mục; giữ cả hai file.
- Target được pin: **`2026.10.6`**; đây là chuỗi phiên bản gọi tắt **6.10**, không phải `2026.6.10`. Không suy ngày phát hành thực tế chỉ từ tên phiên bản.
- Ngày kiểm tra `2026-10-24`, npm `latest=2026.10.6`; không dùng `beta=2026.10.10-beta.3`.
- Engines chính thức: `>=24.22.1 <25 || >=26.12.1`. Driver giữ Node tương thích sẵn có; nếu chưa đạt, cài Node `24.22.1` từ `nodejs.org`, đối chiếu SHA-256 manifest chính thức.
- Không tự nâng các member khác nếu người dùng chỉ yêu cầu một member.
- Đã nghiệm thu trên `user-minhvuong` ngày `2026-10-24`: `2026.9.9` → `2026.10.6`, Node `24.22.1`, Telegram ổn định và model smoke không delivery đạt. Bằng chứng: `/root/_Backups/openclaw-members-2026.10.6/minhvuong/20261024T053800Z/SUCCESS.json`. Đây là trường hợp Telegram-only, không thay thế preflight riêng cho member có Zalo/core patch.

## Input và output

Input bắt buộc: tên member không có tiền tố `user-`, runtime HOME thực tế (`/root` hoặc `/home/<member>`), và có/không `--apply`.

Output: log theo bước, summary không chứa nội dung chat, backup riêng mỗi lần chạy và `SUCCESS.json` khi toàn bộ nghiệm thu đạt, tại:

```text
/root/_Backups/openclaw-members-2026.10.6/<member>/<UTC-timestamp>/
```

Driver không ghi Google Sheet, không upload/post, không gửi Telegram/Zalo test. Chỉ ghi nhật ký host sau khi nâng thành công. Model smoke là request nội bộ không có `--deliver`; vẫn dùng API model hiện hữu.

## Lượt tuần tự đã được duyệt ngày 2026-10-24

Người dùng đã yêu cầu đúng thứ tự: `hoangtuankiet`, `lehuynhphong`, `minhvuong`, `nguyendinhtan`, `qnvuong`, `thanhthai`, `bstuannk`, `trolyketoancatminh`, `doquyet`, `nndung`, `nguyenvantieng`, `levietngoc`, `lethangholand`; sau đó yêu cầu **không tạo backup, nâng luôn**. Việc bỏ backup chỉ áp dụng khi có yêu cầu rõ như lượt này; mặc định driver vẫn backup.

Driver mới nhận `--no-backup` để bỏ toàn bộ archive thủ công và `node.before`, **không** tắt retention/recovery bắt buộc của updater chính thức, không xóa backup cũ. Thư mục dưới `_Backups` của lượt này chỉ chứa log/report/artifact Node, không có nghĩa đã tạo bản backup thủ công. `SUCCESS.json` ghi rõ `manualBackupCreated=false`, `backup=null`, `reportDir`.

```bash
python3 /root/Automation/openclaw/member_sequential_upgrade/upgrade_2026_10_6.py <member> --home <HOME> --apply --no-backup
python3 /root/Automation/openclaw/member_sequential_upgrade/run_2026_10_6.py --no-backup
python3 /root/Automation/openclaw/member_sequential_upgrade/run_2026_10_6.py --apply --no-backup
```

Runner chỉ dùng danh sách 13 member đã duyệt, không lấy danh sách cũ trong `run_sequential.py`. Dry-run runner chỉ in kế hoạch. Chạy thật chỉ có **một** driver hoạt động, giữ batch/fleet lock, nghiệm thu xong rồi nghỉ 30 giây mới sang member kế tiếp. Trước mỗi member cần MemAvailable >=3072 MiB, disk >=8 GiB, load trung bình/CPU <=1.5; thiếu RAM/CPU chờ tối đa 15 phút rồi dừng, không cố chạy khi host yếu.

Nếu member đã đúng target, runner dùng `--verify-only`: xác minh lại config/channel/PID ổn định và model, **không** cài lại hoặc restart. Report tổng hợp: `/root/Data/reports/openclaw-members-2026.10.6/<timestamp>/batch.json`. Lỗi mới phải dừng toàn bộ; sau xử lý nguyên nhân, dùng `--start-member <member-chưa-đạt>` để tiếp tục đúng suffix của thứ tự, không chạy lại thành viên đã đạt.

Runner bật hai ngoại lệ **chỉ cho lỗi đã chứng minh có trước**, không sửa credential/model hay giả báo healthy:

- `--allow-unlinked-zalo`: chỉ cho phép Zalo có `linked=false` ngay preflight. Telegram và mọi kênh đã healthy vẫn phải đạt; account Zalo phải tiếp tục tồn tại hoặc hồi phục, không tự tạo QR. Hoàng Tuấn Kiệt đã có trạng thái này trước nâng ngày 24/10.
- `--allow-preexisting-model-error`: chạy model smoke cả trước và sau nâng. Chỉ dung thứ cùng lỗi authentication/authorization/quota của **cùng agent** đã có từ trước; lỗi mới hoặc đổi loại phải dừng. Report tách `modelSmokePassed`, `modelBaselineErrors`, `modelErrors`; không mô tả model đạt nếu còn lỗi.

Các ngoại lệ mặc định tắt ở driver riêng. Không mở ngoại lệ cho Telegram mất kết nối, event loop degraded, import error, Gateway trùng, crash/OOM, thay đổi policy hoặc lỗi model không xác định. Không bê core/text-delivery bundle 9.9 sang 6.10; guard đặc thù phiên bản phải được review riêng, không suy từ transport probe rằng mọi chức năng custom đã được kiểm thử.

## Các bước thực hiện

### 1. Đọc hướng dẫn và xác định đúng member

Đọc `/root/_Second_AI_Brain/START_HERE.md`, `01_Ban_Do_VPS.md`, `02_Danh_Sach_Project.md`, note `/root/_Second_AI_Brain/projects/<member>_openclaw.md`, checklist production và các `AGENTS.md` liên quan.

```bash
MEMBER=minhvuong
CONTAINER="user-${MEMBER}"
MEMBER_HOME=/root
docker inspect "$CONTAINER" --format '{{range .Mounts}}{{println .Source "->" .Destination}}{{end}}'
docker exec "$CONTAINER" supervisorctl status openclaw-gateway
docker exec "$CONTAINER" node --version
docker exec -e HOME="$MEMBER_HOME" "$CONTAINER" openclaw --version
docker exec "$CONTAINER" npm view openclaw dist-tags --json
docker exec "$CONTAINER" npm view openclaw@2026.10.6 version engines --json
```

Không suy đoán HOME từ tên member. Minh Vương dùng `/root`, dữ liệu bind mount nằm trong `/root/Apps/member_vps/docker-users/data/minhvuong/root`.

### 2. Chạy dry-run

```bash
python3 /root/Automation/openclaw/member_sequential_upgrade/upgrade_2026_10_6.py "$MEMBER" --home "$MEMBER_HOME"
```

Phải có `PREFLIGHT_OK`. Preflight kiểm tra config, Supervisor đang RUNNING, đúng một Gateway, các account enabled/configured đều healthy, dung lượng trống tối thiểu 8 GiB và preview updater đúng target, không downgrade. Không đổi package/config hoặc tự start/restart Gateway. Có tạo log và ledger dry-run của updater.

Driver tự nạp hai file env runtime nếu tồn tại (`gateway.env`, `token-codex.env`) mà không in giá trị. Chạy CLI trần thiếu env có thể báo API key unavailable dù runtime đang hoạt động; không sửa secret để xử lý một cảnh báo do thiếu môi trường.

Preview có thể báo `node-runtime-preflight` khi Node cũ; driver xử lý Node sau khi backup. Bất kỳ chặn khác, baseline lỗi, manager khác Supervisor, hoặc core patch đặc thù chưa review đều phải dừng để chẩn đoán; không ép chạy.

### 3. Chạy thật cho đúng một member đã được yêu cầu

```bash
python3 /root/Automation/openclaw/member_sequential_upgrade/upgrade_2026_10_6.py "$MEMBER" --home "$MEMBER_HOME" --apply
```

Driver thực hiện:

1. Preflight lại; tải và kiểm SHA-256 Node **trước downtime** nếu cần.
2. Giữ fleet lock và lock watchdog hiện hữu của member nếu có; dừng riêng `openclaw-gateway`, xác nhận đã dừng.
3. Backup config, SQLite cùng WAL/SHM, toàn bộ agents/state, credential/env vào archive root-only, package OpenClaw cũ, Node cũ, plugins và file service. Không đưa archive/secret vào skill.
4. Thay Node nếu cần; chạy updater chính thức `openclaw update --tag 2026.10.6 --no-restart --yes --json --timeout 600` trong đúng môi trường member.
5. Chạy `doctor --post-upgrade --json` và config validate; đối chiếu fingerprint model/routing/channels/tools/session/gateway để tránh thay đổi cấu hình ngoài ý muốn.
6. Start bằng Supervisor; kiểm tra singleton Gateway, channel probes và PID ổn định sau ít nhất 35 giây.
7. Chạy model smoke ở session riêng, không deliver; kiểm log mới cho 409 Conflict, missing modules, tombstone, OOM và lỗi gửi Telegram.
8. Chỉ ghi `SUCCESS.json` và nhật ký thành công khi toàn bộ kiểm tra đạt.

Không tự thêm `--accept-capabilities`, `npm --force`, `doctor --fix`, import/xóa session, đổi model, allowlist hoặc credential để vượt một lỗi. Đọc failure report rồi xử lý có căn cứ. Với Zalo/plugin ngoài, review capability/version/migration trước; thành công Telegram-only không chứng minh mọi cấu hình Zalo đã được thử.

### 4. Nghiệm thu và báo cáo

Phải có version đúng `2026.10.6`, Node đúng engines, config valid, config policy không đổi, đúng một Gateway/PID ổn định, tất cả account bắt buộc healthy, model smoke và log check đạt.

Probe healthy **không phải** kiểm thử nhắn tin hai chiều thật. Chỉ gửi tin khi được yêu cầu riêng; không gọi `getUpdates` song song với poller.

Báo member, bản cũ/mới, Node, backup, Gateway, kênh và giới hạn kiểm thử. Cập nhật note member và `/root/_Second_AI_Brain/06_Nhat_Ky_Thay_Doi.md`. Nếu sửa driver/đường dẫn/quy trình, cập nhật skill này và mục tương ứng trong skill `openclaw-member-upgrade-telegram-recovery`.

## Rerun và rollback

- Updater có thể mất nhiều phút ở `validating` / `updater-runtime-retention` để giữ runtime cũ. Không khởi chạy updater thứ hai hoặc bỏ qua validation chỉ vì chưa thấy log mới. Có thể xem ledger chỉ đọc bằng lệnh sau (không in nội dung config/chat):

```bash
docker exec -e HOME="$MEMBER_HOME" "$CONTAINER" python3 -c 'import os,sqlite3; path=os.path.expanduser("~/.openclaw/state/openclaw.sqlite"); connection=sqlite3.connect("file:"+path+"?mode=ro",uri=True); print(connection.execute("SELECT phase,status FROM update_runs ORDER BY created_at_ms DESC LIMIT 1").fetchone())'
```

- Mỗi rerun tạo thư mục backup mới; không ghi đè backup cũ. Sau `STOP`, xem đúng log lỗi trước, kiểm tra version/config/Gateway hiện tại rồi mới chạy lại. Không chạy fleet loop bỏ qua lỗi.
- Lỗi trong cửa sổ nâng: driver chỉ thử start lại Gateway nếu config validate còn chạy thành công; không bảo đảm phục hồi package bị hỏng. Operator phải kiểm tra và phục hồi ngay member lỗi trước khi chuyển member khác.
- Rollback: dừng Gateway; dùng `node.before` và `package-before.tar.gz` của đúng incident. Giữ package lỗi bằng rename sang tên timestamp trước khi giải nén package cũ vào đúng npm root; không chép bundle cũ đè lẫn package mới. Config chỉ khôi phục file thực sự bị thay đổi. Start Supervisor và chạy lại config/channel acceptance.
- `runtime-state-before.tar.gz`, `state-and-service.tar.gz`, `plugins-before.tar.gz` chứa dữ liệu nhạy cảm, chỉ root được đọc. Chỉ rollback SQLite khi chứng minh migration hỏng; DB/WAL/SHM phải phục hồi cùng bộ lúc Gateway dừng, không ghi đè lịch sử mới một cách máy móc.
- Nâng trong container tồn tại qua `docker restart`, nhưng **không bảo đảm qua recreate từ image cũ**. Không tự sửa compose/image hoặc recreate cả cụm. Nếu cần bền vững qua recreate, lập thay đổi image/pin riêng, backup compose và giữ nguyên mount/network/port.

## An toàn và giới hạn

Không sửa `.env`, credential, Chrome profile, cron/nginx/compose, các member khác hay bot sidecar chỉ vì nâng OpenClaw. Không xóa sessions/database hoặc dùng `docker system prune`. Trước khi lưu/cập nhật skill, quét secret; không đưa token/API key/cookie/password/private key thật vào tài liệu, log công khai hoặc câu trả lời.
