---
name: secure-ssh-dev-workspace
description: Create, audit, operate, or remove an isolated developer workspace for an existing VPS project using a dedicated Linux SSH user, VS Code Remote SSH, loopback-only website access through an SSH tunnel, synthetic development data, local Git handoff, and a non-root user service. Use when a project owner wants an employee or contractor to edit and run a website directly on the same VPS without sharing root, production secrets, customer databases, unrestricted sudo, Docker-group access, or direct write access to production.
---

# Secure SSH DEV Workspace

Build a separate DEV copy on the same VPS. Keep production source, secrets, databases, services, Nginx, cron, and Docker unchanged unless the user explicitly requests deployment later.

## Required Inputs

Discover from local context when possible; ask only for genuinely missing blocking data:

- Production project path and applicable `AGENTS.md` files.
- Project framework, dependency install command, check/test command, and local run command.
- Dedicated SSH username; default to a project-specific name such as `dev-<project>`.
- Employee public SSH key. Accept only a public key; never request or store a private key.
- Free loopback DEV port and production service/port identifiers.
- Whether the app needs synthetic databases, seed users, email, webhook, payment, or external API stubs.

## Mandatory Safety Rules

- Read `/root/_Second_AI_Brain/START_HERE.md`, the VPS map, project registry, relevant project note, production checklist, and scoped `AGENTS.md` before changes.
- Default workspace: `/home/<dev-user>/<project-name>_dev`. Do not grant direct write access to a production project under `/root`.
- Create a dedicated user with a locked password, normal shell, its own home, and public-key SSH authentication.
- Never add the user to `sudo`, `root`, `docker`, production service groups, or secret-bearing groups. Docker-group membership is root-equivalent.
- Never copy production `.env`, SQLite/PostgreSQL/MySQL dumps, credentials, API keys, cookies, private keys, customer uploads, logs, browser profiles, virtualenvs, generated static output, or caches.
- Use a project-specific `.env` with synthetic values. Disable real email, payment webhooks, mutations, posting, uploads, API-key creation/revocation, and other external side effects.
- Use synthetic or anonymized development data. Do not give the DEV user read-only access to production databases as a shortcut.
- Bind the DEV website only to `127.0.0.1:<dev-port>`. Access it through SSH tunneling; do not expose the DEV server publicly through Nginx or `0.0.0.0` by default.
- Run the DEV process as the dedicated user, never root. Prefer a systemd user service with lingering so the developer can restart it using `systemctl --user` without sudo.
- Keep a local Git repository in the DEV workspace. Do not require GitHub for heavy projects.
- Never deploy automatically from DEV to production. Require an explicit owner-approved commit and a separate reviewed deployment task.

## Preflight / Dry Run

Inspect without changing state:

```bash
id <dev-user> 2>/dev/null || true
ss -ltnp '( sport = :<dev-port> )'
df -h /home <production-project>
free -h
find <production-project> -name AGENTS.md -print
find <production-project> -maxdepth 2 -type f -printf '%M %U:%G %p\n'
```

Identify and exclude project-specific sensitive/generated files. At minimum inspect:

```text
.env*                   except a sanitized .env.example
*.sqlite, *.sqlite3, *.db
.venv/, venv/, node_modules/
staticfiles/, dist/, build/, __pycache__/
*.log, credentials*, client_secret*, *private*key*
uploads/media containing customer data
```

Confirm production health before proceeding and record a non-secret baseline such as service state and local HTTP status.

## Apply Workflow

1. Create the Linux user and lock password authentication. Create `.ssh/authorized_keys` with `700/600` permissions and validate the public-key fingerprint.
2. Create `/home/<dev-user>/<project-name>_dev` owned only by the developer.
3. Copy source with `rsync` exclusions. Verify production `.env` and databases do not exist in the DEV copy.
4. Create a separate virtualenv or dependency tree as the developer. Never reuse a root-owned production virtualenv.
5. Create project-specific DEV environment variables, database, seed data, and a DEV admin user. Store any generated DEV login in `/home/<dev-user>/.<project>_dev_login` with mode `600`; report the path, not the password.
6. Configure safe adapters: console/local-memory email, empty or fake webhook secrets, dummy payment details, synthetic API data, and unreachable or mocked mutation backends.
7. Initialize local Git after confirming ignore rules. Force-add legitimate source files accidentally ignored by broad patterns, especially migrations containing words such as `token`, then commit the baseline.
8. Create `/home/<dev-user>/.config/systemd/user/<service>.service` running as the developer. Bind only to loopback, enable lingering, and let the developer control it through `systemctl --user`.
9. Run framework checks, tests, HTTP smoke checks, permission checks, Git secret/name scans, ownership audits, and production health checks.
10. Update the relevant global skill/project note and `/root/_Second_AI_Brain/06_Nhat_Ky_Thay_Doi.md` without recording passwords, full keys, tokens, cookies, or `.env` contents.

Adapt commands to the framework. A typical Python/Django user service uses:

```ini
[Service]
WorkingDirectory=/home/<dev-user>/<project-name>_dev
EnvironmentFile=/home/<dev-user>/<project-name>_dev/.env
ExecStart=/home/<dev-user>/<project-name>_dev/.venv/bin/python manage.py runserver 127.0.0.1:<dev-port> --noreload
Restart=on-failure
NoNewPrivileges=true
PrivateTmp=true
UMask=0077
```

For Node, PHP, Go, or other stacks, preserve the same isolation and loopback-only rules while adapting `ExecStart`, dependencies, database setup, and tests.

## Validation Checklist

- Dedicated user has no sudo and no Docker-group membership.
- Public-key fingerprint is valid; `authorized_keys` is `600`; home and `.ssh` permissions are restrictive.
- DEV user cannot read production `.env`, databases, credentials, or `/root` project data.
- No production secrets or customer databases exist in the DEV workspace or local Git.
- Every file under the DEV home has the intended developer ownership.
- DEV service and HTTP checks pass on the selected loopback port.
- Framework check/tests pass, or unrelated pre-existing failures are documented.
- Production service and production HTTP baseline remain healthy.
- DEV port is not left publicly exposed.
- The final response follows `references/developer-handoff-template.md` and fills every applicable field.

## Developer Change Handoff

Require the developer to test and create a focused commit:

```bash
cd /home/<dev-user>/<project-name>_dev
git status
git add -A
git commit -m "Describe the completed change"
git log -1 --oneline
```

The developer sends the owner the commit hash, summary, tested pages, test result, migration/dependency changes, and known limitations. Warn that broad ignore patterns may require `git add -f <legitimate-file>` for new source files.

For deployment, the owner asks Codex to review that exact commit. Back up affected production files/database, apply only approved source and migrations, never copy DEV secrets/data/runtime folders, test, restart production, verify HTTP, and report rollback details.

## Rollback / Access Removal

- Remove or rotate the employee public key immediately when access is no longer needed.
- Stop and disable the user service; disable lingering if no other user services remain.
- Lock the Linux account. Do not delete the workspace automatically; archive it only with explicit approval.
- Preserve Git history long enough to review or recover work.
- Recheck production health after access removal.

## Mandatory Final Report

Use `references/developer-handoff-template.md`. Report concrete values, not vague placeholders, for all discovered fields. If the public key or SSH host is still missing, say exactly what remains blocked.

Never print passwords, private keys, API keys, webhook secrets, database contents, or complete `.env` values. It is acceptable to report usernames, public-key fingerprints, safe file paths, ports, service names, commit hashes, and commands containing no secrets.
