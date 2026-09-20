---
name: member-vps-legacy-openclaw-home
description: Run an existing copied OpenClaw member whose persistent legacy home layout is mounted at its runtime home, without inheriting a source member's hard-coded Supervisor paths.
---

# Legacy Home-layout OpenClaw Member

Use this only for an existing member data directory with `.openclaw/openclaw.json` directly below `data/<member>`. It is for legacy copied members; new members should use `entrypoints/openclaw-root.sh` and the root-layout provisioner.

## Entrypoint and layout

- Entrypoint: `/root/Apps/member_vps/docker-users/entrypoints/openclaw-home.sh`
- Host data: `/root/Apps/member_vps/docker-users/data/<member>`
- Runtime HOME: `/home/<member>`
- Runtime config: `/home/<member>/.openclaw/openclaw.json`
- Container: `user-<member>`

The entrypoint creates a member user and starts only SSH, XRDP, Nginx, the existing config guard, and OpenClaw Gateway under Supervisor. It receives the member name through `MEMBER_USER`; therefore it never contains another member's hard-coded `/home/...` path. It never sets or logs passwords, bot tokens, or provider keys.

## Preflight (read-only)

```bash
test -f /root/Apps/member_vps/docker-users/data/<member>/.openclaw/openclaw.json
docker ps -a --filter "name=^/user-<member>$"
ss -ltn '( sport = :<ssh_port> or sport = :<web_port> )'
```

Back up the target's `openclaw.json`, bot token file, and any config being changed to a root-only directory under `/root/_Backups` before starting a new container.

## Run

Create the container once the member config is valid and credentials are set through root-only files/config management:

```bash
docker run -d --name user-<member> --hostname <member> --restart unless-stopped \
  --cpus 2 --memory 4g --memory-swap 6g --pids-limit 1024 \
  -p <ssh_port>:22 -p <web_port>:80 \
  -e MEMBER_USER=<member> -e MEMBER_NAME='<member> VPS' \
  -v /root/Apps/member_vps/docker-users/data/<member>:/home/<member> \
  -v /root/Apps/member_vps/docker-users/entrypoints:/usr/local/share/member-vps-entrypoints:ro \
  --entrypoint /usr/local/share/member-vps-entrypoints/openclaw-home.sh \
  member_vps-phukiengiakho:latest
```

Do not recreate an existing member container. Do not use this command for a root-layout member.

## Verify and rerun

```bash
docker exec user-<member> supervisorctl status
docker exec -e HOME=/home/<member> user-<member> openclaw config validate
docker exec -e HOME=/home/<member> user-<member> openclaw channels status --probe
```

For a failed first boot, inspect `/tmp/openclaw-supervisor.log` and `/tmp/openclaw-config-guard.log` in that container. Stop/remove only the newly created target container after confirming its exact name; retain the persistent data directory and backup for rerun.

## Safety

- Use only exact member/container paths; never mount another member's data.
- Do not put secrets in this skill, shell history, documentation, or output.
- Keep Telegram owners and Full Exec policy managed by the respective OpenClaw owner-access skills.
- After a production change, update `/root/_Second_AI_Brain/06_Nhat_Ky_Thay_Doi.md` without secrets or personal IDs.
