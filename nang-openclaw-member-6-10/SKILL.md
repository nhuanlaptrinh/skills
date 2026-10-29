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

Kết quả hoàn tất 2026-10-24 11:33 UTC: **12 member được nâng**, Minh Vương đã có target nên không cài/restart lại (người dùng sau đó yêu cầu bỏ qua). Cả 13 có receipt nghiệm thu 6.10; hậu kiểm 12 member vừa nâng đều đúng version/Node và đúng một Gateway Supervisor RUNNING, không quay lại live-check Minh Vương sau yêu cầu bỏ qua. Tất cả model smoke đạt, không gửi tin thật. Zalo `default` của **Hoàng Tuấn Kiệt và Lê Thắng Holand** đã unlinked từ preflight và giữ nguyên, không báo healthy. Hai migration schema được review riêng là Thanh Thái và Nguyễn Văn Tiếng. Tổng kết và evidence links: `/root/Data/reports/openclaw-members-2026.10.6/20261024T061912Z/FINAL.json`. Quiet-window maintenance locks đã nhả; không sửa cron/config để giảm tải, không bảo đảm host luôn ít tải sau batch.

Người dùng đã yêu cầu đúng thứ tự: `hoangtuankiet`, `lehuynhphong`, `minhvuong`, `nguyendinhtan`, `qnvuong`, `thanhthai`, `bstuannk`, `trolyketoancatminh`, `doquyet`, `nndung`, `nguyenvantieng`, `levietngoc`, `lethangholand`; sau đó yêu cầu **không tạo backup, nâng luôn**. Việc bỏ backup chỉ áp dụng khi có yêu cầu rõ như lượt này; mặc định driver vẫn backup.

Driver mới nhận `--no-backup` để bỏ toàn bộ archive thủ công và `node.before`, **không** tắt retention/recovery bắt buộc của updater chính thức, không xóa backup cũ. Thư mục dưới `_Backups` của lượt này chỉ chứa log/report/artifact Node, không có nghĩa đã tạo bản backup thủ công. `SUCCESS.json` ghi rõ `manualBackupCreated=false`, `backup=null`, `reportDir`.

```bash
python3 /root/Automation/openclaw/member_sequential_upgrade/upgrade_2026_10_6.py <member> --home <HOME> --apply --no-backup
python3 /root/Automation/openclaw/member_sequential_upgrade/run_2026_10_6.py --no-backup
python3 /root/Automation/openclaw/member_sequential_upgrade/run_2026_10_6.py --apply --no-backup
```

Runner chỉ dùng danh sách 13 member đã duyệt, không lấy danh sách cũ trong `run_sequential.py`. Dry-run runner chỉ in kế hoạch. Chạy thật chỉ có **một** driver hoạt động, giữ batch/fleet lock, nghiệm thu xong rồi nghỉ 30 giây mới sang member kế tiếp. Trước mỗi member cần MemAvailable >=3072 MiB, disk >=8 GiB, load trung bình/CPU <=1.5; thiếu RAM/CPU chờ tối đa 15 phút rồi dừng, không cố chạy khi host yếu.

Nếu watchdog/probe đồng loạt khiến host không hạ tải, không hạ ngưỡng, kill workload hoặc disable cron toàn cụm. Có thể dùng maintenance flock tạm của **chính member đã nâng trong danh sách** để tạo quiet window có hạn: chỉ chọn job `_sessions`, `_zalouser`, `_zalo_delivery` với `ai_on_failure=false`, exact container match trong registry, acquire nonblocking và không gián đoạn job đang chạy; thử lại acquisition trong cửa sổ nếu lock đang bận. Không giữ lock của target driver đang nâng. Luôn `finally` đóng handle, giới hạn từng quiet window tối đa 10 phút, không sửa cron/config hay stop Gateway. Theo dõi số lock đã lấy và resource gate; hết thời gian vẫn không an toàn thì dừng, không coi việc chờ là acceptance. Không áp dụng cho job `ai_on_failure=true` vì lock-busy có thể kích hoạt AI self-healing.

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

### Host timeout không có nghĩa updater trong container đã dừng

- Đã gặp Lê Việt Ngọc khi host quá tải: outer timeout cũ 1.200 giây giết Docker client nhưng updater remote tiếp tục `activating`. Không chạy updater mới, repair, config rewrite hoặc restart Gateway khi ledger/process chưa xác nhận đã kết thúc; không quy lỗi package chỉ từ config read/cleanup error trong cửa sổ migration.
- Driver hiện dùng outer budget 2.400 giây cho toàn updater nhiều phase, giữ nguyên per-step `--timeout 600`. Nếu outer timeout vẫn xảy ra, driver dừng batch và **không** tự chạy config/recovery start; operator xem ledger read-only và process chính xác, tiếp tục giữ/khôi phục các maintenance locks chưa bận trong cửa sổ recovery có hạn.
- Chờ đúng run chuyển `finished` và đọc status/steps trước khi sửa. Sau `succeeded`, kiểm tra version/config/migration, start đúng Gateway nếu hợp lệ, rồi verify-only nghiệm thu cùng member trước member tiếp theo. Timeout output có thể không được helper lưu; dùng SQLite ledger và report recovery riêng, không giả tạo receipt official CLI.

### Nâng bản 7.1: legacy exec approvals và plugin convergence

- Trên `nguyenvantieng`, updater 7.1 đã nâng package/Node nhưng post-update Doctor dừng do legacy `exec-approvals.json` khác canonical SQLite, plugin Codex chờ parent release install records, config còn `agents.list`. Không start Gateway khi config/state chưa hợp lệ; không xóa DB, ghi đè policy hoặc tự chọn policy quyền rộng hơn.
- Đối chiếu raw SQLite policy bằng SHA-256 với snapshot pre-startup-migration updater tự tạo và lịch sử cấu hình đã được duyệt. Trường hợp đã kiểm chứng: SQLite agent main full/off/full/autoAllowSkills đã được duyệt 2026-09-24, giữ nguyên byte qua upgrade; legacy file defaults rỗng và usage entries không phải nguồn policy được duyệt mới.
- Chỉ khi xác minh được policy có thẩm quyền, giữ nguyên SQLite; giữ legacy source bằng atomic rename sang tên `exec-approvals.json.conflict-retained-<incident>` trong cùng state root, không xóa hoặc in nội dung/socket token. Lưu hash trước và đối chiếu lại sau; đây là lưu bằng chứng xung đột, không tạo archive thủ công. Nếu chưa chứng minh được nguồn policy, dừng để hỏi owner, không bỏ migration gate.
- Chạy official `openclaw update repair --no-restart --yes --json --timeout 600` sau khi updater parent thoát; không `--accept-capabilities` hoặc force. So config migration trước/sau và SQLite policy hash, validate/start Gateway, chạy verify-only acceptance đúng member rồi mới tiếp tục suffix fleet. Ghi rõ raw fingerprint đã migrate nếu có, không giả báo unchanged.

### Fingerprint đổi do migration schema tương đương

- Không vô hiệu hóa fingerprint check. Trên Thanh Thái 9.4 → 6.10, updater thành công nhưng guard dừng vì duy nhất `agents.entries.main.tts.enabled=true` bị bỏ trong khi `tts.auto="inbound"` đã tồn tại và giữ nguyên. Source 6.10 `migrateLegacyTtsEnabled` xác nhận bỏ legacy `enabled` khi `auto` đã được đặt; không đổi chính sách đọc giọng.
- So fingerprint preflight với `openclaw.json.pre-update` hoặc `.last-good` do updater tự giữ, so diff **chỉ in key path, không in secret**. Chỉ khi xác minh toàn bộ khác biệt tương đương theo source chính thức, lưu `MIGRATION_REVIEW.json` chứa fingerprint/key path/nonsecret values và kết luận; không ghi `rawConfigPolicyUnchanged=true` cho lượt nâng này.
- Không chạy broad doctor fix, khôi phục khóa schema đã loại bỏ, hay sửa model/routing để vượt guard. Rerun đúng member target với `--verify-only` qua runner, nghiệm thu đầy đủ trước khi sang member khác. Báo cáo tổng hợp phải dẫn cả receipt nâng/migration-review và receipt verify, phân biệt migration tương đương với raw fingerprint không đổi.

### Lỗi timeout integrity của updater 9.4

Đã xác nhận cùng source SHA-256 và cùng lỗi trên `qnvuong`, `thanhthai`, `trolyketoancatminh` trong batch 2026-10-24; mỗi member được chẩn đoán riêng trước khi áp dụng timeout-only patch.

- Đã gặp trên `qnvuong` ngày 2026-10-24: mọi candidate check đạt nhưng `global install swap` dừng chính xác sau 30 giây với `Package rollback verification timed out`; package vẫn `2026.9.4`, không có swap/backup package đã kích hoạt, Gateway bản cũ phục hồi và probe khỏe. Không suy từ dòng `retained package tree changed` rằng package thực sự đã đổi: khi baseline scan timeout, baseline chưa được tạo nên recovery có thể phát thêm thông báo này.
- Đọc đúng source updater của member, xác nhận `createPackageIntegrityReader` giới hạn `Math.min(MAX_SCAN_MS, timeoutMs)` và `const MAX_SCAN_MS = 3e4`. Bản 6.10 chính thức bỏ trần 30 giây, nhận budget per-step; không chép bundle 6.10 sang 9.4 hoặc bỏ integrity checks.
- Chỉ khi chứng minh đúng lỗi trên, dùng `apply_patch` đổi duy nhất `const MAX_SCAN_MS = 3e4;` thành `const MAX_SCAN_MS = 6e5;` trong bundle updater 9.4 hiện hữu; ghi SHA-256 trước/sau, chạy `node --check`. Đây là tăng deadline lên 600 giây khớp `--timeout 600`, không bỏ hashing/metadata/rollback validation. Không sửa credential/config hoặc dùng npm force. User hiện miễn backup; ngoài lượt này vẫn backup trước sửa package.
- Trên Qnvuong file là `/usr/lib/node_modules/openclaw/dist/update-runner-Bzy-GVSl.mjs`; không suy tên bundle cho member khác. Lệnh dry-run/apply/rerun và input/output vẫn như driver phía trên. Updater thành công sẽ thay cả package bằng 6.10 chính thức nên patch tạm không được replay vào target. Nếu chưa nâng được, ghi rõ trạng thái và hoàn nguyên đúng hằng số khi không còn cần recovery.
- Khởi chạy lại **đúng member bị dừng**, vẫn qua preflight/model/probe/official updater/acceptance đầy đủ; không tiếp tục fleet khi member chưa đạt. Read-only cache warmup đã thử trên Qnvuong nhưng không giải quyết được trần 30 giây.

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

### Kết quả danh sách sáu member riêng ngày 2026-10-24

Hoàn tất cả sáu vào `19:53 UTC`, sau đó hậu kiểm live toàn danh sách đạt. Tất cả từ core `2026.9.9` lên `2026.10.6`, Node `24.22.1`; backup thủ công được tạo mặc định, không dùng miễn trừ `--no-backup` của batch cũ. Config fingerprint trước nâng khớp hậu kiểm, Gateway singleton/PID vẫn giữ từ acceptance, Telegram probe và model smoke no-delivery đạt; không gửi tin thử thật.

Receipt nằm dưới `/root/_Backups/openclaw-members-2026.10.6/<member>/<timestamp>/SUCCESS.json`:

| Member | Timestamp nâng | HOME |
|---|---|---|
| nndungct | `20261024T183253Z` | `/home/nndungct` |
| tranvanminh | `20261024T184842Z` | `/root` |
| nguyentienvinh | `20261024T190040Z` | `/home/nguyentienvinh` |
| daomac | `20261024T191959Z` | `/home/daomac` |
| avata | `20261024T193309Z` | `/root` |
| anhtuan | `20261024T194413Z` | `/root` |

Riêng `nndungct` có receipt verify-only sau triển khai lại `/zaloqr` tại timestamp `20261024T184651Z`; Zalo vẫn unlinked từ trước. `daomac` giữ Zalo linked/running/connected/probe OK, không đăng nhập lại. Không replay core/text-delivery guard bundle 9.9 sang 6.10 và không suy rằng probe đã kiểm thử mọi hành vi custom. Không sửa cron/nginx/Compose, image hoặc recreate container/member ngoài scope.

### Member có plugin owner `/zaloqr`

- Đã nâng `nndungct` từ `2026.9.9` lên `2026.10.6` ngày `2026-10-24`, runtime HOME `/home/nndungct`. Receipt nâng: `/root/_Backups/openclaw-members-2026.10.6/nndungct/20261024T183253Z/SUCCESS.json`. Telegram/model smoke đạt; Zalo `default` đã `linked=false` trước nâng nên chỉ member này dùng `--allow-unlinked-zalo`, không coi Zalo đã đăng nhập.
- Trước nâng, lưu riêng plugin liên kết trong `<state>/tools/telegram-zalo-owner-login`; archive mặc định của driver không bao gồm toàn bộ `tools`. Bản sao của lượt này: `/root/_Backups/nndungct-qr-before-2026.10.6-20261024T183253Z/telegram-zalo-owner-login.tar.gz`.
- Sau khi core đạt target, dùng đúng global skill `telegram-zalo-owner-login` chạy `--dry-run`, `--apply`, `--check` cho chính member, runtime/state/account đã xác minh. Helper sinh lại metadata API/minGateway đúng release `2026.10.6`, giữ nguyên payload đã kiểm chứng, owners và routing; không mở range tương thích rộng hoặc chép core bundle giữa phiên bản. Không tạo QR, login hoặc gửi tin trong quá trình này.
- Sau lần reload của helper, chạy driver `--verify-only` và kiểm tra Telegram/Gateway ổn định trước member kế tiếp. Không dùng runner danh sách 13 member cũ để thực hiện danh sách khác; chạy riêng từng member được chủ VPS chỉ định, giữ resource gate và dừng khi lỗi.
- Scope yêu cầu riêng ngày `2026-10-24` gồm `nndungct`, `tranvanminh`, `nguyentienvinh`, `daomac`, `avata`, `anhtuan`. HOME đã xác minh lần lượt `/home/nndungct`, `/root`, `/home/nguyentienvinh`, `/home/daomac`, `/root`, `/root`; `anhtuan` có state active trong container `/root/.openclaw`, không suy HOME từ bind mount `/home/anhtuan`. Không coi việc có trong danh sách là bằng chứng đã nghiệm thu; xem receipt từng member.

Không sửa `.env`, credential, Chrome profile, cron/nginx/compose, các member khác hay bot sidecar chỉ vì nâng OpenClaw. Không xóa sessions/database hoặc dùng `docker system prune`. Trước khi lưu/cập nhật skill, quét secret; không đưa token/API key/cookie/password/private key thật vào tài liệu, log công khai hoặc câu trả lời.
