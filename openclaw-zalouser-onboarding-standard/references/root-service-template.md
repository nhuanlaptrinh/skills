# Root Or Systemd Zalo Onboarding Template

Use this variant when OpenClaw does not run inside a member Docker container.

```text
RUNTIME_KIND=root-service|systemd-service
SERVICE_UNIT=<service-unit>
MEMBER_HOME=<service HOME>
OPENCLAW_ROOT=<MEMBER_HOME>/.openclaw
AGENT_ID=<agent-id>
ZALO_ACCOUNT_ID=<account-id>
PROJECT_KEY=<unique watchdog key>
```

Keep the same invariants as the member template: one managed Gateway, aligned
core/plugin versions, explicit Zalo policy, channel watchdog, resource/OOM
monitor, cooldown, backup, redacted logs, and no automatic QR login. Replace
Docker commands with the service manager's read-only status and restart
commands; never pass a root-service path to a Docker-only script.
