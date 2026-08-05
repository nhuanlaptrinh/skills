---
name: cau-hinh-9router-codex
description: Cài đặt hoặc sửa cấu hình Codex Extension trong Antigravity và Codex CLI để dùng chung 9Router trên Windows, Linux, macOS hoặc VPS. Use khi người dùng muốn mang cấu hình tương tự /root/.codex/config.toml sang máy khác, cấu hình model_provider/model_providers trong config.toml, đặt NINEROUTER_KEY an toàn, kiểm tra /v1/models, hoặc xử lý lỗi Codex không nhận provider 9Router.
---

# Cấu Hình Codex Qua 9Router Đa Nền Tảng

## Mục Tiêu

Cấu hình Codex Extension trong Antigravity và Codex CLI trên máy khác theo mẫu đang dùng trên VPS:

```toml
model_provider = "router9"
model = "GPT-5.6"
model_reasoning_effort = "medium"

[model_providers.router9]
name = "9Router"
base_url = "https://cdx.anhlaptrinh.vn/v1"
env_key = "NINEROUTER_KEY"
```

API key thật chỉ nằm trong biến môi trường `NINEROUTER_KEY`, không ghi trực tiếp vào `config.toml`.

## Khi Dùng Skill

- Cài Codex Extension trong Antigravity trên Windows, Linux hoặc macOS để chạy qua 9Router.
- Đồng bộ cách cấu hình từ VPS `/root/.codex/config.toml` sang máy khác.
- Sửa lỗi provider, model, endpoint, biến môi trường hoặc lỗi `401`/không kết nối.
- Cấu hình Codex CLI và extension dùng chung user-level config.

## Quy Tắc An Toàn

- Không đọc hoặc in toàn bộ file cấu hình nếu file có thể chứa secret; chỉ lấy các khóa cần thiết và che giá trị nhạy cảm.
- Không ghi API key thật vào skill, tài liệu, repo, shell history hoặc câu trả lời cuối.
- `env_key` phải là tên biến môi trường `NINEROUTER_KEY`, tuyệt đối không phải API key thật.
- Luôn backup `config.toml` trước khi sửa nếu file đã tồn tại.
- Không ghi đè các phần cấu hình khác như `[projects]`, MCP, sandbox hoặc trust nếu task không yêu cầu.
- Không yêu cầu người dùng gửi API key vào chat. Cho người dùng tự nhập trực tiếp trên máy.

## Vị Trí Cấu Hình

| Hệ điều hành | File user config |
|---|---|
| Windows | `%USERPROFILE%\.codex\config.toml` |
| Linux | `${CODEX_HOME:-$HOME/.codex}/config.toml` |
| macOS | `${CODEX_HOME:-$HOME/.codex}/config.toml` |
| VPS chạy root | `/root/.codex/config.toml` |

Nếu có `CODEX_HOME`, ưu tiên thư mục đó. Extension và CLI phải chạy dưới cùng tài khoản người dùng để đọc cùng cấu hình và biến môi trường.

## Workflow Chuẩn

1. Xác định hệ điều hành, tài khoản đang chạy Antigravity và có dùng `CODEX_HOME` hay không.
2. Kiểm tra Codex Extension/Codex CLI đã được cài. Không tự cài extension nếu chưa biết đúng extension ID hoặc nguồn cài đặt.
3. Xác định đường dẫn user config, tạo thư mục `.codex` nếu chưa có.
4. Backup file hiện tại với timestamp.
5. Chỉ thêm hoặc cập nhật ba khóa cấp cao và bảng `[model_providers.router9]`; giữ nguyên cấu hình không liên quan.
6. Đặt API key thật vào biến môi trường `NINEROUTER_KEY` bằng cách không làm lộ key.
7. Kiểm tra biến đã tồn tại nhưng không in giá trị.
8. Test endpoint `/v1/models`, rồi restart hoàn toàn Antigravity/Codex Extension.
9. Mở phiên Codex mới và xác nhận provider/model hoạt động.

## Windows PowerShell

### Tạo thư mục và backup

```powershell
$codexHome = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $env:USERPROFILE ".codex" }
$configPath = Join-Path $codexHome "config.toml"
New-Item -ItemType Directory -Force -Path $codexHome | Out-Null
if (Test-Path $configPath) {
    Copy-Item $configPath "$configPath.bak-$(Get-Date -Format yyyyMMdd-HHmmss)"
}
notepad $configPath
```

Thêm hoặc cập nhật mẫu cấu hình ở phần **Mục Tiêu**, không xóa các bảng khác.

### Lưu API key an toàn

Ưu tiên nhập ẩn trong PowerShell để key không xuất hiện trong lệnh:

```powershell
$secureKey = Read-Host "Nhap 9Router API key" -AsSecureString
$plainKey = [System.Net.NetworkCredential]::new("", $secureKey).Password
[Environment]::SetEnvironmentVariable("NINEROUTER_KEY", $plainKey, "User")
Remove-Variable plainKey, secureKey
```

Đóng hoàn toàn Antigravity rồi mở lại vì process đang chạy không tự nhận User Environment mới.

### Kiểm tra không lộ key

```powershell
if ([Environment]::GetEnvironmentVariable("NINEROUTER_KEY", "User")) { "NINEROUTER_KEY=set" } else { "NINEROUTER_KEY=missing" }
```

### Test gateway

Chạy trong cửa sổ PowerShell mới sau khi restart terminal:

```powershell
$key = [Environment]::GetEnvironmentVariable("NINEROUTER_KEY", "User")
curl.exe -sS -o NUL -w "%{http_code}`n" -H "Authorization: Bearer $key" --max-time 20 "https://cdx.anhlaptrinh.vn/v1/models"
Remove-Variable key
```

## Linux

### Tạo thư mục và backup

```bash
codex_home="${CODEX_HOME:-$HOME/.codex}"
config_path="$codex_home/config.toml"
mkdir -p "$codex_home"
[ ! -f "$config_path" ] || cp -a "$config_path" "$config_path.bak-$(date +%Y%m%d-%H%M%S)"
${EDITOR:-nano} "$config_path"
```

### Lưu API key

Nhập ẩn, sau đó thêm dòng export vào file shell profile phù hợp mà không in key ra màn hình:

```bash
read -rsp 'Nhap 9Router API key: ' NINEROUTER_KEY; echo
export NINEROUTER_KEY
```

Để dùng sau khi đăng nhập lại, lưu bằng trình quản lý secret của hệ điều hành nếu có. Nếu buộc phải dùng shell profile, thêm thủ công `export NINEROUTER_KEY="..."` vào `~/.bashrc`, `~/.zshrc` hoặc file môi trường của desktop session, đặt quyền file `600`, và không commit file đó.

Antigravity mở từ desktop có thể không đọc `~/.bashrc`. Khi đó đặt biến trong môi trường desktop/login session hoặc khởi động Antigravity từ terminal đã có biến.

### Kiểm tra và test

```bash
[ -n "${NINEROUTER_KEY:-}" ] && echo 'NINEROUTER_KEY=set' || echo 'NINEROUTER_KEY=missing'
status=$(curl -sS -o /dev/null -w '%{http_code}' -H "Authorization: Bearer $NINEROUTER_KEY" --max-time 20 'https://cdx.anhlaptrinh.vn/v1/models')
printf 'HTTP %s\n' "$status"
```

## macOS

File cấu hình giống Linux: `${CODEX_HOME:-$HOME/.codex}/config.toml`.

Antigravity mở từ Finder/Dock thường không nhận biến chỉ khai báo trong `~/.zshrc`. Dùng Keychain hoặc đặt biến cho GUI session. Cách tạm thời cho phiên đăng nhập hiện tại:

```bash
read -rsp 'Nhap 9Router API key: ' NINEROUTER_KEY; echo
launchctl setenv NINEROUTER_KEY "$NINEROUTER_KEY"
unset NINEROUTER_KEY
```

Sau đó thoát hoàn toàn và mở lại Antigravity. Kiểm tra tên biến mà không in key:

```bash
[ -n "$(launchctl getenv NINEROUTER_KEY)" ] && echo 'NINEROUTER_KEY=set' || echo 'NINEROUTER_KEY=missing'
```

Lưu ý: `launchctl setenv` không phải cơ chế lưu secret bền vững qua mọi lần đăng nhập. Với máy dùng lâu dài, ưu tiên macOS Keychain hoặc cơ chế quản lý môi trường doanh nghiệp của máy.

## Cập Nhật Config Không Phá Phần Khác

Nếu file đã có nhiều cấu hình, không thay toàn bộ file bằng một heredoc. Hãy sửa TOML có chủ đích:

- Đảm bảo `model_provider = "router9"`.
- Đảm bảo `model = "GPT-5.6"`.
- Đảm bảo `model_reasoning_effort = "medium"`, trừ khi người dùng yêu cầu mức khác.
- Tạo hoặc cập nhật `[model_providers.router9]` với `name`, `base_url`, `env_key` như mẫu.
- Giữ nguyên mọi bảng `[projects."..."]`, MCP và cấu hình khác.

Nếu công cụ TOML không có sẵn, backup rồi sửa bằng editor là phương án an toàn nhất.

## Xử Lý Lỗi

### `env_key` chứa API key thật

Sai:

```toml
env_key = "sk-..."
```

Đúng:

```toml
env_key = "NINEROUTER_KEY"
```

Nếu phát hiện lỗi này, không nhắc lại giá trị key trong output. Hướng dẫn người dùng xoay vòng key nếu key từng bị lưu vào repo, log hoặc chat.

### HTTP `401`

- Không gửi Authorization mà nhận `401`: gateway có thể vẫn hoạt động bình thường.
- Đã gửi key mà vẫn `401`: key thiếu, sai, hết hạn hoặc không có quyền.
- Kiểm tra process Antigravity có thực sự nhận `NINEROUTER_KEY` sau khi restart.

### HTTP `404`

Kiểm tra `base_url` có kết thúc bằng `/v1` và URL test là `/v1/models`. Không ghép thành `/v1/v1/models`.

### Không kết nối, timeout hoặc lỗi DNS

Kiểm tra internet, DNS, proxy/firewall, chứng chỉ TLS và khả năng truy cập `https://cdx.anhlaptrinh.vn` từ chính máy đó.

### CLI chạy được nhưng extension không chạy

Extension có thể chạy trong môi trường GUI khác terminal. Kiểm tra biến môi trường của desktop session, đúng user home, `CODEX_HOME`, rồi restart toàn bộ Antigravity.

### Extension vẫn dùng provider cũ

- Xác nhận đang sửa user config đúng tài khoản.
- Tìm project-local config có thể ghi đè, nhưng không tự xóa.
- Reload window hoặc thoát hoàn toàn Antigravity rồi mở lại.
- Mở phiên chat Codex mới thay vì dùng phiên cũ.

## Tiêu Chí Hoàn Tất

- `config.toml` đúng đường dẫn của user chạy Antigravity.
- Provider là `router9`, model là `GPT-5.6`, endpoint là `https://cdx.anhlaptrinh.vn/v1`.
- `env_key = "NINEROUTER_KEY"`, không có API key thật trong file.
- Biến môi trường tồn tại trong đúng GUI/login session.
- `/v1/models` trả `200` khi gửi key hợp lệ.
- Antigravity đã restart và phiên Codex mới hoạt động.

## Mẫu Báo Cáo

```text
Đã cấu hình Codex Extension/Codex CLI dùng 9Router trên <Windows|Linux|macOS>.
File cấu hình: <đường dẫn config.toml>.
API key được lưu qua biến NINEROUTER_KEY, không ghi vào config hoặc báo cáo.
Kiểm tra gateway: HTTP <mã>.
Đã yêu cầu restart hoàn toàn Antigravity và mở phiên Codex mới.
```
