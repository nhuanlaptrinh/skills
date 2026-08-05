#!/usr/bin/env python3
import argparse
import re
from pathlib import Path


def read_text(path):
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(errors="ignore")
    except FileNotFoundError:
        return ""


def status(ok, message):
    marker = "OK" if ok else "WARN"
    print(f"[{marker}] {message}")


def extract_invoice_prefix(sepay_text):
    match = re.search(r"return\s+f[\"']([A-Z0-9_{}]+)", sepay_text)
    if not match:
        return None
    template = match.group(1)
    prefix = re.match(r"([A-Z0-9]+)", template)
    return prefix.group(1) if prefix else None


def main():
    parser = argparse.ArgumentParser(description="Validate a Django course payment project against the ANCL payment standard.")
    parser.add_argument("--project", required=True, help="Path to /root/10Web_BH/<project>")
    parser.add_argument("--course-code", required=True, help="Expected course code prefix, e.g. ANCL")
    parser.add_argument("--reference", default="/root/10Web_BH/19_domain_ancl", help="Reference payment project, defaults to the ANCL standard")
    args = parser.parse_args()

    project = Path(args.project).resolve()
    reference = Path(args.reference).resolve()
    course_code = args.course_code.strip().upper()
    app = project / "trolyai"

    print(f"Project: {project}")
    print(f"Reference: {reference}")
    print(f"Expected course code: {course_code}")
    print()

    status(project.exists(), "project folder exists")
    status(reference.exists(), "ANCL/reference folder exists")
    status((project / "manage.py").exists(), "manage.py exists")
    status(app.exists(), "trolyai app folder exists")

    sepay_text = read_text(app / "sepay.py")
    views_text = read_text(app / "views.py")
    urls_text = read_text(app / "urls.py")
    env_text = read_text(project / ".env")

    print()
    generated_prefix = extract_invoice_prefix(sepay_text)
    status("def generate_invoice_number" in sepay_text, "generate_invoice_number() found in sepay.py")
    status(generated_prefix == course_code, f"invoice prefix is {generated_prefix!r}, expected {course_code!r}")

    status("re.search" in views_text and course_code in views_text, f"IPN matching code includes {course_code}")
    status("transferAmount" in views_text and "transferType" in views_text, "bank-sync IPN payload support found")
    status(
        "_payment_total_amount" in views_text and "transfer_amount >= required_amount" in views_text,
        "IPN checks VAT-inclusive required amount before marking paid",
    )
    status("_send_payment_success_notification(order)" in views_text, "payment success webhook called after paid transition")

    print()
    status("PAYMENT_SUCCESS_WEBHOOK_URL" in views_text, "payment success n8n webhook variable found")
    status("WEBHOOK_URL" in views_text, "registration webhook variable found")
    status('"course_code"' in views_text or "'course_code'" in views_text, "webhook payload includes course_code")
    status('"subtotal_amount"' in views_text or "'subtotal_amount'" in views_text, "payment success payload includes subtotal_amount")
    status('"vat_amount"' in views_text or "'vat_amount'" in views_text, "payment success payload includes vat_amount")
    status('"payment_code"' in views_text or "'payment_code'" in views_text, "registration payload includes payment_code")
    status('"invoice_number"' in views_text or "'invoice_number'" in views_text, "payment success payload includes invoice_number")

    print()
    status("path('thanhtoan/" in urls_text or 'path("thanhtoan/' in urls_text, "thanhtoan route found")
    status("path('payment/ipn/" in urls_text or 'path("payment/ipn/' in urls_text, "payment IPN route found")
    status("path('payment/check-status/" in urls_text or 'path("payment/check-status/' in urls_text, "payment check-status route found")
    status((app / "templates" / "trolyai" / "thanhtoan.html").exists(), "payment template thanhtoan.html exists")
    payment_template = read_text(app / "templates" / "trolyai" / "thanhtoan.html")
    status("transfer_content" in payment_template, "payment page renders transfer_content")
    status("Thuế VAT" in payment_template or "VAT" in payment_template, "payment page renders VAT line")
    status("Tổng chuyển khoản" in payment_template, "payment page renders final transfer total")
    status("amount-discount" not in payment_template, "payment page hides internal coupon discount detail")
    status("payment/check-status" in payment_template, "payment page polls check-status")
    status("payment/success" in payment_template, "payment page redirects to success page")

    print()
    if env_text:
        env_keys = []
        for line in env_text.splitlines():
            if "=" in line and not line.strip().startswith("#"):
                env_keys.append(line.split("=", 1)[0])
        print("Env keys found: " + ", ".join(env_keys))
    else:
        status(False, ".env missing or unreadable")

    print()
    print("Next manual checks:")
    print("- Create a test registration and confirm the invoice starts with the expected course code.")
    print("- Inspect docker logs after a real or simulated IPN.")
    print("- Confirm n8n workflow routes by course_code, not by a stale generic prefix.")


if __name__ == "__main__":
    main()
