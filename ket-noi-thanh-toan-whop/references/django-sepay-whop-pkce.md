# Django SePay Whop Checkout Reference

## Table Of Contents

- Target architecture
- Expected files
- Data model checklist
- Payment-to-paid flow
- Activation token flow
- Manual activation flow
- Whop Checkout Page Redirection Integration
- URLs and templates
- UI typography and branding
- Environment variables
- Deployment and verification
- Debug playbook
- Common errors
- Adaptation checklist for a new course site

## Target Architecture

The website handles payment before granting Whop course access:

1. Customer submits registration form.
2. Django creates `Registration` and `Order`.
3. `Order.invoice_number` is generated with the course prefix, e.g. `OPCL12345`.
4. Customer sees `/thanhtoan/?invoice=<invoice>` with VietQR.
5. Customer transfers to the business bank account with transfer content exactly equal to the invoice number.
6. SePay bank-sync IPN posts transaction data to `/payment/ipn/`.
7. Backend extracts invoice from transaction content and validates amount.
8. Backend marks the order paid, creates an `activation_token`, sends email/webhook notification.
9. Customer opens `/activate/?token=<token>`.
10. Customer clicks "Đăng nhập bằng Whop".
11. Django starts Whop login by calling the Whop API to create a checkout configuration for the hidden free plan (e.g. `plan_f7W4cuCGkBNrE`).
12. Whop returns a `purchase_url`. The backend appends `&email=<customer_email>&email.disabled=1` to prefill and lock the email, then redirects the customer there.
13. Customer registers or logs in on Whop's hosted checkout form and completes the free order.
14. Whop redirects the customer back to `/api/whop/checkout-callback/?token=<token>&membership_id=<membership_id>&checkout_id=<checkout_id>`.
15. Django receives the callback parameters, saves `membership_id` as `whop_membership_id`, and sets `whop_status` to `'activated'`.
16. Customer is redirected back to the success screen at `/activate/?token=<token>`.
17. The success screen does not auto-redirect. It shows a clear "Vào học trên Whop" button so customers can read the sign-in warning and choose when to leave the page.
18. If `/payment/success/?invoice=...` is opened after a paid order already has `activation_token`, redirect it to `/activate/?token=...` so the customer sees one consistent post-payment UI.

## Expected Files

Typical project layout:

```text
/root/10Web_BH/<number>_domain_<code>/
├── docker-compose.yml
├── .env
├── manage.py
├── mysite/settings.py
└── trolyai/
    ├── models.py
    ├── sepay.py
    ├── whop.py
    ├── urls.py
    ├── views.py
    └── templates/trolyai/
        ├── thanhtoan.html
        ├── payment_success.html
        └── activate.html
```

Search targets:

```bash
rg -n "WHOP|whop|activation_token|payment_ipn|check-status|generate_invoice_number|Order|Registration|thanhtoan|checkout_configurations" .
```

Read `.env` keys only. Do not print values.

## Data Model Checklist

`Registration` should include:

- `name`
- `email`
- `phone`
- `payment_status`: `pending`, `paid`, `failed`, `cancelled`
- `created_at`

`Order` should include:

- `registration`
- `invoice_number` unique and indexed
- `amount`
- `status`: `created`, `paid`, `failed`, `cancelled`
- `payment_method`
- `sepay_transaction_id` or equivalent
- `activation_token` unique and indexed
- `whop_status`: `pending`, `activation_ready`, `oauth_pending`, `activated`, `disabled`, `failed`
- `whop_membership_id`
- `whop_error`
- `whop_synced_at`
- `activated_at`

If fields are missing, add migrations. Do not rename existing paid order data unless explicitly asked.

## Payment-To-Paid Flow

Registration creates the order:

```python
registration = Registration.objects.create(
    name=name,
    email=email,
    phone=phone,
)

order = Order.objects.create(
    registration=registration,
    invoice_number=generate_invoice_number(),
    amount=COURSE_AMOUNT_NUMBER,
    description=f"Khoa hoc {COURSE_NAME}",
)
```

Invoice generation:

```python
def generate_invoice_number():
    return f"{COURSE_CODE}{random.randint(1, 99999)}"
```

VietQR must use final payable total and invoice as `addInfo`:

```python
qr_url = generate_vietqr_url("congty", payment_total, order.invoice_number)
```

IPN bank-sync pattern:

```python
@csrf_exempt
@require_POST
def payment_ipn(request):
    data = json.loads(request.body)

    if "transferAmount" in data or "transferType" in data:
        transfer_type = data.get("transferType", "")
        transfer_amount = int(data.get("transferAmount", 0))
        content = data.get("content", "").upper()

        if transfer_type == "in":
            match = re.search(r"((?:OPCL|OLDPREFIX)\d+)", content)
            if match:
                invoice_number = match.group(1)
                try:
                    order = Order.objects.select_related("registration").get(
                        invoice_number=invoice_number
                    )
                    required_amount = payment_total_amount(order.amount)
                    if transfer_amount >= required_amount:
                        mark_order_paid(order, "Bank sync")
                except Order.DoesNotExist:
                    logger.warning("Order not found: %s", invoice_number)

        return JsonResponse({"success": True}, status=200)
```

Paid transition:

```python
def mark_order_paid(order, source):
    if order.status == "paid":
        if not order.activation_token:
            prepare_whop_activation(order)
        return

    order.status = "paid"
    order.payment_method = order.payment_method or "BANK_TRANSFER"
    order.registration.payment_status = "paid"
    order.registration.save(update_fields=["payment_status"])
    order.save(update_fields=["status", "payment_method", "updated_at"])

    prepare_whop_activation(order)
    send_payment_success_notification(order)
```

## Activation Token Flow

Only create activation tokens for paid orders:

```python
def build_activation_link(request, order):
    if request:
        return request.build_absolute_uri(
            reverse("activate_course") + f"?token={order.activation_token}"
        )
    return f"{SITE_BASE_URL.rstrip()}/activate/?token={order.activation_token}"


def prepare_whop_activation(order):
    if order.activation_token:
        return order.activation_token

    for _ in range(20):
        token = secrets.token_urlsafe(24)
        if not Order.objects.filter(activation_token=token).exists():
            break
    else:
        raise RuntimeError("Could not generate unique activation token")

    order.activation_token = token
    order.whop_status = "activation_ready"
    order.whop_error = None
    order.whop_synced_at = timezone.now()
    order.save(update_fields=[
        "activation_token",
        "whop_status",
        "whop_error",
        "whop_synced_at",
        "updated_at",
    ])
    send_whop_access_email(order)
    return token
```

## Manual Activation Flow

Use this when the course owner wants to skip the website payment page for selected customers. The owner enters the customer's email, receives the normal activation link, and sends it to the customer.

Default route:

```python
path("kichhoatthucong/", views.manual_activation, name="manual_activation")
```

Default behavior:

- Do not require an admin code/password unless the user explicitly asks for one.
- Validate the customer email.
- If a paid order with an existing `activation_token` already exists for the email, reuse it.
- Otherwise create a `Registration` marked paid and an `Order` marked paid.
- Set `payment_method = "MANUAL_ACTIVATION"`.
- Call the same `prepare_whop_activation(order)` helper used by real bank payments.
- Display the resulting `/activate/?token=...` link with a copy button.

Example helper:

```python
from django.core.exceptions import ValidationError
from django.core.validators import validate_email


def create_or_get_manual_activation_order(email, name="", phone=""):
    normalized_email = email.strip().lower()
    validate_email(normalized_email)

    existing_order = (
        Order.objects.select_related("registration")
        .filter(
            registration__email__iexact=normalized_email,
            status="paid",
            activation_token__isnull=False,
        )
        .exclude(activation_token="")
        .order_by("-created_at")
        .first()
    )
    if existing_order:
        return existing_order

    registration = Registration.objects.create(
        name=name or normalized_email.split("@")[0],
        email=normalized_email,
        phone=phone or "Kich hoat thu cong",
        payment_status="paid",
    )
    order = Order.objects.create(
        registration=registration,
        invoice_number=generate_invoice_number(),
        amount=COURSE_AMOUNT_NUMBER,
        description=f"Khoa hoc {COURSE_NAME} - Kich hoat thu cong",
        status="paid",
        payment_method="MANUAL_ACTIVATION",
    )
    prepare_whop_activation(order)
    return order
```

View pattern:

```python
def manual_activation(request):
    context = {
        "course_name": COURSE_NAME,
        "customer_email": "",
        "customer_name": "",
        "customer_phone": "",
        "activation_link": "",
        "order": None,
        "errors": [],
    }
    if request.method != "POST":
        return render(request, "trolyai/manual_activation.html", context)

    email = request.POST.get("email", "").strip().lower()
    name = request.POST.get("name", "").strip()
    phone = request.POST.get("phone", "").strip()

    try:
        order = create_or_get_manual_activation_order(email, name, phone)
    except ValidationError:
        context["errors"] = ["Email khách hàng không hợp lệ."]
        context["customer_email"] = email
        return render(request, "trolyai/manual_activation.html", context)

    # Call n8n webhook notification
    activation_link = build_activation_link(request, order)
    _send_activation_link_webhook(order, activation_link, "Manual Activation")

    context.update({
        "customer_email": order.registration.email,
        "customer_name": order.registration.name,
        "customer_phone": order.registration.phone,
        "activation_link": activation_link,
        "order": order,
    })
    return render(request, "trolyai/manual_activation.html", context)
```

## Whop Checkout Page Redirection Integration

Instead of complex OAuth PKCE handling (which interrupts redirect sessions during first-time registrations), redirect paid customers to a Whop Checkout Page pre-filled and locked with their payment email.

### `whop.py` helper

```python
import logging
from urllib.parse import urlencode, urlsplit, urlunsplit, parse_qsl, urljoin
import requests
from django.conf import settings

logger = logging.getLogger(__name__)

def _lock_checkout_email(purchase_url, customer_email):
    """Prefill and lock email on the Whop checkout configuration page."""
    if not purchase_url or not customer_email:
        return purchase_url

    parts = urlsplit(purchase_url)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query["email"] = customer_email
    query["email.disabled"] = "1"
    return urlunsplit((
        parts.scheme,
        parts.netloc,
        parts.path,
        urlencode(query),
        parts.fragment,
    ))

def create_course_access_link(customer_email, order_id, customer_name="", course_code="", course_name="", custom_redirect_url=None):
    """Create a Whop hosted checkout link for the paid order using Checkout Configurations API."""
    api_key = getattr(settings, "WHOP_API_KEY", "")
    plan_id = getattr(settings, "WHOP_PLAN_ID", "")

    if not api_key or not plan_id:
        return {
            "success": False,
            "status": "disabled",
            "error": "Missing WHOP_API_KEY or WHOP_PLAN_ID.",
        }

    base_url = getattr(settings, "WHOP_API_BASE_URL", "https://api.whop.com/api/v1").rstrip("/")
    redirect_url = custom_redirect_url or getattr(settings, "WHOP_REDIRECT_URL", "https://whop.com/")
    
    payload = {
        "plan_id": plan_id,
        "mode": "payment",
        "metadata": {
            "external_order_id": order_id,
            "customer_email": customer_email,
            "customer_name": customer_name,
            "course_code": course_code,
            "course_name": course_name,
        },
        "redirect_url": redirect_url,
    }

    response = requests.post(
        f"{base_url}/checkout_configurations",
        json=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        timeout=15,
    )

    if response.status_code >= 400:
        logger.warning("Whop checkout API error %s: %s", response.status_code, response.text[:500])
        return {
            "success": False,
            "status": "failed",
            "error": f"Whop API {response.status_code}: {response.text[:500]}",
        }

    data = response.json()
    purchase_url = data.get("purchase_url", "")
    if purchase_url.startswith("/"):
        purchase_url = urljoin("https://whop.com", purchase_url)
    purchase_url = _lock_checkout_email(purchase_url, customer_email)

    if not purchase_url:
        return {
            "success": False,
            "status": "failed",
            "error": "Whop response missing purchase_url.",
        }

    return {
        "success": True,
        "status": "created",
        "checkout_id": data.get("id", ""),
        "purchase_url": purchase_url,
        "raw": data,
    }
```

### Django Views for Login and Checkout Callback

```python
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.conf import settings
from trolyai.models import Order
from trolyai.whop import create_course_access_link

def whop_login(request):
    """Redirect a paid customer to Whop Checkout, specifying custom callback URL."""
    token = request.GET.get("token", "").strip()
    if not token:
        return redirect(f"{reverse('activate_course')}?error=missing_token")

    try:
        order = Order.objects.select_related("registration").get(activation_token=token)
    except Order.DoesNotExist:
        return redirect(f"{reverse('activate_course')}?token={token}&error=invalid_token")

    if order.status != "paid":
        return redirect(f"{reverse('activate_course')}?token={token}&error=not_paid")

    if order.whop_status == "activated" and order.whop_membership_id:
        return redirect(f"{reverse('activate_course')}?token={token}")

    # Build callback redirect URL
    scheme = request.scheme or "https"
    host = request.get_host()
    custom_redirect = f"{scheme}://{host}/api/whop/checkout-callback/?token={token}"

    res = create_course_access_link(
        customer_email=order.registration.email,
        order_id=order.invoice_number,
        customer_name=order.registration.name,
        course_code=settings.COURSE_CODE,
        course_name=settings.COURSE_NAME,
        custom_redirect_url=custom_redirect,
    )

    if not res.get("success"):
        order.whop_status = "failed"
        order.whop_error = res.get("error", "Checkout configuration failed.")
        order.save(update_fields=["whop_status", "whop_error", "updated_at"])
        return redirect(f"{reverse('activate_course')}?token={token}&error=whop_not_configured")

    purchase_url = res.get("purchase_url", "")
    order.whop_status = "oauth_pending"
    order.whop_error = None
    order.save(update_fields=["whop_status", "whop_error", "updated_at"])
    return redirect(purchase_url)

def whop_checkout_callback(request):
    """Callback triggered after successful Whop Checkout session completion."""
    token = request.GET.get("token", "").strip()
    membership_id = request.GET.get("membership_id", "").strip()
    checkout_id = request.GET.get("checkout_id", "").strip()

    if not token:
        return redirect(f"{reverse("activate_course")}?error=missing_token")

    try:
        order = Order.objects.select_related("registration").get(activation_token=token)
    except Order.DoesNotExist:
        return redirect(f"{reverse("activate_course")}?token={token}&error=invalid_token")

    if order.status != "paid":
        return redirect(f"{reverse("activate_course")}?token={token}&error=not_paid")

    if order.whop_status == "activated" and order.whop_membership_id:
        return redirect(f"{reverse("activate_course")}?token={token}")

    m_id = membership_id or order.whop_membership_id or ""
    order.whop_status = "activated"
    # Fallback to checkout ID if membership ID not received in query string parameters
    order.whop_membership_id = m_id or (f"checkout_{checkout_id}" if checkout_id else "checkout_completed")
    order.whop_error = None
    order.whop_synced_at = timezone.now()
    order.activated_at = timezone.now()
    order.save(update_fields=[
        "whop_status",
        "whop_membership_id",
        "whop_error",
        "whop_synced_at",
        "activated_at",
        "updated_at",
    ])
    return redirect(f"{reverse("activate_course")}?token={token}")
```

## URLs And Templates

### URL Configuration (`urls.py`)

```python
from django.urls import path
from trolyai import views

urlpatterns = [
    path("kichhoatthucong/", views.manual_activation, name="manual_activation"),
    path("activate/", views.activate_course, name="activate_course"),
    path("api/whop/login/", views.whop_login, name="whop_login"),
    path("api/whop/checkout-callback/", views.whop_checkout_callback, name="whop_checkout_callback"),
]
```

### Premium Activation UI (`activate.html`)

Preferred current pattern: use `/activate/` as the single customer-facing post-payment screen. Do not maintain two visually different success screens for paid customers.

Payment success redirect pattern:

```python
activation_link = build_activation_link(request, order) if order and order.activation_token else ""
if order and order.activation_token:
    return redirect(f"{reverse('activate_course')}?token={order.activation_token}")
```

Activation template state pattern:

```django
{% if not order %}
    <p>Link kích hoạt không hợp lệ hoặc đã bị thiếu mã token.</p>
{% elif order.whop_status == 'activated' or order.whop_status == 'oauth_pending' %}
    <a class="action-btn" href="{{ course_url }}">Vào học trên Whop</a>
{% else %}
    <p>Đăng nhập hoặc tạo tài khoản Whop bằng đúng email đã thanh toán để truy cập khóa học ngay.</p>
    <a class="action-btn" href="{% url 'whop_login' %}?token={{ token }}">Kích hoạt trên Whop</a>
{% endif %}
```

For `activated` and `oauth_pending`, prefer the same explanatory block. This prevents customers from seeing a terse "already activated" page in one state and a clearer "sign in correctly, do not pay again" page in another state.
Do not include countdown or auto-redirect JavaScript on the default activation success page. Add it only if the user explicitly requests timed redirection.
Uses `Be Vietnam Pro` font-family fallback and premium micro-interactions. The default activation success page is static and uses a manual course-entry button:

```html
{% load static %}
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Kích hoạt khóa học - Anh Lập Trình</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:wght@400;500;600;700;800;900&display=swap&subset=vietnamese" rel="stylesheet">
    <style>
        * { box-sizing: border-box; }
        body {
            margin: 0;
            min-height: 100vh;
            font-family: 'Be Vietnam Pro', Arial, sans-serif;
            background: #f4fbf9;
            color: #0f172a;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 24px;
        }
        .activation-box {
            width: 100%;
            max-width: 640px;
            text-align: center;
            background: #ffffff;
            border: 1px solid #dbe7e4;
            border-radius: 8px;
            padding: 40px 28px;
            box-shadow: 0 18px 50px rgba(15, 23, 42, 0.12);
        }
        h1 {
            margin: 0 0 14px;
            font-size: 32px;
            line-height: 1.25;
            color: #006b5e;
        }
        p {
            margin: 0 auto 18px;
            max-width: 520px;
            font-size: 17px;
            line-height: 1.65;
            color: #475569;
        }
        .email-box {
            margin: 22px auto;
            padding: 14px 16px;
            max-width: 480px;
            background: #eefaf7;
            border: 1px solid #b2e0d9;
            border-radius: 8px;
            color: #00574d;
            font-weight: 700;
            overflow-wrap: anywhere;
        }
        .action-btn {
            display: inline-block;
            margin-top: 8px;
            background: #6c5ce7;
            color: #ffffff;
            padding: 16px 32px;
            border-radius: 8px;
            text-decoration: none;
            font-size: 18px;
            font-weight: 800;
            box-shadow: 0 10px 24px rgba(108, 92, 231, 0.28);
            transition: all 0.2s ease-in-out;
        }
        .action-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 12px 28px rgba(108, 92, 231, 0.38);
        }
        .notice {
            margin: 22px auto 0;
            padding: 14px 16px;
            max-width: 520px;
            border-radius: 8px;
            background: #fff7ed;
            border: 1px solid #fed7aa;
            color: #9a3412;
            font-weight: 700;
        }
        .success {
            background: #ecfdf5;
            border-color: #a7f3d0;
            color: #047857;
        }
        .home-link {
            display: inline-block;
            margin-top: 22px;
            color: #00786a;
            font-weight: 700;
            text-decoration: none;
        }
    </style>
</head>
<body>
    <main class="activation-box">
        <h1>Kích hoạt khóa học</h1>

        {% if not order %}
            <p>Link kích hoạt không hợp lệ hoặc đã bị thiếu mã token.</p>
            <div class="notice">Vui lòng kiểm tra lại email kích hoạt hoặc liên hệ admin.</div>
            <a class="home-link" href="/">Quay về trang chủ</a>
        {% elif order.whop_status == 'activated' %}
            <div class="success-icon" style="font-size: 56px; color: #10b981; margin-bottom: 16px;">✓</div>
            <p style="font-size: 19px; font-weight: 700; color: #0f172a; margin-bottom: 12px;">Kích hoạt thành công!</p>
            <p>Tài khoản của bạn đã được liên kết với chương trình học trên Whop.</p>
            <div class="email-box">{{ order.registration.email }}</div>
            <a id="btn-enter-course" class="action-btn" href="{{ course_url }}" style="background: #10b981; box-shadow: 0 10px 24px rgba(16, 185, 129, 0.28);">Vào khóa học ngay</a>
        {% else %}
            <p>Đăng nhập hoặc tạo tài khoản Whop bằng đúng email đã thanh toán để truy cập khóa học ngay.</p>
            <div class="email-box">{{ order.registration.email }}</div>

            {% if error == 'whop_not_configured' %}
                <div class="notice">Cổng kích hoạt Whop đang thiếu quyền tạo Checkout. Thanh toán của anh/chị đã được ghi nhận, admin sẽ cập nhật cấu hình hoặc kích hoạt thủ công.</div>
            {% elif error %}
                <div class="notice">Có lỗi khi kích hoạt. Vui lòng thử lại hoặc liên hệ admin.</div>
            {% endif %}

            <a class="action-btn" href="{% url 'whop_login' %}?token={{ token }}">Đăng nhập hoặc Tạo tài khoản Whop</a>
            <a class="home-link" href="/" style="display: inline-block; margin-top: 22px;">Quay về trang chủ</a>
        {% endif %}
    </main>
</body>
</html>
```

## UI Typography and Branding

All customer-facing activation templates should include `Be Vietnam Pro` dynamically loaded via Google Fonts. 

If a branding logo is available, import it via static files and render it prominently at the top of payment and activation views:

```django
{% load static %}
<div class="brand-header">
    <img src="{% static 'trolyai/images/logo.png' %}" alt="Logo" class="logo">
</div>
```

## Environment Variables

Safe `.env.example`:

```dotenv
WHOP_API_KEY=Nhap_API_Cua_Ban
WHOP_PLAN_ID=Nhap_Gia_Tri_Cua_Ban
WHOP_API_BASE_URL=https://api.whop.com/api/v1
WHOP_COURSE_URL=https://whop.com/anh-lap-trinh/
```

Pass these environment variables dynamically inside `docker-compose.yml`:

```yaml
environment:
  - WHOP_API_KEY=${WHOP_API_KEY:-}
  - WHOP_PLAN_ID=${WHOP_PLAN_ID:-}
  - WHOP_API_BASE_URL=${WHOP_API_BASE_URL:-https://api.whop.com/api/v1}
  - WHOP_COURSE_URL=${WHOP_COURSE_URL:-https://whop.com/anh-lap-trinh/}
```

## Deployment and Verification

Recreate and restart the docker container after `.env` edits:

```bash
docker compose up -d --build --force-recreate
```

Confirm that variables are read correctly from python without exposing keys:

```bash
docker exec <container> python manage.py shell -c "
from django.conf import settings
print('WHOP_API_KEY prefix:', settings.WHOP_API_KEY[:6], 'Length:', len(settings.WHOP_API_KEY))
print('WHOP_PLAN_ID:', settings.WHOP_PLAN_ID)
print('WHOP_COURSE_URL:', settings.WHOP_COURSE_URL)
"
```

Verify Django code status inside the running app container:

```bash
docker exec <container> python manage.py check
```

## Debug Playbook

Check the status of an activation token:

```bash
docker exec <container> python manage.py shell -c "
from trolyai.models import Order
token = 'Nhap_Token_Cua_Ban'
o = Order.objects.select_related('registration').get(activation_token=token)
print('Order invoice:', o.invoice_number, 'Status:', o.status, 'Whop status:', o.whop_status)
print('Email:', o.registration.email, 'Membership:', o.whop_membership_id)
"
```

Reset an order activation state back to pending:

```bash
docker exec <container> python manage.py shell -c "
from trolyai.models import Order
o = Order.objects.get(activation_token='Nhap_Token_Cua_Ban')
o.whop_status = 'activation_ready'
o.whop_membership_id = ''
o.whop_error = None
o.save(update_fields=['whop_status', 'whop_membership_id', 'whop_error', 'updated_at'])
print('Reset completed.')
"
```

## Common Errors

`Missing WHOP_API_KEY or WHOP_PLAN_ID`
- Cause: The env variables are not present in `.env` or missing inside `docker-compose.yml` environment blocks.
- Fix: Add the variables to `.env` and rebuild the container.

`Whop API 400/401: Unauthorized / Bad Request`
- Cause: The plan ID is incorrect or the API key lacks permission to create checkout configurations.
- Fix: Verify configuration variables in Whop dashboard.

`Whop course redirection redirects to Access Denied`
- Cause: The customer is redirected immediately before Whop servers replicate the checkout membership record (~3-5 seconds replication lag).
- Fix: Keep customers on the activation success page with a manual "Vào học trên Whop" button; remind them to sign in with the activated email before entering Whop.

## Adaptation Checklist For A New Course Site

1. Identify course code, domain, course name, and the hidden free plan ID.
2. Confirm payment page uses target invoice prefix and exact transfer content.
3. Confirm paid IPN amount logic and old-prefix compatibility.
4. Add Whop database columns (`whop_status`, `whop_membership_id`, `whop_error`, `whop_synced_at`, `activated_at`) to `Order` model and run migrations.
5. Add `/activate/`, `/api/whop/login/`, and `/api/whop/checkout-callback/` URLs.
6. Configure the `whop.py` module to request checkout configuration endpoints using `WHOP_API_KEY`.
7. Configure env variables in `.env` and `docker-compose.yml`. Rebuild the container.
8. Test flow with manual activation email to get a paid activation link.
9. Open the activation link in an incognito window, complete Whop checkout sign-up/login, verify callback activation and the manual course-entry button.
10. Ensure the successful payment page (`/payment/success/`) redirects to `/activate/?token=...` for paid orders with an activation token; keep amount/backup-link/Zalo support UI only as fallback for unresolved orders.
11. Ensure `/activate/` uses the same clear guidance UI for both `whop_status='activated'` and `whop_status='oauth_pending'`, including the "do not pay again; sign in with the activated email" warning.
