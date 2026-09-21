# Citizen Registry & CCCD RBAC Lookup (`citizen-registry-rbac`)

OpenClaw skill tra cứu dữ liệu nhân khẩu, hộ gia đình, số thứ tự danh sách và số định danh cá nhân (CCCD) từ bảng tính địa phương (Bảng A6) với cơ chế phân quyền kiểm soát truy cập (RBAC) và che mờ dữ liệu (Data Masking) tuân thủ Nghị định 13/2023/NĐ-CP qua Telegram và Zalo.

---

## Tính năng nổi bật

- **Kiểm soát phân quyền chặt chẽ (RBAC)**:
  - Chỉ cho phép các Telegram / Zalo ID thuộc danh sách Owner (cán bộ, quản trị viên được chỉ định) tra cứu.
  - Người dùng lạ ngoài danh sách bị từ chối tự động.
- **Bảo vệ dữ liệu thông minh theo ngữ cảnh kênh**:
  - **Trong tin nhắn riêng (DM 1-1)**: Cung cấp đầy đủ thông tin (Họ tên, STT, Ngày sinh, SĐT, Số CCCD) để phục vụ công việc hành chính.
  - **Trong nhóm chat (Group)**: Tự động che mờ (`--mask`) số CCCD dạng `0331******24` và số điện thoại dạng `097****818` nhằm tránh rủi ro lộ lọt danh tính ở nơi đông người.
- **Độc lập, siêu nhẹ**:
  - Viết 100% bằng thư viện có sẵn của Python (`zipfile`, `xml.etree.ElementTree`, `unicodedata`).
  - Không cần cài đặt thêm `pandas`, `openpyxl` hay bất kỳ thư viện ngoài nào. Đảm bảo chạy ngay trên mọi máy tính Windows và Linux VPS.
- **Tìm kiếm đa năng**:
  - Tìm theo Họ và tên (tự động nhận diện có dấu hoặc không dấu).
  - Tìm theo Số CCCD (12 chữ số hoặc 4 số đuôi).
  - Tìm theo Số điện thoại.
  - Tìm theo Mã hộ gia đình hoặc Số thứ tự dòng (STT).

---

## Cài đặt trên Windows (Local OpenClaw Gateway)

1. Sao chép skill vào thư mục quản lý skills của OpenClaw:
```powershell
$dest = "$env:USERPROFILE\.openclaw\skills\citizen-registry-rbac"
New-Item -ItemType Directory -Force $dest | Out-Null
robocopy D:\citizen-registry-rbac $dest /E
```

2. Kiểm tra tình trạng dữ liệu và hoạt động của skill:
```powershell
python D:\citizen-registry-rbac\scripts\lookup_citizen.py --doctor
```

3. Khởi động lại OpenClaw Gateway (nếu cần):
```powershell
openclaw gateway restart
```

---

## Cài đặt trên Linux VPS (Remote Gateway)

1. Sao chép hoặc clone thư mục skill vào VPS:
```bash
git clone <url-kho-chua-skill> "$HOME/.agents/skills/citizen-registry-rbac"
# hoặc dùng rsync/scp đưa thư mục vào:
# rsync -avz D:/citizen-registry-rbac/ user@vps_ip:~/.agents/skills/citizen-registry-rbac/
```

2. Cấp quyền thực thi:
```bash
chmod +x "$HOME/.agents/skills/citizen-registry-rbac/scripts/lookup_citizen.py"
```

3. Lưu trữ file dữ liệu Excel an toàn:
```bash
mkdir -p "$HOME/.config/citizen-registry-rbac"
chmod 700 "$HOME/.config/citizen-registry-rbac"
cp /path/to/bang_a6.xlsx "$HOME/.config/citizen-registry-rbac/bang_a6.xlsx"
chmod 600 "$HOME/.config/citizen-registry-rbac/bang_a6.xlsx"
```

4. Cấu hình biến môi trường trỏ đến file dữ liệu:
```bash
echo 'export CITIZEN_DATA_FILE="$HOME/.config/citizen-registry-rbac/bang_a6.xlsx"' >> ~/.bashrc
source ~/.bashrc
```

5. Kiểm tra hoạt động:
```bash
python3 "$HOME/.agents/skills/citizen-registry-rbac/scripts/lookup_citizen.py" --doctor
```

---

## Cấu hình Phân quyền trong `openclaw.json`

Thêm Telegram User ID của các cán bộ được ủy quyền vào `openclaw.json`:
```json
{
  "tools": {
    "elevated": {
      "enabled": true,
      "allowFrom": {
        "telegram": [
          "8342048167",
          "8977732250"
        ]
      }
    }
  },
  "channels": {
    "telegram": {
      "enabled": true,
      "allowFrom": [
        "8342048167",
        "8977732250"
      ]
    }
  },
  "commands": {
    "ownerAllowFrom": [
      "telegram:8342048167",
      "telegram:8977732250"
    ]
  }
}
```

---

## Cú pháp tra cứu mẫu

```bash
# Tra cứu đầy đủ (dành cho Admin trong chat 1-1 DM)
python lookup_citizen.py "Hà Thị Giang"

# Tra cứu che mờ (dành cho nhóm chat công cộng)
python lookup_citizen.py "Hà Thị Giang" --mask

# Tra cứu định dạng JSON
python lookup_citizen.py "033184008524" --json
```
