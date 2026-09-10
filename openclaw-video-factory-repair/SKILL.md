---
name: openclaw-video-factory-repair
description: Skill chuyên dụng độc lập dùng để chẩn đoán, phòng ngừa và tự động khắc phục 100% các lỗi hệ thống Video Factory (Delivery failed, dính logo mẫu, Heartbeat alert spam, render chậm, thiếu cache) trên MỌI VPS (Standalone host hoặc Docker member).
---

# OpenClaw Video Factory Universal Repair & Recovery Skill

Skill này là **bản độc lập chuyên dụng (Portable Standalone Skill)** được đóng gói hoàn chỉnh để:
1. **Khắc phục ngay lập tức** khi bất kỳ VPS nào (VPS hiện tại hoặc VPS mới triển khai trong tương lai) gặp lỗi gửi video, lỗi render chậm hoặc lỗi tin nhắn lạ.
2. **Tự động hóa hoàn toàn 1-chạm** thông qua script `repair.py` (hỗ trợ kiểm tra `--audit` và tự động sửa `--apply`).
3. **Cẩm nang tra cứu nguyên nhân gốc rễ (Root Cause Analysis)** và giải pháp chuẩn xác cho kỹ sư/AI.

---

## 1. Hướng dẫn sử dụng nhanh (Quick Start)

### Bước 1: Kiểm tra sức khỏe hệ thống (Read-only Audit)
Lệnh này quét toàn bộ file cấu hình và tài nguyên trên VPS, chỉ báo cáo lỗi chứ KHÔNG thay đổi dữ liệu:
```bash
python3 /root/.agents/skills/openclaw-video-factory-repair/scripts/repair.py --audit
```

### Bước 2: Tự động sửa lỗi toàn diện (Auto-Heal & Fix)
Lệnh này sẽ tự động sao lưu cấu hình gốc trước, sau đó sửa toàn bộ các lỗi phát hiện được:
```bash
python3 /root/.agents/skills/openclaw-video-factory-repair/scripts/repair.py --apply
```

---

## 2. Danh mục 5 lỗi điển hình & Cách khắc phục triệt để

### 🔴 Lỗi 1: `⚠️ <file>: Delivery failed. Try sending this file again`
* **Hiện tượng:** Video render ra file MP4 thành công trong thư mục workspace, nhưng khi bot gửi link `MEDIA:...` ra Telegram thì Telegram báo lỗi Delivery failed.
* **Nguyên nhân gốc rễ:**
  1. Trong `openclaw.json`, `toolsBySender["*"].deny` có chứa `"group:fs"`.
  2. Các ID admin Telegram chỉ được định danh ở dạng `channel:telegram:<id>`.
  3. Khi xử lý tin nhắn trực tiếp (DM) gửi media, OpenClaw không có prefix `channel:telegram:`, dẫn đến việc kiểm tra quyền bị đẩy vào nhóm wildcard `*` và bị chặn bởi `deny: ["group:fs"]`.
* **Cách khắc phục:**
  - Xóa `"group:fs"` khỏi danh sách `deny` của `*`.
  - Thêm định danh trực tiếp `"id:<telegram_id>": {}` song song với `"channel:telegram:<telegram_id>": {}`.
  - Script `repair.py --apply` sẽ tự động thực hiện việc này.

---

### 🔴 Lỗi 2: Video render bị dính Logo mẫu "Anh Lập Trình" hoặc chữ "💡 KHÁM PHÁ CÔNG NGHỆ"
* **Hiện tượng:** Khách hàng yêu cầu làm video nhưng video xuất ra tự động bị chèn logo mẫu ở góc phải và tiêu đề gán cứng.
* **Nguyên nhân:** File template demo gốc `index.html` của dự án HyperFrames có sẵn thẻ `<div class="brand"><img src="logo1.png"></div>` và `<div class="eyebrow">💡 KHÁM PHÁ CÔNG NGHỆ</div>`. Script cũ kế thừa nguyên mẫu này.
* **Cách khắc phục:**
  - Cập nhật script `generate_video.py` để mặc định tắt hoàn toàn logo và chữ công nghệ.
  - Thêm cờ `--logo <đường_dẫn_file>` và `--title <tiêu_đề>` để chỉ thêm logo khi khách hàng thực sự yêu cầu và cung cấp file.

---

### 🔴 Lỗi 3: Bot tự động gửi tin nhắn kỹ thuật `First heartbeat alert...` / `SIGTERM` vào Telegram
* **Hiện tượng:** Bot đột nhiên nhắn vào Telegram: `First heartbeat alert: your bot runs periodic background checks... Tác vụ máy chủ tạm đã được dừng chủ động...`.
* **Nguyên nhân:** Cơ chế Heartbeat của OpenClaw định kỳ quét tiến trình. Khi một tiến trình render bị hủy (`pkill`), sự kiện `SIGTERM` bị đưa vào Heartbeat và gửi cảnh báo ra Telegram vì chưa cấu hình chặn.
* **Cách khắc phục:**
  - Trong `openclaw.json`, đặt `agents.defaults.heartbeat.target` thành `"none"`:
    ```json
    "agents": {
      "defaults": {
        "heartbeat": {
          "target": "none"
        }
      }
    }
    ```

---

### 🔴 Lỗi 4: Render video bị nghẽn rất lâu (3–5 phút)
* **Hiện tượng:** Mỗi lần render video mất từ 3 đến 5 phút, máy chủ ngốn CPU cao ở bước khởi động Chrome.
* **Nguyên nhân:** Thiếu thư mục cache đã giải nén sẵn của Chrome headless shell (`/root/.cache/hyperframes`), khiến mỗi lần render Node.js phải tự giải nén lại từ file zip 112MB.
* **Cách khắc phục:**
  - Chuẩn bị sẵn thư mục giải nén `chrome-headless-shell-linux64` trong `/root/.cache/hyperframes/`. Tốc độ render sau đó sẽ giảm xuống còn **~35 - 45 giây**.

---

### 🔴 Lỗi 5: Lỗi phân quyền ghi file workspace (`EACCES: permission denied`)
* **Hiện tượng:** Script báo lỗi không thể tạo thư mục hoặc ghi file video vào workspace.
* **Cách khắc phục:**
  - Phân quyền thư mục workspace về user chuẩn (`chown -R 1001:1001 ~/.openclaw/workspace/output`).

---

## 3. Cách chuyển giao Skill này sang một VPS hoàn toàn mới
Nếu anh tạo một VPS mới và muốn đem toàn bộ kỹ năng sửa lỗi này sang:
1. Copy toàn bộ thư mục `/root/.agents/skills/openclaw-video-factory-repair/` sang VPS mới vào cùng đường dẫn `/root/.agents/skills/`.
2. Trên VPS mới, chỉ cần chạy 1 lệnh:
   ```bash
   python3 /root/.agents/skills/openclaw-video-factory-repair/scripts/repair.py --apply
   ```
Toàn bộ hệ thống OpenClaw và Video Factory trên VPS mới sẽ tự động được vá lỗi và sẵn sàng hoạt động ổn định.
