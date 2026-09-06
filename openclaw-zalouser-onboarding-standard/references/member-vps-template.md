# Member Zalo Onboarding Template

Fill this template with non-secret identifiers only. Keep actual credentials,
cookies, QR payloads, private IDs, and token files out of the template.

```text
RUNTIME_KIND=docker-member
CONTAINER=user-<label>
MEMBER_HOME=/home/<label>
MEMBER_LABEL=<label>
OPENCLAW_ROOT=/home/<label>/.openclaw
DATA_DIR=/root/Apps/member_vps/docker-users/data/<label>
AGENT_ID=main
ZALO_ACCOUNT_ID=default
TELEGRAM_ACCOUNT_ID=<account>
PROJECT_KEYS=member_<label>_gateway_supervisor,member_<label>_zalouser,member_<label>_resource_guard
```

Required outputs are sanitized status lines, backup paths, log/state paths,
cron marker names, and validation results. Never record secret values.

The host-side Gateway guard must make the persistent entrypoint and active
Supervisor config agree. The channel guard must use the exact member HOME and
must restart only a Supervisor-managed Gateway. The resource guard must use a
separate state file and must not kill unrelated production services.
