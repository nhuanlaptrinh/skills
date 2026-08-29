---
name: 9router-usage-dashboard
description: Operate, verify, repair, or update the Django dashboard at altcp.anhlaptrinh.vn and codex.anhlaptrinh.vn that summarizes 9Router cost by API key name for today, the current month, or a custom date range. Use when Codex needs to manage the ALT 9Router usage/cost app, its Gunicorn service, Nginx domains, data mapping, filters, or deployment.
---

# 9Router Usage Dashboard

## Paths

- Project: `/root/Apps/9router_usage_dashboard`
- Usage and API-name input: `/root/.9router/db/data.sqlite`
- Service: `altcp-dashboard.service`
- Bulk email worker: `altcp-bulk-email-worker.service`
- Telegram bot service: `altcp-telegram-bot.service`
- Nginx: `/etc/nginx/sites-available/altcp.anhlaptrinh.vn` and `/etc/nginx/sites-available/codex.anhlaptrinh.vn`
- Domains: `https://altcp.anhlaptrinh.vn` and `https://codex.anhlaptrinh.vn`
- Credentials file: `/root/.altcp_dashboard_credentials` with mode `600`
- Coupon administration: `https://codex.anhlaptrinh.vn/coupon/` (superuser only)
- Member email administration: `https://codex.anhlaptrinh.vn/gui-email/` (superuser only)

## Public Landing Page

The public route `/` presents Token Codex pricing and benefits before authentication. It emphasizes the commercial conversion `1 USD paid = 10 USD provider-equivalent usage credit`, shows concrete VND examples, explains that the credit is internal usage credit rather than cash or a provider-sold account, and offers separate registration and login actions. Use the Anh Lập Trình logo at `static/img/logo-anh-lap-trinh.png`. The authenticated dashboard route is `/bang-dieu-khien/`.

The public route `/huong-dan-tich-hop/` documents the OpenAI-compatible Base URL `https://codex.anhlaptrinh.vn/v1`. Keep examples for OpenClaw, ChatGPT Codex in Antigravity, NousResearch Hermes Agent, Python, and Node.js. Token Codex currently accepts the exact model IDs `GPT-5.6-sol`, `GPT-5.6-terra`, and `GPT-5.6-luna`. Use SOL as the default in short code examples, list all three in the guide and OpenClaw provider configuration, and remind users that model IDs are case-sensitive. Examples must use placeholders or environment-variable names rather than real keys. Users may query `/v1/models` with their own key to confirm the current list, and must not append `/v1` twice. Keep links to this guide on both the public landing page and authenticated dashboard.

## Behavior

Authenticate login emails case-insensitively through `dashboard.auth_backends.CaseInsensitiveEmailBackend`. Keep Django's default backend listed second so sessions created before this change remain valid. Registration and account-creation flows must continue storing normalized lowercase email values.

Read the active 9Router SQLite database directly in read-only mode without modifying it. Map `usageHistory.apiKey` to `apiKeys.name`. Aggregate three displayed columns: API name, request count, and USD cost. Interpret date filters in `Asia/Ho_Chi_Minh`. Default to the complete history view; also support today, current month, and a custom date range. On the superuser dashboard, support server-side `api_search` filtering by partial API name; normalize Vietnamese accents, spaces, separators, and `đ`/`d`, and apply the same search to the aggregate table and request ledger while preserving date and pagination parameters. Show the latest available record timestamp so stale source data is explicit.

The authenticated dashboard also includes a paginated request activity ledger using the same date filter. Each row may show the internal usage row ID, Vietnam timestamp to the second, assigned API name, provider/model, endpoint, status, prompt/completion token counts, and USD cost. Keep it at 50 rows per page. Never expose the complete API key in usage reports, connection ID, prompt, response, `meta`, or other request content.

For regular customers, the dashboard top bar shows a clear `Tài khoản đang đăng nhập` identity badge using `request.user.email`, falling back to the Django username only when the email field is empty. Keep this visible beside the logout action so customers can confirm which email account is active.

Superusers see all usage. Regular Django users see only API records assigned through `dashboard.UserApiAccess`. Assignments store the 9Router API UUID and display name, never the complete API key. A user with no assignments must receive an empty report rather than unrestricted data.

The superuser-only customer management page includes a separate member-cost report. It can show today, the current month, all time, or a custom date range in `Asia/Ho_Chi_Minh`. Calculate the selected range once per assigned `apiKeys.id`, then sum the assigned API totals for each Django user. Do not calculate from API display names and do not expose complete API key values.

Each member row on `/nguoi-dung/` also has a `Lịch sử request` action. Show a paginated 50-row ledger filtered strictly by that user's assigned API UUIDs. Use a separate `Model đang sử dụng` column and include provider, timestamp, request ID, API name, endpoint, status, prompt/completion tokens, and cost. Never expose another customer's rows, full API keys, prompts, responses, connection IDs, or metadata.

The same member table also shows each customer's editable USD credit limit, all-time spent amount, remaining credit, usage percentage, and an over-limit warning. All-time spent includes current usage for assigned API UUIDs plus `ManagedApiKey.closed_cost` for revoked keys. Admins edit the limit through `/nguoi-dung/`; spent and remaining values are calculated read-only. Django Admin exposes the same limit editing and calculated spent/remaining values as a technical fallback.

Customers may reveal and copy their own managed API key more than once from the authenticated dashboard. Keep the key masked in the initial HTML and fetch it only through the CSRF-protected `POST /api/<managed-key-id>/hien/` endpoint after verifying the `ManagedApiKey.user` owner. Read the value by `external_api_key_id` from the 9Router SQLite database in read-only mode; do not duplicate the complete key in the Django database. Return `Cache-Control: no-store`, never put a key in a URL, log, usage report, documentation, or another customer's response, and clear the revealed value from the browser DOM after 60 seconds. The one explicit admin exception is a successful manual provisioning action: the newly returned key is shown once on the redirected customer-edit page so the superuser can copy and send it, with a no-store response; it is not shown on ordinary admin pages or in general messages/logs and is removed from the temporary session slot after that display. Revoked or legacy-deleted keys must not be revealable.

Customers may create an API key with zero remaining credit. Create it in 9Router, immediately set `isActive=false`, save `ManagedApiKey.disabled_reason` as `Đã dùng hết hạn mức`, and still let the owner reveal/copy or revoke it. Count quota-disabled keys toward `max_api_keys` so zero-credit accounts cannot create unlimited keys. Existing credit enforcement reactivates these keys after credit is added. Never leave a newly created zero-credit key active between creation and the next enforcement run.

Never store request prompts or responses. Never print, log, or document complete API keys except for the one-time admin provisioning display described above; do not retain that value in domain models or ordinary logs.

## Isolated DEV Workspace

Use the global skill `secure-ssh-dev-workspace` for creating, auditing, handing off, or removing this type of isolated SSH developer environment.

- SSH user: `dev-altcp`, without `sudo` or Docker-group access.
- Workspace: `/home/dev-altcp/9router_usage_dashboard_dev`.
- Synthetic 9Router database: `/home/dev-altcp/dev_data/9router/db/data.sqlite`.
- Local DEV port: `127.0.0.1:8873`; access it only through an SSH tunnel.
- User service: `/home/dev-altcp/.config/systemd/user/altcp-dashboard-dev.service`, enabled with lingering so it continues running without an active SSH session.
- Initial DEV login is stored locally at `/home/dev-altcp/.dev_altcp_login` with mode `600`; never copy it into documentation or responses.
- The workspace has its own `.env`, Django database, virtualenv, synthetic usage data, and local Git history. It cannot read the production `.env`, Django database, or 9Router database under `/root`.
- Start DEV as `dev-altcp`, never as root:

```bash
cd /home/dev-altcp/9router_usage_dashboard_dev
set -a; . ./.env; set +a
source .venv/bin/activate
python manage.py runserver 127.0.0.1:8873
```

- Normal service control from the employee's SSH session:

```bash
systemctl --user status altcp-dashboard-dev
systemctl --user restart altcp-dashboard-dev
```

- Review `git diff` and tests in the DEV workspace before manually applying approved source changes to production. Never copy `.env`, `db.sqlite3`, `.venv`, `staticfiles`, logs, or DEV credentials to production.
- The SSH account remains password-locked. Add only the employee's public SSH key to `/home/dev-altcp/.ssh/authorized_keys`; never store or request their private key.

## Dry Run

```bash
cd /root/Apps/9router_usage_dashboard
set -a; . ./.env; set +a
.venv/bin/python manage.py check
.venv/bin/python manage.py test
```

## Run And Verify

```bash
systemctl restart altcp-dashboard
systemctl status altcp-dashboard --no-pager
systemctl status altcp-bulk-email-worker.service --no-pager
curl -I http://127.0.0.1:8870/dang-nhap/
curl -I https://altcp.anhlaptrinh.vn/dang-nhap/
curl -I https://codex.anhlaptrinh.vn/dang-nhap/
```

## Customer Accounts

Use the superuser-only page `/nguoi-dung/` for normal account operations. It supports creating a customer with email/password, assigning one or more APIs, changing the name/email/password, replacing API assignments, locking or reopening the account, deleting a customer, and filtering each member's assigned-API cost by today, current month, all time, or custom dates. The member list can be sorted by all-time usage, selected-period cost, newest or oldest registration, and name. The API checklist reads active names and UUIDs from the 9Router SQLite database. Its `Tìm kiếm` action filters only after click or Enter, matches normalized partial names, preserves checked values, hides the complete Django checkbox wrapper (`[id$="api_ids"] > div`) for non-matches, and resets the checklist scroll position so matching rows appear immediately.

Deleting a customer is a destructive POST action with browser confirmation. Before deleting the Django user, revoke every active `ManagedApiKey` owned by that user through the local 9Router API. Do not revoke APIs that were only assigned through `UserApiAccess`. If any owned API cannot be revoked, keep the user account and show an error so the admin can retry safely.

Django Admin remains available as a technical fallback at `/admin/`, but the normal operational workflow should use `/nguoi-dung/`. Do not make customer accounts superusers or staff.

On the customer edit view at `/nguoi-dung/`, a superuser can submit the `action=create_api_key` form to provision a key without logging in as the customer. The action targets regular, active customers only, bypasses only the customer's self-service `allow_key_creation` flag, keeps the `max_api_keys` limit, and creates both `ManagedApiKey` and `UserApiAccess` for that customer. A zero-credit customer receives a key that is immediately disabled with `QUOTA_DISABLED_REASON` (`Đã dùng hết hạn mức`) and it still counts toward the key limit. After a successful action, the complete key is displayed once on the redirected edit page in a no-store response for the superuser to copy/send; it is not placed in the URL, generic messages, logs, or ordinary admin pages, and the temporary session value is consumed immediately. The customer can also reveal/copy the same key from their own dashboard through the owner-checked endpoint.

Customers can self-register at `/dang-ky/`; new accounts start with zero credit. Admins can also create accounts manually and configure the USD credit limit, permission to create keys, and maximum active keys. Customers create or revoke their own keys from the authenticated dashboard and can reveal/copy their own key more than once. Full keys are never persisted in Django domain models; a newly provisioned admin key may exist briefly in the session solely to render the one-time post-redirect notice, then is consumed.

Public website registration requires a Vietnamese phone number. Accept `0...`, `84...`, or `+84...`, normalize it to exactly 10 digits beginning with `0`, store it in `CustomerAccount.phone_number`, and include it in the admin registration notification. Existing accounts and non-public administrative/Telegram creation flows may keep the field blank. The superuser customer page may display, edit, and search the stored phone number.

Every standalone website page includes the shared partial `dashboard/templates/dashboard/includes/zalo_contact.html` exactly once. It renders the fixed bottom-right Zalo support button for `https://zalo.me/0854838394`, with mobile positioning preserved in `static/css/app.css`. Change the number only in the shared partial and update coverage tests; do not paste independent Zalo widgets into individual templates.

## Member Email Campaigns

Use the superuser-only `/gui-email/` page when an administrator needs to send one announcement to registered members. Regular users must receive HTTP 403. The form supports a sender display name, subject, plain-text body, all-member delivery, or filters by account status, partial name/email, registration date range, month, and year. The sender email is fixed to `DJANGO_DEFAULT_FROM_EMAIL`; never allow arbitrary From addresses because they can break SMTP authorization and deliverability.

The safe preview step is mandatory. It signs the message, filters, and recipient snapshot for a limited time; changing any of them requires a new preview. Exclude superusers, invalid addresses, and duplicate lowercase addresses. Support `{{ ten }}` and `{{ email }}` placeholders, escape the HTML alternative, and send a separate message to each recipient so no customer can see another customer's address.

`dashboard.EmailCampaign` stores the campaign, filters, counts, status, and safe last error. Migration `dashboard.0017_emailcampaign_preview_token_hash` stores a unique hash of the signed preview token, so a double-click cannot create duplicate campaigns. `dashboard.EmailDelivery` stores each recipient snapshot and delivery state. Do not place SMTP credentials, API keys, prompts, cookies, or other secrets in either model. A worker interruption marks in-flight deliveries failed and deliberately does not auto-retry them, preventing accidental duplicate email. The UI may retry ordinary failed deliveries only.

Paths and commands:

- Worker source: `dashboard/management/commands/process_bulk_email_queue.py`
- Worker unit source: `deploy/altcp-bulk-email-worker.service`
- Installed unit: `/etc/systemd/system/altcp-bulk-email-worker.service`
- Dry run: use the UI `Xem trước người nhận` action or `.venv/bin/python manage.py test dashboard.tests.BulkEmailTests`; neither sends production email.
- Real worker run: `.venv/bin/python manage.py process_bulk_email_queue` processes all currently queued campaigns once. Use only when queued production email is intentionally ready.
- Continuous production worker: `.venv/bin/python manage.py process_bulk_email_queue --loop`, normally managed only by systemd.
- Verify: `systemctl is-active altcp-bulk-email-worker.service` and inspect a sanitized `journalctl -u altcp-bulk-email-worker.service`; never create a real campaign merely as a smoke test.

Inputs are Django users and the administrator's message/filter fields. Outputs are SMTP messages plus `EmailCampaign`/`EmailDelivery` audit rows; there is no Sheet or external API write other than SMTP. Batch size, poll interval, delay, stale timeout, and preview lifetime may be adjusted through `BULK_EMAIL_*` environment variables without changing SMTP credentials. To rerun after an ordinary SMTP failure, use `Gửi lại email lỗi`; never reset sent deliveries to queued.

Customers can buy additional Token Codex credit at `/mua-token/`. Packages are fixed from 10 USD through 1000 USD in 10 USD steps; arbitrary values are rejected. The customer payment rate is fixed at 25,000 VND per purchased USD, and each purchased USD adds 10 USD of provider credit to the existing `CustomerAccount.credit_limit`. Example: a 10 USD package costs 250,000 VND and adds 100 USD of Token Codex credit.

The purchase page shows only a neutral promotion-code input and does not display active codes in its visible copy. `CHAOMUNG30` adds 30% bonus credit for a customer's first paid purchase. `THANTHIET50` adds 50% bonus credit and may be used once per customer even if they have previous purchases. `THANTHIETX20` applies a provider-credit multiplier of 20 only to new purchases of 40 USD or more while preserving the package's normal VND charge: 40 USD adds 800 USD credit and 100 USD adds 2,000 USD. It may be redeemed for at most three paid purchases per customer account. `DNX25` applies a provider-credit multiplier of 25 to new purchases of 40 USD or more, preserves the package's normal VND charge, and is repeatable without a redemption limit: 40 USD adds 1,000 USD credit and 100 USD adds 2,500 USD. Keep all historical orders and already-granted credit unchanged when changing this minimum; do not recalculate or modify existing `TokenPurchase` or `CustomerAccount` rows. `THANTHIET15` applies a provider-credit multiplier of 15 to every selected package, preserves the normal VND charge, and may be redeemed once per customer account. `HOCVIENKH` is a free student trial coupon: it represents a 2 USD customer value, immediately adds 20 USD provider credit without VietQR payment, and may be redeemed only once per customer. `NGUOITHAN400` is a private family coupon: it represents a 40 USD customer value, immediately adds 400 USD provider credit without payment, and may be redeemed only once per customer. Redeem free-credit coupons inside a database transaction while locking `CustomerAccount`, and record a zero-VND `paid` `TokenPurchase` so repeat use is rejected. Percentage promotions keep the VietQR amount unchanged, apply from the 10 USD package, and cap the bonus at 1,000 USD. Repeatable coupons `DAMUA3000K` and `DAMUA4000K` override the selected package with a 3,000 VND or 4,000 VND payment respectively and exactly 100 USD provider credit; customers may use repeatable coupons again after the previous order with that code is paid or expired. Store the normalized code and locked amount/credit values on `TokenPurchase`; credit `provider_credit_usd + promotion_bonus_usd` only after full payment. Reject unknown codes, purchases below a promotion-specific `min_purchase_usd`, redemption beyond a configured `max_redemptions`, reuse of non-repeatable paid codes, and a second active order using the same code. Configuration uses `TOKEN_PROMOTIONS`, `TOKEN_PROMOTION_MIN_PURCHASE_USD`, `TOKEN_PROMOTION_THANTHIETX20_MIN_PURCHASE_USD`, `TOKEN_PROMOTION_DNX25_MIN_PURCHASE_USD`, and `TOKEN_PROMOTION_MAX_BONUS_USD` without requiring secrets.

## Admin Coupon Management

- Superusers manage database-backed coupons at `/coupon/`; regular users receive HTTP 403 and anonymous visitors are redirected to login.
- `dashboard.Coupon` supports percentage bonus, provider multiplier, free fixed credit, and fixed VND payment for fixed credit.
- Admins can set active dates, first-purchase restriction, minimum package, repeatability, and per-user redemption limits. The website and Telegram bot resolve these coupons from the same database-backed promotion layer.
- Migration `dashboard.0014_seed_editable_default_coupons` stores all nine built-in codes as `is_system=True` database rows. Admins may edit their benefits, conditions, dates, and active state, while the code itself stays locked to preserve order references.
- Migration `dashboard.0015_coupon_safe_delete` implements recoverable deletion. The superuser `Xóa mã` action sets `is_deleted=True`, disables the coupon, records `deleted_at` and `deleted_by`, hides it from the active management list, and keeps the row plus all `TokenPurchase` history. The archive provides `Khôi phục mã`; restore clears deletion audit fields but leaves the coupon paused for review.
- A database row is authoritative even when paused, scheduled, expired, or soft-deleted. Do not fall back to the matching `settings.TOKEN_PROMOTIONS` entry in those cases, or an admin-deleted coupon would silently reactivate. Keep `settings.TOKEN_PROMOTIONS` only as compatibility fallback when no database row exists.
- A custom coupon cannot reuse a built-in or archived code. Django Admin does not permit physical coupon deletion; use the superuser management page for safe delete/restore behavior.
- Never physically delete a coupon after it has appeared on a `TokenPurchase`. Existing pending or historical orders retain their locked values and audit trail; deletion only blocks new redemptions.
- Browser previews are informational. Enforce coupon status, dates, purchase minimum, pending-order protection, first-purchase rules, and redemption limits again in the server-side purchase flow.

Each new paid purchase uses a short transfer code formatted as `CDX` plus exactly four digits, for example `CDX4565`, and a VietQR image for the configured BIDV account. `PaymentCodeLease` keeps each code reserved for `PAYMENT_CODE_REUSE_DAYS` (default 30 days), enforces a unique lease row, and retries random generation up to `PAYMENT_CODE_RESERVATION_ATTEMPTS` (default 100) when a collision occurs. The webhook resolves a short code only through its current lease and only accepts an unexpired `pending` or `underpaid` order. Continue parsing the legacy `CDX` plus 10 alphanumeric format so existing orders remain payable. The account number and account holder values must come from `TOKEN_PAYMENT_ACCOUNT_*` environment variables and must not be copied into this skill. The order page embeds the exact VND amount and invoice code in the QR, displays bank details, and polls the authenticated status endpoint. After the status endpoint confirms `paid`, the browser redirects to `https://codex.anhlaptrinh.vn/thantoanthanhcong/?invoice=CDX...`. This authenticated page must verify that the invoice belongs to the logged-in customer and is `paid`, show the credited amount, count down 5 seconds, and then return to `/bang-dieu-khien/?payment_invoice=CDX...` so the existing dashboard confirmation remains available. The canonical SePay bank-sync IPN is `https://codex.anhlaptrinh.vn/payment/ipn/`, configured by `SEPAY_WEBHOOK_URL`, matching the shared course-website convention. Keep `/api/sepay/webhook/` as a backward-compatible alias, but register only `/payment/ipn/` in SePay. Configure SePay to send incoming-transfer JSON and authenticate with the secret stored only in `SEPAY_WEBHOOK_SECRET`, using either `X-Secret-Key` or `Authorization: Apikey ...`. Never document or print the real secret.

The webhook stores a payload hash and unique transaction/event ID, accepts incoming transfers only, extracts the `CDX...` invoice from transfer content, accumulates partial payments, and adds credit only after the received total reaches the exact required amount. Database row locks and unique event IDs prevent duplicate credit. Expired orders that receive money move to manual review instead of being credited automatically. Successful payment sends separate confirmation emails to the customer and the admin address configured by `ADMIN_NOTIFICATION_EMAIL`; do not document the production recipient. Payment email delivery failure must be logged without changing the already completed payment or credited limit.

Webhook authentication primarily uses `SEPAY_WEBHOOK_SECRET`. If SePay delivers a callback with a mismatched key, the app logs only the provided header source, length, SHA-256 fingerprint prefix, and request IP—never the secret itself. A fallback may accept the callback only when Nginx's overwritten `X-Real-IP` is in `SEPAY_TRUSTED_IPS`; all invoice, incoming-transfer, amount, expiry, database-lock, and duplicate-event checks still apply. Keep the trusted list narrow and never replace it with open unauthenticated access.

Account passwords use one simple rule: at least 6 characters. Letters-only, mixed values, and numeric-only passwords are accepted.

Successful self-registration sends an admin notification only after the database transaction commits. The message includes the customer's name, email, Vietnam-local registration time, and initial 0 USD credit. The recipient is configured through `ADMIN_NOTIFICATION_EMAIL`; do not document the production recipient. Email delivery failure must be logged without rolling back or blocking the completed registration.

Password recovery starts at `/quen-mat-khau/` and uses Django's signed, expiring reset link. The form normalizes the submitted email, verifies that it belongs to an active user with a usable password, and shows a clear validation error when the email is not registered instead of redirecting to a false success page. Successful SMTP dispatch is logged with a masked recipient only. The new-password form follows the same 6-character rule. SMTP delivery is configured only through `DJANGO_EMAIL_BACKEND`, `DJANGO_EMAIL_HOST`, `DJANGO_EMAIL_PORT`, `DJANGO_EMAIL_HOST_USER`, `DJANGO_EMAIL_HOST_PASSWORD`, `DJANGO_EMAIL_USE_TLS`, `DJANGO_EMAIL_USE_SSL`, and `DJANGO_DEFAULT_FROM_EMAIL`; never place credentials in this skill.

The credit guard runs every minute from `/etc/cron.d/altcp-credit-guard` using `manage.py enforce_credit_limits`. When usage reaches the account limit, it must soft-disable the 9Router key with `PUT /api/keys/{id}` and `{"isActive": false}` while preserving the key ID, secret, `ManagedApiKey`, and `UserApiAccess`. When the account later has available credit, it re-enables only keys whose disabled reason is exactly `Đã dùng hết hạn mức` using `{"isActive": true}`. Never auto-reactivate user-revoked or admin-deleted keys. SePay payment, free-credit coupon, and admin credit updates trigger immediate reactivation after transaction commit; the minute guard retries as self-healing. Keep `closed_cost` at zero for soft-disabled keys because their usage history remains queryable, avoiding double counting. Legacy quota keys deleted by the old behavior cannot recover the same secret; mark them for replacement and instruct the customer to create a new key. This remains a near-real-time safety limit, not transactional pre-request reservation, so a small overshoot remains possible.

The same guard sends a low-credit warning when an active customer reaches at least 80% of their USD credit limit. Customer-facing and admin-facing email copy calls the service `Tài khoản Token Codex` and must not display the name `9Router`. It always includes the customer's login email and `https://codex.anhlaptrinh.vn/`. Include the gift coupon `THANTHIET15` with a ×15 credit multiplier only when the customer has no `paid` purchase using that code, and state clearly that the coupon may be used only once per account. It sends separate emails to the customer's account email and the admin address configured by `CREDIT_ALERT_ADMIN_EMAIL`; do not document the production recipient. The warning records the credit limit used for that notification so the per-minute guard does not spam repeated messages. A new warning can be sent after the limit changes, or after usage falls below 80% and later crosses the threshold again. SMTP remains configured only through the existing `DJANGO_EMAIL_*` variables; do not place SMTP credentials in this skill.

After assigning access, verify with a non-superuser account that only the assigned API names appear and that `/nguoi-dung/` returns HTTP 403. Never test by putting a complete API key in a URL, form, log, or document.

## Deployment Changes

Before changing Nginx or systemd, copy the affected file to a timestamped folder under `/root/_Backups`. After editing:

The Codex API route in `/etc/nginx/sites-available/codex.anhlaptrinh.vn` uses `client_max_body_size 50M` inside `location /v1/` so large Codex context requests reach 9Router instead of failing with HTTP 413. Keep this limit scoped to the API route unless there is a verified need elsewhere.

```bash
nginx -t
systemctl daemon-reload
systemctl reload nginx
systemctl restart altcp-dashboard
```

## Tạo Tài Khoản Khách Hàng Bằng Command

Dùng global skill `tao-user-token-codex` hoặc command `manage.py create_customer_account` khi cần tạo user từ email. Command mặc định cấp mật khẩu tạm `alt123`, hạn mức `250` USD và tạo 1 API key, hỗ trợ `--dry-run`, `--api-name`, `--no-create-api`, đồng thời từ chối ghi đè user đã tồn tại nếu không có `--update-existing`. Full API key chỉ hiển thị một lần; không ghi vào tài liệu hoặc log.

## Telegram Bot

Production includes the Telegram account-linking and customer-management bot from the isolated DEV workspace. The source is `/root/Apps/9router_usage_dashboard/botapp`, the entrypoint is `manage.py run_otp_bot`, and the unit is `altcp-telegram-bot.service`. It uses the same Django production database and reads `TELEGRAM_BOT_TOKEN` only from the production `.env`; never print or document that value.

The bot supports email/OTP linking, account status, API-key listing/creation/revocation, free-credit promotions, and staff/superuser administration after Telegram verification. Regular customers also have a `Mua thêm Token` menu action and `/muatoken` command. On the purchase menu, customers may save or clear an optional promotion code before selecting a package. Clicking a preset package must create the order and send VietQR immediately; custom packages accept 10 through 1,000 USD in 10 USD steps and also create the QR immediately after amount entry. Paid and free promotion codes resolve through `dashboard.promotions`, so active database coupons created at `/coupon/` follow the same conditions as the website without restarting the bot. Enforce minimum package, active dates, first-purchase, repeatability, redemption limits, fixed-price offers, percentage bonuses, and provider multipliers such as `THANTHIETX20` and `DNX25`. Free-credit codes must redirect customers to `/promo`. The bot creates the order through the shared `create_purchase_with_reserved_code` and `payment_values` backend, sends the generated VietQR image directly in chat, and exposes a user-scoped payment-status check button. Keep SePay webhook processing and crediting shared with the website; never implement a second Telegram-only crediting path. Hide this customer purchase action from staff/superusers. Migration `dashboard.0010_customeraccount_is_verified_telegram_and_more` only adds Telegram-link fields to `CustomerAccount`; never recreate, flush, replace, or import the DEV database when deploying bot code. Do not copy DEV `.env`, virtualenv, usage database, logs, or credentials.

Telegram callbacks can originate from either text messages or QR photo messages. Never call `edit_message_text` on a photo-only message; reply with a new text message or edit its caption instead. Keep a fallback `buy_token` callback outside the purchase conversation and accept `buy_token` inside every active purchase state so stale menu buttons still respond.

## Referral wallet

New website and Telegram registrations require a valid six-character referral code. Every `CustomerAccount` has a unique code derived from the email local part where possible. After a SePay order becomes `paid`, credit the referrer with `REFERRAL_COMMISSION_PERCENT` (default 30%) of the order's actual VND charge for at most `REFERRAL_COMMISSION_MAX_PURCHASES` (default 3) qualifying purchases per referred customer, including fixed-price coupons such as `DAMUA3000K` and `DAMUA4000K`. Record the commission and wallet ledger entry in the same database transaction; never credit again for the same `TokenPurchase`, and never generate commission for referral-wallet purchases. The separate VNĐ wallet can buy standard Token packages at the normal ×10 rate or request a bank withdrawal from `REFERRAL_WITHDRAWAL_MIN_VND` (default 500,000 VNĐ). Withdrawal requests reserve balance immediately; admin actions mark them paid or reject and refund through `/admin/`. Telegram exposes `Giới thiệu & Ví hoa hồng`, `/gioithieu`, wallet purchase, and withdrawal flows. Never log full bank account details, secrets, tokens, API keys, prompts, or responses.

Telegram OTP emails must include the six-digit code in the email subject. Keep the HTML email high-contrast and restricted to black and white backgrounds/text/borders; retain a Vietnamese plain-text alternative. Never log the OTP value.

The bot uses polling, not a webhook. Keep `httpx` and `httpcore` logs at `WARNING` or higher so Telegram request URLs cannot expose the bot token in new journald entries. Verify with `systemctl is-active altcp-telegram-bot.service`, sanitized journal checks, and `manage.py check`; do not send real customer messages as a deployment test.

## Inputs And Outputs

- Input: 9Router `usageHistory` and `apiKeys` tables in the active SQLite database.
- Output: public and authenticated HTML pages, including the customer dashboard, registration, payment success confirmation, and shared Zalo contact; no Sheet writes.
- Local state: Django authentication and `UserApiAccess` assignments at `/root/Apps/9router_usage_dashboard/db.sqlite3`.
- Commercial state: `CustomerAccount` limits and `ManagedApiKey` metadata in the same Django database. Complete API keys are not stored in domain models; the admin provisioning flow may hold a newly returned value briefly in the session for its one-time no-store display.
- Alert state: `CustomerAccount.low_credit_alert_sent_at` and `low_credit_alert_credit_limit` prevent repeated 80% warning emails.
- Payment state: `TokenPurchase` stores invoice, package, VND amount, provider credit, status, safe SePay transaction ID, and before/after credit limits. `Coupon` stores admin-created promotion rules without secrets. `PaymentCodeLease` maps the current four-digit code to its order and reuse deadline. `SePayWebhookEvent` stores deduplication metadata without retaining full webhook payloads.

## Rerun And Recovery

The dashboard calculates from the current SQLite database on every page request, so no import or rerender job is required. If data is unavailable, verify database/WAL file permissions and SQLite integrity without printing secret-bearing content.

## Safety

- Do not edit `/root/.9router/db/data.sqlite`, its WAL/SHM files, legacy JSON files, or provider credentials.
- Do not expose `.env`, the credentials file, API keys, tokens, prompts, or responses.
- Do not accept an unauthenticated SePay webhook and do not test production with a fake valid incoming payment, because a valid webhook intentionally changes customer credit.
- Keep the dashboard behind Django login and HTTPS.
- Run tests, `nginx -t`, and HTTP checks after production changes.
- Update this skill and `/root/_Second_AI_Brain/06_Nhat_Ky_Thay_Doi.md` when paths, filters, columns, domain, service, or data logic changes.
