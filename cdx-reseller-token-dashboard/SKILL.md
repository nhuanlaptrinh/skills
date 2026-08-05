---
name: cdx-reseller-token-dashboard
description: Operate, verify, repair, deploy, or extend the CDX reseller customer portal at cdx.anhlaptrinh.vn, which uses cdx.anhlaptrinh.vn/v1 for customers and manages keys, usage, and reseller balance only through the signed HTTPS API at doitac.anhlaptrinh.vn.
---

# CDX Reseller Token Dashboard

## Scope

- Project: `/root/Apps/cdx_token_dashboard`
- Website: `https://cdx.anhlaptrinh.vn`
- Customer Base URL: `https://cdx.anhlaptrinh.vn/v1`
- Web service: `cdx-token-dashboard.service`
- Credit timer: `cdx-credit-guard.timer`
- Local port: `127.0.0.1:8872`
- Nginx: `/etc/nginx/sites-available/cdx.anhlaptrinh.vn`
- Static root: `/var/www/cdx-static`
- App database: `/root/Apps/cdx_token_dashboard/db.sqlite3`
- Credentials: `/root/.cdx_dashboard_credentials`
- Parent portal: `/root/Apps/partner_token_billing`
- Parent API: `https://doitac.anhlaptrinh.vn/api/reseller/v1`

## Architecture

`cdx.anhlaptrinh.vn` hosts the customer website and proxies `/v1/*` to `https://doitac.anhlaptrinh.vn/v1/*`. Customers receive Base URL `https://cdx.anhlaptrinh.vn/v1` and unique child API keys.

The app never gives the parent reseller API key or HMAC secret to customers. It stores both only in `.env` mode `600` and uses them server-side to call the partner HTTPS API. Every request includes timestamp, one-time nonce, and HMAC SHA-256 signature. The partner validates the parent key, enforces credit and key-count limits, manages child keys, and returns only the child-key usage owned by this reseller.

CDX production does not read `/root/.9router`. Key management, usage reports, and reseller balance all travel through HTTPS to `doitac.anhlaptrinh.vn`. The old loopback endpoint remains blocked publicly with HTTP 404 for rollback only.

CDX superusers see a live read-only reseller balance panel at the top of `/bang-dieu-khien/`: total internal credit, all-time spent, remaining credit, active key count, active CDX child-key count, and the partner key limit. These values come from the partner bridge on every dashboard request and are not copied into the CDX database.

## Safe Checks

```bash
cd /root/Apps/cdx_token_dashboard
set -a; . ./.env; set +a
.venv/bin/python manage.py check
PARTNER_BRIDGE_API_KEY='' PARTNER_BRIDGE_HMAC_SECRET='' TOKEN_PAYMENT_INVOICE_PREFIX='CDX' .venv/bin/python manage.py test
systemctl status cdx-token-dashboard.service --no-pager
systemctl status cdx-credit-guard.timer --no-pager
nginx -t
curl -I https://cdx.anhlaptrinh.vn/
curl -I https://cdx.anhlaptrinh.vn/dang-nhap/
```

Verify the displayed upstream without exposing a key:

```bash
curl -fsS https://cdx.anhlaptrinh.vn/huong-dan-tich-hop/ | rg 'https://cdx\.anhlaptrinh\.vn/v1'
```

## Deploy

```bash
cd /root/Apps/cdx_token_dashboard
set -a; . ./.env; set +a
.venv/bin/python manage.py migrate --noinput
.venv/bin/python manage.py collectstatic --noinput
.venv/bin/python manage.py check
systemctl restart cdx-token-dashboard.service
systemctl restart cdx-credit-guard.timer
nginx -t
systemctl reload nginx
```

When bridge behavior changes, also test and restart `doitac-token-billing.service`, then update the global `partner-token-billing` skill.

## Inputs And Outputs

- Input: customer registrations, customer credit limits, customer API names, reseller parent API key and HMAC secret from local `.env`, partner account state, remote usage data, and optional SePay webhook events.
- Output: customer accounts, unique child API keys shown once, usage reports, credit enforcement, VietQR payment orders, and integration instructions using the CDX Base URL.
- Admin output: live partner-account credit limit, spent amount, remaining amount, and key utilization from `partner_token_billing`.
- Local writes: CDX Django database and CDX static files; partner-owned child-key changes go only through the signed HTTPS API.
- External writes: Cloudflare DNS only during domain setup; SePay only sends events after its webhook is configured separately.

## Payment

- Webhook URL: `https://cdx.anhlaptrinh.vn/payment/ipn/`.
- Invoice prefix: `CDR`, separate from the original Token Codex `CDX` prefix and partner portal `DTA` prefix.
- Automatic payment crediting requires SePay to be configured externally with the CDX webhook URL and its separate secret.

## Recovery And Rerun

- Restart web: `systemctl restart cdx-token-dashboard.service`.
- Run guard now: `systemctl start cdx-credit-guard.service`.
- Rebuild static: `.venv/bin/python manage.py collectstatic --noinput`.
- If key creation fails, check HTTPS/DNS/Cloudflare access to `doitac.anhlaptrinh.vn`, parent credit, parent key status, key count, HMAC secret equality, and NTP clock synchronization.
- Rerun migrations, collectstatic, service restart, and checks after code updates. DNS and Certbot are already configured for `cdx.anhlaptrinh.vn`.

## Safety

- Never print, document, commit, or send the parent reseller API key, child full keys, `.env`, passwords, SMTP credentials, SePay secret, or Cloudflare token.
- Do not point this app back to the local 9Router admin API; that would bypass partner billing.
- Keep system time synchronized; requests more than 300 seconds away from the partner clock are rejected.
- Do not copy the original Django database or credentials into this project.
- Keep `.env`, `db.sqlite3`, and `/root/.cdx_dashboard_credentials` at mode `600`.
- Back up partner database, CDX database, Nginx, and systemd files before production changes.
- Update `/root/_Second_AI_Brain/projects/cdx_token_dashboard.md` and the VPS change log after important changes.
