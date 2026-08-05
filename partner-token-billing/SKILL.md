---
name: partner-token-billing
description: Operate, verify, repair, deploy, or extend the independent Django partner AI portal at doitac.anhlaptrinh.vn. Use for partner registration approval, 1 USD to 20 USD internal usage-credit billing, partner API-key management, usage reports, credit enforcement, Gunicorn, Nginx, Cloudflare DNS, SSL, or SePay integration for this app.
---

# Partner Token Billing

## Scope

- Project: `/root/Apps/partner_token_billing`
- Domain: `https://doitac.anhlaptrinh.vn`
- Base URL: `https://doitac.anhlaptrinh.vn/v1`
- Service: `doitac-token-billing.service`
- Credit guard: `doitac-credit-guard.timer`
- Local port: `127.0.0.1:8871`
- Nginx: `/etc/nginx/sites-available/doitac.anhlaptrinh.vn`
- Static root: `/var/www/doitac-static`
- App database: `/root/Apps/partner_token_billing/db.sqlite3`
- Usage source, read-only: `/root/.9router/db/data.sqlite`

This app is independent from `/root/Apps/9router_usage_dashboard`. Do not edit, migrate, stop, or reuse the old app database when operating the partner portal.

## Behavior

- New registrations start with `is_active=false`, zero credit, and wait for superuser approval.
- Superusers manage partners at `/quan-tri/` or `/nguoi-dung/`.
- The fixed commercial conversion is `1 USD paid = 20 USD internal usage credit`.
- Credit is internal service capacity, not cash and not a provider-owned balance.
- Each partner may create up to 20 named API keys by default, ideally one per downstream customer or application.
- All keys assigned to a partner share the partner's total credit limit.
- Partners can create downstream-client profiles, assign API keys, set a resale multiplier, and view estimated revenue and profit.
- Partners can customize brand name, logo URL, primary color, and request a dedicated API subdomain.
- The portal only manages the commercial relationship between ALT and the partner. Partners receive Base URL, API keys, usage reports, credit, and payment tools, then build and operate their own sales websites independently.
- Do not add partner storefronts, downstream-customer login, downstream payment orders, or retail-customer billing to this project unless the user explicitly changes the approved scope.
- A custom Base URL is shown only after its domain status is changed to `active`; pending domains continue using the shared Base URL.
- Usage is calculated from 9Router `usageHistory` joined to `apiKeys`, filtered by assigned external API UUIDs.
- Full API keys display once and must never be stored in documentation or logs.
- New payment invoice codes use prefix `DTA`, separate from Token Codex `CDX` invoices.
- Promotions from the Token Codex project are disabled in this app.

## Safe Checks

```bash
cd /root/Apps/partner_token_billing
set -a; . ./.env; set +a
.venv/bin/python manage.py check
.venv/bin/python manage.py showmigrations --plan
.venv/bin/python manage.py test
nginx -t
systemctl status doitac-token-billing.service --no-pager
systemctl status doitac-credit-guard.timer --no-pager
curl -I https://doitac.anhlaptrinh.vn/
curl -I https://doitac.anhlaptrinh.vn/dang-ky/
```

To preview account creation without writing:

```bash
cd /root/Apps/partner_token_billing
set -a; . ./.env; set +a
.venv/bin/python manage.py create_customer_account \
  --email 'partner@example.com' \
  --full-name 'Đối tác mẫu' \
  --credit 0 \
  --no-create-api \
  --dry-run
```

## Deploy Changes

Before modifying existing Nginx or systemd files, back them up under `/root/_Backups`.

```bash
cd /root/Apps/partner_token_billing
set -a; . ./.env; set +a
.venv/bin/python manage.py migrate --noinput
.venv/bin/python manage.py collectstatic --noinput
.venv/bin/python manage.py test
nginx -t
systemctl daemon-reload
systemctl restart doitac-token-billing.service
systemctl restart doitac-credit-guard.timer
systemctl reload nginx
```

## Partner Custom Domain

Use a dedicated API subdomain such as `api.tencongty.vn`, not the company's main website domain.

Dry run:

```bash
cd /root/Apps/partner_token_billing
scripts/provision_partner_domain.sh \
  --email partner@example.com \
  --domain api.tencongty.vn \
  --dry-run
```

Real provisioning after the DNS A record points directly to the VPS:

```bash
cd /root/Apps/partner_token_billing
scripts/provision_partner_domain.sh \
  --email partner@example.com \
  --domain api.tencongty.vn
```

The script validates DNS, backs up an existing site file under `/root/_Backups`, writes an Nginx proxy to local 9Router, obtains SSL with Certbot, reloads Nginx, and marks the domain active in Django. Rerun the same command after correcting DNS or SSL issues.

The shared ingress `9router.anhlaptrinh.vn` and generated partner-domain `/v1/` locations allow request bodies up to `50M` to support long OpenAI Responses API requests.

## Signed HTTPS Reseller API

- Public URL: `https://doitac.anhlaptrinh.vn/api/reseller/v1`.
- Used by `/root/Apps/cdx_token_dashboard`, including from another VPS, to manage unique child keys and read reseller-owned usage and balance.
- Authentication requires an active partner API key plus a separate HMAC secret from `.env`; never print or document either value.
- Every request signs method, full path, Unix timestamp, nonce, and body SHA-256. Nonces are stored once in `ResellerBridgeNonce`; clock skew over 300 seconds and replayed nonces are rejected.
- The bridge validates the key against 9Router, maps it to `ManagedApiKey`, enforces partner status, remaining credit, `allow_key_creation`, and `max_api_keys`, then records child keys with prefix `CDX-`.
- Supported operations: list keys with live balance, create a child key, set `isActive`, delete a child key, and read usage rows for the partner's `CDX-` child keys.
- The list response includes total internal credit, all-time spent, remaining credit, total active keys, active CDX child keys, and `max_api_keys`; CDX displays this read-only to its superusers.
- Public Nginx rate-limits `/api/reseller/v1/`; the legacy loopback endpoint remains limited to localhost and public Nginx returns 404 for `/internal/reseller-bridge/`.
- The CDX client sends `User-Agent: CDX-Reseller-Bridge/1.0` because Cloudflare Browser Integrity otherwise returns error 1010 for Python urllib.
- When changing this bridge, run the partner test suite and the CDX end-to-end key test, then update both global skills.

## Inputs And Outputs

- Input: partner registration, admin approval, credit limit, downstream clients, resale multipliers, branding, custom-domain request, named API keys, 9Router usage history, and optional SePay webhook events.
- Output: authenticated reseller dashboard, per-client revenue estimates, branded Base URL, request/token/cost reports, OpenAI-compatible API access, payment orders, and automatic quota enforcement.
- Local writes: partner Django database and static files only.
- External writes: create, activate, deactivate, or delete partner API keys through the local 9Router admin API.
- No Google Sheet or unrelated API writes.

## Payment

- Payment URL: `https://doitac.anhlaptrinh.vn/payment/ipn/`.
- The app has a separate webhook secret in `.env`; never print it.
- Automatic SePay crediting works only after SePay is configured to send events to the partner webhook.
- Until that external webhook is configured, a superuser may approve partners and adjust credit manually.

## Recovery

- Restart web: `systemctl restart doitac-token-billing.service`.
- Run guard now: `systemctl start doitac-credit-guard.service`.
- Rebuild static: `.venv/bin/python manage.py collectstatic --noinput`.
- Verify source database only with read-only SQLite checks; never edit `/root/.9router/db/data.sqlite`.
- If a key was disabled only because credit was exhausted, increasing credit allows the guard to reactivate it.

## Safety

- Do not modify `/root/Apps/9router_usage_dashboard` for partner-portal tasks.
- Do not expose `.env`, Cloudflare credentials, provider credentials, complete API keys, prompts, or responses.
- Do not test `/v1` with a real complete API key in a URL or log.
- Keep Django login and HTTPS enabled.
- Run tests, `nginx -t`, service checks, and public HTTP checks after production changes.
- Update this skill, `/root/_Second_AI_Brain/projects/partner_token_billing.md`, and `/root/_Second_AI_Brain/06_Nhat_Ky_Thay_Doi.md` after operational changes.
