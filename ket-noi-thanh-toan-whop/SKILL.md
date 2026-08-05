---
name: ket-noi-thanh-toan-whop
description: Set up, audit, or repair course website flows where a successful bank transfer via VietQR/SePay marks a Django order paid, creates a private activation token, redirects the customer to a Whop free checkout page (pre-filled email), verifies the completion callback, updates the database, and shows a clear activation success page with a manual course-entry button.
---

# Ket Noi Thanh Toan Whop

## Overview

Use this skill when a course website sells through bank transfer first, then grants Whop access after the payment is confirmed. The preferred pattern is:

`registration -> Order invoice -> VietQR/SePay paid IPN -> activation token -> Whop Free Checkout page (hidden free plan) -> Whop membership creation & redirect callback -> update DB status -> clear activation success page -> manual course-entry button`.

It also covers manual activation cases where the site owner wants a private/internal page to enter a customer's email, skip the website payment step, create a paid order, generate an activation link, and send that link to the customer.

Keep real API keys, company details, SePay secrets, and customer data out of skill files and examples. Use placeholders.

## When To Use

- A user asks to connect a Django course website to Whop after successful bank transfer.
- A payment page already creates `Order`/`Registration`, and the next step is Whop activation.
- A site receives SePay bank-sync IPN but customers do not get Whop access.
- Debugging errors like `checkout_failed`, `whop_not_configured`, `invalid_token`, or `membership_failed`.
- Reusing the OPCL-style flow for another course domain under `/root/10Web_BH/<number>_domain_<code>`.
- Adding a manual activation page such as `/khtc/` or `/kichhoatthucong/` where the owner enters an email and receives a customer activation link without requiring website payment.

If the task only checks payment/VietQR without Whop activation, use `kiem-tra-thanh-toan-website-khoa-hoc` instead or alongside this skill.

## Core Rules

- Treat bank transfer as the source of payment truth; Whop is used for access activation after payment, not for checkout.
- Use invoice numbers as transfer content, e.g. `<COURSE_CODE><digits>`.
- Mark paid only after the backend confirms sufficient transfer amount.
- Create a private `activation_token` only after `Order.status == "paid"`.
- Use Whop Free Checkout (via Checkout Configurations API) for the hidden free plan (e.g. `plan_f7W4cuCGkBNrE`) instead of Whop OAuth. This ensures unregistered users can register (via OTP) and claim access directly on the checkout form without losing redirect context.
- Prefill and lock the customer's email on the checkout page using `&email=<email>&email.disabled=1` to prevent email mismatches.
- Configure `redirect_url` in the checkout configuration payload to route back to our checkout callback URL `/api/whop/checkout-callback/?token=<token>`.
- In the callback, save the returned `membership_id` to the order and mark it `'activated'`.
- Do not auto-redirect customers from the activation success page. Present a clear manual "Vào học trên Whop" button so customers can read the sign-in warning before leaving the page.
- In the payment success screen view, calculate the total paid amount dynamically (subtotal after coupon + VAT 8%, rounded up to nearest thousand) and format it, instead of hardcoding the default course price constant.
- In the payment success template, display the backup activation link (`activation_link`) inside a copyable text box with a "Copy link" button, so that the customer has a way to resume activation or save the link. Also, display a Zalo support button/box linking to `https://zalo.me/<number>` so users can request support during learning.
- To avoid customers seeing two different post-payment UIs, redirect `/payment/success/` to `/activate/?token=<activation_token>` whenever the paid order has an activation token. Keep `payment_success.html` only as a fallback when the order/token cannot be resolved.
- Use one shared `/activate/` UI for both `whop_status == 'activated'` and `whop_status == 'oauth_pending'`. The copy should say the email has been granted Whop access, remind the customer to sign in with the exact activated email, and clearly warn that seeing Join/payment on Whop usually means they are not signed in and they should not pay again.
- Preserve old unpaid/paid orders and old invoice prefixes when adapting an existing site.
- For manual activation, create or reuse a paid `Order` for the email, set `Registration.payment_status = "paid"`, set `Order.status = "paid"`, set `payment_method = "MANUAL_ACTIVATION"`, call the same activation-token helper, return the normal `/activate/?token=...` customer link, and send that generated activation link to the same n8n activation/payment-success webhook used after paid IPN.
- Do not require an admin code/password for manual activation unless the user explicitly asks for one. If adding a guard, keep it in `.env` and never print it.
- Customer-facing and internal payment/activation pages should use a Vietnamese-friendly web font. Prefer `Be Vietnam Pro` with CSS fallback: `font-family: 'Be Vietnam Pro', Arial, sans-serif;`.
- If a logo is available in the project or provided by the user, copy/reuse it in the app static assets and place it visibly in the manual activation/payment interface.

## Quick Workflow

1. Inspect project structure.
   - Read `docker-compose.yml`, `.env` keys only, `mysite/settings.py`, `trolyai/models.py`, `trolyai/views.py`, `trolyai/whop.py`, `trolyai/sepay.py`, `trolyai/urls.py`, and activation/payment templates.
   - Never print secret values. Print only whether keys are set, prefix, or length when needed.

2. Verify payment success path.
   - Registration creates `Registration` and `Order`.
   - `Order.invoice_number` starts with target course code.
   - QR `addInfo` equals `order.invoice_number`.
   - SePay IPN extracts invoice from transfer content.
   - Paid transition updates both `Order.status` and `Registration.payment_status`.
   - Paid transition creates or preserves `activation_token`.

3. Verify Whop config.
   - Required for checkout creation: `WHOP_API_KEY` or `WHOP_COMPANY_API_KEY`, `WHOP_PLAN_ID`, `WHOP_API_BASE_URL`, `WHOP_COURSE_URL`.
   - The Whop plan must be a free plan or a hidden free plan (e.g. `plan_f7W4cuCGkBNrE`) so the checkout configuration doesn't prompt for payment.

4. Implement Whop Free Checkout page redirect.
   - Login endpoint calls `create_course_access_link` to create a checkout configuration for the hidden free plan, passing `redirect_url` as `/api/whop/checkout-callback/?token=<token>`.
   - Keep `create_course_access_link` compatible with both older `custom_redirect_url` callers and newer `plan_id` / `redirect_url` callers. The helper should accept `plan_id=''` and `redirect_url=None`, use `plan_id` first and fall back to `settings.WHOP_PLAN_ID`, then use `redirect_url` first, `custom_redirect_url` second, and `settings.WHOP_REDIRECT_URL` last.
   - Append `&email=<customer_email>&email.disabled=1` to the returned `purchase_url` and redirect the user there.

4b. Optional OAuth-login-first variant.
   - Use this only when the course owner wants to force the student to sign in to Whop and enter the Whop email/code before course access is granted.
   - In `whop_login`, generate a PKCE verifier/challenge, store `whop_oauth_code_verifier` on the paid order, then redirect to `build_oauth_authorize_url(...)` with `state=<activation_token>`.
   - In `whop_callback`, exchange the OAuth code, fetch userinfo, require the Whop email to match the paid email, call `create_membership_for_user(...)`, then redirect to `WHOP_COURSE_URL`.
   - Keep checkout callback routes as fallback/backward compatibility if existing Whop links still return there.
   - Required env vars: `WHOP_APP_ID`, `WHOP_APP_SECRET` or `WHOP_CLIENT_SECRET`, `WHOP_OAUTH_REDIRECT_URI`, `WHOP_API_KEY`, `WHOP_PLAN_ID`, and `WHOP_COURSE_URL`.

5. Implement checkout callback activation.
   - Callback receives `membership_id` and `checkout_id` from Whop.
   - Save `membership_id` as `whop_membership_id`, set `whop_status` to `'activated'`, and save syncing timestamps.
   - Redirect the user back to `/activate/?token=<token>` (the success screen).
   - Render a premium success screen with a manual "Vào học trên Whop" button. Do not add countdown or auto-redirect JavaScript unless the user explicitly asks for it.

6. Unify the customer activation UI.
   - In the payment success view, after creating or finding `activation_token`, immediately `redirect(f"{reverse('activate_course')}?token={order.activation_token}")`.
   - In `activate.html`, handle `activated` and `oauth_pending` with the same customer-facing block instead of two separate designs.
   - Recommended copy: "Email này đã được cấp quyền truy cập khóa học trên Whop. Bây giờ bạn chỉ cần đăng nhập đúng tài khoản Whop là vào học được."
   - Include a visible "Lưu ý quan trọng" warning that customers do not need to pay again if Whop shows Join/payment; they should sign in using the activated email first.
   - Keep the success page static: no countdown card, no `setInterval`, no `window.location` auto-redirect, and no secondary stay-on-page button.
   - If available, include a Sign in screenshot/illustration and a short guide video below the Whop course button.

7. If requested or useful, implement manual activation.
   - Add route `/khtc/` by default; if the project already has `/kichhoatthucong/`, keep it as a redirect or compatibility route when useful.
   - Add a form for customer email, optional name, optional phone.
   - Validate email with Django's `validate_email`.
   - Reuse an existing paid activation link for that email if one exists; otherwise create a paid `Registration`/`Order` and call the existing activation-token helper.
   - Immediately after creating/reusing the activation link, call a helper such as `_send_activation_link_webhook(order, activation_link, 'Manual Activation')`.
   - The manual activation webhook payload must include at least `name`, `email`, `phone`, `payment_status`, `invoice_number`, `amount`, `payment_method`, `course_code`, `course_name`, `whop_status`, `whop_plan_id` when available, `activation_link`, and `source`.
   - Use the same n8n activation webhook constant as paid payment success, for example `PAYMENT_SUCCESS_WEBHOOK_URL`, so manual activation behaves like a successful paid IPN.
   - Render the resulting activation link with a copy button.
   - Use `Be Vietnam Pro` for Vietnamese typography and include the company/course logo when available.

8. Deploy and verify.
   - Run `python manage.py check`.
   - Recreate container after `.env` changes: `docker compose up -d --build --force-recreate`.
   - Check runtime env inside the container by prefix/length only.
   - Test activation link from a paid order.
   - Test `/payment/success/?invoice=<invoice_with_token>` returns `302` to `/activate/?token=...`; do not print the real token in public notes.
   - Test an order with `whop_status='activated'` and another with `whop_status='oauth_pending'`; both should render the same clear activation guidance UI.
   - For manual activation, test `/khtc/` returns 200, includes the email form, includes the logo static path, and does not require an admin code unless explicitly configured.
   - Test a manual activation POST from inside the Docker container and confirm the n8n webhook responds, for example with a 2xx status or a body like `{"message":"Workflow was started"}`. If testing from the host cannot resolve the Docker service name such as `n8n3-app`, repeat the test inside the app container before deciding the webhook is broken.
   - Use logs and database fields to identify exact failure stage.

## Reference

For detailed implementation patterns, code snippets, migration checklist, debug commands, and customer-facing error mapping, read:

- `references/django-sepay-whop-pkce.md`

## Safety

- Do not include real `.env` values, API keys, SePay secrets, Whop client secrets, customer emails, bank account secrets, cookies, logs with tokens, or live webhook URLs in skill files.
- Use placeholders such as `Nhap_API_Cua_Ban`, `Nhap_Gia_Tri_Cua_Ban`, `email_cua_ban@example.com`, and `https://example.com/...`.
- When creating, updating, publishing, or preparing this skill for GitHub, use `khu-token-api-secret`.

## 2026-07 Webhook-Driven Whop Activation Addendum

For ANCL and any course website that grants software/course access through Whop memberships, do not treat checkout callback or membership create response as final activation proof.

Required pattern:

1. Before creating a Whop membership for a known Whop user, call `GET /v5/memberships?product_ids=<product_id>&user_ids=<user_id>` or the configured API-base equivalent. If a membership already has `active`, `completed`, or `trialing` status, reuse it and PATCH metadata with `external_order_id` instead of creating a duplicate.
2. Checkout configuration payloads must include metadata with `external_order_id`, `customer_email`, `customer_name`, `course_code`, `course_name`, and `source`.
3. Checkout callbacks should only save `whop_membership_id` and set local status to a pending state such as `oauth_pending`. They must not mark the order activated unless a prior valid membership lookup confirmed a stable membership.
4. Add a Whop webhook endpoint, for example `/api/whop/webhook/`, and configure Whop Dashboard > Developer > Webhooks to send `membership.went_valid` and `payment.succeeded` events to it.
5. Verify webhook signature using a secret from environment such as `WHOP_WEBHOOK_SECRET`. Never hardcode the real secret in code, docs, examples, or skill files.
6. Store processed webhook event ids in a database table to dedupe repeated Whop deliveries.
7. Only after a valid webhook, mark the order `activated`, keep `activation_token`, store `whop_membership_id`, and write a mapping log: `order_id` / invoice number ↔ membership id ↔ token ↔ timestamp.
8. If duplicate membership cleanup is implemented, PATCH/copy metadata to the membership that will remain active before canceling the older membership. Never cancel first.
9. For existing memberships missing metadata, repair with `PATCH /v5/memberships/{id}` and at minimum set `metadata.external_order_id` to the invoice/order id.

Environment placeholders to document in `.env.example`:

```dotenv
WHOP_PRODUCT_ID=Nhap_Gia_Tri_Cua_Ban
WHOP_WEBHOOK_SECRET=Nhap_Gia_Tri_Cua_Ban
```

Verification commands:

```bash
docker compose exec -T <django-service> python manage.py check
docker compose exec -T <django-service> python manage.py migrate
```

## 2026-07 Multi-Site Rollout Notes

Applied the webhook-driven Whop activation standard across the Whop-related course websites under `/root/Apps/course_websites/10Web_BH`:

- `02_domain_tlai` app `webtrolyai`
- `03_domain_oplw` app `trolyai`
- `19_domain_ancl` app `trolyai`
- `20_domain_anob` app `trolyai`
- `22_domain_opcl` app `trolyai`
- `28_domain_alt` app `website` using `ManualActivationOrder`
- `31_domain_anvi` app `anvi`

Shared operational rule: each project exposes `/api/whop/webhook/` and needs its own `WHOP_WEBHOOK_SECRET` in `.env`. If Whop membership lookup needs a product id separate from the plan id, set `WHOP_PRODUCT_ID` in that project `.env`. For `28_domain_alt`, mapping/log tables point to `ManualActivationOrder`; for the other course sites they point to `Order`.

After changing this standard, rerun for every affected website:

```bash
docker compose exec -T <container> python manage.py makemigrations <app>
docker compose exec -T <container> python manage.py migrate
docker compose exec -T <container> python manage.py check
```

## 2026-07 Activate Page Sign-In Guide UI

For course websites that use the shared Whop activation page, the `activated` / `oauth_pending` state should include a clear Whop sign-in guide before the final course button:

- A short heading: `Minh họa thao tác đăng nhập:`.
- Copy telling customers to click `Sign in` in the top-right Whop screen first, then log in with the exact paid/activated email.
- The static image `whop_signin_guide.svg` stored under the app static folder, for example `trolyai/static/trolyai/images/whop_signin_guide.svg`.
- The activated email box shown immediately after the illustration.
- The manual `Vào học trên Whop` button.
- An embedded YouTube guide using `https://www.youtube.com/embed/A8LN16u9DdI?feature=oembed`.

Applied to these templates under `/root/Apps/course_websites/10Web_BH`:

- `02_domain_tlai/webtrolyai/templates/webtrolyai/activate.html`
- `03_domain_oplw/trolyai/templates/trolyai/activate.html`
- `19_domain_ancl/trolyai/templates/trolyai/activate.html`
- `20_domain_anob/trolyai/templates/trolyai/activate.html`
- `22_domain_opcl/trolyai/templates/trolyai/activate.html`
- `28_domain_alt/website/templates/website/activate.html`
- `31_domain_anvi/anvi/templates/anvi/activate.html`

After editing, verify with:

```bash
docker compose exec -T <container> python manage.py check
docker compose exec -T <container> python manage.py shell -c "from django.template.loader import get_template; get_template('<app>/activate.html'); print('template_ok')"
```

## 2026-07 Activate Page Course Button Placement

On shared Whop activation pages, in the `activated` / `oauth_pending` state, place the manual course-entry button immediately after the confirmation sentence:

`Email này đã được cấp quyền truy cập khóa học trên Whop. Bây giờ bạn chỉ cần đăng nhập đúng tài khoản Whop là vào học được.`

Preferred order:

1. Confirmation sentence that the email has been granted Whop access.
2. Short text: `Bạn sẽ học trực tiếp trên Whop. Bạn có thể bấm nút bên dưới để vào ngay.`
3. Manual `Vào học trên Whop` button using `{{ course_url }}`.
4. Important warning not to pay again; sign in with the activated email first.
5. Sign-in illustration block using `whop_signin_guide.svg`.
6. YouTube sign-in guide embed.

This placement was applied to:

- `02_domain_tlai/webtrolyai/templates/webtrolyai/activate.html`
- `03_domain_oplw/trolyai/templates/trolyai/activate.html`
- `19_domain_ancl/trolyai/templates/trolyai/activate.html`
- `20_domain_anob/trolyai/templates/trolyai/activate.html`
- `22_domain_opcl/trolyai/templates/trolyai/activate.html`
- `28_domain_alt/website/templates/website/activate.html`
- `31_domain_anvi/anvi/templates/anvi/activate.html`
