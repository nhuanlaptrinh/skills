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

The output contains RAM/swap/PSI/OOM counts and a severity. Dry-run does not
write state or send alerts. Always pass a member-specific `--state-file` for
members other than daomac; the script's default state path belongs to daomac.

## Scheduled Run

```bash
/root/Automation/watchdog/shared_self_healing/run_project.sh member_daomac_resource_guard
```

Run through cron every five minutes using the shared launcher. The registry
entry must set `type` to `host_resource` and `ai_on_failure` to `false`.
When Telegram delivery is intentionally disabled, add `--no-notify` to the
registry `run_command`; the guard continues collecting log/state metrics.

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

On this host, member resource guards may run with `--no-notify` so
critical host/OOM conditions are retained in logs without sending Telegram
alerts. Re-enable notifications only by removing that flag from the relevant
registry entries after owner approval.

## Safety

- Back up `project_config.json` and the root crontab before changing schedules.
- Do not restart the whole member container for a resource alert.
- Do not kill unrelated Chrome, Python, Node, Docker, or OpenClaw processes.
- Do not modify `.env`, token files, browser profiles, credentials, sessions, or
  SQLite state as part of this guard.
- If host memory remains critical, investigate the high-memory workload or
  increase host capacity; do not hide the incident by deleting state.

## Cat Minh OOM recovery (2026-10-30)

Target: `user-trolyketoancatminh`, runtime HOME `/home/trolyketoancatminh`,
persistent config on host:
`/root/Apps/member_vps/docker-users/data/trolyketoancatminh/.openclaw/openclaw.json`.
Three Telegram accounts share one Gateway. Kernel cgroup OOM kills repeatedly
interrupted work; native `main-session-restart-recovery` sent the English
"continuing your interrupted request" notice after each automatic restart.
Suppressing the notice would not fix the OOM.

Recovery applied without recreating the container:

- Docker memory limit: 2 GiB -> 4 GiB; combined RAM+swap: 3 GiB -> 6 GiB.
  These settings persist in Docker across container restart. Do not recreate
  this legacy container; preserve these limits in any future migration.
- `agents.defaults.maxConcurrent=2` and
  `agents.defaults.subagents.maxConcurrent=1`, applied through native config
  patch and verified by a hot-reload receipt. The main concurrency default in
  2026.10.6 is CPU-derived and can substantially exceed member capacity.
- Separate embedding errors on `main` and `aictycatminh` were confirmed with
  `memory status --deep`: their OpenAI embedding backend had no credentials.
  Both were moved to per-agent FTS-only using `openclaw-memory-fts-only`, with
  SQLite Backup API snapshots first. `ai_catminh` already used FTS-only.
  This stops failed background embedding sync; it is not proof that embedding
  was the sole source of the Gateway's memory consumption.
- Passive guard `member_trolyketoancatminh_resource_guard` runs every five
  minutes through the shared launcher, with `ai_on_failure=false` and
  `--no-notify`. It records pressure; it does not restart the Gateway or
  guarantee prevention of host-wide resource exhaustion.

Dry-run (read-only, no delivery):

```bash
python3 /root/Automation/watchdog/shared_self_healing/scripts/check_member_resource_guard.py \
  --container user-trolyketoancatminh --member-home /home/trolyketoancatminh \
  --member-label trolyketoancatminh --account trolyketoancatminh \
  --state-file /root/Automation/watchdog/shared_self_healing/state/member_trolyketoancatminh_resource_guard.json \
  --dry-run --no-notify
```

Scheduled/manual run:

```bash
/root/Automation/watchdog/shared_self_healing/run_project.sh member_trolyketoancatminh_resource_guard
```

Output: `logs/member_trolyketoancatminh_resource_guard.log` and
`state/member_trolyketoancatminh_resource_guard.json` beneath the shared center.
No Sheet writes, API publishing, or Telegram notifications. Rerun the dry-run
for inspection or the launcher to record the latest state. The state file stores
severity/reasons; detailed metrics are in the log.

Backups: `/root/_Backups/member_vps/trolyketoancatminh/oom-recovery/20261030T051023Z`.
Before another resource update, snapshot Docker resource settings and check host
RAM headroom. Increasing `--memory-swap` is an allowance, not additional host
swap capacity. Use the following only for this diagnosed target:

```bash
docker update --memory 4g --memory-swap 6g user-trolyketoancatminh
```

Validate config patch
with `--dry-run` first and wait for the hot-reload log receipt. Do not edit tokens,
provider credentials, session SQLite, or browser profiles.

Rollback only this member's concurrency keys, Docker resource values from
`resources.before.json`, this registry entry and its marked cron block. Preserve
subsequent/unrelated edits; do not restore the whole shared registry or crontab.
For the two per-agent FTS overrides, follow the memory skill's rollback and
restore semantic search only after its embedding provider works. Keep new
session data; database snapshots are not routine rollback inputs.
Returning to the old 2 GiB limit can immediately reintroduce the OOM incident.
Acceptance: one stable Gateway PID, all three configured Telegram accounts probe
successfully, no increasing `memory.events` OOM counter, and an isolated model
smoke without `--deliver`. A probe is not proof of completed accounting work.
