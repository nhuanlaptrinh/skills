---
name: chuyen-website-khoa-hoc-vps-moi
description: Chuyen website khoa hoc/Django/Docker trong /root/10Web_BH sang VPS moi, gan domain/subdomain anhlaptrinh.vn, chay Docker Compose, cau hinh nginx reverse proxy, cap SSL Certbot, cap nhat webhook n8n tu domain cu sang domain moi, va xu ly URL noi bo n8n khi website cung VPS hoac khac VPS. Use when the user asks to migrate, run, repair, deploy, or reconnect a course website after moving n8n/VPS/domain, especially projects like /root/10Web_BH/*_domain_* with docker-compose.yml, Django views.py, nginx, Certbot, and n8n webhook URLs.
---

# Chuyen Website Khoa Hoc VPS Moi

## Scope

Use this skill for reusable website migration/deployment work only. Do not include one-off workflow-specific edits unless the user explicitly asks for that workflow by name.

Typical targets:
- Django course sites under `/root/10Web_BH/<number>_domain_<code>`.
- Docker Compose services that expose port `8000` or `80`.
- nginx host-level reverse proxy on ports `80/443`.
- n8n webhook URL changes after moving from one n8n domain/VPS to another.

## Core Workflow

1. Inspect before changing:
   - `sed -n '1,160p' docker-compose.yml`
   - `sed -n '1,120p' */views.py` or `rg -n "webhook|n8n|replace\\(|vpsn8n|n8nalt|n8n3-app|WEBHOOK" <project>`
   - `docker compose ps`
   - `docker ps --format '{{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}'`
   - `rg -n "<domain>|proxy_pass|server_name" /etc/nginx/sites-available /etc/nginx/sites-enabled /etc/nginx/conf.d`

2. Classify n8n URLs:
   - Public old domain, for example `https://vpsn8n.anhlaptrinh.vn/...`.
   - Public new domain, for example `https://n8nalt.anhlaptrinh.vn/...`.
   - Internal Docker URL, for example `http://n8n3-app:5678/...`.
   - Internal replacement logic, for example `.replace("https://vpsn8n.anhlaptrinh.vn", "http://n8n3-app:5678")`.

3. Ask before internal URL decisions when unclear:
   - If website is on a different VPS from n8n: remove/avoid internal Docker URL logic and call the public n8n domain directly.
   - If website and n8n are on the same VPS and same Docker network: use the current n8n service/container name, for example `http://n8nalt-app:5678/...`.
   - If the user already confirms same/different VPS, act without asking again.

4. Update code narrowly:
   - Replace old public n8n domain with new public n8n domain.
   - Replace old internal n8n host such as `n8n3-app` with the current service/container such as `n8nalt-app` only when same VPS/network is confirmed.
   - Do not change unrelated business logic, prices, coupons, course content, or one-off n8n workflows.
   - Run `python3 -m py_compile <changed .py files>` for Django/Python changes.

5. Start or repair the website container:
   - If the host nginx proxies to localhost, ensure compose publishes only loopback:
     `ports: ["127.0.0.1:<host_port>:<container_port>"]`
   - Keep Docker network membership needed for internal n8n calls, commonly `root_traefik`.
   - Run `docker compose up -d --build` when dependencies/image may be stale; otherwise `docker compose up -d`.
   - Check `docker compose ps` and `docker logs --tail 120 <container>`.

6. Configure nginx host reverse proxy:
   - If no Traefik container is running and nginx owns ports 80/443, Docker labels alone are not enough.
   - Create `/etc/nginx/sites-available/<domain>` and symlink to `sites-enabled`.
   - Proxy to the loopback port published by Docker, for example `proxy_pass http://127.0.0.1:8000;`.
   - Include `Host`, `X-Real-IP`, `X-Forwarded-For`, `X-Forwarded-Proto`, `X-Forwarded-Host`, and `X-Forwarded-Port` headers.
   - Run `nginx -t` before `service nginx reload`.

7. Enable HTTPS:
   - First test HTTP locally with `curl -I -H "Host: <domain>" http://127.0.0.1/`.
   - Run `certbot --nginx -d <domain> --non-interactive --agree-tos --redirect`.
   - If Certbot fails DNS validation, report that DNS must point to this VPS before HTTPS can work.

8. Validate end to end:
   - `curl -I -H "Host: <domain>" http://127.0.0.1/`
   - `curl -I --resolve <domain>:443:127.0.0.1 https://<domain>/`
   - `curl -I https://<domain>/` when DNS works from the environment.
   - Check container logs for `200` responses and Django errors.
   - Verify n8n app URL if touched: `curl -I https://<new-n8n-domain>/`.

## nginx Template

Use this as the starting point for HTTP; let Certbot add HTTPS blocks.

```nginx
server {
    listen 80;
    listen [::]:80;
    server_name DOMAIN_HERE;

    location / {
        proxy_pass http://127.0.0.1:PORT_HERE;
        proxy_http_version 1.1;

        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host $host;
        proxy_set_header X-Forwarded-Port $server_port;

        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";

        proxy_read_timeout 3600s;
        proxy_send_timeout 3600s;
        proxy_buffering off;
    }
}
```

## Safety Rules

- Backup before database or broad text rewrites.
- Never expose app ports on `0.0.0.0` unless the user explicitly asks; prefer `127.0.0.1`.
- Do not print secrets, tokens, credentials, real customer data, or full workflow JSON in the final answer.
- Do not run real payment, Zalo, Facebook, or activation workflows as a test unless the user explicitly asks.
- Prefer reporting exact files changed and validation commands/results.
