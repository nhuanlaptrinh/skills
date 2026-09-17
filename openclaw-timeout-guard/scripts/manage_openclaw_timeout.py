#!/usr/bin/env python3
"""Safely inspect, update, validate, and reload timeoutSeconds in OpenClaw.

Supports:
- Member VPS containers under /root/Apps/member_vps/docker-users/data/<member>
- Local/Host OpenClaw at /root/.openclaw/openclaw.json
- Arbitrary custom openclaw.json on any VPS

Features:
- Dry-run by default
- Automatic backup to /root/_Backups/openclaw-timeout-guard/<target>/<timestamp>
- Atomic JSON write preserving file permissions
- Config validation (openclaw config validate)
- Controlled Gateway reload (supervisorctl or systemd)
- Isolated no-delivery smoke test
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_TIMEOUT_SECONDS = 180
DEFAULT_BACKUP_ROOT = Path("/root/_Backups/openclaw-timeout-guard")
MEMBERS_BASE_DIR = Path("/root/Apps/member_vps/docker-users/data")


def find_openclaw_json(member_dir: Path) -> Path | None:
    candidates = [
        member_dir / "root" / ".openclaw" / "openclaw.json",
        member_dir / ".openclaw" / "openclaw.json",
    ]
    # Check /home/*/.openclaw/openclaw.json
    home_dir = member_dir / "home"
    if home_dir.is_dir():
        for sub in home_dir.iterdir():
            if sub.is_dir():
                candidates.append(sub / ".openclaw" / "openclaw.json")

    for cand in candidates:
        if cand.is_file():
            return cand
    return None


def discover_all_members() -> list[tuple[str, Path, Path]]:
    results = []
    if not MEMBERS_BASE_DIR.is_dir():
        return results
    for entry in sorted(MEMBERS_BASE_DIR.iterdir()):
        if entry.is_dir():
            cfg = find_openclaw_json(entry)
            if cfg:
                results.append((entry.name, entry, cfg))
    return results


def write_json_atomic(path: Path, data: dict) -> None:
    mode = path.stat().st_mode & 0o777
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(tmp_name, mode)
        os.replace(tmp_name, path)
    finally:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)


def create_backup(cfg_path: Path, target_name: str, backup_root: Path) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dest_dir = backup_root / target_name / stamp
    dest_dir.mkdir(parents=True, exist_ok=True)
    backup_file = dest_dir / "openclaw.json.before"
    shutil.copy2(cfg_path, backup_file)
    return backup_file


def inspect_config(cfg_path: Path) -> dict:
    with open(cfg_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    agents = data.get("agents", {})
    defaults = agents.get("defaults", {})
    current_timeout = defaults.get("timeoutSeconds")
    
    entries = agents.get("entries", {})
    agent_overrides = {}
    for aid, aconf in entries.items():
        if isinstance(aconf, dict) and "timeoutSeconds" in aconf:
            agent_overrides[aid] = aconf["timeoutSeconds"]

    return {
        "path": str(cfg_path),
        "timeoutSeconds": current_timeout,
        "is_default": current_timeout is None,
        "effective_timeout": current_timeout if current_timeout is not None else 30,
        "agent_overrides": agent_overrides,
    }


def update_timeout(cfg_path: Path, target_timeout: int) -> tuple[bool, int | None, int]:
    with open(cfg_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    agents = data.setdefault("agents", {})
    defaults = agents.setdefault("defaults", {})
    old_val = defaults.get("timeoutSeconds")

    if old_val == target_timeout:
        return False, old_val, target_timeout

    defaults["timeoutSeconds"] = target_timeout
    write_json_atomic(cfg_path, data)
    return True, old_val, target_timeout


def run_container_command(container: str, cmd: str) -> tuple[int, str]:
    full_cmd = ["docker", "exec", container, "sh", "-lc", cmd]
    res = subprocess.run(full_cmd, capture_output=True, text=True)
    out = (res.stdout + "\n" + res.stderr).strip()
    return res.returncode, out


def run_local_command(cmd: str) -> tuple[int, str]:
    res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    out = (res.stdout + "\n" + res.stderr).strip()
    return res.returncode, out


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Safely inspect and update timeoutSeconds in OpenClaw config."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--member", help="Member directory name (e.g. tranvanminh) or 'all'")
    group.add_argument("--config", help="Direct path to openclaw.json")

    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT_SECONDS,
        help=f"Target timeout in seconds (default: {DEFAULT_TIMEOUT_SECONDS})",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check/audit timeout without making changes",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply changes (without this flag, runs in dry-run mode)",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Run openclaw config validate after apply",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Reload Gateway after apply",
    )
    parser.add_argument(
        "--smoke-test",
        action="store_true",
        help="Run an isolated no-delivery smoke test",
    )
    parser.add_argument(
        "--backup-root",
        type=Path,
        default=DEFAULT_BACKUP_ROOT,
        help="Root directory for backups",
    )

    args = parser.parse_args()

    targets: list[tuple[str, Path, str | None]] = []

    if args.member:
        if args.member.lower() == "all":
            all_m = discover_all_members()
            for name, m_dir, cfg in all_m:
                targets.append((name, cfg, f"user-{name}"))
        else:
            m_dir = MEMBERS_BASE_DIR / args.member
            if not m_dir.is_dir():
                print(f"[ERROR] Member directory not found: {m_dir}", file=sys.stderr)
                return 1
            cfg = find_openclaw_json(m_dir)
            if not cfg:
                print(f"[ERROR] openclaw.json not found in {m_dir}", file=sys.stderr)
                return 1
            targets.append((args.member, cfg, f"user-{args.member}"))
    else:
        cfg = Path(args.config).resolve()
        if not cfg.is_file():
            print(f"[ERROR] Config file not found: {cfg}", file=sys.stderr)
            return 1
        targets.append((cfg.stem, cfg, None))

    print(f"Loaded {len(targets)} target(s). Target timeout: {args.timeout}s.\n")

    for name, cfg_path, container in targets:
        info = inspect_config(cfg_path)
        current_t = info["timeoutSeconds"]
        eff_t = info["effective_timeout"]
        is_def = info["is_default"]

        status_str = f"{current_t}s" if not is_def else "UNSET (default 30s)"
        print(f"Target: {name}")
        print(f"  Path: {cfg_path}")
        print(f"  Current timeoutSeconds: {status_str} (effective: {eff_t}s)")
        if info["agent_overrides"]:
            print(f"  Agent overrides: {info['agent_overrides']}")

        if args.check:
            print("  [CHECK MODE] No changes requested.\n")
            continue

        if current_t == args.timeout:
            print(f"  [OK] Already configured to {args.timeout}s. No update needed.\n")
            continue

        if not args.apply:
            print(f"  [DRY-RUN] Would update timeoutSeconds: {status_str} -> {args.timeout}s")
            print("  [DRY-RUN] Pass --apply to commit changes.\n")
            continue

        # APPLY
        backup_file = create_backup(cfg_path, name, args.backup_root)
        print(f"  [BACKUP] Saved to {backup_file}")

        changed, old_v, new_v = update_timeout(cfg_path, args.timeout)
        print(f"  [APPLY] Updated agents.defaults.timeoutSeconds: {old_v} -> {new_v}")

        # VALIDATE
        if args.validate or args.reload:
            if container:
                code, out = run_container_command(container, "openclaw config validate")
            else:
                code, out = run_local_command("openclaw config validate")
            if code == 0:
                print(f"  [VALIDATE] Config valid.")
            else:
                print(f"  [VALIDATE ERROR] Code {code}: {out}", file=sys.stderr)

        # RELOAD
        if args.reload:
            if container:
                code, out = run_container_command(container, "supervisorctl restart openclaw-gateway")
            else:
                code, out = run_local_command("systemctl --user restart openclaw-gateway")
            if code == 0:
                print(f"  [RELOAD] Gateway restarted successfully.")
            else:
                print(f"  [RELOAD ERROR] Code {code}: {out}", file=sys.stderr)

        # SMOKE TEST
        if args.smoke_test:
            smoke_cmd = (
                "openclaw agent --agent main --session-key agent:main:timeout-smoke "
                f"--message 'Reply OK' --thinking off --timeout {args.timeout} --json"
            )
            if container:
                code, out = run_container_command(container, smoke_cmd)
            else:
                code, out = run_local_command(smoke_cmd)
            if code == 0:
                print(f"  [SMOKE TEST] OK.")
            else:
                print(f"  [SMOKE TEST ERROR] Code {code}: {out}", file=sys.stderr)

        print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
