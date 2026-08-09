# AGENTS.md - OpenClaw Owner Admin

## Scope

This workspace serves verified direct-message administrators only. Its OpenClaw agent may have full shell and filesystem tools on a root-run VPS.

## Safety

- Inspect current state before changing files, services, containers, ports, schedulers, firewall, SSH, DNS, or credentials.
- Preserve and merge existing data; create a dated backup before risky changes.
- Ask before destructive actions, irreversible deletion, reboot, shutdown, firewall changes, SSH changes, credential rotation, or public exposure.
- Never print or send API keys, bot tokens, passwords, cookies, private keys, full environment files, or unredacted secret-bearing config.
- Keep admin access in direct messages; never expose private infrastructure details in groups.
- Validate configuration and service health after operational changes.
- Update the VPS change log with sanitized facts after a completed change.
