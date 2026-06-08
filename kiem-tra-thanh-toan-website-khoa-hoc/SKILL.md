---
name: kiem-tra-thanh-toan-website-khoa-hoc
description: Validate course website payment pages against the working ANCL payment standard, including Django registration-to-payment flow, VietQR/SePay transfer page, course-code payment content such as ANCLxxxxx or OPLWxxxxx, IPN paid detection, check-status polling, and n8n activation webhook payloads for /root/10Web_BH projects.
---

# Kiem Tra Hop Le Trang Thanh Toan Website Khoa Hoc

Use this skill when the user asks to:

- kiểm tra trang thanh toán có hợp lệ không
- kiểm tra mã/nội dung chuyển khoản có đúng prefix khóa học không, ví dụ `ANCLxxxxx`, `OPLWxxxxx`
- kiểm tra thanh toán thành công có đổi trạng thái và gửi qua n8n không
- áp dụng chuẩn thanh toán đang chạy ở ANCL sang một dự án khóa học khác
- tạo hoặc chỉnh trang thanh toán dựa trên mẫu ANCL

## Default Scope

- Website projects: `/root/10Web_BH/<number>_domain_<code>`
- Course knowledge: `/root/Second_Brain/01_chuong_trinh_dao_tao/<number>_domain_<code>`
- Preferred stack when present: Django app with `trolyai/views.py`, `trolyai/sepay.py`, `trolyai/models.py`, `trolyai/urls.py`, templates under `trolyai/templates/trolyai/`.
- Default transfer content format: `<COURSE_CODE><random_digits>`, uppercase, no spaces. Examples: `ANCL17925`, `OPLW82721`.
- Canonical reference project: `/root/10Web_BH/19_domain_ancl`. Treat ANCL as the current working standard for Django payment validation unless the user names a different reference project.

## ANCL Standard

A target payment page is considered valid when it matches the ANCL pattern:

- A registration creates a `Registration` row and an `Order` row.
- `Order.invoice_number` starts with the target course code, e.g. `ANCL12345`.
- `/thanhtoan/?invoice=<CODE12345>` renders a QR payment page.
- The QR `addInfo` / transfer content is exactly the invoice number.
- `/payment/check-status/?invoice=<CODE12345>` returns `is_paid: true` only after backend order status is paid.
- `/payment/ipn/` can read SePay bank-sync payloads and extract the invoice from transaction content.
- Paid transition updates both `Order.status` and `Registration.payment_status`.
- Paid transition sends the n8n activation webhook with `course_code`, `invoice_number`, `amount`, and customer info.
- Existing old invoice prefixes remain payable if the project previously created unpaid orders with that old prefix.
- Coupon fixed-price standard: support `DAMUA2000` when requested, setting `Order.amount` to `2000` and regenerating the QR amount.
- VAT standard: show and charge VAT 8% on the payment page. Treat `Order.amount` as the subtotal after coupon, then calculate `VAT = subtotal * 8%` and `payment_total = subtotal + VAT`.
- The QR amount, IPN required amount, and payment-success n8n `amount` must use `payment_total`, not the subtotal.
- The payment page should not show internal coupon detail text such as `Đã giảm: ... · Coupon ...`; after applying coupon, show only the new payable amount and optionally the crossed-out original price.

## Quick Audit

Run the bundled checker first when auditing an existing project:

```bash
python /root/.agents/skills/kiem-tra-thanh-toan-website-khoa-hoc/scripts/check_payment_project.py \
  --project /root/10Web_BH/19_domain_ancl \
  --course-code ANCL
```

Use its findings as hints, then inspect the code directly before editing.

## Workflow

1. Identify the target course code.
   - Prefer explicit user input.
   - Otherwise infer from folder name: `/root/10Web_BH/19_domain_ancl` -> `ANCL`.
   - Confirm the same code appears in the Second Brain payment text, e.g. `Nội dung chuyển khoản (Syntax): ANCL [Số điện thoại]`.

2. Compare the target against the ANCL reference.
   - Read these files in ANCL when needed:
     - `/root/10Web_BH/19_domain_ancl/trolyai/sepay.py`
     - `/root/10Web_BH/19_domain_ancl/trolyai/views.py`
     - `/root/10Web_BH/19_domain_ancl/trolyai/urls.py`
     - `/root/10Web_BH/19_domain_ancl/trolyai/templates/trolyai/thanhtoan.html`
   - Do not blindly copy the ANCL course name, price, bank account, coupon codes, or old invoice data.
   - Copy the structure/pattern only, then substitute the target course code and course-specific config.

3. Inspect the current payment flow.
   - Search for `generate_invoice_number`, `payment_ipn`, `PAYMENT_SUCCESS_WEBHOOK_URL`, `WEBHOOK_URL`, `Order`, `payment/check-status`, `thanhtoan`.
   - Read `.env` keys only, not secret values.
   - Compare with a known working project if one is named by the user.

4. Enforce payment code consistency.
   - `generate_invoice_number()` must return `f"{COURSE_CODE}{digits}"`.
   - QR transfer content must be `order.invoice_number`.
   - IPN bank-sync regex must recognize the current code.
   - If old orders already exist with a previous prefix, keep backward compatibility in the regex, e.g. `((?:ANCL|ALT)\d+)`.
   - Avoid using generic `ALT` for single-course sites unless the course code is actually ALT.

5. Verify payment page validity.
   - Route `/thanhtoan/` exists and requires a valid `invoice`.
   - Page displays customer info, course amount, bank account, QR image, and transfer content.
   - Transfer content shown to customer exactly equals `invoice_number`.
   - QR URL includes the same amount as the final `payment_total`.
   - Coupon, if present, updates `Order.amount` before QR generation.
   - Fixed-price coupon, when requested, should use `DAMUA2000` -> `2.000 VNĐ`.
   - VAT 8% should be visible as a separate line, with `Tổng chuyển khoản` equal to subtotal plus VAT.
   - Hide internal coupon descriptions from the customer-facing amount box.
   - Polling JavaScript calls `/payment/check-status/` and redirects to `/payment/success/` after paid.

6. Verify IPN and paid-state handling.
   - `/payment/ipn/` must accept SePay bank-sync payloads with `transferType`, `transferAmount`, and `content`.
   - For inbound transfers, extract invoice from `content.upper()`.
   - Only mark paid when `transfer_amount >= payment_total`, where `payment_total = Order.amount + VAT 8%`.
   - Set both `order.status = "paid"` and `order.registration.payment_status = "paid"`.
   - Call the n8n activation webhook once when transitioning from unpaid to paid.
   - Return HTTP 200 to SePay even when an order is not found, after logging the issue.

7. Verify n8n payloads.
   - Registration webhook should include: `name`, `email`, `phone`, `payment_code`, `amount`, `course_code`, `course_name`, `payment_link`, `source`, `url`, `origin_url`.
   - Payment-success webhook should include: `name`, `email`, `phone`, `payment_status`, `invoice_number`, `amount`, `subtotal_amount`, `vat_rate_percent`, `vat_amount`, `payment_method`, `course_code`, `course_name`, `source`.
   - Do not hardcode real secrets in skill files or examples. Prefer env vars for configurable URLs where practical.

8. Build or adapt the payment page when requested.
   - Registration creates `Registration` and `Order`, then redirects to `/thanhtoan/?invoice=<CODE12345>`.
   - Payment page shows one clear QR, bank account details, transfer amount, and transfer content.
   - QR URL should include `amount` and `addInfo=<invoice_number>`.
   - Add VAT 8% after coupon calculation, then use the VAT-inclusive total for QR and IPN.
   - Frontend polling should call `/payment/check-status/?invoice=<invoice>` and redirect to `/payment/success/` only after backend status is `paid`.
   - Keep coupon logic, if any, server-side; update `Order.amount` before rendering QR.

9. Deploy and verify.
   - Run `python3 manage.py check`.
   - If Docker Compose changed, run `docker compose config --quiet`.
   - Recreate/restart the service if necessary.
   - Check logs: `docker logs --tail 200 <container>`.
   - Create a test registration and confirm the invoice prefix is correct.
   - Do not send real test payment unless the user explicitly asks. For payload tests, mock `requests.post` or use a local dry run.

## Implementation Reference

For Django/SePay/n8n patterns and snippets, read:

- `references/django-sepay-n8n-payment.md`

## Safety

- Never print real `.env` values, SePay secret keys, bot tokens, or n8n private URLs in the final answer.
- Do not put real tokens, account secrets, emails, cookies, or browser profiles into the skill.
- When creating/updating this skill or preparing it for GitHub, use `khu-token-api-secret`.
- Preserve old invoices after changing prefixes; do not rename existing paid orders unless the user explicitly requests it.
