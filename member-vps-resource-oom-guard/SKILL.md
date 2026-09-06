---
name: member-vps-resource-oom-guard
description: Monitor and reduce repeat failures caused by host RAM, swap, memory pressure, or OOM events affecting an OpenClaw member VPS. Use when a member Gateway or Zalo listener freezes during host resource exhaustion, when kernel OOM kills appear, or when a reusable cooldown-based resource guard is needed without killing unrelated production services.
---

# Member VPS Resource/OOM Guard

Use the shared watchdog implementation on the main VPS. The guard is
conservative: it observes host memory and the target member cgroup, records
sanitized state, and alerts through a healthy Telegram account. It never kills
another container or process automatically.

## Files

- Script: `/root/Automation/watchdog/shared_self_healing/scripts/check_member_resource_guard.py`
- Registry: `/root/Automation/watchdog/shared_self_healing/project_config.json`
- Launcher: `/root/Automation/watchdog/shared_self_healing/run_project.sh`
- State: `/root/Automation/watchdog/shared_self_healing/state/member_<name>_resource_guard.json`
- Log: `/root/Automation/watchdog/shared_self_healing/logs/member_<name>_resource_guard.log`

## Dry Run

```bash
python3 /root/Automation/watchdog/shared_self_healing/scripts/check_member_resource_guard.py \
  --container user-daomac --member-home /home/daomac --member-label daomac \
  --account daomac --dry-run
```

The output contains RAM/swap/PSI/OOM counts and a severity. It never sends an
alert in dry-run mode, but it updates only the sanitized cooldown state.

## Scheduled Run

```bash
/root/Automation/watchdog/shared_self_healing/run_project.sh member_daomac_resource_guard
```

Run through cron every five minutes using the shared launcher. The registry
entry must set `type` to `host_resource` and `ai_on_failure` to `false`.

## Detection

The guard checks `MemAvailable`, `SwapFree`, memory PSI `full avg10`, recent
kernel OOM lines from the last fifteen minutes, and the target member cgroup's
memory usage and `memory.events`. Warning and critical alerts are rate-limited
for six hours. The target cgroup is observed separately so the guard does not
confuse another member's browser workload with daomac's Gateway.

## Output And Rerun

No secret, token, cookie, sender ID, message text, credential, or QR payload is
printed. Rerun the dry-run after a host memory incident, inspect the resource
log and state file, then run the shared launcher normally. Zalo recovery remains
the responsibility of `openclaw-zalo-reliability`; this guard only reports
resource pressure.

## Safety

- Back up `project_config.json` and the root crontab before changing schedules.
- Do not restart the whole member container for a resource alert.
- Do not kill unrelated Chrome, Python, Node, Docker, or OpenClaw processes.
- Do not modify `.env`, token files, browser profiles, credentials, sessions, or
  SQLite state as part of this guard.
- If host memory remains critical, investigate the high-memory workload or
  increase host capacity; do not hide the incident by deleting state.
