# Django SePay Whop PKCE Reference

## Table Of Contents

- Target architecture
- Expected files
- Data model checklist
- Payment-to-paid flow
- Activation token flow
- Manual activation flow
- Whop OAuth public client + PKCE
- Whop membership creation
- URLs and templates
- UI typography and branding
- Environment variables
- Deployment and verification
- Debug playbook
- Common errors
- Adaptation checklist for a new course site

## Target Architecture

The website handles payment before Whop:

1. Customer submits registration form.
2. Django creates `Registration` and `Order`.
3. `Order.invoice_number` is generated with the course prefix, e.g. `OPCL12345`.
4. Customer sees `/thanhtoan/?invoice=<invoice>` with VietQR.
5. Customer transfers to the business bank account with transfer content exactly equal to the invoice number.
6. SePay bank-sync IPN posts transaction data to `/payment/ipn/`.
7. Backend extracts invoice from transaction content and validates amount.
8. Backend marks the order paid, creates `activation_token`, sends email/webhook.
9. Customer opens `/activate/?token=<token>`.
10. Customer clicks "Sign in with Whop".
11. Django starts Whop OAuth public-client PKCE flow.
12. Whop redirects back to `/api/whop/callback/?code=...&state=<token>`.
13. Django exchanges code using `code_verifier`, without `client_secret`.
14. Django fetches Whop userinfo and verifies email matches paid registration email.
15. Django creates Whop membership for the configured plan.
16. Customer is redirected to the Whop course URL.

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
rg -n "WHOP|whop|activation_token|payment_ipn|check-status|generate_invoice_number|Order|Registration|thanhtoan|oauth" .
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
- `whop_oauth_code_verifier`
- `whop_user_id`
- `whop_user_email`
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
- Do not create Whop membership directly from this internal page; the customer still uses the normal Whop OAuth email verification flow.

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

    context.update({
        "customer_email": order.registration.email,
        "customer_name": order.registration.name,
        "customer_phone": order.registration.phone,
        "activation_link": build_activation_link(request, order),
        "order": order,
    })
    return render(request, "trolyai/manual_activation.html", context)
```

## Whop OAuth Public Client + PKCE

Use OAuth public client when Whop app is configured for PKCE. Do not send `client_secret` to `/oauth/token`.

`whop.py`:

```python
import base64
import hashlib
import secrets
from urllib.parse import urlencode

import requests
from django.conf import settings


def base64url(data):
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def generate_pkce_pair():
    code_verifier = secrets.token_urlsafe(48)
    code_challenge = base64url(
        hashlib.sha256(code_verifier.encode("ascii")).digest()
    )
    return code_verifier, code_challenge


def build_oauth_authorize_url(redirect_uri, state, code_challenge, nonce=""):
    app_id = getattr(settings, "WHOP_APP_ID", "")
    if not app_id:
        return ""

    oauth_base_url = getattr(
        settings, "WHOP_OAUTH_BASE_URL", "https://api.whop.com/oauth"
    ).rstrip("/")
    params = {
        "response_type": "code",
        "client_id": app_id,
        "redirect_uri": redirect_uri,
        "scope": "openid profile email",
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }
    if nonce:
        params["nonce"] = nonce
    return f"{oauth_base_url}/authorize?{urlencode(params)}"


def exchange_oauth_code(code, redirect_uri, code_verifier):
    app_id = getattr(settings, "WHOP_APP_ID", "")
    oauth_base_url = getattr(
        settings, "WHOP_OAUTH_BASE_URL", "https://api.whop.com/oauth"
    ).rstrip("/")
    payload = {
        "grant_type": "authorization_code",
        "code": code,
        "client_id": app_id,
        "redirect_uri": redirect_uri,
        "code_verifier": code_verifier,
    }

    response = requests.post(
        f"{oauth_base_url}/token",
        json=payload,
        headers={"Content-Type": "application/json"},
        timeout=15,
    )
    if response.status_code >= 400:
        return {
            "success": False,
            "error": f"OAuth token {response.status_code}: {response.text[:500]}",
        }
    return {"success": True, "tokens": response.json()}


def fetch_oauth_userinfo(access_token):
    oauth_base_url = getattr(
        settings, "WHOP_OAUTH_BASE_URL", "https://api.whop.com/oauth"
    ).rstrip("/")
    response = requests.get(
        f"{oauth_base_url}/userinfo",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=15,
    )
    if response.status_code >= 400:
        return {
            "success": False,
            "error": f"OAuth userinfo {response.status_code}: {response.text[:500]}",
        }
    return {"success": True, "user": response.json()}
```

Login endpoint:

```python
def whop_login(request):
    token = request.GET.get("token", "").strip()
    if not token:
        return redirect(f"{reverse('activate_course')}?error=missing_token")

    try:
        order = Order.objects.select_related("registration").get(
            activation_token=token
        )
    except Order.DoesNotExist:
        return redirect(f"{reverse('activate_course')}?token={token}&error=invalid_token")

    if order.status != "paid":
        return redirect(f"{reverse('activate_course')}?token={token}&error=not_paid")

    if order.whop_status == "activated" and order.whop_membership_id:
        return redirect(settings.WHOP_COURSE_URL)

    if not getattr(settings, "WHOP_APP_ID", ""):
        order.whop_status = "disabled"
        order.whop_error = "Missing WHOP_APP_ID."
        order.save(update_fields=["whop_status", "whop_error", "updated_at"])
        return redirect(f"{reverse('activate_course')}?token={token}&error=whop_not_configured")

    redirect_uri = getattr(settings, "WHOP_OAUTH_REDIRECT_URI", "") or request.build_absolute_uri(reverse("whop_callback"))
    code_verifier, code_challenge = generate_pkce_pair()
    auth_url = build_oauth_authorize_url(
        redirect_uri,
        token,
        code_challenge,
        nonce=token,
    )

    if not auth_url:
        return redirect(f"{reverse('activate_course')}?token={token}&error=whop_not_configured")

    order.whop_oauth_code_verifier = code_verifier
    order.whop_status = "oauth_pending"
    order.whop_error = None
    order.save(update_fields=[
        "whop_oauth_code_verifier",
        "whop_status",
        "whop_error",
        "updated_at",
    ])
    return redirect(auth_url)
```

Callback endpoint:

```python
def whop_callback(request):
    code = request.GET.get("code", "").strip()
    token = request.GET.get("state", "").strip()
    oauth_error = request.GET.get("error", "").strip()

    if oauth_error:
        return redirect(f"{reverse('activate_course')}?token={token}&error=oauth_error")

    if not code or not token:
        return redirect(f"{reverse('activate_course')}?error=missing_oauth_data")

    try:
        order = Order.objects.select_related("registration").get(
            activation_token=token
        )
    except Order.DoesNotExist:
        return redirect(f"{reverse('activate_course')}?token={token}&error=invalid_token")

    if order.status != "paid":
        return redirect(f"{reverse('activate_course')}?token={token}&error=not_paid")

    if not order.whop_oauth_code_verifier:
        return redirect(f"{reverse('activate_course')}?token={token}&error=session_expired")

    redirect_uri = getattr(settings, "WHOP_OAUTH_REDIRECT_URI", "") or request.build_absolute_uri(reverse("whop_callback"))
    token_result = exchange_oauth_code(
        code,
        redirect_uri,
        order.whop_oauth_code_verifier,
    )
    if not token_result.get("success"):
        order.whop_status = "failed"
        order.whop_error = token_result.get("error", "OAuth token exchange failed.")
        order.save(update_fields=["whop_status", "whop_error", "updated_at"])
        return redirect(f"{reverse('activate_course')}?token={token}&error=oauth_token_failed")

    access_token = token_result.get("tokens", {}).get("access_token")
    if not access_token:
        order.whop_status = "failed"
        order.whop_error = "OAuth token response missing access_token."
        order.save(update_fields=["whop_status", "whop_error", "updated_at"])
        return redirect(f"{reverse('activate_course')}?token={token}&error=oauth_token_failed")

    user_result = fetch_oauth_userinfo(access_token)
    if not user_result.get("success"):
        order.whop_status = "failed"
        order.whop_error = user_result.get("error", "OAuth userinfo failed.")
        order.save(update_fields=["whop_status", "whop_error", "updated_at"])
        return redirect(f"{reverse('activate_course')}?token={token}&error=userinfo_failed")

    # Continue with email verification and membership creation.
```

Important: Whop authorization codes are single-use and expire quickly. If callback fails, send customer back to `/activate/?token=<token>` and start a fresh OAuth login.

## Whop Membership Creation

Membership creation uses server-side API key, not OAuth public client secret.

```python
def create_membership_for_user(user_id, order_id="", customer_email=""):
    api_key = getattr(settings, "WHOP_API_KEY", "")
    plan_id = getattr(settings, "WHOP_PLAN_ID", "")
    if not api_key or not plan_id:
        return {
            "success": False,
            "status": "disabled",
            "error": "Missing WHOP_API_KEY/WHOP_COMPANY_API_KEY or WHOP_PLAN_ID.",
        }

    base_url = getattr(
        settings, "WHOP_API_BASE_URL", "https://api.whop.com/api/v1"
    ).rstrip("/")
    payload = {
        "plan_id": plan_id,
        "user_id": user_id,
        "metadata": {
            "external_order_id": order_id,
            "customer_email": customer_email,
            "source": "bank_transfer_oauth_activation",
        },
    }
    response = requests.post(
        f"{base_url}/memberships",
        json=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        timeout=15,
    )
    if response.status_code >= 400:
        return {
            "success": False,
            "status": "failed",
            "error": f"Whop membership API {response.status_code}: {response.text[:500]}",
        }

    data = response.json()
    return {
        "success": True,
        "status": "activated",
        "membership_id": data.get("id", ""),
    }
```

After userinfo:

```python
user = user_result.get("user", {})
whop_email = (user.get("email") or "").strip().lower()
paid_email = (order.registration.email or "").strip().lower()
whop_user_id = user.get("sub") or user.get("id") or ""

if not whop_email or whop_email != paid_email:
    order.whop_status = "failed"
    order.whop_user_email = whop_email or None
    order.whop_user_id = whop_user_id or None
    order.whop_error = f"Email Whop khong khop voi email da thanh toan: {paid_email}"
    order.save(update_fields=[
        "whop_status",
        "whop_user_email",
        "whop_user_id",
        "whop_error",
        "updated_at",
    ])
    return redirect(f"{reverse('activate_course')}?token={token}&error=email_mismatch")

membership_result = create_membership_for_user(
    user_id=whop_user_id,
    order_id=order.invoice_number,
    customer_email=order.registration.email,
)
if not membership_result.get("success"):
    order.whop_status = membership_result.get("status", "failed")
    order.whop_error = membership_result.get("error", "Membership creation failed.")
    order.whop_synced_at = timezone.now()
    order.save(update_fields=[
        "whop_status",
        "whop_error",
        "whop_synced_at",
        "updated_at",
    ])
    return redirect(f"{reverse('activate_course')}?token={token}&error=membership_failed")

order.whop_status = "activated"
order.whop_user_email = whop_email
order.whop_user_id = whop_user_id
order.whop_membership_id = membership_result.get("membership_id") or order.whop_membership_id
order.whop_error = None
order.whop_oauth_code_verifier = None
order.whop_synced_at = timezone.now()
order.activated_at = timezone.now()
order.save(update_fields=[
    "whop_status",
    "whop_user_email",
    "whop_user_id",
    "whop_membership_id",
    "whop_error",
    "whop_oauth_code_verifier",
    "whop_synced_at",
    "activated_at",
    "updated_at",
])
return redirect(settings.WHOP_COURSE_URL)
```

## URLs And Templates

URLs:

```python
urlpatterns = [
    path("kichhoatthucong/", views.manual_activation, name="manual_activation"),
    path("activate/", views.activate_course, name="activate_course"),
    path("api/whop/login/", views.whop_login, name="whop_login"),
    path("api/whop/callback/", views.whop_callback, name="whop_callback"),
]
```

Activation page behavior:

- Invalid token: show invalid link.
- Paid and activation ready: show registered email and "Đăng nhập bằng Whop".
- `email_mismatch`: tell customer to sign in with the paid email.
- `oauth_token_failed`: tell customer to retry; the OAuth code may have expired or been reused.
- `userinfo_failed`: tell admin OAuth userinfo failed.
- `membership_failed`: tell admin membership API failed.
- `whop_not_configured`: tell admin missing app ID/API key/plan.
- `activated`: show "Vào khóa học".

Do not show internal stack traces or raw tokens to customers.

Manual activation page behavior:

- Show the company/course logo clearly in the header.
- Show a concise form: customer email, optional name, optional phone.
- After submit, show customer email, invoice/order code, Whop status, read-only activation link, and a copy button.
- The generated link should be the same customer-facing activation URL used after bank payment.
- Keep the page operational as the first screen; avoid a marketing landing page.

## UI Typography And Branding

For Vietnamese course payment/activation pages, use `Be Vietnam Pro` by default:

```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:wght@400;500;600;700;800;900&display=swap&subset=vietnamese" rel="stylesheet">
```

```css
body {
    font-family: 'Be Vietnam Pro', Arial, sans-serif;
    -webkit-font-smoothing: antialiased;
    text-rendering: optimizeLegibility;
}
```

Use the project's existing logo if available. If the user provides a logo path, copy it into the Django app static folder, for example:

```text
trolyai/static/trolyai/images/company_logo.png
```

Reference it in templates with Django static:

```django
{% load static %}
<img class="logo" src="{% static 'trolyai/images/company_logo.png' %}" alt="Anh Lập Trình">
```

## Environment Variables

Safe `.env.example`:

```dotenv
WHOP_API_KEY=Nhap_API_Cua_Ban
WHOP_PLAN_ID=Nhap_Gia_Tri_Cua_Ban
WHOP_REDIRECT_URL=https://whop.com/your-course/
WHOP_API_BASE_URL=https://api.whop.com/api/v1
WHOP_APP_ID=Nhap_Gia_Tri_Cua_Ban
WHOP_OAUTH_BASE_URL=https://api.whop.com/oauth
WHOP_OAUTH_REDIRECT_URI=https://example.com/api/whop/callback/
WHOP_COURSE_URL=https://whop.com/your-course/
```

Notes:

- `WHOP_APP_SECRET` is not required for public-client PKCE OAuth exchange.
- `WHOP_API_KEY` is still required for membership creation.
- If using Docker Compose, pass env vars explicitly:

```yaml
environment:
  - WHOP_API_KEY=${WHOP_API_KEY:-}
  - WHOP_PLAN_ID=${WHOP_PLAN_ID:-}
  - WHOP_API_BASE_URL=${WHOP_API_BASE_URL:-https://api.whop.com/api/v1}
  - WHOP_APP_ID=${WHOP_APP_ID:-}
  - WHOP_OAUTH_BASE_URL=${WHOP_OAUTH_BASE_URL:-https://api.whop.com/oauth}
  - WHOP_OAUTH_REDIRECT_URI=${WHOP_OAUTH_REDIRECT_URI:-https://example.com/api/whop/callback/}
  - WHOP_COURSE_URL=${WHOP_COURSE_URL:-https://whop.com/your-course/}
```

## Deployment And Verification

After changing `.env` or Docker Compose:

```bash
docker compose up -d --build --force-recreate
```

Check runtime env without printing secrets:

```bash
docker exec <container> python manage.py shell -c "
from django.conf import settings
print('WHOP_APP_ID', settings.WHOP_APP_ID[:4], len(settings.WHOP_APP_ID))
print('WHOP_API_KEY', settings.WHOP_API_KEY[:5], len(settings.WHOP_API_KEY))
print('WHOP_PLAN_ID', settings.WHOP_PLAN_ID[:5], len(settings.WHOP_PLAN_ID))
print('WHOP_OAUTH_REDIRECT_URI', settings.WHOP_OAUTH_REDIRECT_URI)
"
```

Verify Django:

```bash
docker exec <container> python manage.py check
curl -I -L --max-time 15 https://example.com
```

Verify manual activation page when implemented:

```bash
curl -s -L --max-time 15 https://example.com/kichhoatthucong/ | rg -n "Be Vietnam Pro|Email khách hàng|company_logo|Tạo link kích hoạt"
```

Verify token exchange payload does not include `client_secret`:

```bash
docker exec <container> python manage.py shell -c "
from trolyai import whop
captured = {}
class R:
    status_code = 400
    text = '{}'
def fake_post(url, json=None, headers=None, timeout=None):
    captured.update({'url': url, 'json': json})
    return R()
whop.requests.post = fake_post
whop.exchange_oauth_code('code123', 'https://example.com/api/whop/callback/', 'verifier123')
print(captured['json'])
print('client_secret' in captured['json'])
"
```

Expected final line: `False`.

## Debug Playbook

Inspect one activation token:

```bash
docker exec <container> python manage.py shell -c "
from trolyai.models import Order
activation_token_value = 'Nhap_Gia_Tri_Cua_Ban'
o = Order.objects.select_related('registration').get(activation_token=activation_token_value)
print(o.invoice_number, o.status, o.whop_status, o.whop_error)
print(bool(o.whop_oauth_code_verifier), o.registration.email)
"
```

Reset a paid order to retry activation:

```bash
docker exec <container> python manage.py shell -c "
from trolyai.models import Order
activation_token_value = 'Nhap_Gia_Tri_Cua_Ban'
o = Order.objects.get(activation_token=activation_token_value)
o.whop_status = 'activation_ready'
o.whop_error = None
o.whop_oauth_code_verifier = None
o.save(update_fields=['whop_status', 'whop_error', 'whop_oauth_code_verifier', 'updated_at'])
print(o.invoice_number, o.status, o.whop_status)
"
```

Check logs:

```bash
docker logs --tail 200 <container>
```

Check URLs:

```bash
curl -I -L --max-time 15 https://example.com
curl -s -L --max-time 15 'https://example.com/activate/?token=Nhap_Gia_Tri_Cua_Ban' | rg -n "Đăng nhập|Whop|email"
```

## Common Errors

`client_secret lacks oauth:token_exchange permission`

- Cause: backend is sending `client_secret` while Whop app is configured as a public client, or the secret belongs to the wrong type of credential.
- Fix: remove `client_secret` from `/oauth/token` payload and use PKCE only.

`client_secret is required`

- Cause: Whop app is configured as confidential client, but backend is not sending secret.
- Fix: decide with Whop settings. For this skill, prefer public client + PKCE and configure Whop accordingly.

`invalid_grant`

- Cause: authorization code expired, reused, redirect URI mismatch, or wrong code verifier.
- Fix: start OAuth again from `/activate/?token=...`; ensure stored verifier is from the same login attempt; ensure redirect URI exact match.

`session_expired`

- Cause: `whop_oauth_code_verifier` missing on order.
- Fix: customer must click login again from activation page.

`email_mismatch`

- Cause: customer logged into Whop with an email different from paid registration email.
- Fix: ask customer to sign into Whop with the paid email, or update policy if business accepts alternate verified emails.

`userinfo_failed`

- Cause: OAuth access token failed at `/userinfo`, missing scopes, or Whop outage.
- Fix: ensure scopes include `openid profile email`.

`membership_failed`

- Cause: `WHOP_API_KEY` lacks permission, wrong `WHOP_PLAN_ID`, endpoint changed, or user ID invalid.
- Fix: inspect `order.whop_error`; verify membership API key, plan ID, and required Whop permissions.

Payment succeeds but activation email is missing:

- Check `prepare_whop_activation()` runs inside paid transition.
- Check email backend or n8n webhook.
- Manually inspect `Order.activation_token`.

Activation link says invalid:

- Token not found, wrong database/container, or old email link.
- Verify container volume points to the expected database.

## Adaptation Checklist For A New Course Site

1. Identify course code, domain, course name, amount, VAT/coupon policy.
2. Confirm payment page uses target invoice prefix and exact transfer content.
3. Confirm paid IPN amount logic and old-prefix compatibility.
4. Add Whop fields/migration to `Order`.
5. Add `whop.py` helpers or update existing helper to public-client PKCE.
6. Add URLs: `/activate/`, `/api/whop/login/`, `/api/whop/callback/`.
7. Add optional `/kichhoatthucong/` manual activation page if the owner wants to create links from customer email without website payment.
8. Add activation/manual templates with email guidance, clear error messages, `Be Vietnam Pro`, and visible logo when available.
9. Configure env vars in `.env` and `docker-compose.yml`.
10. Recreate container after env changes.
11. Create a test registration, mark paid via mock IPN or controlled test transaction.
12. Open clean activation link and complete Whop sign-in.
13. Verify DB: `status=paid`, `whop_status=activated`, `whop_membership_id` set.
14. Verify customer lands on `WHOP_COURSE_URL`.
15. Sanitize logs and examples before sharing or committing.
