---
name: "google-drive-rclone-setup"
description: "Cài đặt hoặc sửa kết nối Google Drive bằng rclone trên VPS/OpenClaw, gồm OAuth Client ID riêng + token, OAuth headless từ Windows, quyền chỉ đọc hoặc đọc/ghi, giới hạn root_folder_id, kiểm tra đọc/ghi an toàn, backup cấu hình, thay tài khoản và xử lý khác biệt giữa các phiên bản rclone."
---

# Google Drive qua rclone

Dùng khi cần kết nối một tài khoản Google Drive mới với máy OpenClaw, cấu hình phạm vi làm việc theo folder, kiểm tra kết nối hoặc thu hồi/thay tài khoản.

Khi người dùng yêu cầu **OAuth Client ID riêng + token**, đọc và thực hiện đầy đủ tài liệu:

```text
references/oauth-client-id-rieng.md
```

Không rút gọn các bước bảo mật, backup, nhập token không tương tác và kiểm tra ghi/xóa trong tài liệu đó.

## Nguyên tắc an toàn

- Không yêu cầu hoặc nhận mật khẩu Google, OTP hay mã khôi phục.
- OAuth token và refresh token là bí mật. Không lặp lại token trong phản hồi hoặc log công khai.
- Nhắc người dùng chỉ gửi token trong cuộc trò chuyện riêng và xóa tin nhắn chứa token sau khi cấu hình.
- Khi nhập token qua PTY/terminal do AI điều khiển, tắt terminal echo trước khi chạy `rclone config reconnect`; không để token xuất hiện trong output công cụ.
- Không dùng `rclone config edit` trong PTY có ghi log để thêm Client Secret hoặc token trên rclone bản cũ. Bản `1.60.1` có thể tự in toàn bộ `client_secret` và `token` tại màn hình `Configuration complete`, dù đã chạy `stty -echo`.
- Trước khi thay cấu hình, kiểm tra remote và sao lưu file cấu hình với quyền `0600`.
- `root_folder_id` chỉ giới hạn gốc hiển thị/thao tác của remote; OAuth scope `drive` vẫn có thể cấp quyền toàn Drive.
- Muốn giới hạn quyền thực sự ở phía Google: dùng tài khoản Google phụ, chỉ chia sẻ folder cần thiết cho tài khoản đó, rồi xác thực rclone bằng tài khoản phụ.
- Không dùng lệnh ghi, xóa hoặc di chuyển file để kiểm thử nếu người dùng chưa cho phép. Mặc định chỉ liệt kê và đọc metadata.

## 1. Kiểm tra môi trường

```bash
command -v rclone || true
rclone version 2>/dev/null || true
rclone listremotes 2>/dev/null || true
```

Nếu chưa có rclone và không có quyền cài gói hệ thống, cài binary chính thức vào `~/.local/bin/rclone`. Xác minh phiên bản sau cài. Không ghi đè binary hiện có nếu chưa kiểm tra.

Trên Ubuntu có quyền root, có thể cài từ kho hệ điều hành:

```bash
apt-get update -qq
DEBIAN_FRONTEND=noninteractive apt-get install -y rclone
rclone version
```

Ghi lại phiên bản vì một số lệnh như `rclone config redacted` không có trên bản cũ, ví dụ `1.60.1` của Ubuntu 24.04.

## 2. Chuẩn bị tài khoản và folder

Với quyền đọc/ghi, khuyến nghị:

1. Dùng tài khoản Google phụ dành cho VPS/OpenClaw.
2. Chỉ chia sẻ folder cần dùng cho tài khoản phụ.
3. Cấp quyền `Editor` cho tài khoản phụ.
4. Lấy `FOLDER_ID` từ URL dạng:

```text
https://drive.google.com/drive/folders/FOLDER_ID?usp=drive_link
```

Không ghi folder ID thật vào skill, tài liệu mẫu hoặc source dùng chung.

## 3. Tạo remote Google Drive

Tên mặc định: `gdrive`.

Chạy tương tác:

```bash
rclone config
```

Chọn:

1. `New remote`
2. Tên `gdrive`
3. Storage `drive` (Google Drive)
4. `client_id` và `client_secret`: để trống nếu dùng khóa chung; ưu tiên OAuth Client ID riêng cho kết nối lâu dài
5. Scope:
   - `drive.readonly` nếu chỉ cần đọc
   - `drive` nếu người dùng xác nhận cần đọc/ghi
6. Service account: để trống nếu dùng đăng nhập cá nhân
7. Advanced config: No, trừ khi có yêu cầu cụ thể
8. Máy OpenClaw không có browser: chọn No ở auto-auth

### Cách ổn định cho rclone bản Ubuntu cũ

Một số bản cũ không hỏi `root_folder_id` trong luồng cơ bản. Nếu nhập folder ID khi không nhìn kỹ prompt, giá trị có thể rơi nhầm vào `service_account_file`. Ưu tiên tạo remote không tương tác:

```bash
rclone config create gdrive drive \
  scope=drive \
  root_folder_id=FOLDER_ID \
  config_is_local=false
```

Với quyền chỉ đọc, thay `scope=drive` bằng `scope=drive.readonly`.

Lệnh trên có thể chỉ tạo remote chưa có token. Tiếp tục bằng `rclone config reconnect gdrive:`; không tạo thêm remote trùng tên.

Khi dùng OAuth Client ID riêng, ưu tiên quy trình:

1. Tạo remote không tương tác với `client_id`, `scope` và `root_folder_id`.
2. Đọc `client_secret` từ file local quyền `600`; tạo remote với output chuyển vào `/dev/null`, không đặt secret thật vào tài liệu hoặc lệnh được công khai.
3. Yêu cầu người dùng chạy `rclone authorize "drive" CLIENT_ID CLIENT_SECRET` trên máy có browser.
4. Lưu token vào file local quyền `600`, rồi nhập bằng `rclone config update ... token=... --non-interactive >/dev/null`.
5. Không dùng `rclone config edit` hoặc `config reconnect` trong PTY có ghi log nếu chúng có thể in command state, Client Secret hoặc token.

## 4. Xác thực từ Windows

Khởi chạy reconnect trong PTY và tắt echo để ký tự người dùng nhập không bị terminal echo:

```bash
old_stty="$(stty -g)"
trap 'stty "$old_stty"' EXIT INT TERM
stty -echo
rclone config reconnect gdrive:
```

Chọn `n` ở `Use auto config?`. Rclone sẽ in lệnh `rclone authorize` dành cho máy có trình duyệt.

Lưu ý: `stty -echo` chỉ tắt việc terminal lặp lại ký tự nhập. Nó không ngăn chương trình tự in cấu hình. Vì vậy chỉ dùng với `rclone config reconnect`, tránh dùng với `rclone config edit` trên bản cũ.

Yêu cầu người dùng tải đúng rclone từ trang chính thức `https://rclone.org/downloads/`, giải nén và mở PowerShell trong thư mục chứa `rclone.exe`.

Chạy đúng lệnh mà rclone trên máy OpenClaw hiển thị, ví dụ:

```powershell
.\rclone.exe authorize "drive" "eyJzY29wZSI6ImRyaXZlIn0"
```

Người dùng đăng nhập Google và bấm Allow. Sau đó sao chép duy nhất chuỗi nằm giữa:

```text
Paste the following into your remote machine --->
...
<---End paste
```

Không dùng lại URL callback `127.0.0.1`; URL này chỉ có tác dụng cục bộ, tạm thời trên máy Windows.

Nhập token vào prompt `config_token`. Với My Drive chọn No ở câu hỏi Shared Drive; với Shared Drive chọn đúng theo yêu cầu.

Sau khi reconnect kết thúc, bảo đảm terminal echo được khôi phục. Nếu phiên bị ngắt bất thường, chạy:

```bash
stty echo
```

## 5. Xử lý phiên cấu hình bị hết hạn

Nếu phiên tương tác cũ không còn hoặc remote có token rỗng:

```bash
rclone config reconnect gdrive:
```

Chọn No ở auto-auth, nhập token mới, rồi chọn My Drive/Shared Drive phù hợp.

Không tạo remote trùng tên nếu `gdrive` đã tồn tại. Kiểm tra bằng:

```bash
rclone listremotes
```

Nếu phiên bản hỗ trợ thì dùng `rclone config redacted gdrive`. Nếu không hỗ trợ, không dùng `rclone config show` trực tiếp vì lệnh đó có thể in token. Chỉ đọc các trường an toàn:

```bash
CONFIG_FILE="$(rclone config file | tail -n 1)"
awk -F' *= *' '
  /^\[gdrive\]$/ {inside=1; print; next}
  /^\[/ {inside=0}
  inside && $1=="type" {print "type = " $2}
  inside && $1=="scope" {print "scope = " $2}
  inside && $1=="root_folder_id" {print "root_folder_id = " $2}
  inside && $1=="token" {print "token = <present, redacted>"}
' "$CONFIG_FILE"
```

## 6. Backup và giới hạn gốc

Lấy folder ID từ URL dạng:

```text
https://drive.google.com/drive/folders/FOLDER_ID?usp=drive_link
```

Xác định file cấu hình, bảo vệ và backup trước khi sửa remote đang tồn tại:

```bash
CONFIG_FILE="$(rclone config file | tail -n 1)"
chmod 600 "$CONFIG_FILE"
mkdir -p /root/_Backups/rclone
install -m 600 "$CONFIG_FILE" "/root/_Backups/rclone/rclone.conf.$(date -u +%Y%m%dT%H%M%SZ).bak"
```

Đặt:

```ini
root_folder_id = FOLDER_ID
```

trong section `[gdrive]` hoặc cập nhật bằng phương thức cấu hình không kích hoạt OAuth lại. Sau khi sửa, bảo đảm file config có quyền `0600`.

Không tuyên bố đây là giới hạn quyền tuyệt đối. Nêu rõ token vẫn giữ OAuth scope đã cấp.

## 7. Kiểm tra đọc không phá hủy

```bash
rclone listremotes
rclone lsf gdrive: --max-depth 1
rclone size gdrive: --json
```

Tiêu chí hoàn tất:

- `gdrive:` xuất hiện trong danh sách remote.
- Cấu hình an toàn xác nhận có `type`, `scope`, `root_folder_id` và token hiện diện nhưng không in giá trị token.
- Liệt kê được folder gốc mong muốn.
- Nếu có `root_folder_id`, kết quả chỉ bắt đầu tại folder đó.
- Báo tên file/folder và số lượng để người dùng đối chiếu; không tiết lộ dữ liệu không cần thiết.

## 8. Kiểm tra quyền ghi có xác nhận

Chỉ chạy khi người dùng đã yêu cầu hoặc xác nhận cần quyền ghi. Dùng tên file duy nhất, nội dung vô hại và xóa ngay sau khi xác minh:

```bash
TEST_LOCAL="$(mktemp)"
TEST_REMOTE="_rclone_write_test_$(date -u +%Y%m%dT%H%M%SZ).txt"
printf 'Kiem tra quyen ghi rclone - %s UTC\n' "$(date -u '+%Y-%m-%d %H:%M:%S')" > "$TEST_LOCAL"

rclone copyto "$TEST_LOCAL" "gdrive:$TEST_REMOTE"
rclone lsf gdrive: --include "$TEST_REMOTE" --files-only
rclone deletefile "gdrive:$TEST_REMOTE"
unlink "$TEST_LOCAL"

if rclone lsf gdrive: --include "$TEST_REMOTE" --files-only | rg -q .; then
  echo 'WRITE_TEST_DELETE_FAILED'
  exit 1
else
  echo 'WRITE_TEST_OK_AND_REMOVED'
fi
```

Nếu upload thành công nhưng xóa thất bại, báo rõ tên file thử để người dùng xử lý; không che giấu file còn sót.

## 9. Cảnh báo và bảo trì

- Nếu rclone cảnh báo shared Google client ID sắp ngừng hoạt động hoặc bị giới hạn, đề xuất tạo OAuth Client ID riêng trong Google Cloud và cấu hình lại.
- Khi đổi tài khoản, nghi ngờ token lộ hoặc muốn thu hồi: người dùng thu hồi quyền rclone trong Google Account → Security → Third-party connections, rồi chạy reconnect với token mới.
- Nếu token từng được gửi trong chat, khuyến nghị xóa tin nhắn và thu hồi/kết nối lại khi dữ liệu nhạy cảm.
- Không ghi token vào skill, Second Brain, changelog, shell script, file hướng dẫn hoặc câu trả lời hoàn tất.
- Sau thay đổi quan trọng trên VPS, cập nhật `/root/_Second_AI_Brain/06_Nhat_Ky_Thay_Doi.md` nhưng chỉ ghi trạng thái, scope, loại Drive, kết quả kiểm tra và đường dẫn backup; không ghi credential.

## Mẫu báo cáo hoàn tất

Báo ngắn gọn:

- Remote đã kết nối hay chưa
- Quyền đọc hay đọc/ghi
- My Drive hay Shared Drive
- Có đặt `root_folder_id` không
- Nội dung cấp một nhìn thấy khi kiểm tra
- Kết quả kiểm tra ghi và xác nhận file thử đã xóa, nếu có
- Quyền file cấu hình là `600` và đã backup
- Cảnh báo rằng giới hạn folder ở rclone không thay thế giới hạn quyền phía Google
