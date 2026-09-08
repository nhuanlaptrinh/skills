---
name: recover-openclaw-member-gateway
description: Compatibility entry point for member Gateway recovery. Use openclaw-zalo-reliability references/supervisor-watchdog.md as canonical guidance.
---

# Recover OpenClaw Member Gateway

Use `/root/.agents/skills/openclaw-zalo-reliability/references/supervisor-watchdog.md` and the Shared Watchdog Center for Gateway/Supervisor recovery. Do not start a second Gateway, alter credentials, or recreate the container for a Gateway-only repair.

For `lehuynhphong`, verify `user-lehuynhphong`, `/home/lehuynhphong`, exactly one `openclaw-gateway` under Supervisor, then run:

```bash
/usr/bin/python3 /root/Automation/watchdog/shared_self_healing/scripts/check_member_gateway_supervisor.py --container user-lehuynhphong --member-home /home/lehuynhphong --member-label lehuynhphong --gateway-user root --dry-run
```
