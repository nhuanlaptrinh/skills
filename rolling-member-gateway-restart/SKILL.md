---
name: rolling-member-gateway-restart
description: Lên lịch và vận hành restart tuần tự OpenClaw Gateway trong các VPS thành viên có swap cao, có kiểm tra Telegram/Zalo và dừng batch khi trạng thái suy giảm.
---

# Rolling Member Gateway Restart

Dùng khi host có nhiều container member OpenClaw bị swap cao và cần làm sạch
trang bộ nhớ theo từng Gateway. Pipeline chỉ restart process
`openclaw-gateway` dưới Supervisor bên trong member; không restart/recreate
Docker container và không đụng SSH, nginx, XRDP, sidecar, credential,
workspace, transcript hoặc `.env`.

## Files

- Script: `/root/Automation/watchdog/rolling_member_restart/rolling_member_gateway_restart.py`
- Tests: `/root/Automation/watchdog/rolling_member_restart/test_rolling_member_gateway_restart.py`
- Log: `/root/Automation/watchdog/rolling_member_restart/rolling_member_gateway_restart.jsonl`
- State: `/root/Automation/watchdog/rolling_member_restart/state/last_run.json`
- Lock: `/root/Automation/watchdog/rolling_member_restart/rolling_member_gateway_restart.lock`
- Cron backup: `/root/_Backups/rolling-member-gateway-restart/`
- Cron stdout/stderr: `/root/Automation/watchdog/rolling_member_restart/cron.log`

## Schedule

Cron runs daily at `20:50 UTC` (`03:50 Asia/Ho_Chi_Minh`). The script allows
the maintenance only on the anchored local dates 19/11/2026, 22/11, 25/11,
28/11, 01/12, and every three days thereafter. This avoids the day-of-month
reset that `*/3` would have at some month boundaries.

The current scheduled entry is:

```cron
# rolling_member_gateway_restart: every 3 days at 03:50 Asia/Ho_Chi_Minh
50 20 * * * /usr/bin/env XDG_RUNTIME_DIR=/run/user/0 DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/0/bus /usr/bin/python3 /root/Automation/watchdog/rolling_member_restart/rolling_member_gateway_restart.py --scheduled >> /root/Automation/watchdog/rolling_member_restart/cron.log 2>&1
```

## Dry run and execution

List the current high-swap scope without probing or restarting:

```bash
/usr/bin/python3 /root/Automation/watchdog/rolling_member_restart/rolling_member_gateway_restart.py --dry-run
```

Run a maintenance batch manually (explicit operator action; bypasses the
calendar gate):

```bash
/usr/bin/python3 /root/Automation/watchdog/rolling_member_restart/rolling_member_gateway_restart.py --run
```

Probe one member without restarting it:

```bash
/usr/bin/python3 /root/Automation/watchdog/rolling_member_restart/rolling_member_gateway_restart.py --probe-member user-avata
```

Validate the offline safety tests:

```bash
/usr/bin/python3 -m unittest discover -s /root/Automation/watchdog/rolling_member_restart -p 'test_*.py' -v
```

## Selection and verification

The threshold is 700 MiB of `memory.swap.current`; stopped containers are
never started. The authorized current scope is recorded in the script. Before
each member restart the pipeline checks Supervisor, a no-recent-session
activity guard, the member's channel status, and host Gateway/9Router health.
After restarting, it waits for one Gateway process, probes configured
Telegram and Zalo accounts twice, and checks the host Gateway PID and local
9Router health again. A pre-existing unlinked or disconnected Zalo account is
recorded and preserved; a previously healthy account must remain healthy.

The next restart happens only after the previous restarted member passes the
checks. A restart, probe, or host-health failure stops the batch. A member with
session activity within ten minutes, a recent session lock, a busy watchdog
lock, or no running Gateway is skipped without starting or stopping it. An
unlinked Zalo account is not reported healthy. No real Telegram or Zalo
message is sent. The batch starts only between 03:50 and 04:05 local time on
an eligible date and starts no further member after 90 minutes.

The 12-member allowlist is explicit in `MEMBERS`; it excludes the invoice
application member `phukiengiakho`, stopped members, the host Gateway,
9Router/proxy, websites and future members. At runtime, even an allowed
member is selected only if it is running and still has at least 700 MiB swap.
This releases the Gateway's swapped pages; remaining swapped pages belonging
to other processes are retained.

## Safety and rollback

- Do not use `docker restart`, `docker rm`, `docker compose down`, `swapoff`,
  cache dropping, or process kills as part of this pipeline.
- Do not bypass the health checks to continue a failed batch.
- Before changing the cron entry, back up the root crontab under
  `/root/_Backups/rolling-member-gateway-restart/` and preserve unrelated jobs.
- To disable the schedule, remove only the marked cron line after backing up
  the crontab. A Gateway process can be restored manually with the member's
  existing Supervisor configuration; the pipeline does not alter that config.
- Review the JSONL log and `last_run.json` after each scheduled window. Logs
  contain status and counts only and must never contain tokens, cookies,
  passwords, prompts, or raw channel output.
