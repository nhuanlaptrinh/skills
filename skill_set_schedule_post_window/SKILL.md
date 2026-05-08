---
name: skill_set_schedule_post_window
description: Kỹ năng thiết lập lịch tự động đăng bài Facebook/Fanpage bằng Windows Task Scheduler hoặc Linux cron.
---

# 🕒 Schedule Setup cho Facebook Auto Poster

Skill này giúp thiết lập lịch chạy tự động cho các dự án đăng bài Facebook/Fanpage.

- Trên Windows: dùng Windows Task Scheduler.
- Trên Linux/server: dùng cron.

Khi người dùng yêu cầu "set lịch", "thiết lập lịch đăng", "hẹn giờ đăng", "đăng mỗi ngày", hoặc yêu cầu tương đương, Agent phải mở skill này trước, xác định hệ điều hành/môi trường đang chạy, rồi làm theo đúng nhánh tương ứng.

## 📂 Thành phần
- Script thiết lập tự động: `scripts/setup_schedule.ps1`

## ⚙️ Hướng dẫn sử dụng cho Agent (AI)

## A. Windows Task Scheduler

Sử dụng lệnh PowerShell để tự động thiết lập lịch. Có 2 chế độ chính:

### 1. Chế độ chạy liên tục (Mỗi 5 phút)
Chế độ này **không yêu cầu quyền Admin**, phù hợp khi muốn script liên tục kiểm tra sheet xem có bài mới không.
```powershell
powershell -ExecutionPolicy Bypass -File ".agents\skills\skill_set_schedule_post_window\scripts\setup_schedule.ps1" -Mode "5Mins"
```

### 2. Chế độ chạy Hàng ngày (Daily)
Chế độ này yêu cầu quyền Admin (`-RunLevel Highest`) để có thể đánh thức máy (`WakeToRun`). Do Agent (AI) thường không có quyền Admin, hãy dùng lệnh ép hiển thị hộp thoại UAC yêu cầu người dùng cấp quyền:
```powershell
powershell -c "Start-Process powershell -Verb runAs -ArgumentList '-ExecutionPolicy Bypass -File \"$(Get-Location)\.agents\skills\skill_set_schedule_post_window\scripts\setup_schedule.ps1\" -Mode \"Daily\" -Time \"09:00AM\"'"
```
*(Người dùng sẽ thấy popup hiện ra hỏi quyền, hãy nhắc họ bấm Yes).*

## 🛑 Chuẩn ALT
Các kịch bản setup trong skill này luôn được tuân thủ Chuẩn ALT:
1. Xác định đường dẫn linh hoạt qua working directory (`$projectDir = (Get-Item -Path ".\").FullName`).
2. Gắn kết trực tiếp tới Python của môi trường ảo (`venv\Scripts\python.exe`).
3. Không sử dụng các đường dẫn cứng như `C:\Users\...` hay `D:\...`.

## B. Linux/Server Cron

Dùng nhánh này khi project đang chạy trên Linux/server, ví dụ môi trường `/root/...`.

### Nguyên tắc bắt buộc

1. Không thay thế hoặc xóa các cron job hiện có nếu không được yêu cầu.
2. Chỉ append job mới cho project cần set lịch.
3. Nếu script chính có thể đăng bài thật, không chạy test wrapper trực tiếp trừ khi người dùng yêu cầu đăng ngay.
4. Phải dùng đường dẫn tuyệt đối trong cron.
5. Phải có log file riêng để kiểm tra sau khi cron chạy.
6. Nếu server dùng UTC nhưng người dùng nói giờ Việt Nam, quy đổi `Asia/Ho_Chi_Minh` sang UTC. Ví dụ `10:00` Việt Nam = `03:00` UTC.

### Quy trình chuẩn

Mở terminal tại thư mục gốc project, kiểm tra giờ và cron:

```bash
date
env TZ=Asia/Ho_Chi_Minh date
crontab -l
pgrep -a cron
```

Tạo wrapper trong thư mục script của skill/project. Wrapper cần tự `cd` về project, đặt timezone log, gọi Python bằng đường dẫn tuyệt đối, và ghi log.

Mẫu wrapper:

```bash
#!/usr/bin/env bash
set -uo pipefail

PROJECT_ROOT="/duong/dan/tuyet/doi/den/project"
SCRIPT_PATH="$PROJECT_ROOT/path/to/main_script.py"
LOG_DIR="$PROJECT_ROOT/logs"
LOG_FILE="$LOG_DIR/daily_post.log"

mkdir -p "$LOG_DIR"
export TZ="Asia/Ho_Chi_Minh"

{
  echo "============================================================"
  echo "[$(date '+%Y-%m-%d %H:%M:%S %Z')] Start daily post"
  cd "$PROJECT_ROOT" || exit 1
  /usr/bin/python3 "$SCRIPT_PATH"
  status=$?
  echo "[$(date '+%Y-%m-%d %H:%M:%S %Z')] Finished with exit code $status"
  exit "$status"
} >> "$LOG_FILE" 2>&1
```

Cấp quyền và kiểm tra cú pháp:

```bash
chmod +x path/to/run_daily_post.sh
bash -n path/to/run_daily_post.sh
```

Thêm cron job theo kiểu append an toàn:

```bash
CRON_FILE="/tmp/project_schedule.cron"
JOB="0 3 * * * /duong/dan/tuyet/doi/den/project/path/to/run_daily_post.sh"
COMMENT="# project_name: post 1 item daily at 10:00 Asia/Ho_Chi_Minh (03:00 UTC)"
crontab -l > "$CRON_FILE" 2>/dev/null || true
if grep -Fq "$JOB" "$CRON_FILE"; then
  printf '%s\n' "Cron job already exists."
else
  printf '\n%s\n%s\n' "$COMMENT" "$JOB" >> "$CRON_FILE"
  crontab "$CRON_FILE"
  printf '%s\n' "Cron job added."
fi
```

Xác minh:

```bash
crontab -l
pgrep -a cron
tail -n 80 /duong/dan/tuyet/doi/den/project/logs/daily_post.log
```

Nếu `pgrep -a cron` không thấy tiến trình cron, thử khởi động cron:

```bash
/usr/sbin/cron
pgrep -a cron
```

Trong môi trường sandbox, thao tác `crontab` hoặc `/usr/sbin/cron` có thể cần quyền ngoài sandbox. Khi bị lỗi kiểu `Read-only file system`, `Operation not permitted`, hoặc không thấy tiến trình do sandbox, cần chạy lại bằng quyền phù hợp.

## C. Case Đã Thiết Lập: Fanpage Auto Poster

Project:

```bash
/root/05_skill_facebook_zalo/skill_post_fanpage
```

Script chính:

```bash
/root/05_skill_facebook_zalo/skill_post_fanpage/.agent/skills/post-fanpage-fb/scripts/Facebook_Post_Bai_Fanpage.py
```

Wrapper đã tạo:

```bash
/root/05_skill_facebook_zalo/skill_post_fanpage/.agent/skills/post-fanpage-fb/scripts/run_daily_post.sh
```

Log:

```bash
/root/05_skill_facebook_zalo/skill_post_fanpage/logs/fanpage_daily_post.log
```

Cron đã cài cho lịch đăng 1 bài/ngày lúc 10:00 sáng giờ Việt Nam:

```cron
# skill_post_fanpage: post 1 Fanpage item daily at 10:00 Asia/Ho_Chi_Minh (03:00 UTC)
0 3 * * * /root/05_skill_facebook_zalo/skill_post_fanpage/.agent/skills/post-fanpage-fb/scripts/run_daily_post.sh
```

Lưu ý: server đang chạy UTC, nên `0 3 * * *` là 10:00 sáng Việt Nam.

## D. Case Đã Thiết Lập: Facebook Personal Auto Poster

Project:

```bash
/root/05_skill_facebook_zalo/skill_post_facebook_personal
```

Script chính:

```bash
/root/05_skill_facebook_zalo/skill_post_facebook_personal/.agents/skills/fb-auto-poster/scripts/OpenFBV2POST.py
```

Python/runtime:

```bash
/usr/bin/xvfb-run -a /root/05_skill_facebook_zalo/skill_post_facebook_personal/venv_linux/bin/python
```

Log:

```bash
/root/05_skill_facebook_zalo/skill_post_facebook_personal/cron_post.log
```

Cron đã cài cho lịch đăng 1 bài/ngày lúc 19:00 giờ Việt Nam:

```cron
# skill_post_facebook_personal: post 1 personal Facebook item daily at 19:00 Asia/Ho_Chi_Minh (12:00 UTC)
0 12 * * * cd /root/05_skill_facebook_zalo/skill_post_facebook_personal && /usr/bin/xvfb-run -a /root/05_skill_facebook_zalo/skill_post_facebook_personal/venv_linux/bin/python /root/05_skill_facebook_zalo/skill_post_facebook_personal/.agents/skills/fb-auto-poster/scripts/OpenFBV2POST.py >> /root/05_skill_facebook_zalo/skill_post_facebook_personal/cron_post.log 2>&1
```

Lưu ý: server đang chạy UTC, nên `0 12 * * *` là 19:00 Việt Nam.
