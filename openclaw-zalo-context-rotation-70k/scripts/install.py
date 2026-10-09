#!/usr/bin/env python3
"""Install one member's Zalo context rotation; default is read-only dry-run."""

import argparse
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path, PurePosixPath
import re
import shlex
import sqlite3
import subprocess
import sys
import tempfile


SCRIPTS = Path(__file__).resolve().parent


def execute(command, **kwargs):
    try:
        return subprocess.run(command, capture_output=True, text=True, timeout=90, **kwargs)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError("required command unavailable or timed out") from exc


def crontab():
    result = execute(["crontab", "-l"])
    if result.returncode == 1 and "no crontab" in result.stderr.lower():
        return ""
    if result.returncode:
        raise RuntimeError("cannot read existing crontab")
    return result.stdout


def arguments():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--container", required=True)
    parser.add_argument("--member-label", required=True)
    parser.add_argument("--member-home", required=True)
    parser.add_argument("--member-data-dir", type=Path, required=True)
    parser.add_argument("--agent", default="main")
    parser.add_argument("--threshold", type=int, default=70000)
    parser.add_argument("--idle-seconds", type=int, default=180)
    parser.add_argument("--center-dir", type=Path, default=Path("/root/Automation/watchdog/shared_self_healing"))
    parser.add_argument("--backup-root", type=Path, default=Path("/root/_Backups"))
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    for value in (args.container, args.member_label, args.agent):
        if not re.fullmatch(r"[a-zA-Z0-9_-]+", value):
            parser.error("container, member label and agent must be safe identifiers")
    if args.threshold <= 0 or args.idle_seconds < 180:
        parser.error("threshold must be positive; idle must be >= 180 seconds")
    for path in (args.member_data_dir, args.center_dir, args.backup_root, Path(args.member_home)):
        if not path.is_absolute() or "\n" in str(path) or "\r" in str(path):
            parser.error("paths must be absolute and single-line")
    if any(character in str(args.center_dir) for character in " \t%"):
        parser.error("center path must be cron-safe (no whitespace or percent)")
    return args


def verify_target(args):
    config = args.member_data_dir / ".openclaw/openclaw.json"
    database = args.member_data_dir / ".openclaw/state/openclaw.sqlite"
    if not config.is_file() or not database.is_file():
        raise RuntimeError("member-data-dir must directly contain .openclaw config and state/openclaw.sqlite")
    result = execute(["docker", "inspect", "--format", '{"running":{{.State.Running}},"mounts":{{json .Mounts}}}', args.container])
    if result.returncode:
        raise RuntimeError("container inspection failed")
    metadata = json.loads(result.stdout)
    if not metadata.get("running"):
        raise RuntimeError("container is not running")
    internal = PurePosixPath(args.member_home) / ".openclaw/openclaw.json"
    mounts = [mount for mount in metadata["mounts"] if internal.is_relative_to(PurePosixPath(mount["Destination"]))]
    if not mounts:
        raise RuntimeError("active member HOME has no verifiable host mount")
    mount = max(mounts, key=lambda item: len(item["Destination"]))
    expected = Path(mount["Source"]) / str(internal.relative_to(PurePosixPath(mount["Destination"])))
    if expected.resolve() != config.resolve():
        raise RuntimeError("host member data does not match container HOME mount")
    command = [sys.executable, str(SCRIPTS / "rotate_zalo_sessions.py"),
               "--container", args.container, "--member-home", args.member_home,
               "--agent", args.agent, "--threshold", str(args.threshold),
               "--active-window-seconds", str(args.idle_seconds), "--dry-run"]
    result = execute(command)
    if result.returncode:
        raise RuntimeError("Gateway read-only rotation preflight failed")
    print(result.stdout.strip())


def read_registry(path):
    data = json.loads(path.read_text()) if path.exists() else {}
    if not isinstance(data, dict):
        raise RuntimeError("invalid watchdog registry")
    return data


def option(command, name):
    tokens = shlex.split(command)
    if name not in tokens:
        return None
    index = tokens.index(name) + 1
    if index >= len(tokens):
        raise RuntimeError("invalid existing registry command")
    return tokens[index]


def make_plan(args, registry, cron):
    key = f"member_{args.member_label}_sessions"
    prefix = f"agent:{args.agent}:zalouser:"
    for existing_key, entry in registry.items():
        if not isinstance(entry, dict):
            raise RuntimeError("invalid existing registry entry")
        command = entry.get("run_command", "")
        if existing_key == key:
            if option(command, "--container") != args.container or option(command, "--key-prefix") != prefix:
                raise RuntimeError("project key already belongs to another scope")
        elif option(command, "--container") == args.container and option(command, "--key-prefix") == prefix:
            raise RuntimeError("another rotation job already covers this member; review before installing")
    runtime = args.center_dir / "scripts/rotate_zalo_sessions_70k.py"
    if runtime.exists() and runtime.read_bytes() != (SCRIPTS / "rotate_zalo_sessions.py").read_bytes():
        raise RuntimeError("installed shared runtime differs; review upgrade rather than overwriting other members")
    command = shlex.join([sys.executable, str(runtime), "--container", args.container,
                         "--member-home", args.member_home, "--agent", args.agent,
                         "--key-prefix", prefix, "--threshold", str(args.threshold),
                         "--active-window-seconds", str(args.idle_seconds),
                         "--state-dir", str(args.center_dir / "state"), "--max-resets-per-run", "1"])
    updated = dict(registry)
    updated[key] = {
        "project_root": str(args.center_dir), "run_command": command,
        "log_file": str(args.center_dir / f"logs/{key}.log"),
        "lock_file": str(args.center_dir / f"state/{key}.lock"),
        "type": "openclaw_session", "ai_on_failure": False,
    }
    marker = f"member_{args.member_label}_sessions_70k"
    begin, end = f"# BEGIN {marker}", f"# END {marker}"
    lines = cron.splitlines()
    if lines.count(begin) != lines.count(end) or lines.count(begin) > 1:
        raise RuntimeError("ambiguous cron marker")
    if begin in lines:
        start, finish = lines.index(begin), lines.index(end)
        if finish <= start:
            raise RuntimeError("invalid cron marker order")
        outside = lines[:start] + lines[finish + 1:]
        expected = f"* * * * * {shlex.quote(str(args.center_dir / 'run_project.sh'))} {key}"
        if lines[start + 1:finish] != [expected]:
            raise RuntimeError("existing cron block differs; review it before replacement")
    else:
        outside = lines
    if any(not line.lstrip().startswith("#") and re.search(r"(?<!\S)" + re.escape(key) + r"(?!\S)", line) for line in outside):
        raise RuntimeError("rotation is scheduled outside its marker; resolve duplicate first")
    block = [begin, f"* * * * * {shlex.quote(str(args.center_dir / 'run_project.sh'))} {key}", end]
    if begin not in lines:
        lines.extend(block)
    return key, updated, "\n".join(lines) + "\n"


def atomic_write(path, content, mode=0o600):
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(dir=path.parent, prefix=".rotation-")
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(name, mode)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def apply_plan(args, path, key, registry, cron, previous_cron, previous_registry=None):
    if previous_registry is not None and read_registry(path) != previous_registry:
        raise RuntimeError("registry changed before apply; inspect before retry")
    registry_before = path.read_bytes() if path.exists() else None
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    backup = args.backup_root / f"{key}-70k" / stamp
    backup.mkdir(parents=True, mode=0o700)
    print(f"backup={backup}", flush=True)
    atomic_write(backup / "crontab.before", previous_cron.encode())
    if path.exists():
        atomic_write(backup / "project_config.json.before", path.read_bytes())
    else:
        atomic_write(backup / "registry-was-absent", b"\n")
    atomic_write(backup / "openclaw.json", (args.member_data_dir / ".openclaw/openclaw.json").read_bytes())
    source = args.member_data_dir / ".openclaw/state/openclaw.sqlite"
    with sqlite3.connect(source.resolve().as_uri() + "?mode=ro", uri=True) as database:
        with sqlite3.connect(backup / "openclaw.sqlite") as destination:
            database.backup(destination)
    (backup / "openclaw.sqlite").chmod(0o600)
    launcher = args.center_dir / "run_project.sh"
    if not launcher.exists():
        atomic_write(launcher, (SCRIPTS / "run_project.sh").read_bytes(), 0o750)
    elif not launcher.is_file() or not os.access(launcher, os.X_OK):
        raise RuntimeError("existing shared launcher is not executable")
    atomic_write(args.center_dir / "scripts/rotate_zalo_sessions_70k.py", (SCRIPTS / "rotate_zalo_sessions.py").read_bytes(), 0o750)
    if (path.read_bytes() if path.exists() else None) != registry_before:
        raise RuntimeError("registry changed concurrently; inspect before retry")
    if crontab() != previous_cron:
        raise RuntimeError("crontab changed concurrently; inspect backup and registry before retry")
    atomic_write(path, (json.dumps(registry, ensure_ascii=False, indent=2) + "\n").encode())
    if cron != previous_cron and execute(["crontab", "-"], input=cron).returncode:
        raise RuntimeError("cron installation failed; inspect backup and registry before retry")
    if crontab() != cron:
        raise RuntimeError("cron readback differs; inspect before retry")
    print(f"installed={key} schedule=every_minute threshold={args.threshold} reset_limit=1")


def main():
    args = arguments()
    verify_target(args)
    path = args.center_dir / "project_config.json"
    if not args.apply:
        key, unused_registry, unused_cron = make_plan(args, read_registry(path), crontab())
        print(f"mode=dry-run project={key} threshold={args.threshold} writes=none")
        return 0
    if os.geteuid() != 0:
        raise RuntimeError("apply requires root for host cron, private backups and Docker")
    os.umask(0o077)
    args.center_dir.mkdir(parents=True, exist_ok=True)
    with (args.center_dir / ".zalo-rotation-install.lock").open("a") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        registry = read_registry(path)
        cron = crontab()
        key, updated, scheduled = make_plan(args, registry, cron)
        apply_plan(args, path, key, updated, scheduled, cron, registry)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        print(f"installation_failed: {exc}; review any printed backup path before retry", file=sys.stderr)
        raise SystemExit(1)
    except (ValueError, OSError, sqlite3.Error):
        print("installation_failed: malformed metadata, file access or backup failure; inspect any printed backup before retry", file=sys.stderr)
        raise SystemExit(1)
