# Developer Handoff Template

Fill every applicable field after setup. Keep secrets in protected local files and report only their paths.

## SSH Access

- VPS host/IP: `<ssh-host>`
- SSH port: `<ssh-port>`
- SSH user: `<dev-user>`
- Authentication: public key only
- Public-key fingerprint: `<fingerprint>`
- SSH command: `ssh -p <ssh-port> <dev-user>@<ssh-host>`
- VS Code Remote SSH target: `<dev-user>@<ssh-host>`

## Workspace

- Production project: `<production-project>` — read/write access not granted
- DEV workspace: `<dev-workspace>`
- Framework/runtime: `<runtime>`
- Dependency environment: `<venv-or-node-modules-path>`
- Synthetic DEV data: `<dev-data-path-or-none>`
- DEV login username: `<dev-login-user-or-none>`
- DEV login password location: `<protected-local-file-or-none>`

## Website Access

- DEV service: `<service-name>`
- VPS loopback address: `http://127.0.0.1:<remote-dev-port>`
- Local tunnel port: `<local-port>`
- Tunnel command: `ssh -N -p <ssh-port> -L <local-port>:127.0.0.1:<remote-dev-port> <dev-user>@<ssh-host>`
- Browser URL on developer computer: `http://127.0.0.1:<local-port>`
- If Windows rejects the local port, retry with another free local port while keeping the remote port unchanged.

## Service Commands

```bash
systemctl --user status <service-name>
systemctl --user restart <service-name>
systemctl --user stop <service-name>
systemctl --user start <service-name>
```

## Development Commands

```bash
cd <dev-workspace>
<load-dev-environment>
<activate-dependencies>
<check-command>
<test-command>
```

## Git Handoff

```bash
cd <dev-workspace>
git status
git add -A
git commit -m "Describe the completed change"
git log -1 --oneline
```

Send the owner:

```text
Completed change: <summary>
Commit: <commit-hash>
Tests/checks: <result>
Pages tested: <paths>
Migration/dependency changes: <none-or-details>
Known limitations: <none-or-details>
```

## Restrictions

- No root or unrestricted sudo.
- No Docker-group access.
- No production `.env`, databases, customer data, credentials, or private keys.
- No direct production edits, restart, migration, or deployment.
- No public DEV port; use the SSH tunnel.
- Production deployment requires owner approval and review of the exact commit.

## Verification Status

- DEV service: `<active/inactive>`
- DEV HTTP: `<status>`
- Tests/checks: `<status>`
- Production service after setup: `<status>`
- Production HTTP after setup: `<status>`
- Remaining action: `<none-or-specific-blocker>`
