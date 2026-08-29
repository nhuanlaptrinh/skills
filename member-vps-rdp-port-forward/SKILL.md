---
name: member-vps-rdp-port-forward
description: Configure and verify a dedicated public host port that forwards Remote Desktop traffic to a Docker member VPS container's xrdp service.
---

# Member VPS RDP Port Forward

Use when a member VPS has xrdp listening on container port `3389`, but the host already uses port `3389` or Docker does not publish the member RDP port.

## Scope

- Target member: `lethangholand`
- Container: `user-lethangholand`
- Persistent data: `/root/Apps/member_vps/docker-users/data/lethangholand`
- Public endpoint: `187.127.177.163:33890`
- systemd socket: `/etc/systemd/system/member-vps-rdp-lethangholand.socket`
- systemd proxy: `/etc/systemd/system/member-vps-rdp-lethangholand.service`

## Port path

The host owns public IP `187.127.177.163`. The path is TCP host `33890` to `user-lethangholand:3389`. This preserves the host's own xrdp listener on `3389` and does not require container recreation.

## Checks

```bash
systemctl status member-vps-rdp-lethangholand.socket member-vps-rdp-lethangholand.service --no-pager
ss -ltnp | grep ':33890'
docker exec user-lethangholand ss -ltnp | grep ':3389'
ufw status numbered | grep '33890/tcp'
```

## Apply or rerun

```bash
systemctl daemon-reload
systemctl enable --now member-vps-rdp-lethangholand.socket
ufw allow 33890/tcp comment 'RDP member lethangholand'
```

The socket activates `systemd-socket-proxyd`. The service resolves the current container IP whenever it starts and exits after 30 idle seconds, so later connections refresh the target after container changes.

## Input and output

- Input: TCP RDP on host port `33890`.
- Output: TCP RDP to port `3389` of the running `user-lethangholand` container.
- Runtime state: systemd unit state and journal; no Sheet or API writes.

## Rollback

```bash
systemctl disable --now member-vps-rdp-lethangholand.socket
ufw delete allow 33890/tcp
```

Do not delete the member data directory or recreate the production container for this change. Keep firewall snapshots under `/root/_Backups` before modifying production forwarding.

## Safety

- Never place passwords, API keys, cookies, tokens, private keys, or `.env` contents in this skill.
- Do not change the member password or xrdp credentials unless explicitly requested.
- Verify the container and its xrdp listener before applying the public port.
