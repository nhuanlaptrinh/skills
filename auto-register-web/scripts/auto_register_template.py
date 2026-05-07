"""
Auto Register Web Account - Template Script
=============================================
Template dùng bởi AI Agent để tạo script đăng ký tự động.
Các placeholder {{URL}}, {{COUPON}}, {{FULL_NAME}}, {{EMAIL}} sẽ được thay thế
bằng thông tin thực tế từ người dùng trước khi chạy.

Yêu cầu: pip install selenium
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import time
import traceback

# ============ THÔNG TIN ĐĂNG KÝ ============
URL = "{{URL}}"
COUPON = "{{COUPON}}"
FULL_NAME = "{{FULL_NAME}}"
EMAIL = "{{EMAIL}}"
# =============================================

LOG_FILE = "auto_register_log.txt"


def log(msg):
    """Ghi log ra terminal và file đồng thời."""
    print(msg)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(msg + "\n")


def setup_driver():
    """Khởi tạo Chrome WebDriver với các tùy chọn tối ưu."""
    options = Options()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_experimental_option("excludeSwitches", ["enable-logging"])
    return webdriver.Chrome(options=options)


def main():
    # Xóa log cũ
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write("")

    driver = setup_driver()
    wait = WebDriverWait(driver, 20)

    try:
        # Bước 1: Truy cập website
        log(f"BƯỚC 1: Truy cập {URL}...")
        driver.get(URL)
        time.sleep(3)
        log("   OK!")

        # Bước 2: Bấm nút Đăng Ký Ngay
        log("BƯỚC 2: Bấm nút Đăng Ký Ngay...")
        btn_register = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, 'a[href="order"]'))
        )
        driver.execute_script("arguments[0].click();", btn_register)
        time.sleep(3)
        log("   OK!")

        # Bước 3: Nhập mã coupon
        log(f"BƯỚC 3: Nhập mã coupon {COUPON}...")
        coupon_input = wait.until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, 'input[placeholder="Coupon code"]')
            )
        )
        coupon_input.clear()
        coupon_input.send_keys(COUPON)
        time.sleep(1)
        log("   OK!")

        # Bước 4: Bấm Apply và chờ coupon được áp dụng
        log("BƯỚC 4: Bấm nút Apply...")
        apply_btn = wait.until(
            EC.element_to_be_clickable(
                (By.XPATH, "//button[contains(., 'Apply')]")
            )
        )
        driver.execute_script("arguments[0].click();", apply_btn)

        log("   Đang chờ áp dụng coupon (có thể mất 10-30s)...")
        wait_long = WebDriverWait(driver, 50)
        wait_long.until(
            EC.presence_of_element_located(
                (By.XPATH, "//button[contains(., 'Complete')]")
            )
        )
        log("   OK - Đã thấy nút 'Complete my purchase', coupon đã áp dụng!")

        # Bước 5: Nhập họ tên
        log(f"BƯỚC 5: Nhập tên: {FULL_NAME}...")
        name_input = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input#name"))
        )
        name_input.click()
        time.sleep(0.5)
        name_input.clear()
        name_input.send_keys(FULL_NAME)
        time.sleep(0.5)
        val = name_input.get_attribute("value")
        log(f"   OK - Tên: '{val}'")

        # Bước 6: Nhập email
        log(f"BƯỚC 6: Nhập email: {EMAIL}...")
        email_input = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input#email"))
        )
        email_input.click()
        time.sleep(0.5)
        email_input.clear()
        email_input.send_keys(EMAIL)
        time.sleep(1)
        val = email_input.get_attribute("value")
        log(f"   OK - Email: '{val}'")

        # Bước 7: Hoàn tất đăng ký
        log("BƯỚC 7: Bấm nút Complete my purchase...")
        complete_btn = wait.until(
            EC.element_to_be_clickable(
                (By.XPATH, "//button[contains(., 'Complete')]")
            )
        )
        driver.execute_script(
            "arguments[0].scrollIntoView({block: 'center'});", complete_btn
        )
        time.sleep(1)
        driver.execute_script("arguments[0].click();", complete_btn)

        log("   Đang xử lý đơn hàng...")
        time.sleep(10)

        log("\nHOÀN TẤT ĐĂNG KÝ THÀNH CÔNG!")
        log(f"URL cuối: {driver.current_url}")
        time.sleep(5)

    except Exception as e:
        log(f"\nLỖI: {e}")
        log(traceback.format_exc())
        time.sleep(15)

    finally:
        driver.quit()
        log("Đã đóng trình duyệt.")


if __name__ == "__main__":
    main()
