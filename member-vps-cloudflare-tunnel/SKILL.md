---
name: member-vps-cloudflare-tunnel
description: Install, operate, verify, repair, or connect a Docker member VPS to Cloudflare Tunnel so WordPress, Django, OpenClaw, or other dynamic websites can use HTTPS domains without host Nginx, host ports 80/443, Docker socket, or host SSH access. Use for member containers under /root/Apps/member_vps/docker-users/data when adding a tunnel connector, checking Tunnel health, attaching a Public Hostname, or restoring cloudflared after restart.
---

# Member VPS Cloudflare Tunnel

## Architecture

Use an outbound connector inside the member container:

`Domain -> Cloudflare HTTPS -> cloudflared in member -> Nginx localhost:80 -> local app`

Keep the member on Docker bridge networking. Do not expose its database, mount the Docker socket, grant host SSH, or modify host Nginx for Tunnel domains.

## Required paths

- Manager project: `/root/Apps/member_vps/docker-users`
- Member data: `/root/Apps/member_vps/docker-users/data/<member>`
- Persistent binary: `<member-data>/.local/bin/cloudflared`
- Persistent token: `<member-data>/.cloudflared/tunnel-token`
- Persistent logs: `<member-data>/.cloudflared/cloudflared.log`
- Setup script: `scripts/setup_member_cloudflare_tunnel.sh`
- Member domain command: `scripts/gan-domain`
- Backup: `/root/_Backups/member_vps/<container>/cloudflared/<timestamp>`
- Change log: `/root/_Second_AI_Brain/06_Nhat_Ky_Thay_Doi.md`

## Before applying

1. Read the VPS Second AI Brain files, the member `AGENTS.md`, and the production checklist.
2. Create a remotely managed Cloudflare Tunnel in the dashboard.
3. Rotate any token pasted into chat or logs.
4. Save the fresh token directly inside the member at `~/.cloudflared/tunnel-token` with mode `600`. Never print or copy its contents.
5. Confirm the local origin with `curl -I -H 'Host: <domain>' http://127.0.0.1:80/` inside the container.

## Dry-run

```bash
bash /root/.agents/skills/member-vps-cloudflare-tunnel/scripts/setup_member_cloudflare_tunnel.sh \
  --container user-anhlaptrinhthu \
  --data-dir /root/Apps/member_vps/docker-users/data/anhlaptrinhthu \
  --member-home /home/anhlaptrinh \
  --origin http://127.0.0.1:80 \
  --dry-run
```

Dry-run validates the container, bind mount, token metadata, origin format, and planned paths without reading the token or changing production.

## Apply

```bash
bash /root/.agents/skills/member-vps-cloudflare-tunnel/scripts/setup_member_cloudflare_tunnel.sh \
  --container user-anhlaptrinhthu \
  --data-dir /root/Apps/member_vps/docker-users/data/anhlaptrinhthu \
  --member-home /home/anhlaptrinh \
  --origin http://127.0.0.1:80 \
  --apply
```

The script backs up the active entrypoint and Supervisor config, installs a checksum-verified persistent cloudflared binary, adds cloudflared to the generated Supervisor configuration, starts it without restarting the member container, and checks the local metrics endpoint.

## Prepare a local domain

The setup script installs the persistent `gan-domain` command in the member. Use it to create the local Nginx virtual host before adding the matching Cloudflare Public Hostname:

```bash
sudo gan-domain add example.com --port 8000 --dry-run
sudo gan-domain add example.com --port 8000

sudo gan-domain add static.example.com \
  --root /home/<member>/websites/static.example.com

gan-domain check example.com
gan-domain list
gan-domain status
```

The command stores canonical Nginx files under `/home/<member>/.gan-domain/nginx`, links them into `/etc/nginx/conf.d`, validates Nginx before reload, and prints the Public Hostname values to enter in Cloudflare. It refuses to overwrite a domain already managed by another Nginx config.

The Tunnel runtime token cannot edit DNS or Public Hostnames. Full one-command Cloudflare automation requires a separate scoped API token with only the necessary Tunnel and DNS permissions; never reuse or expose the runtime token.

## Attach a Public Hostname

After the connector is Healthy, open Cloudflare Zero Trust and select:

`Networks -> Tunnels/Connectors -> <tunnel> -> Public Hostnames -> Add`

Set:

- Hostname: the required domain or subdomain.
- Service type: `HTTP`.
- URL: `localhost:80` when Nginx in the member routes by `Host`.

Cloudflare creates the proxied DNS route and edge certificate. The zone must be active in the same Cloudflare account. For WordPress or Django, keep Nginx as the local origin and configure the application to trust proxy HTTPS headers.

## Verify

```bash
docker exec user-<member> supervisorctl \
  -c /home/<member>/.cloudflared/supervisord.conf status

docker exec user-<member> sh -lc \
  'curl -fsS http://127.0.0.1:49312/metrics | grep cloudflared_tunnel_ha_connections'

curl -I https://<domain>/
```

Expected results:

- `cloudflared-tunnel` is `RUNNING`.
- `cloudflared_tunnel_ha_connections` is greater than zero.
- HTTPS returns the member website, not the host default page.
- No new public port or host Nginx site is required.

## Rerun and rollback

- Rerun `--apply` safely to restore the binary, persistent Supervisor files, or a stopped connector.
- Do not rotate the Tunnel token during ordinary reruns.
- To rollback, stop the dedicated persistent Supervisor process, restore the backed-up entrypoint, and restart the container only during an approved maintenance window.
- If the container is recreated from an old image, rerun the setup script because the binary and token remain in the persistent member data directory.

## Safety

- Never pass the Tunnel token on the command line or include it in logs, skills, backups, or answers.
- Keep the token file root-owned with mode `600`.
- Use `info` logging, not `debug`, because debug logs may include request headers.
- Do not grant Cloudflare Global API Key access. Domain automation requires a separate narrowly scoped API token.
- Do not overwrite an existing Nginx virtual host or Cloudflare hostname without checking ownership and conflicts.
- Back up before changing the container entrypoint, Supervisor, Nginx, or DNS, and update the Second AI Brain change log after production changes.
