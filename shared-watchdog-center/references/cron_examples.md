# Cron Examples

Server UTC, Vietnam time UTC+7:

```cron
# BEGIN ALT_SHARED_WATCHDOG
# 08:00 VN -> 01:00 UTC
0 1 * * * /root/path/shared_self_healing/run_project.sh personal_alt
# 13:00 VN -> 06:00 UTC
0 6 * * * /root/path/shared_self_healing/run_project.sh fanpage_alt
# END ALT_SHARED_WATCHDOG
```

Append safely:

```bash
tmp=$(mktemp)
crontab -l 2>/dev/null | sed '/# BEGIN ALT_SHARED_WATCHDOG/,/# END ALT_SHARED_WATCHDOG/d' > "$tmp" || true
cat >> "$tmp" <<'CRON'
# BEGIN ALT_SHARED_WATCHDOG
0 1 * * * /root/path/shared_self_healing/run_project.sh project_name
# END ALT_SHARED_WATCHDOG
CRON
crontab "$tmp"
rm -f "$tmp"
```
