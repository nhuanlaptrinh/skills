---
name: mo-port-vps-thanh-vien
description: Mở port TCP cho app hoặc VPS/host thành viên chạy bằng Docker container trên VPS chính. Use when the user asks in Vietnamese to "mở port", "allow port", "mở cổng", "cho phép port", "mở port app", or "sử dụng ở host/vps thành viên". By default, treat "mở port <PORT>" as opening an application port, not an SSH port, unless the user explicitly says SSH or the port is already a Docker SSH mapping.
---

# Mở Port VPS Thành Viên

Use this skill when the user asks to open a TCP port for an app or member VPS/host on a Docker-based parent VPS.

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
