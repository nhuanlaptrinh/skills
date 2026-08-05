---
name: mo-port-vps-thanh-vien
description: Mở port TCP cho app hoặc VPS/host thành viên chạy bằng Docker container trên VPS chính. Use when the user asks in Vietnamese to "mở port", "allow port", "mở cổng", "cho phép port", "mở port app", or "sử dụng ở host/vps thành viên". By default, treat "mở port <PORT>" as opening an application port, not an SSH port, unless the user explicitly says SSH or the port is already a Docker SSH mapping.
---

# Mở Port VPS Thành Viên

Use this skill when the user asks to open a TCP port for an app or member VPS/host on a Docker-based parent VPS.

## Member VPS Create Helper

This VPS has a reusable helper for creating Docker-based member VPS containers:

```bash
cd /root/Apps/member_vps/docker-users
bash manage-user.sh create <name> <password> [ssh_port] [web_port]
bash manage-user.sh list
bash manage-user.sh show <name>
```

Example:

```bash
cd /root/Apps/member_vps/docker-users
bash manage-user.sh create phong '<PASSWORD>' 1123 8123
```

If `ssh_port` and `web_port` are omitted, the script chooses the next free SSH port starting from `1121` and the next free web port starting from `8121`.

The helper creates:

```text
container: user-<name>
data: /root/Apps/member_vps/docker-users/data/<name>
mount: /root/Apps/member_vps/docker-users/data/<name> -> /home/<name>
ports: <ssh_port> -> 22, <web_port> -> 80
image: member_vps-phukiengiakho:latest by default
```

Safety rules:

- Do not write real passwords into docs, logs, or final responses.
- Before creating a user, the helper checks that the container, data folder, and ports do not already exist.
- The helper opens UFW for both selected ports when UFW is available.
- After creation, test SSH/web public ports and update `/root/_Second_AI_Brain/06_Nhat_Ky_Thay_Doi.md` without recording the password.

## Important Default

When the user says only "mở port <PORT>" or "mở cổng <PORT>", assume they mean an **app port**.

For an app port, do all three layers:

1. Confirm the app is listening inside the target `user-*` container.
2. Open UFW on the parent VPS.
3. Forward the parent VPS public port to the same app port inside the target container, for example:

```text
<PUBLIC_IP>:11190 -> user-daomac:11190
```

Only treat a port as SSH when the user explicitly says SSH, asks for an SSH command, or Docker already publishes the port as `<HOST_PORT>->22/tcp`.

## Default Member Port Plan

When the user asks to create/open website ports for existing member containers without specifying exact ports, use this default plan first. SSH ports are only for login; website/app ports are separate browser-facing HTTP ports.

If the user says commands like "mở web port mặc định", "mở port cho thành viên", "mở luôn", or asks to apply this default plan, do not merely explain the mapping. Execute the opening immediately: check conflicts, open UFW, add Docker DNAT/ACCEPT rules, create or update a persistent systemd oneshot service, enable/start it, and test the public ports. Report if a port is firewall/forward-ready but not accepting because no app is listening inside the container yet.

```text
user-alt:
SSH 1112
Web 18792

user-hieu:
SSH 1115
Web 18796

user-huuhuy:
SSH 1117
Web 18797

user-xuanvu:
SSH 1118
Web 18798
```

Important reservation: do not assign `18795` to a member website by default because this VPS uses it as the fixed public OpenClaw link, forwarded to local OpenClaw gateway `18789`.

Before applying this plan, always re-check conflicts in all layers and change any conflicting web port to the next free port, preferably continuing upward from `18799`:

```bash
ss -ltnp | rg ':<PORT>\b' || true
docker ps --format 'table {{.Names}}\t{{.Ports}}' | rg '<PORT>|NAMES' || true
ufw status verbose | rg '<PORT>|Status|Default' || true
iptables -t nat -S | rg '<PORT>' || true
systemctl list-unit-files --type=service | rg '<PORT>|forward|member' || true
```

If a member has an app running on an internal port such as `3000`, `5000`, `8000`, or `8501`, map the assigned public web port to that internal app port, for example:

```text
194.59.165.104:18797 -> user-huuhuy:3000
```

For the standard default same-port mapping on this VPS, create or update this persistent helper when applying the plan:

```bash
/usr/local/sbin/forward-default-member-web-ports.sh
/etc/systemd/system/forward-default-member-web-ports.service
systemctl enable --now forward-default-member-web-ports.service
```

The standard same-port mappings are:

```text
194.59.165.104:18792 -> user-alt:18792
194.59.165.104:18796 -> user-hieu:18796
194.59.165.104:18797 -> user-huuhuy:18797
194.59.165.104:18798 -> user-xuanvu:18798
```

After opening, test each public port. If the test says `not accepting`, do not call it a firewall failure when UFW and DNAT exist; explain that the member still needs to run an app inside the container on `0.0.0.0:<WEB_PORT>` or provide the app's real internal port so the forward can be changed.

## Workflow

1. Identify the target host port from the user request.
2. Identify the target container:
   - If the user names a `user-*` container, use it.
   - If the port is already published by Docker, identify the owning container.
   - If the user did not name a container and the port is not published, inspect likely `user-*` containers or ask which user/container should receive the app port.
3. Check Docker mappings:

```bash
docker ps --format 'table {{.Names}}\t{{.Ports}}' | rg '<PORT>|NAMES'
```

4. If the port is already published by Docker, identify the container and destination port:

```bash
docker inspect <container> --format 'name={{.Name}} ip={{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}} ports={{json .NetworkSettings.Ports}} status={{.State.Status}}'
iptables -t nat -S | rg '<PORT>|<container-ip>'
```

5. For app ports, check whether the app is listening inside the target container:

```bash
docker exec <container> sh -lc "ss -lntp 2>/dev/null | grep ':<PORT>' || netstat -lntp 2>/dev/null | grep ':<PORT>' || true"
```

The app should bind `0.0.0.0:<PORT>`. If it binds only `127.0.0.1:<PORT>`, public forwarding can still fail or only work through a local tunnel depending on the app; tell the user to start the app on `0.0.0.0`.

6. Open the host firewall for TCP:

```bash
ufw allow <PORT>/tcp
ufw status verbose | rg '<PORT>|Status|Default'
```

7. If this is an app port and Docker did not already publish the desired `<HOST_PORT>-><CONTAINER_PORT>`, add a host DNAT rule and a small systemd oneshot service so the forward survives reboot/container IP changes.

DNAT pattern:

```bash
container_ip="$(docker inspect <container> --format '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}')"
iptables -t nat -C DOCKER ! -i docker0 -p tcp -m tcp --dport <HOST_PORT> -j DNAT --to-destination "${container_ip}:<CONTAINER_PORT>" 2>/dev/null \
  || iptables -t nat -A DOCKER ! -i docker0 -p tcp -m tcp --dport <HOST_PORT> -j DNAT --to-destination "${container_ip}:<CONTAINER_PORT>"
iptables -C DOCKER -d "${container_ip}/32" ! -i docker0 -o docker0 -p tcp -m tcp --dport <CONTAINER_PORT> -j ACCEPT 2>/dev/null \
  || iptables -I DOCKER 1 -d "${container_ip}/32" ! -i docker0 -o docker0 -p tcp -m tcp --dport <CONTAINER_PORT> -j ACCEPT
```

8. Test the public port using the server's public IPv4:

```bash
public_ip="$(curl -4 -s ifconfig.me || curl -4 -s icanhazip.com)"
timeout 3 bash -lc "</dev/tcp/${public_ip}/<PORT>" && echo "public <PORT> accepting" || echo "public <PORT> not accepting"
```

9. If this is explicitly a member SSH port, give the user:

```bash
ssh root@<PUBLIC_IP> -p <PORT>
```

## If Docker Has No Mapping For An App Port

If the requested port should reach an app inside a `user-*` container but Docker did not publish it:

- Find the intended container from the user's wording or nearby mappings.
- Check whether the app is listening inside the container:

```bash
docker exec <container> sh -lc "ss -lntp 2>/dev/null | grep ':<PORT>' || netstat -lntp 2>/dev/null | grep ':<PORT>' || true"
```

- If the container already exists and should not be recreated, add a host DNAT rule and a small systemd oneshot service so the forward survives reboot/container IP changes.
- Ensure the app inside the container binds `0.0.0.0:<PORT>`, not only `127.0.0.1:<PORT>`.

## Local Helper

This server may have a helper script:

```bash
/usr/local/sbin/open-member-port.sh <host_port>
/usr/local/sbin/open-member-port.sh <host_port> <container_name> [container_port]
```

Use it when available. For an app port inside `user-daomac`, run for example:

```bash
/usr/local/sbin/open-member-port.sh 11190 user-daomac 11190
```

## Response Style

Report briefly:

- Which `user-*` container the port maps to.
- Whether it is an app port or SSH port.
- Whether UFW was opened.
- Whether DNAT/forward exists, for example `<PUBLIC_IP>:11190 -> user-daomac:11190`.
- Whether the public port accepts connections.
- The exact URL or command the user should run.

If the port accepts but login fails, explain that firewall is solved and the remaining issue is credentials or SSH config inside the container.
