# Django SePay n8n Payment Pattern Based on ANCL

## Core Files

Typical project layout:

```text
/root/10Web_BH/<project>/
├── .env
├── docker-compose.yml
├── manage.py
└── trolyai/
    ├── models.py
    ├── sepay.py
    ├── urls.py
    ├── views.py
    └── templates/trolyai/
        ├── index.html
        ├── thanhtoan.html
        ├── payment_success.html
        ├── payment_error.html
        └── payment_cancel.html
```

Reference implementation:

```text
/root/10Web_BH/19_domain_ancl
```

Use ANCL as the standard for structure and behavior, not for course-specific values. When applying to another project, replace course code, course name, amount, domain, and any project-specific bank/coupon settings.

## Required Model Shape

`Registration` should track customer info and `payment_status`.

`Order` should track:

- `registration`
- `invoice_number`
- `amount`
- `status`
- `sepay_order_id`
- `sepay_transaction_id`
- `payment_method`
- `description`

Use existing migrations when present; do not rewrite database history casually.

## Prefix Pattern

In `trolyai/sepay.py`:

```python
COURSE_CODE = "ANCL"


def generate_invoice_number():
    return f"{COURSE_CODE}{random.randint(1, 99999)}"
```

If the project already defines `COURSE_CODE` in `views.py`, either import it carefully or duplicate the constant in `sepay.py` to keep the change small. For a larger cleanup, move shared config to `settings.py` or a `payment_config.py` module.

Validation rule: the first visible transfer code generated for a new registration must start with the target course code. For example:

- ANCL site: `ANCL12345`
- OPLW site: `OPLW12345`
- ANVI site: `ANVI12345`

## VietQR Pattern

```python
def generate_vietqr_url(bank_key, amount, content):
    account = BANK_ACCOUNTS.get(bank_key)
    if not account:
        return ""

    template = "qr_only"
    return (
        f"https://img.vietqr.io/image/"
        f"{account['bank_id']}-{account['account_number']}-{template}.png"
        f"?amount={int(amount)}"
        f"&addInfo={quote(content)}"
        f"&accountName={quote(account['account_name'])}"
    )
```

The `content` argument should be `order.invoice_number`, not the phone number or course name.

On `thanhtoan.html`, the visible transfer content and the QR `addInfo` must match exactly. If they differ, the page is invalid because SePay/n8n may not match the transaction.

## Coupon Pattern

When a fixed-price coupon is requested, use `DAMUA2000` as the standard coupon code:

```python
COUPONS = {
    "DAMUA2000": {
        "fixed_amount": 2000,
        "label": "DAMUA2000 - Còn 2.000đ",
    },
}
```

The coupon handler should set `Order.amount` to `2000`, save the coupon in `Order.description`, and regenerate the payment page so the QR amount becomes `2.000 VNĐ`.

If VAT is enabled, `Order.amount` remains the subtotal after coupon. The final QR amount is subtotal plus VAT.

Customer-facing payment pages should not show internal coupon descriptions such as:

```text
Đã giảm: 1.459.000 VNĐ · Coupon DAMUA2000 gia con 2.000 VNĐ
```

Show the new payable amount and optionally the crossed-out original price only.

## VAT 8% Pattern

Use VAT 8% as the standard payment-page tax pattern:

```python
VAT_RATE_PERCENT = Decimal("8")


def _calculate_vat_amount(amount):
    subtotal = Decimal(str(amount))
    vat = subtotal * VAT_RATE_PERCENT / Decimal("100")
    return vat.quantize(Decimal("1"), rounding=ROUND_HALF_UP)


def _payment_total_amount(amount):
    subtotal = Decimal(str(amount))
    return (subtotal + _calculate_vat_amount(subtotal)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
```

Render:

- `subtotal_amount`: học phí after coupon
- `vat_rate_percent`: `8`
- `vat_amount`: VAT amount
- `total_amount`: final transfer amount

Use `total_amount` for the VietQR `amount` parameter:

```python
qr_congty = generate_vietqr_url("congty", total_amount, transfer_content)
```

For IPN bank-sync, compare the incoming transfer with `_payment_total_amount(order.amount)`, not `order.amount`.

## IPN Bank Sync Pattern

```python
@csrf_exempt
@require_POST
def payment_ipn(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        logger.error("IPN: Invalid JSON body")
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    if "transferAmount" in data or "transferType" in data:
        transfer_type = data.get("transferType", "")
        transfer_amount = int(data.get("transferAmount", 0))
        content = data.get("content", "")

        if transfer_type == "in":
            match = re.search(r"((?:ANCL|ALT)\d+)", content.upper())
            if match:
                invoice_number = match.group(1)
                try:
                    order = Order.objects.select_related("registration").get(invoice_number=invoice_number)
                except Order.DoesNotExist:
                    logger.warning("IPN: Order not found: %s", invoice_number)
                    return JsonResponse({"success": True}, status=200)

                required_amount = _payment_total_amount(order.amount)
                if transfer_amount >= required_amount and order.status != "paid":
                    order.status = "paid"
                    order.registration.payment_status = "paid"
                    order.registration.save()
                    order.save()
                    _send_payment_success_notification(order)

        return JsonResponse({"success": True}, status=200)
```

Replace `ANCL` with the target course code. Keep old prefixes only when old unpaid invoices already exist.

For a project converted from a wrong prefix, accept both prefixes in IPN but generate only the new correct prefix:

```python
match = re.search(r"((?:OPLW|ALT)\d+)", content.upper())
```

In that example, new OPLW invoices use `OPLWxxxxx`, while old `ALTxxxxx` invoices can still be paid.

## n8n Payload Pattern

Registration notification:

```python
payload = {
    "name": name,
    "email": email,
    "phone": phone or "Không có",
    "payment_code": invoice_number or "Không có",
    "amount": COURSE_AMOUNT,
    "course_code": COURSE_CODE,
    "course_name": COURSE_NAME,
    "source": "Website Anh Lập Trình (Django)",
    "url": url,
    "origin_url": origin_url,
    "payment_link": payment_link or "",
}
```

Payment success / activation notification:

```python
payload = {
    "name": reg.name,
    "email": reg.email,
    "phone": reg.phone,
    "payment_status": "PAID",
    "invoice_number": order.invoice_number,
    "amount": str(order.amount),
    "payment_method": order.payment_method or "BANK_TRANSFER",
    "course_code": COURSE_CODE,
    "course_name": COURSE_NAME,
    "source": "SePay Payment Gateway",
}
```

## Dry-Run Webhook Test

To verify payload shape without sending to n8n:

```bash
cd /root/10Web_BH/<project>
python3 manage.py shell -c "
from trolyai import views
views.requests.post = lambda url, json, timeout: type('R', (), {'status_code': 200, 'text': 'ok'})()
from trolyai.models import Order
order = Order.objects.select_related('registration').filter(status='paid').first()
views._send_payment_success_notification(order)
print('dry-run ok')
"
```

## Useful Searches

```bash
rg -n "generate_invoice_number|payment_ipn|PAYMENT_SUCCESS_WEBHOOK_URL|WEBHOOK_URL|course_code|payment/check-status|thanhtoan|requests.post" /root/10Web_BH/<project>
```

```bash
rg -n "Nội dung chuyển khoản|Syntax|ANCL|OPLW|thanh toán|chuyển khoản" /root/Second_Brain/01_chuong_trinh_dao_tao/<course>
```
