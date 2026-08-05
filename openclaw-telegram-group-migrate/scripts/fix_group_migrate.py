#!/usr/bin/env python3
import argparse, json, os, re, shutil, subprocess, sys
from datetime import datetime, timezone

MIGRATE_RE = re.compile(r'(?:Group migrated:.*?|Migrating group config from\s+)(-\d+)\s*(?:→|->|to)\s*(-\d+)')
GROUP_RE = re.compile(r'telegram:group:(-?\d+)')

def run_logs(since):
    cmd = ['journalctl','--user','-u','openclaw-gateway.service','--since',since,'--no-pager','-o','cat']
    try:
        return subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL)
    except Exception:
        return ''

def load_config(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_config(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write('\n')

def main():
    ap = argparse.ArgumentParser(description='Detect and fix OpenClaw Telegram group migration requireMention rules.')
    ap.add_argument('--config', default='/root/.openclaw/openclaw.json')
    ap.add_argument('--group-id', required=True, help='Old or current Telegram group id')
    ap.add_argument('--since', default='7 days ago')
    ap.add_argument('--apply', action='store_true', help='Write config; otherwise dry-run')
    ap.add_argument('--backup-dir', default='/root/_Backups/openclaw')
    args = ap.parse_args()

    config = load_config(args.config)
    telegram = config.setdefault('channels', {}).setdefault('telegram', {})
    groups = telegram.setdefault('groups', {})
    logs = run_logs(args.since)

    target_ids = {args.group_id}
    migrations = []
    for old, new in MIGRATE_RE.findall(logs):
        if old == args.group_id or new == args.group_id or old in target_ids:
            target_ids.add(old); target_ids.add(new); migrations.append((old, new))

    inbound_seen = sorted(set(GROUP_RE.findall(logs)))
    configured = {gid: groups.get(gid) for gid in sorted(target_ids) if gid in groups}
    missing = [gid for gid in sorted(target_ids) if groups.get(gid, {}).get('requireMention') is not False]

    print('CONFIG', args.config)
    print('GROUP_INPUT', args.group_id)
    print('MIGRATIONS', migrations or 'none')
    print('TARGET_IDS', sorted(target_ids))
    print('CONFIGURED', configured or 'none')
    print('MISSING_REQUIRE_MENTION_FALSE', missing or 'none')
    print('INBOUND_GROUP_IDS_RECENT', inbound_seen[-20:] if inbound_seen else 'none')

    if not missing:
        return 0
    if not args.apply:
        print('DRY_RUN: add --apply to update config and backup first')
        return 2

    os.makedirs(args.backup_dir, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
    backup = os.path.join(args.backup_dir, f'openclaw.json.{stamp}.bak')
    shutil.copy2(args.config, backup)
    groups.setdefault('*', {'requireMention': True})
    for gid in missing:
        groups[gid] = {'requireMention': False}
    save_config(args.config, config)
    load_config(args.config)
    print('UPDATED', args.config)
    print('BACKUP', backup)
    print('NEXT: wait 2-5 seconds then check journalctl for config hot reload applied')
    return 0

if __name__ == '__main__':
    sys.exit(main())
