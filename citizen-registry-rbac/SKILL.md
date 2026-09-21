---
name: citizen-registry-rbac
description: Tra cứu dữ liệu nhân khẩu, số thứ tự (STT), hộ gia đình và số CCCD từ bảng dữ liệu dân cư với cơ chế phân quyền RBAC và che mờ bảo vệ dữ liệu (Data Masking) tuân thủ Nghị định 13/2023/NĐ-CP. Sử dụng khi người dùng yêu cầu tra cứu thông tin nhân thân, số CCCD, số điện thoại, chủ hộ hoặc vị trí trong danh sách cử tri/dân cư qua Telegram hoặc Zalo.
metadata:
  openclaw:
    emoji: "🪪"
    requires:
      anyBins: ["python3", "python"]
    primaryEnv: CITIZEN_DATA_FILE
---

# Citizen Registry & CCCD RBAC Lookup

Kỹ năng tra cứu dữ liệu dân cư, số định danh cá nhân (CCCD), số điện thoại và mã hộ gia đình từ bảng tính dữ liệu công tác địa phương (ví dụ Bảng A6) có tích hợp kiểm soát truy cập phân quyền (RBAC) và tự động che mờ bảo vệ dữ liệu cá nhân.

Helper script nằm tại:
`{baseDir}/scripts/lookup_citizen.py`

Script hoạt động hoàn toàn bằng thư viện tiêu chuẩn của Python (`zipfile`, `xml.etree.ElementTree`, `unicodedata`), không cần cài đặt thêm thư viện bên ngoài (`openpyxl`, `pandas`), đảm bảo chạy trơn tru trên cả **Windows** lẫn **Linux VPS**.

---

## Quy trình nghiệp vụ & Phân quyền an toàn (RBAC Workflow)

Khi nhận được yêu cầu tra cứu thông tin cá nhân hoặc CCCD:

### 1. Xác thực quyền của người gửi (Caller Verification)
- **Authorized Owner (Quản trị viên / Cán bộ phụ trách)**:
  - Chỉ những tài khoản có ID nằm trong allowlist của hệ thống (`commands.ownerAllowFrom` hoặc `tools.elevated.allowFrom`) mới được quyền tra cứu.
  - Nếu người gửi **không** nằm trong danh sách được phép: Lập tức từ chối và giải thích người dùng cần liên hệ cán bộ quản trị để được hỗ trợ.

### 2. Phân biệt ngữ cảnh kênh (Channel Context)
- **Kênh tin nhắn riêng (Direct Message / 1-1 Chat)**:
  - Khi Authorized Owner hỏi trong DM 1-1: Trợ lý **được phép và có trách nhiệm cung cấp đầy đủ thông tin**, bao gồm số CCCD, ngày sinh, số điện thoại.
  - Lệnh thực thi: Chạy lệnh bình thường (không dùng `--mask`).
- **Kênh nhóm (Group Chat, ví dụ nhóm Thôn / TDP)**:
  - Để tuân thủ Nghị định 13/2023/NĐ-CP về Bảo vệ dữ liệu cá nhân (tránh lộ lọt dữ liệu định danh ở môi trường nhiều người xem):
  - Trợ lý **bắt buộc** phải kích hoạt cờ `--mask` khi gọi script.
  - Kết quả trả về trong nhóm sẽ được che dạng: `0331******24` và `097****818`.
  - Hướng dẫn cán bộ nhắn riêng (DM) với bot nếu cần lấy đầy đủ 12 số CCCD để làm thủ tục.

---

## Hướng dẫn dòng lệnh (CLI Invocation)

### Trên Linux VPS
```bash
# Kiểm tra tình trạng file dữ liệu
python3 "{baseDir}/scripts/lookup_citizen.py" --doctor

# Tra cứu đầy đủ trong tin nhắn riêng (DM)
python3 "{baseDir}/scripts/lookup_citizen.py" "Hà Thị Giang"

# Tra cứu có che mờ số CCCD và SĐT (trong Nhóm chat)
python3 "{baseDir}/scripts/lookup_citizen.py" "Hà Thị Giang" --mask

# Tra cứu với file dữ liệu tùy biến
python3 "{baseDir}/scripts/lookup_citizen.py" "033184008524" --data-file "/var/data/bang_a6.xlsx"
```

### Trên Windows
```powershell
# Kiểm tra môi trường
python "{baseDir}\scripts\lookup_citizen.py" --doctor

# Tra cứu cho Admin trong DM
python "{baseDir}\scripts\lookup_citizen.py" "Hà Thị Giang"

# Tra cứu có che mờ (Masking)
python "{baseDir}\scripts\lookup_citizen.py" "Hà Thị Giang" --mask
```

---

## Các tiêu chí tìm kiếm hỗ trợ
Script tự động nhận diện kiểu dữ liệu đầu vào mà không cần chỉ định trước cột:
- **Họ và tên**: Tìm kiếm gần đúng, tự động chuẩn hóa tiếng Việt có dấu hoặc không dấu (ví dụ: `Hà Thị Giang`, `ha thi giang`).
- **Số CCCD**: Tìm kiếm theo số CCCD 12 số hoặc 4 số đuôi.
- **Số điện thoại**: Tìm kiếm theo số điện thoại liên hệ.
- **Mã hộ gia đình**: Ví dụ `12064-008902`.
- **Số thứ tự (STT)**: Tra nhanh theo số thứ tự dòng trong danh sách cử tri/dân cư.
