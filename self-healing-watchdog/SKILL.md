---
name: self-healing-watchdog
description: Thiết lập hệ thống tự động sửa lỗi (Self-Healing) cho các dự án Python/Selenium chạy Cron trên Linux, sử dụng trợ lý AI OpenClaw.
---

# Self-Healing Watchdog (AI Tự Chữa Lành Code)

Kỹ năng này giúp thiết lập một hệ thống giám sát tự động phát hiện lỗi và triệu hồi Trợ lý AI (OpenClaw) tự động vá lỗi, chạy test và báo cáo kết quả qua Telegram cho bất kỳ dự án Python/Selenium nào chạy Cron trên Linux.

## 🚀 Luồng hoạt động chuẩn:
1. **Lỗi xảy ra**: Script chính kết thúc thất bại và trả về mã thoát khác 0 (exit 1).
2. **Kích hoạt Watchdog**: File Shell Script (.sh) bắt được mã lỗi và chạy `self_healing_watchdog.py`.
3. **Triệu hồi OpenClaw**: Watchdog đọc log lỗi, lưu trạng thái chống lặp vô hạn và gọi AI OpenClaw vào làm việc ngầm để sửa code và kiểm tra.

---

## 🛠️ Hướng dẫn cài đặt nhanh cho dự án mới:

### Bước 1: Chuẩn hóa code Python chính để trả về Exit Code khác 0 khi lỗi
Trong file Python chính của bạn (ví dụ: `app.py`), hãy đảm bảo khi có lỗi nghiêm trọng xảy ra, chương trình phải gọi `sys.exit(1)`.
* *Lưu ý*: Hãy thực hiện đóng trình duyệt Chrome/Selenium (`driver.quit()`) trước khi exit để tránh treo RAM.

**Ví dụ cấu trúc chuẩn:**
```python
import sys
import os

def main():
    success = False
    driver = None
    try:
        # Khởi tạo driver và logic chạy của bạn...
        driver = build_driver()
        
        # ... logic đăng bài hoặc cào dữ liệu ...
        
        success = True  # Đánh dấu thành công khi chạy xong hết
    except Exception as e:
        print(f"❌ Gặp lỗi: {e}")
        if driver:
            driver.save_screenshot("error.png")
    finally:
        if driver:
            driver.quit() # Luôn đóng Chrome sạch sẽ
            
    if not success:
        sys.exit(1)  # Bắt buộc thoát với mã lỗi 1 để Shell bắt được

if __name__ == "__main__":
    main()
```

---

### Bước 2: Tạo file `self_healing_watchdog.py` trong dự án mới
Copy đoạn code mẫu dưới đây và tạo file `self_healing_watchdog.py` ngay tại thư mục gốc của dự án cần bảo vệ.

**Nội dung `self_healing_watchdog.py`:**
```python
import os
import re
import subprocess
import json

# ==========================================
# CẤU HÌNH ĐƯỜNG DẪN DỰ ÁN MỚI CỦA BẠN TẠI ĐÂY
# ==========================================
PROJECT_ROOT = "/root/du_an_moi_cua_ban"          # Đường dẫn tuyệt đối đến dự án
LOG_FILE = os.path.join(PROJECT_ROOT, "logs/chay_cron.log")  # Đường dẫn đến file log của Cron
SCRIPT_TO_FIX = ".agents/skills/fb-auto-poster/scripts/OpenFBV2POST.py" # Script chính cần AI sửa nếu lỗi
TEST_COMMAND = "cd /root/du_an_moi_cua_ban && /usr/bin/python3 app.py" # Lệnh chạy thử nghiệm sau khi sửa

STATE_FILE = os.path.join(PROJECT_ROOT, "self_healing_state.json")

def read_last_lines(filepath, n=60):
    if not os.path.exists(filepath):
        return ""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            lines = f.readlines()
            return "".join(lines[-n:])
    except Exception as e:
        return f"Error reading log: {e}"

def main():
    print("🤖 Đang chạy Watchdog tự chữa lành (Self-Healing)...")
    if not os.path.exists(LOG_FILE):
        print(f"Không tìm thấy file log: {LOG_FILE}")
        return
        
    log_content = read_last_lines(LOG_FILE, 60)
    has_error = "❌" in log_content or "Lỗi" in log_content or "Exception" in log_content or "Traceback" in log_content
    
    if not has_error:
        print("✅ Không phát hiện lỗi nghiêm trọng trong file log gần nhất.")
        return

    # Trích xuất đoạn lỗi gần nhất
    error_match = re.findall(r"(Lỗi.*?(?===|Finished|$))", log_content, re.DOTALL)
    current_error = error_match[-1].strip() if error_match else log_content.strip()

    # Chống lặp vô hạn nếu AI không sửa được
    last_healed_content = ""
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                state = json.load(f)
                last_healed_content = state.get("last_healed_content", "")
        except:
            pass

    if current_error == last_healed_content:
        print("⚠️ Lỗi này đã được AI xử lý ở phiên trước đó nhưng chưa thành công. Tạm dừng để tránh vòng lặp.")
        return

    print("🚨 Phát hiện lỗi! Đang triệu hồi Trợ lý AI OpenClaw tự vá code ngầm...")

    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump({"last_healed_content": current_error}, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Lỗi ghi file trạng thái: {e}")

    # Prompt ra lệnh cho AI Agent
    prompt = (
        f"Dự án tại thư mục: '{PROJECT_ROOT}' vừa gặp lỗi khi chạy tự động.\n"
        f"Dưới đây là phần log lỗi ghi nhận được:\n"
        f"```\n{current_error}\n```\n"
        f"Yêu cầu:\n"
        f"1. Hãy phân tích lỗi trên.\n"
        f"2. Chỉnh sửa trực tiếp file code: '{PROJECT_ROOT}/{SCRIPT_TO_FIX}' để sửa lỗi logic/selector.\n"
        f"3. Chạy thử nghiệm bằng lệnh: '{TEST_COMMAND}' để kiểm tra xem đã hết lỗi chưa.\n"
        f"4. Báo cáo lại kết quả chi tiết sửa đổi qua tin nhắn Telegram cho tôi."
    )

    try:
        cmd = ["openclaw", "agent", "--message", prompt]
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print("🚀 Đã triệu hồi OpenClaw Self-Healing Agent thành công!")
    except Exception as e:
        print(f"❌ Lỗi triệu hồi OpenClaw: {e}")

if __name__ == "__main__":
    main()
```

---

### Bước 3: Cấu hình file Shell kích hoạt trong Cron
Trong file shell script chạy cron của bạn (ví dụ: `run_cron.sh`), hãy bọc phần gọi watchdog lại để nó **chỉ chạy khi lệnh chính trả về trạng thái thất bại (non-zero status)**:

```bash
# Thực hiện lệnh chạy chính của bạn
/usr/bin/xvfb-run -a /usr/bin/python3 app.py
status=$?

# Chỉ chạy Watchdog tự chữa lành vết thương khi có lỗi xảy ra (exit code khác 0)
if [ "$status" -ne 0 ]; then
  /usr/bin/python3 "/path/to/your/project/self_healing_watchdog.py"
fi

exit "$status"
```

Bằng cách áp dụng 3 bước chuẩn hóa này, bất kỳ dự án cron tự động nào của bạn trên VPS cũng có thể biến thành một hệ sinh thái **Tự chữa lành bằng AI** cực kỳ đẳng cấp!
