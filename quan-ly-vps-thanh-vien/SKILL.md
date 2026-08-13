---
name: quan-ly-vps-thanh-vien
description: Tạo, liệt kê, kiểm tra, chuẩn hóa tài nguyên và dừng/bật lại OpenClaw riêng cho các VPS thành viên Docker tại cấu trúc production hiện hành.
---

# Quản Lý VPS Thành Viên

Skill này dùng để tạo, liệt kê, kiểm tra hoặc giới hạn tài nguyên các container member VPS trên máy chính.

## Source Of Truth

- Project: `/root/docker-users`
- Script: `/root/docker-users/manage-user.sh`
- Dữ liệu persistent: `/root/docker-users/data/<username>`; kiểm tra `docker inspect` vì member mới/custom có thể tách `home` và `root` thành các bind mount riêng.
- Image fallback hiện hành của `manage-user.sh`: `vps-user-env`; có thể override bằng `MEMBER_VPS_IMAGE`.

## Giới Hạn Mặc Định

Container tạo mới mặc định có:

- CPU: `2`
- RAM: `4g` (`6g` gồm swap)
- Mutable disk guard: `17 GiB`
- Restart policy: `unless-stopped`

Ngoại lệ disk guard hiện hành:

- `user-dinh`: `24 GiB`
- PMT: `25 GiB`, tính gộp `user-pmt`, writable layer của `n8n-pmt-app`/`n8n-pmt-runners`, bind data và named volume `root_n8n_pmt_data`.

## Lệnh Quản Lý Chính

1. **Liệt kê danh sách thành viên:**
   ```bash
   /root/docker-users/manage-user.sh list
   ```

2. **Tạo thành viên mới:**
   ```bash
   /root/docker-users/manage-user.sh create <username> <password> <ssh_port> <web_port>
   ```
   Không ghi mật khẩu thật vào log, tài liệu hoặc câu trả lời.

3. **Xem một thành viên:**
   ```bash
   /root/docker-users/manage-user.sh show <username>
   ```

4. **Kiểm tra live resource:**
   ```bash
   docker stats --no-stream user-<username>
   ```

5. **Áp giới hạn live cho container có sẵn:**
   ```bash
   docker update --cpus 2 --memory 4g --memory-swap 6g --pids-limit 1024 user-<username>
   ```

6. **Xác minh sau cập nhật:**
   ```bash
   docker inspect user-<username> --format 'cpu={{.HostConfig.NanoCpus}} memory={{.HostConfig.Memory}} memory_swap={{.HostConfig.MemorySwap}} pids={{.HostConfig.PidsLimit}} running={{.State.Running}} restart_count={{.RestartCount}} oom={{.State.OOMKilled}}'
   ```

7. **Xem dung lượng mutable của tất cả member:**
   ```bash
   /root/docker-users/manage-user.sh disk-status
   ```

## Disk Guard

- Script: `/root/docker-users/member-vps-disk-guard.sh`
- Cấu hình: `/root/docker-users/member-vps-disk-guard.conf`
- Trạng thái gần nhất: `/var/lib/member-vps-disk-guard/status.tsv`
- Systemd timer: `member-vps-disk-guard.timer`, chạy mỗi 5 phút với CPU nice `19` và I/O class `idle`.
- Tổng dung lượng thông thường được tính bằng writable layer `SizeRw` cộng các bind mount persistent nằm dưới thư mục `data` của project. Shared image layers không tính riêng cho từng member.
- Riêng PMT, guard tính thêm writable layer của `n8n-pmt-app` và `n8n-pmt-runners` cùng toàn bộ named volume `root_n8n_pmt_data`; khi đạt `25 GiB`, enforce sẽ dừng app, runner và `user-pmt` nếu đang chạy.
- Dry-run/báo cáo: `member-vps-disk-guard.sh --report`.
- Chạy enforce thật: `member-vps-disk-guard.sh --enforce`; container đang chạy sẽ bị `docker stop` khi tổng dung lượng đạt hoặc vượt giới hạn.
- Docker hiện dùng `overlayfs` trên root filesystem `ext4`; thử nghiệm xác nhận `docker run --storage-opt size=...` chỉ lưu option nhưng không thực thi quota. Vì vậy disk guard là cơ chế stop-at-limit, không phải filesystem hard quota và có thể vượt nhẹ trong khoảng giữa hai lần kiểm tra.
- Không tự chuyển Docker sang XFS/project quota hoặc recreate container để tạo hard quota nếu chưa có maintenance plan và backup dữ liệu writable layer.

Trước thay đổi hàng loạt phải dùng `member-vps-disk-guard.sh --report`, `docker inspect` và `docker stats --no-stream` để audit, sau đó snapshot cấu hình vào `/root/_Backups`.

## OpenClaw Trong Member VPS

- Các container legacy hiện có thể lưu `/root/.openclaw` trong writable layer. Hai bind mount mặc định chỉ là `/workspace` và `/root/data`; không recreate hoặc xóa container nếu chưa backup dữ liệu writable layer.
- Gateway mặc định lắng nghe loopback tại cổng `18789`; Telegram polling chỉ hoạt động khi tiến trình `openclaw-gateway` đang chạy.
- Kiểm tra read-only trước khi sửa:
  ```bash
  docker top user-<username> -eo pid,ppid,user,etimes,stat,args
  docker exec user-<username> sh -lc "ss -lntp | grep ':18789 ' || true"
  docker exec user-<username> sh -lc 'HOME=/home/<username> openclaw gateway status'
  docker exec user-<username> sh -lc 'HOME=/home/<username> openclaw channels status --probe'
  ```
- Không mặc định mọi member đều dùng `HOME=/home/<username>`. Container legacy có thể giữ config thật tại `/root/.openclaw`; xác định `HOME` đúng bằng `docker top`, kiểm tra file config tồn tại và chạy `openclaw config validate` với từng HOME khả dĩ trước khi thêm Supervisor. Block Supervisor phải dùng đúng HOME chứa config đang hoạt động, nếu không Gateway có thể lên nhưng Telegram báo `not configured`.
- Một số image tạo lại `/etc/supervisor/conf.d/member-vps.conf` từ `/usr/local/bin/member-vps-entrypoint.sh` mỗi lần container khởi động. Nếu chỉ sửa file supervisor đã sinh, thay đổi sẽ mất sau `docker restart`.
- Member `user-trolyketoancatminh` dùng OpenClaw persistent tại host `/root/Apps/member_vps/docker-users/data/trolyketoancatminh/.openclaw`, tương ứng `HOME=/home/trolyketoancatminh` trong container. `/root/.openclaw` là symlink tương thích tới HOME persistent để các đường dẫn lịch sử cũ vẫn đọc được.
- Member này chạy hai agent tách biệt: `main` dùng `workspace`, còn `ai_catminh` dùng `workspace_AI_CatMinh`; mỗi agent có Telegram account và workspace riêng. Bản `AI_CatMinh` trên OpenClaw VPS chính phải giữ `enabled=false` khi bot đang chạy trong member để tránh hai Gateway polling cùng token.
- Backup migration và rollback của member này nằm dưới `/root/_Backups/openclaw/trolyketoancatminh/20260808T183813Z`; không xóa `/root/.openclaw.pre-persistent-20260808T183813Z` trong container nếu chưa xác nhận không còn cần rollback và đã kiểm tra disk guard.
- Muốn OpenClaw tự lên bền vững, backup entrypoint root-only vào `/root/_Backups`, sau đó thêm chương trình sau vào heredoc supervisor bên trong entrypoint của đúng container:
  ```ini
  [program:openclaw-gateway]
  command=/usr/bin/openclaw gateway run
  environment=HOME="/home/<username>"
  autorestart=true
  startsecs=5
  startretries=20
  stdout_logfile=/tmp/openclaw-supervisor.log
  stderr_logfile=/tmp/openclaw-supervisor.log
  ```
- Kiểm tra cú pháp bản entrypoint đã sửa bằng `bash -n`, copy lại đúng container, rồi `docker restart user-<username>` để entrypoint sinh supervisor config mới.
- Xác minh sau sửa: container không OOM, `openclaw-gateway` là child của `supervisord`, cổng `18789` đang listen, `gateway health` báo `OK`, và account Telegram báo `running`, `connected`, `works`, `audit ok`.
- Nếu Telegram vẫn `connected` nhưng trả thông báo chung `Something went wrong while processing your request`, kiểm tra log agent. Lỗi `No callable tools remain after resolving explicit tool allowlist` kèm `tools.allow: group:messaging` nghĩa là allowlist không khớp tool đã đăng ký; backup `openclaw.json`, gỡ riêng `tools.allow`, giữ nguyên `tools.profile`/media/channels và chạy `openclaw config validate`. Sau đó phải restart đúng tiến trình Gateway do Telegram connector có thể giữ snapshot policy cũ dù config hot-reload; chờ polling về `connected`, rồi xác minh trên đúng session DM bằng `openclaw agent` không có `--deliver` trước khi yêu cầu người dùng nhắn lại.
- Để phòng lỗi này tái diễn, dùng global skill `/root/.agents/skills/openclaw-member-config-guard/SKILL.md`; guard chỉ tự gỡ `group:messaging`, backup config, validate và restart riêng Gateway khi tool policy đổi.
- Rollback: copy entrypoint backup trở lại container, đặt owner `root:root`, mode `0755`, rồi restart đúng container. Không recreate container vì dữ liệu ngoài bind mount có thể mất.
- Không in nội dung token, credential, cookie, `.env` hoặc toàn bộ log plugin có thể chứa session/cookie. Chỉ dùng Telegram `getMe`/`getWebhookInfo` với output đã lọc khi cần xác minh token và hàng đợi; không tự gửi tin thật.

### Đổi Tên Member Hoặc Thư Mục Dữ Liệu

- Đổi riêng tên thư mục host khi container đang chạy không phải là đổi tên member hoàn chỉnh. Bind mount hiện tại vẫn giữ inode nên dịch vụ có thể chạy tạm thời, nhưng `docker inspect` vẫn lưu source cũ và lần restart sau có thể tạo/mount một thư mục rỗng.
- Trước khi restart, so sánh `docker inspect`, `stat` đường dẫn host, `stat` mount trong container và `findmnt -T`. Source Docker, đường dẫn host và mount trong container phải cùng inode/dữ liệu.
- Nếu chỉ cần phục hồi production, đưa dữ liệu về đúng source đang ghi trong `docker inspect`. Docker có thể tự tạo lại source cũ trong lúc sửa; nếu dữ liệu bị lồng vào thư mục rỗng, di chuyển inode dữ liệu ra một sibling tạm rồi dùng `mv -T` thay thế thư mục rỗng, sau đó kiểm tra lại inode trước khi restart.
- `docker rename` chỉ đổi tên container; nó không đổi hostname, Linux user, HOME, mount destination, label hoặc source path. Muốn đổi toàn bộ sang username mới phải có kế hoạch migrate/recreate riêng, backup cả writable layer `/root`, dữ liệu bind mount, cổng và credential; không làm trong một task kiểm tra nhanh.

#### Quy Trình Đổi Tên End-to-End

1. Audit container cũ bằng `docker inspect`, `docker top`, `docker stats`, port, mount, inode, HTTP/SSH và OpenClaw health; xác nhận container đích và thư mục đích chưa tồn tại.
2. Tạo backup root-only gồm Docker inspect, entrypoint, Supervisor config, `/root/.openclaw` và archive dữ liệu bind mount. Nếu OpenClaw active nằm trong writable layer `/root`, phải snapshot toàn bộ writable layer bằng `docker commit`; không chỉ copy thư mục `/home`.
3. Snapshot image từ member có thể chứa credential và trạng thái riêng tư. Chỉ giữ local, không push/export, không dùng cho member khác và ghi rõ image/container rollback trong project note.
4. Dừng container cũ, chốt snapshot cuối, đổi container cũ sang tên backup không bắt đầu bằng `user-`, dùng `mv -T` đổi source data, rồi tạo container mới với nguyên port, limit, restart policy nhưng dùng container name, hostname, service label, source path và mount destination mới.
5. Nếu dữ liệu hoặc virtualenv còn đường dẫn tuyệt đối `/home/<old>`, tạo symlink tương thích `/home/<old>` → `/home/<new>` trong container mới thay vì sửa hàng loạt ngay trong cửa sổ migration.
6. Nếu bất kỳ bước nào lỗi: xóa riêng container mới, chuyển data về source cũ, đổi container rollback về tên cũ và start lại. Không xóa image/container cũ trước khi container mới qua restart thật.
7. Xác minh sau một lần `docker restart`: hostname/label/mount mới, inode host và container trùng nhau, SSH/web/XRDP/Supervisor/OpenClaw đều hoạt động, Telegram `works, audit ok`, agent test không `--deliver`, không OOM và disk guard nhận đúng tên mới.
8. Lưu ý `docker commit` chuyển dung lượng writable cũ thành image layer; disk guard chỉ báo phần writable mới cộng bind mount. Dùng thêm `docker system df`, image size và backup retention để đánh giá dung lượng thật.

### Tạm Dừng Riêng OpenClaw

Dùng quy trình này khi cần dừng Gateway nhưng vẫn giữ container, SSH, Nginx và XRDP hoạt động:

1. Xác nhận đúng container, tiến trình và cổng trước khi sửa:
   ```bash
   docker inspect user-<username> --format 'running={{.State.Running}} status={{.State.Status}} mounts={{json .Mounts}}'
   docker top user-<username> -eo pid,ppid,user,etimes,stat,args
   docker exec user-<username> sh -lc "ss -lntp | grep ':18789 ' || true"
   ```
2. Kiểm tra `/etc/supervisor/conf.d/member-vps.conf` và entrypoint thực tế. Nếu entrypoint sinh lại Supervisor config khi container khởi động, phải sửa đồng bộ cả hai file.
3. Backup hai file root-only vào `/root/_Backups` rồi dùng bản copy cục bộ và `apply_patch`; không in nội dung file env/secret. Trong đúng block `[program:openclaw-gateway]`, đặt:
   ```ini
   autostart=false
   autorestart=false
   ```
4. Kiểm tra `bash -n` cho entrypoint, copy hai file lại đúng container, giữ owner/mode ban đầu rồi yêu cầu Supervisor reload:
   ```bash
   docker kill --signal HUP user-<username>
   ```
   `SIGHUP` sẽ reload Supervisor và khởi động lại ngắn các service do Supervisor quản lý; phải kiểm tra lại SSH/Nginx/XRDP.
5. Xác minh OpenClaw không còn tiến trình hoặc cổng listen, container vẫn running và các dịch vụ còn lại đang chạy:
   ```bash
   docker top user-<username> -eo pid,ppid,user,etimes,stat,args
   docker exec user-<username> sh -lc "pgrep -af openclaw-gateway || true; ss -lntp | grep ':18789 ' || true"
   docker inspect user-<username> --format 'running={{.State.Running}} status={{.State.Status}} restart_count={{.RestartCount}} oom={{.State.OOMKilled}}'
   ```

### Bật Lại OpenClaw

- Backup trạng thái đang dừng trước khi sửa.
- Trong đúng block `[program:openclaw-gateway]` của entrypoint và Supervisor config, gỡ `autostart=false` hoặc đặt `autostart=true`, đồng thời đặt `autorestart=true`.
- Kiểm tra cú pháp, copy lại, chạy `docker kill --signal HUP user-<username>`, rồi xác minh Gateway health, cổng `18789` và channel probe.
- Không recreate container chỉ để bật lại OpenClaw.

## Quy Trình Tạo Mới Thành Viên (Bắt buộc)

Khi người dùng yêu cầu tạo một thành viên mới, AI phải thực hiện đầy đủ các bước sau:
1. **Kiểm tra cổng port:** Đảm bảo cổng dự định cấp chưa được sử dụng (`ss -tlnp`).
2. **Chạy lệnh tạo user:** Dùng script source of truth và truyền mật khẩu an toàn, SSH port, web port khi cần.
3. **Kiểm tra firewall:** Script tự gọi UFW cho SSH/web port nếu UFW có sẵn; vẫn phải kiểm tra lại rule và port listen.
4. **Kiểm tra giới hạn:** Xác nhận CPU `2e9`, RAM `4294967296`, RAM+swap `6442450944`, PID `1024`.
5. **Kiểm tra và bàn giao:** Kiểm tra container running, SSH/web port, mount riêng và không lộ mật khẩu.
6. **Disk guard:** Container mới tự nhận mức mặc định `17 GiB` theo tên `user-<username>`; chạy `manage-user.sh disk-status` để xác nhận xuất hiện trong báo cáo.

## Quy Tắc An Toàn & Bảo Mật

- **Không recreate tùy tiện:** Chỉ `/home/<username>` được bind-mount mặc định. Dữ liệu trong `/root` của container có thể mất khi xóa/tạo lại.
- **Giới hạn tài nguyên:** Không bỏ CPU/RAM/PID limit nếu chưa có yêu cầu rõ ràng và kiểm tra sức tải VPS chính.
- **Thay đổi live:** Trước khi hạ RAM container đang chạy, kiểm tra mức dùng hiện tại để tránh OOM; theo dõi `memory.events`, dịch vụ và port sau cập nhật.
- **Mật khẩu & Token:** Tuyệt đối không ghi mật khẩu thật hoặc token vào file nhật ký thay đổi (`/root/_Second_AI_Brain/06_Nhat_Ky_Thay_Doi.md`). Thay vào đó hãy dùng placeholder hoặc chỉ ghi nhận hành động.
- **Đổi mật khẩu SSH:** Trước khi chạy `passwd`, kiểm tra entrypoint có gọi `chpasswd` mỗi lần container khởi động hay không. Nếu có, backup entrypoint root-only rồi thêm marker khởi tạo để lần restart sau không ghi đè mật khẩu mới; đặt mật khẩu qua TTY, không đưa mật khẩu vào command line, file skill hoặc nhật ký. Xác minh bằng một phiên SSH ép dùng `PreferredAuthentications=password` và không restart container chỉ để thử.
- **Kiểm tra trùng cổng:** Script `manage-user.sh` tự động kiểm tra cổng port đã bị sử dụng chưa, nhưng AI nên chủ động kiểm tra bằng `ss -tlnp` hoặc `docker ps` trước để tư vấn cổng trống phù hợp cho người dùng.
- **Tách dữ liệu:** Mỗi member phải dùng đúng `/root/Apps/member_vps/docker-users/data/<username>`; không mount chung folder giữa nhiều member.
- **Khi vượt disk guard:** Điều tra và dọn đúng dữ liệu của member trước; không tự khởi động lại container liên tục khi chưa giảm xuống dưới giới hạn.
