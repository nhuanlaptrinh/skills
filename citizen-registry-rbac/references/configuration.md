# Hướng Dẫn Cấu Hình & Tích Hợp Cho VPS / Hệ Thống Khác

Tài liệu này hướng dẫn cách đưa skill `citizen-registry-rbac` lên một máy chủ Linux VPS hoặc Windows khác và cấu hình phân quyền trong OpenClaw.

---

## 1. Cấu trúc thư mục khuyến nghị trên Linux VPS

Trên Linux VPS, bạn có thể đặt skill vào thư mục kỹ năng của OpenClaw:
```bash
# Thư mục skill được OpenClaw quản lý
$HOME/.agents/skills/citizen-registry-rbac
# Hoặc:
$HOME/.openclaw/skills/citizen-registry-rbac
```

Thư mục lưu trữ file dữ liệu Excel dân cư an toàn (chỉ cho phép user hiện tại đọc):
```bash
mkdir -p "$HOME/.config/citizen-registry-rbac"
chmod 700 "$HOME/.config/citizen-registry-rbac"

# Sao chép file Excel dữ liệu (ví dụ bang_a6.xlsx) vào thư mục này
cp /duong/dan/bang_a6.xlsx "$HOME/.config/citizen-registry-rbac/bang_a6.xlsx"
chmod 600 "$HOME/.config/citizen-registry-rbac/bang_a6.xlsx"
```

---

## 2. Cấu hình biến môi trường

Nếu muốn chỉ định đường dẫn file Excel cố định mà không cần truyền tham số `--data-file`:
Tạo file `$HOME/.config/citizen-registry-rbac/runtime.env`:
```bash
CITIZEN_DATA_FILE="/root/.config/citizen-registry-rbac/bang_a6.xlsx"
```

Và khai báo vào file profile shell (`~/.bashrc` hoặc `~/.profile`):
```bash
export CITIZEN_DATA_FILE="/root/.config/citizen-registry-rbac/bang_a6.xlsx"
```

---

## 3. Cấu hình phân quyền trong openclaw.json

Mở file `~/.openclaw/openclaw.json` trên VPS:

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

## 4. Kiểm tra (Doctor Check)

Sau khi cài đặt xong, chạy lệnh kiểm tra trên VPS:
```bash
python3 "$HOME/.agents/skills/citizen-registry-rbac/scripts/lookup_citizen.py" --doctor
```
Nếu màn hình xuất hiện `Doctor result: OK` kèm số lượng bản ghi, hệ thống đã sẵn sàng hoạt động.
