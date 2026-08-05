---
name: google-drive-vps-sync
description: Thiết lập đồng bộ hai chiều thư mục Google Drive My Drive và VPS bằng rclone bisync, xác thực OAuth, đồng bộ thủ công hoặc tự động bằng Cron mỗi phút. Dùng khi cần sync PC ↔ Google Drive ↔ VPS trên Ubuntu mà không viết Google Drive API.
---

# Google Drive VPS Sync

## Khi nào dùng skill này

Dùng skill này khi người dùng muốn thiết lập hoặc hướng dẫn đồng bộ dữ liệu theo mô hình:

```text
PC
↓ Google Drive Desktop
Google Drive (My Drive)
↓ rclone
VPS
```

Phù hợp khi:

- Đồng bộ hai chiều giữa PC và VPS thông qua Google Drive.
- Không muốn viết Google Drive API.
- Chấp nhận độ trễ khoảng 1 phút.
- Muốn cấu hình nhanh và ổn định.

## Điều kiện

- VPS Ubuntu.
- Quyền root hoặc sudo.
- Google Drive Desktop đã đăng nhập trên PC.
- VPS có Internet.

## Thông tin cần hỏi người dùng trước khi chạy

Trước khi cấu hình đồng bộ, luôn hỏi người dùng tên thư mục Google Drive muốn đồng bộ.

Nếu người dùng chưa cung cấp, hỏi ngắn gọn:

```text
Bạn muốn đồng bộ thư mục nào trên Google Drive? Nếu chưa có tên riêng, mình sẽ dùng mặc định: SYNCVPS.
```

Quy ước mặc định:

```env
GOOGLE_DRIVE_FOLDER=SYNCVPS
VPS_SYNC_FOLDER=/root/SYNCVPS
```

Nếu người dùng cung cấp tên khác, ví dụ `ARABICA_CAFE`, thì dùng:

```env
GOOGLE_DRIVE_FOLDER=ARABICA_CAFE
VPS_SYNC_FOLDER=/root/ARABICA_CAFE
```

Các lệnh bên dưới đang dùng ví dụ mặc định `SYNCVPS`; khi chạy thực tế phải thay theo thư mục người dùng cung cấp.

## Kiểm tra và cài đặt rclone

Trước tiên kiểm tra VPS đã có `rclone` chưa:

```bash
command -v rclone >/dev/null 2>&1 && rclone version
```

Nếu đã hiện phiên bản `rclone` thì bỏ qua bước cài đặt.

Nếu chưa có `rclone`, chạy trên VPS:

```bash
curl https://rclone.org/install.sh | sudo bash
```

Kiểm tra:

```bash
rclone version
```

## Cấu hình Google Drive

Chạy:

```bash
rclone config
```

Thực hiện theo:

```text
n
```

Tên Remote:

```text
gdrive
```

Storage:

```text
drive
```

Hoặc chọn số:

```text
24
```

Không nhập:

```text
Google Drive
```

Vì rclone chỉ nhận backend là `drive`.

Các bước tiếp theo:

```text
client_id:
=> Bấm Enter để bỏ qua

client_secret:
=> Bấm Enter để bỏ qua

scope:
=> Nhập 1 rồi Enter

service_account_file:
=> Bấm Enter để bỏ qua

advanced config:
=> Nhập n rồi Enter

auto config:
=> Nhập n rồi Enter
```

Lưu ý: `Bấm Enter để bỏ qua` nghĩa là không nhập nội dung gì, chỉ bấm phím `Enter` để dùng mặc định.

Sau đó VPS sẽ hiện hướng dẫn chạy lệnh `rclone authorize` trên máy có trình duyệt, thường là PC Windows. Ví dụ VPS có thể đưa ra lệnh dạng:

```text
rclone authorize "drive" "eyJjbGllbnRfaWQiOiIiLCJjbGllbnRfc2VjcmV0IjoiIn0"
```

Trên Windows, nếu đang dùng file `rclone.exe`, chạy lệnh tương ứng dạng:

```cmd
rclone.exe authorize "drive" "eyJjbGllbnRfaWQiOiIiLCJjbGllbnRfc2VjcmV0IjoiIn0"
```

Sau khi chạy xong trên PC, rclone sẽ trả về một đoạn token dài. Copy toàn bộ token đó rồi quay lại VPS, dán vào dòng:

```text
config_token>
```

Sau khi dán token vào `config_token>`, bấm `Enter` để tiếp tục cấu hình trên VPS.

Khi lấy được token từ máy Windows, có thể lưu lại token vào file `.env` của skill để tra cứu nội bộ:

```bash
nano /root/.agents/skills/google-drive-vps-sync/.env
```

Điền vào dòng:

```env
RCLONE_CONFIG_TOKEN='DAN_TOAN_BO_TOKEN_VAO_DAY'
```

Nếu đã copy `.env` sang thư mục sync, cập nhật thêm file này:

```bash
nano /root/SYNCVPS/.env
```

Lưu ý: token này là thông tin nhạy cảm, không commit lên GitHub và không gửi cho người khác.

## Xác thực bằng máy Windows

Trên Windows tải rclone.

Mở CMD trong thư mục chứa `rclone.exe`.

Copy đúng lệnh `rclone authorize ...` mà VPS hiển thị. Nếu lệnh bắt đầu bằng `rclone authorize`, có thể đổi thành `rclone.exe authorize` khi chạy trên Windows.

Ví dụ:

```cmd
rclone.exe authorize "drive" "eyJjbGllbnRfaWQiOiIiLCJjbGllbnRfc2VjcmV0IjoiIn0"
```

Sau đó:

- Trình duyệt trên PC sẽ mở ra.
- Đăng nhập Google và cấp quyền.
- CMD sẽ trả về một đoạn token dài.
- Copy toàn bộ token đó.
- Quay lại VPS, dán token vào dòng `config_token>`.
- Bấm `Enter` để cấu hình tiếp.

Tiếp tục:

```text
Shared Drive
=> n

Keep remote
=> y
```

Kiểm tra:

```bash
rclone lsd gdrive:
```

Nếu hiện danh sách thư mục là thành công.

## Đồng bộ hai chiều thư mục

Trước bước này phải xác nhận tên thư mục Google Drive với người dùng. Ví dụ người dùng chọn thư mục:

```text
SYNCVPS
```

Nếu thư mục chưa có trên Google Drive, tạo bằng:

```bash
rclone mkdir gdrive:SYNCVPS
```

Tạo thư mục trên VPS:

```bash
mkdir -p /root/SYNCVPS
```

Copy file cấu hình `.env` của skill vào thư mục sync nếu file `.env` nguồn tồn tại:

```bash
cp /root/.agents/skills/google-drive-vps-sync/.env /root/SYNCVPS/.env
```

Nếu `/root/SYNCVPS/.env` đã tồn tại và không muốn ghi đè, dùng:

```bash
[ -f /root/SYNCVPS/.env ] || cp /root/.agents/skills/google-drive-vps-sync/.env /root/SYNCVPS/.env
```

Chạy thử kiểm tra trước, chưa thay đổi dữ liệu thật:

```bash
rclone bisync gdrive:SYNCVPS /root/SYNCVPS --dry-run --resync
```

Nếu kết quả ổn, chạy lần đầu để tạo trạng thái đồng bộ hai chiều:

```bash
rclone bisync gdrive:SYNCVPS /root/SYNCVPS --resync --progress
```

Các lần sau chạy bình thường:

```bash
rclone bisync gdrive:SYNCVPS /root/SYNCVPS --progress
```

Kiểm tra:

```bash
ls -l /root/SYNCVPS
```

## Đồng bộ tự động bằng Cron

Mở Cron:

```bash
crontab -e
```

Thêm:

```cron
* * * * * /usr/bin/rclone bisync gdrive:SYNCVPS /root/SYNCVPS >/dev/null 2>&1
```

Khuyến nghị khi chạy Cron thực tế: dùng `flock` để tránh một cặp sync tự chạy chồng lên chính nó, và ghi log ra ngoài thư mục sync:

```cron
* * * * * /usr/bin/flock -n /tmp/rclone-bisync-syncvps.lock /usr/bin/rclone bisync gdrive:SYNCVPS /root/SYNCVPS --log-file /var/log/rclone-bisync-syncvps.log --log-level INFO >/dev/null 2>&1
```

Kiểm tra:

```bash
crontab -l
```

## Chạy nhiều cặp thư mục cùng lúc

Có thể chạy nhiều cặp đồng bộ cùng lúc nếu mỗi cặp là một cặp thư mục riêng biệt, ví dụ:

```text
gdrive:ARABICA_CAFE ↔ /root/SYNCVPS
gdrive:GG ADS       ↔ /root/SYNCVPS11
```

Hai cặp riêng như trên thường không xung đột với nhau, kể cả Cron cùng chạy trong một phút, vì mỗi cặp có đường dẫn, trạng thái bisync, lock và log riêng.

Khi tạo thêm một cặp sync mới, phải dùng riêng:

- Thư mục Google Drive riêng.
- Thư mục VPS riêng.
- Lệnh `--dry-run --resync` riêng.
- Lệnh `--resync` lần đầu riêng.
- Lock file riêng, ví dụ `/tmp/rclone-bisync-gg-ads.lock`.
- Log file riêng, ví dụ `/var/log/rclone-bisync-gg-ads.log`.

Ví dụ Cron cho 2 cặp riêng:

```cron
* * * * * /usr/bin/flock -n /tmp/rclone-bisync-arabica-cafe.lock /usr/bin/rclone bisync gdrive:ARABICA_CAFE /root/SYNCVPS --log-file /var/log/rclone-bisync-arabica-cafe.log --log-level INFO >/dev/null 2>&1
* * * * * /usr/bin/flock -n /tmp/rclone-bisync-gg-ads.lock /usr/bin/rclone bisync 'gdrive:GG ADS' /root/SYNCVPS11 --log-file /var/log/rclone-bisync-gg-ads.log --log-level INFO >/dev/null 2>&1
```

Không dùng chung một thư mục VPS cho nhiều thư mục Google Drive, và không sync một thư mục Google Drive vào nhiều thư mục VPS khác nhau, trừ khi hiểu rất rõ rủi ro. Các kiểu cấu hình này dễ gây ghi đè, xoá nhầm hoặc conflict.

Nếu muốn giảm tải API Google Drive, có thể lệch phút các job thay vì để tất cả cùng `* * * * *`, ví dụ:

```cron
* * * * * /usr/bin/flock -n /tmp/rclone-bisync-arabica-cafe.lock /usr/bin/rclone bisync gdrive:ARABICA_CAFE /root/SYNCVPS --log-file /var/log/rclone-bisync-arabica-cafe.log --log-level INFO >/dev/null 2>&1
*/2 * * * * /usr/bin/flock -n /tmp/rclone-bisync-gg-ads.lock /usr/bin/rclone bisync 'gdrive:GG ADS' /root/SYNCVPS11 --log-file /var/log/rclone-bisync-gg-ads.log --log-level INFO >/dev/null 2>&1
```

Lưu ý: `flock` chỉ chống chạy chồng cho cùng một cặp sync. Nó không ngăn conflict nội dung nếu người dùng sửa cùng một file ở PC và VPS trước khi sync kịp hoàn tất.

## Ví dụ dễ hiểu

Khi dùng `rclone bisync gdrive:SYNCVPS /root/SYNCVPS`, dữ liệu đi hai chiều qua Google Drive:

```text
PC ↔ Google Drive/SYNCVPS ↔ VPS /root/SYNCVPS
```

Ví dụ:

- Bạn tạo `demo.txt` trên PC trong thư mục `SYNCVPS` của Google Drive Desktop.
- Google Drive Desktop tự upload `demo.txt` lên Google Drive.
- Cron trên VPS chạy `rclone bisync`, file `demo.txt` xuất hiện trong `/root/SYNCVPS`.
- Bạn tạo `server.txt` trong `/root/SYNCVPS` trên VPS.
- Cron trên VPS chạy `rclone bisync`, file `server.txt` được đẩy lên Google Drive rồi xuất hiện trên PC.
- Nếu bạn xoá `demo.txt` trên VPS, lần `bisync` tiếp theo sẽ xoá `demo.txt` trên Google Drive và PC.
- Nếu bạn xoá `server.txt` trên PC, lần `bisync` tiếp theo sẽ xoá `server.txt` trên VPS.

## Đồng bộ một chiều từ VPS lên Google Drive nếu cần

Nếu chỉ muốn đẩy file từ VPS lên Google Drive, dùng `rclone copy` thay vì `sync` để tránh xóa dữ liệu trên Google Drive:

```bash
rclone copy /root/SYNCVPS gdrive:SYNCVPS --progress
```

Ví dụ nếu thư mục VPS là `/root/arabica` và thư mục Google Drive là `ARABICA_CAFE`:

```bash
rclone copy /root/arabica gdrive:ARABICA_CAFE --progress
```

Lưu ý: `copy` chỉ copy/thêm/cập nhật file từ nguồn sang đích, không xóa file thừa ở đích.

## Test

Trên PC:

```text
Google Drive Desktop
↓
My Drive
↓
SYNCVPS
↓
Tạo file test.txt
```

Đợi khoảng 1 phút.

Kiểm tra VPS:

```bash
ls /root/SYNCVPS
```

Nếu thấy `test.txt` là thành công.

## Lưu ý quan trọng

- Mặc định của skill là đồng bộ hai chiều `PC ↔ Google Drive ↔ VPS` bằng `rclone bisync`.
- Nếu xóa file trên Google Drive hoặc PC thì VPS cũng bị xóa sau lần `bisync` tiếp theo.
- Nếu xóa file trên VPS thì Google Drive và PC cũng bị xóa sau lần `bisync` tiếp theo.
- Nếu chỉ cần đẩy file từ VPS lên Google Drive một lần, dùng `rclone copy` để hạn chế rủi ro xóa nhầm.
- Không chạy hai lệnh `sync` đối nghịch cho cùng một thư mục.
- Nên làm việc trong `My Drive`, không dùng thư mục `Máy tính (Computers)` của Google Drive Desktop vì rclone mặc định chỉ làm việc với `My Drive`.
- Mặc định dùng thư mục `SYNCVPS` trên Google Drive và `/root/SYNCVPS` trên VPS.
- Khi áp dụng thực tế, có thể thay `SYNCVPS` và `/root/SYNCVPS` theo tên thư mục nguồn/đích của người dùng.
