# Member Gateway Recovery

Use this branch when both Telegram and Zalo stop, `openclaw-gateway` is absent,
port 18789 disappears, the member proxy returns 502, or the process does not
survive a container restart.

## Diagnose The Process Manager

1. Confirm the container is running.
2. Identify the Gateway PID and parent process.
3. Inspect the active Supervisor config and the persistent entrypoint that
   regenerates it.
4. Confirm the member HOME and existing owner of the `.openclaw` tree.
5. Never start another Gateway while one is already live.

## Back Up Before Apply

Preserve the active/persistent Supervisor files, `openclaw.json`, session index,
watchdog registry, cron, and member project note in a root-only timestamped
backup. Do not place secrets in documentation or terminal output.

## Restore Persistent Supervisor Management

Add the same `[program:openclaw-gateway]` block to both:

- `/etc/supervisor/conf.d/member-vps.conf`
- `/usr/local/bin/member-vps-entrypoint.sh`

Use the exact member HOME and current data owner. The standard behavior is:

```ini
[program:openclaw-gateway]
command=/usr/bin/openclaw gateway run
environment=HOME="<member-home>"
user=<existing-data-owner>
autorestart=true
startsecs=5
startretries=20
stopsignal=TERM
stopasgroup=true
killasgroup=true
stdout_logfile=/tmp/openclaw-supervisor.log
stderr_logfile=/tmp/openclaw-supervisor.log
stdout_logfile_maxbytes=10MB
stdout_logfile_backups=3
```

Validate a staged entrypoint with `bash -n` and the staged Supervisor config
before applying. Reload Supervisor once, then require exactly one Gateway whose
parent is Supervisor/PID 1. Do not recreate the container.

Testing recovery by terminating only the Gateway PID is fault injection; do it
only with explicit owner authorization. Passive verification is the default.

## Recover A Persistently Stuck Session

After the Gateway is healthy, run session maintenance. If a backed-up idle
session remains broken after summary compaction, freeze/stop only the Gateway,
remove exactly that key from `sessions.json`, preserve its transcript, and let
Supervisor create one fresh process. Never clear the whole session store.

When missing or drifted Supervisor configuration caused the incident, install
the host-side guard described in
[supervisor-watchdog.md](supervisor-watchdog.md).
