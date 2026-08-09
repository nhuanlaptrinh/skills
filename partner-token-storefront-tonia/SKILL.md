---
name: partner-token-storefront-tonia
description: Operate, verify, repair, deploy, or update the independent Django Token Codex retail storefront at tonia.hocvienai.org. Use for its domain, SSL, Gunicorn, Nginx, reseller bridge, customer accounts, email notifications, dynamic VietQR, MB Bank payment configuration, SePay webhook, payment orders, crediting, or production recovery.
---

# Tonia Token Storefront

## Scope

- Project: `/root/Apps/partner_token_storefront_lethang`
- Domain: `https://tonia.hocvienai.org`
- Service: `lethang-token-storefront.service`
- Local port: `127.0.0.1:8872`
- Nginx: `/etc/nginx/sites-available/tonia.hocvienai.org`
- Legacy redirect/webhook compatibility: `/etc/nginx/sites-available/lethang.anhlaptrinh.vn`
- Static root: `/var/www/lethang-static`
- Database: `/root/Apps/partner_token_storefront_lethang/db.sqlite3`
- Project note: `/root/_Second_AI_Brain/projects/partner_token_storefront_tonia.md`
- Coupon administration: `https://tonia.hocvienai.org/coupon/` (superuser only)
- Học Viện AI logo: `/root/Apps/partner_token_storefront_lethang/static/img/logo-hoc-vien-ai.png`

Keep this storefront independent from `/root/Apps/9router_usage_dashboard` and `/root/Apps/partner_token_billing`. Do not reuse or edit their Django databases.

Authenticate customer login emails case-insensitively through `dashboard.auth_backends.CaseInsensitiveEmailBackend`. Keep Django's default backend second so existing sessions survive deployment, and continue storing newly registered emails in lowercase.

## Reseller Isolation

- All key and usage operations must use `https://doitac.anhlaptrinh.vn/api/reseller/v1`; the storefront must never open 9Router SQLite or derive the 9Router CLI admin token.
- Runtime auth uses a dedicated non-customer parent API key plus HMAC secret from `.env`. The partner email/password identifies the account administratively but is never sent by the storefront.
- `ManagedApiKey.user` is the only runtime ownership mapping. Do not restore API-assignment checkboxes or use legacy `UserApiAccess` rows for authorization.
- Raw child keys are returned only in the immediate create response with `Cache-Control: no-store`; there is no reveal-later endpoint and no raw key in sessions or the storefront database.
- Superusers may see only the upstream balance and `CDX-` child-key usage belonging to this partner. They must never receive a global 9Router key list.
- The systemd service uses `InaccessiblePaths` to block `/root/.9router`, the partner project/database, and other sensitive root workspaces. Preserve and verify this sandbox after unit changes.

## Customer API Base URL

- The customer-facing OpenAI-compatible Base URL is `https://tonia.hocvienai.org/v1`.
- Nginx locations `= /v1` and `/v1/` in `/etc/nginx/sites-available/tonia.hocvienai.org` proxy directly to `http://127.0.0.1:20128`; all other paths continue to the storefront Gunicorn service on `127.0.0.1:8872`.
- Preserve the authorization header, real client IP, forwarded host/protocol/port, WebSocket upgrade, 50 MB body limit, 3600-second streaming timeouts, disabled buffering, and disabled redirects. Do not proxy the storefront root to 9Router.
- Keep `https://codex.anhlaptrinh.vn/v1` working as an upstream-compatible legacy domain, but show the Tonia Base URL in the storefront landing page, integration guide, examples, tests, and README.
- For an explicitly requested production acceptance test, verify an invalid key returns `401`, a valid parent key can list the required models, and one tightly limited chat completion succeeds. Never print the key, prompt, or response; do not include a paid inference in routine dry-run checks.

## Payment Behavior

- Generate VietQR dynamically from `TOKEN_PAYMENT_*` in `.env`; never replace it with a static QR image because every order needs its own amount and invoice code.
- Keep the active receiving account number only in `.env`. When changing only `TOKEN_PAYMENT_ACCOUNT_NUMBER`, preserve the bank ID, bank name, account holder names, webhook secret, and all other payment settings unless separately requested.
- Match the configured receiver against every account identifier SePay provides, including `accountNumber`, `subAccount`, and virtual-account aliases. Preserve alphanumeric VietQR identifiers during normalization; do not reduce them to only their trailing digits.
- Receive SePay events at `https://tonia.hocvienai.org/payment/ipn/`; keep `/api/sepay/webhook/` as the compatibility alias.
- Credit an order only after an incoming, authenticated, non-duplicate event reaches the configured bank account and the received amount is sufficient.
- Reserve upstream partner capacity before creating paid/free/referral/admin credit. If capacity cannot be confirmed after funds arrive, move the order to `manual_review` instead of crediting beyond the partner account.
- Keep webhook secrets and reseller credentials only in `.env`. Do not print, log, copy into documentation, or expose them in URLs.
- Automatic payment requires the matching MB Bank account to be connected to SePay and the external SePay integration to target the Tonia webhook URL.

## Email Notifications And Credit Guard

- SMTP is configured only through `DJANGO_EMAIL_*` in the storefront `.env`. Keep the protected system sender, SMTP user, and app password aligned with `/root/Apps/9router_usage_dashboard`, but set `ADMIN_NOTIFICATION_EMAIL` and `CREDIT_ALERT_ADMIN_EMAIL` to this partner's own admin mailbox. Never print or document their values.
- A successful registration emails the admin after the database transaction commits. A successful SePay payment emails both the customer and admin after credit has committed. Email delivery failures are logged but must never roll back account creation, payment state, or credited limits.
- `lethang-credit-guard.timer` runs `/etc/systemd/system/lethang-credit-guard.service` every minute with the storefront `EnvironmentFile`. It invokes `manage.py enforce_credit_limits`, warns the customer and admin at 80% usage, and applies the existing quota disable/reactivation rules.
- Store `low_credit_alert_sent_at` and `low_credit_alert_credit_limit` to avoid repeated warning emails. Permit another warning only after the credit limit changes or usage falls below 80% and later crosses the threshold again.
- Check the schedule with `systemctl list-timers lethang-credit-guard.timer --all --no-pager`. Run one real guard pass with `systemctl start lethang-credit-guard.service`, then inspect `systemctl status lethang-credit-guard.service --no-pager`; this can send real warnings or change quota state and is not a dry run.

## Coupon Behavior

- Keep all legacy codes in `settings.TOKEN_PROMOTIONS` functional.
- Custom coupons are stored in `dashboard.Coupon` and managed by superusers at `/coupon/`.
- Supported custom types are percentage bonus, provider multiplier, free fixed credit, and fixed VND payment for fixed credit.
- Enforce active dates, first-purchase rules, per-user limits, minimum package values, and pending-order protection in the server-side purchase flow; browser previews are informational only.
- Never delete a coupon after it has appeared on an order. The custom admin page deactivates it to preserve the payment audit trail.

## Analytics Tracking

- The storefront uses Meta Pixel ID `1081888194506886` for site-wide `PageView` tracking.
- Keep the tracking code in the single shared partial `/root/Apps/partner_token_storefront_lethang/dashboard/templates/dashboard/includes/meta_pixel.html` and include it exactly once inside the `<head>` of every standalone page template.
- When changing or removing the Pixel ID, edit only the shared partial and update the template coverage tests. Never paste a second Pixel initialization directly into individual pages.

## Safe Checks

```bash
cd /root/Apps/partner_token_storefront_lethang
set -a; . ./.env; set +a
.venv/bin/python manage.py check
.venv/bin/python manage.py showmigrations --plan
.venv/bin/python manage.py test
if rg -n "NINEROUTER_SQLITE_FILE|/root/\\.9router|20128|x-9r-cli-token" dashboard botapp config \
  --glob '!dashboard/tests.py' --glob '!dashboard/migrations/**'; then exit 1; fi
nginx -t
systemctl status lethang-token-storefront.service --no-pager
systemctl is-active lethang-credit-guard.timer
systemctl is-enabled lethang-credit-guard.timer
curl -I https://tonia.hocvienai.org/
curl -I https://tonia.hocvienai.org/dang-ky/
curl -o /dev/null -w '%{http_code}\n' -H 'Authorization: Bearer invalid-test-token' https://tonia.hocvienai.org/v1/models
```

Treat these checks as the dry run. They must not create a real order, API key, customer, or SePay event.

## Deploy

Back up `.env`, changed source files, and Nginx files under `/root/_Backups` before editing.

```bash
cd /root/Apps/partner_token_storefront_lethang
set -a; . ./.env; set +a
.venv/bin/python manage.py migrate --noinput
.venv/bin/python manage.py collectstatic --noinput
.venv/bin/python manage.py test
nginx -t
systemctl daemon-reload
systemctl restart lethang-token-storefront.service
systemctl enable --now lethang-credit-guard.timer
systemctl reload nginx
```

For a domain change, confirm DNS first, create a dedicated Nginx site, run `nginx -t`, obtain SSL with Certbot, then convert normal traffic on the old domain into a 301 redirect. Preserve exact legacy SePay webhook locations as direct proxies until the external integration is confirmed on the new URL. Do not rename the stable service, static root, or project folder merely to match the public domain.

## Inputs And Outputs

- Input: customer registrations, signed reseller bridge responses, partner capacity, package amount, promotion code, dynamic invoice code, and SePay webhook payload.
- Output: customer dashboard, API-key management, usage reports, coupon administration, VietQR payment page, paid order status, and credited internal usage limit.
- Local writes: storefront SQLite database and collected static files.
- External calls: signed reseller bridge to the partner portal, VietQR image generation, email delivery, SePay webhook delivery, and Meta Pixel `PageView` tracking from rendered browser pages.
- No Google Sheet writes and no automatic social posting.

## Recovery And Rerun

- Restart web: `systemctl restart lethang-token-storefront.service`.
- Rerun credit enforcement: `systemctl start lethang-credit-guard.service`; inspect the oneshot result and timer journal before retrying.
- Rebuild static: `.venv/bin/python manage.py collectstatic --noinput`.
- Recheck SSL: `certbot certificates` and `curl -I https://tonia.hocvienai.org/`.
- If an authenticated payment was previously stored as an unlinked event because of account mismatch, do not delete and blindly replay it. Back up SQLite consistently, lock the event/order/customer rows, verify event ID, amount, invoice content, expiry, capacity, and empty prior payment state, then reconcile exactly once and link the event to the paid order.
- Rerun a failed deployment only after `manage.py check`, the payment test class, and `nginx -t` pass.
- Restore only the exact changed file from the timestamped backup; do not restore or overwrite the database unless the user explicitly requests data recovery.

## Safety

- Do not expose `.env`, complete API keys, HMAC secrets, webhook secrets, email credentials, prompts, responses, or customer private data.
- Create or reset the storefront admin password only through a non-echoing prompt; never put it in a command argument, source file, README, project note, skill, or change log.
- Do not send a fake successful webhook to production; use Django tests for crediting verification.
- The storefront has no legitimate read path to `/root/.9router` or the partner database. Treat any reintroduced SQLite/CLI-admin access as a security regression.
- After important changes, update this skill, the project note, and `/root/_Second_AI_Brain/06_Nhat_Ky_Thay_Doi.md`.
