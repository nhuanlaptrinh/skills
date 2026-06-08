---
name: ket-noi-thanh-toan-whop
description: Set up, audit, or repair course website flows where a successful bank transfer via VietQR/SePay marks a Django order paid, creates a private activation token, lets the paid customer sign in with Whop OAuth public client + PKCE, then creates Whop membership/access. Use for Anh Lap Trinh course websites similar to OPCL, ANCL, ALT, OPLW when payment success must activate Whop access or when debugging Whop OAuth/token/membership errors after bank transfer.
---

# Ket Noi Thanh Toan Whop

## Overview

Use this skill when a course website sells through bank transfer first, then grants Whop access after the payment is confirmed. The preferred pattern is:

`registration -> Order invoice -> VietQR/SePay paid IPN -> activation token -> Whop OAuth public client + PKCE -> verify email -> create Whop membership -> redirect to course`.

It also covers manual activation cases where the site owner wants a private/internal page to enter a customer's email, skip the website payment step, create a paid order, generate an activation link, and send that link to the customer.

Keep real API keys, client secrets, SePay secrets, webhook URLs, bank details, and customer data out of skill files and examples. Use placeholders.

## When To Use

- A user asks to connect a Django course website to Whop after successful bank transfer.
- A payment page already creates `Order`/`Registration`, and the next step is Whop activation.
- A site receives SePay bank-sync IPN but customers do not get Whop access.
- Debugging errors like `oauth_token_failed`, `whop_not_configured`, `invalid_client`, `invalid_grant`, `email_mismatch`, or `membership_failed`.
- Reusing the OPCL-style flow for another course domain under `/root/10Web_BH/<number>_domain_<code>`.
- Adding a manual activation page such as `/kichhoatthucong/` where the owner enters an email and receives a customer activation link without requiring website payment.

If the task only checks payment/VietQR without Whop activation, use `kiem-tra-thanh-toan-website-khoa-hoc` instead or alongside this skill.

## Core Rules

- Treat bank transfer as the source of payment truth; Whop is used for access activation after payment, not for checkout.
- Use invoice numbers as transfer content, e.g. `<COURSE_CODE><digits>`.
- Mark paid only after the backend confirms sufficient transfer amount.
- Create a private `activation_token` only after `Order.status == "paid"`.
- Use Whop OAuth as a public client with PKCE: send `code_challenge` at authorize time and `code_verifier` at token exchange time.
- Do not send `client_secret` in OAuth token exchange when Whop app is configured as a public client.
- Verify the Whop email matches the paid registration email before granting membership.
- Create membership with a server-side Whop API key after email verification.
- Preserve old unpaid/paid orders and old invoice prefixes when adapting an existing site.
- For manual activation, create or reuse a paid `Order` for the email, set `Registration.payment_status = "paid"`, set `Order.status = "paid"`, set `payment_method = "MANUAL_ACTIVATION"`, call the same activation-token helper, and return the normal `/activate/?token=...` customer link.
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
   - Required for OAuth sign-in: `WHOP_APP_ID`, `WHOP_OAUTH_REDIRECT_URI`, `WHOP_COURSE_URL`.
   - Required for membership creation: `WHOP_API_KEY` or `WHOP_COMPANY_API_KEY`, `WHOP_PLAN_ID`, `WHOP_API_BASE_URL`.
   - Optional/legacy: `WHOP_APP_SECRET`; do not require it for public-client PKCE flow.
   - Redirect URI must match exactly, including trailing slash if configured: `https://<domain>/api/whop/callback/`.

4. Implement OAuth public-client PKCE.
   - Login endpoint creates `code_verifier`, derives SHA256 `code_challenge`, stores verifier on the order, and redirects to Whop authorize.
   - Callback loads order by `state`, sends `grant_type`, `code`, `client_id`, `redirect_uri`, and `code_verifier` to Whop token endpoint.
   - Token exchange payload must not include `client_secret`.

5. Implement membership activation.
   - Fetch `/oauth/userinfo` with returned access token.
   - Compare Whop email to `order.registration.email`, normalized lowercase.
   - If emails match, create membership for the Whop user and configured plan.
   - Save `whop_user_id`, `whop_user_email`, `whop_membership_id`, `whop_status`, and `activated_at`.
   - Redirect to `WHOP_COURSE_URL` only after activation succeeds.

6. If requested or useful, implement manual activation.
   - Add route `/kichhoatthucong/`.
   - Add a form for customer email, optional name, optional phone.
   - Validate email with Django's `validate_email`.
   - Reuse an existing paid activation link for that email if one exists; otherwise create a paid `Registration`/`Order` and call the existing activation-token helper.
   - Render the resulting activation link with a copy button.
   - Use `Be Vietnam Pro` for Vietnamese typography and include the company/course logo when available.

7. Deploy and verify.
   - Run `python manage.py check`.
   - Recreate container after `.env` changes: `docker compose up -d --build --force-recreate`.
   - Check runtime env inside the container by prefix/length only.
   - Test activation link from a paid order.
   - For manual activation, test `/kichhoatthucong/` returns 200, includes the email form, includes the logo static path, and does not require an admin code unless explicitly configured.
   - Use logs and database fields to identify exact failure stage.

## Reference

For detailed implementation patterns, code snippets, migration checklist, debug commands, and customer-facing error mapping, read:

- `references/django-sepay-whop-pkce.md`

## Safety

- Do not include real `.env` values, API keys, SePay secrets, Whop client secrets, customer emails, bank account secrets, cookies, logs with tokens, or live webhook URLs in skill files.
- Use placeholders such as `Nhap_API_Cua_Ban`, `Nhap_Gia_Tri_Cua_Ban`, `email_cua_ban@example.com`, and `https://example.com/...`.
- When creating, updating, publishing, or preparing this skill for GitHub, use `khu-token-api-secret`.
