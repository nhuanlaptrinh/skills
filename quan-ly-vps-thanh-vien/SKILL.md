---
name: quan-ly-vps-thanh-vien
description: Tạo, liệt kê, kiểm tra và chuẩn hóa tài nguyên các VPS thành viên Docker bằng manage-user.sh tại cấu trúc Apps hiện hành.
---

# Quản Lý VPS Thành Viên

Skill này dùng để tạo, liệt kê, kiểm tra hoặc giới hạn tài nguyên các container member VPS trên máy chính.

## Source Of Truth

- Project: `/root/Apps/member_vps/docker-users`
- Script: `/root/Apps/member_vps/docker-users/manage-user.sh`
- Dữ liệu persistent: `/root/Apps/member_vps/docker-users/data/<username>`
- Mount trong container: `/home/<username>`
- Image mặc định: `member_vps-phukiengiakho:latest`

## Giới Hạn Mặc Định

Container tạo mới mặc định có:

- CPU: `2`
- RAM: `4g`
- Tổng RAM + swap: `6g`
- PID tối đa: `1024`
- Mutable disk guard: `10 GiB`
- Restart policy: `unless-stopped`

Ngoại lệ disk guard hiện hành:

- `user-quocphong`: `25 GiB`
- `user-anhlaptrinhthu`: không giới hạn dung lượng

Có thể override lúc chạy script bằng các biến:

- `MEMBER_VPS_CPUS`
- `MEMBER_VPS_MEMORY`
- `MEMBER_VPS_MEMORY_SWAP`
- `MEMBER_VPS_PIDS_LIMIT`

## Lệnh Quản Lý Chính

1. **Liệt kê danh sách thành viên:**
   ```bash
   /root/Apps/member_vps/docker-users/manage-user.sh list
   ```

2. **Tạo thành viên mới:**
   ```bash
   /root/Apps/member_vps/docker-users/manage-user.sh create <username> <password> [ssh_port] [web_port]
   ```
   Không ghi mật khẩu thật vào log, tài liệu hoặc câu trả lời.

3. **Xem một thành viên:**
   ```bash
   /root/Apps/member_vps/docker-users/manage-user.sh show <username>
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
   /root/Apps/member_vps/docker-users/manage-user.sh disk-status
   ```

## Disk Guard

- Script: `/root/Apps/member_vps/docker-users/member-vps-disk-guard.sh`
- Cấu hình: `/root/Apps/member_vps/docker-users/member-vps-disk-guard.conf`
- Trạng thái gần nhất: `/var/lib/member-vps-disk-guard/status.tsv`
- Systemd timer: `member-vps-disk-guard.timer`, chạy mỗi 10 phút với CPU nice `19` và I/O class `idle`.
- Tổng dung lượng được tính bằng writable layer `SizeRw` cộng các bind mount persistent nằm dưới thư mục `data` của project. Shared image layers không tính riêng cho từng member.
- Dry-run/báo cáo: `member-vps-disk-guard.sh --report`.
- Chạy enforce thật: `member-vps-disk-guard.sh --enforce`; container đang chạy sẽ bị `docker stop` khi tổng dung lượng đạt hoặc vượt giới hạn.
- Docker hiện dùng `overlayfs` trên root filesystem `ext4`; thử nghiệm xác nhận `docker run --storage-opt size=...` chỉ lưu option nhưng không thực thi quota. Vì vậy disk guard là cơ chế stop-at-limit, không phải filesystem hard quota và có thể vượt nhẹ trong khoảng giữa hai lần kiểm tra.
- Không tự chuyển Docker sang XFS/project quota hoặc recreate container để tạo hard quota nếu chưa có maintenance plan và backup dữ liệu writable layer.

Script hiện không có chế độ dry-run. Trước thay đổi hàng loạt phải dùng `docker inspect` và `docker stats --no-stream` để audit, sau đó snapshot cấu hình vào `/root/_Backups`.

## Quy Trình Tạo Mới Thành Viên (Bắt buộc)

Khi người dùng yêu cầu tạo một thành viên mới, AI phải thực hiện đầy đủ các bước sau:
1. **Kiểm tra cổng port:** Đảm bảo cổng dự định cấp chưa được sử dụng (`ss -tlnp`).
2. **Chạy lệnh tạo user:** Dùng script source of truth và truyền mật khẩu an toàn, SSH port, web port khi cần.
3. **Kiểm tra firewall:** Script tự gọi UFW cho SSH/web port nếu UFW có sẵn; vẫn phải kiểm tra lại rule và port listen.
4. **Kiểm tra giới hạn:** Xác nhận CPU `2e9`, RAM `4294967296`, RAM+swap `6442450944`, PID `1024`.
5. **Kiểm tra và bàn giao:** Kiểm tra container running, SSH/web port, mount riêng và không lộ mật khẩu.
6. **Disk guard:** Container mới tự nhận mức mặc định `10 GiB` theo tên `user-<username>`; chạy `manage-user.sh disk-status` để xác nhận xuất hiện trong báo cáo.

## Quy Tắc An Toàn & Bảo Mật

- **Không recreate tùy tiện:** Chỉ `/home/<username>` được bind-mount mặc định. Dữ liệu trong `/root` của container có thể mất khi xóa/tạo lại.
- **Giới hạn tài nguyên:** Không bỏ CPU/RAM/PID limit nếu chưa có yêu cầu rõ ràng và kiểm tra sức tải VPS chính.
- **Thay đổi live:** Trước khi hạ RAM container đang chạy, kiểm tra mức dùng hiện tại để tránh OOM; theo dõi `memory.events`, dịch vụ và port sau cập nhật.
- **Mật khẩu & Token:** Tuyệt đối không ghi mật khẩu thật hoặc token vào file nhật ký thay đổi (`/root/_Second_AI_Brain/06_Nhat_Ky_Thay_Doi.md`). Thay vào đó hãy dùng placeholder hoặc chỉ ghi nhận hành động.
- **Kiểm tra trùng cổng:** Script `manage-user.sh` tự động kiểm tra cổng port đã bị sử dụng chưa, nhưng AI nên chủ động kiểm tra bằng `ss -tlnp` hoặc `docker ps` trước để tư vấn cổng trống phù hợp cho người dùng.
- **Tách dữ liệu:** Mỗi member phải dùng đúng `/root/Apps/member_vps/docker-users/data/<username>`; không mount chung folder giữa nhiều member.
- **Khi vượt disk guard:** Điều tra và dọn đúng dữ liệu của member trước; không tự khởi động lại container liên tục khi chưa giảm xuống dưới giới hạn.
