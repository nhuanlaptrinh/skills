import argparse
import contextlib
import datetime
import fcntl
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import subprocess
import tempfile


SKILL_ROOT = Path(__file__).resolve().parents[1]
PLUGIN_ID = "telegram-zalo-owner-login"
LEGACY_ID = "vuhoainam-telegram-zalo-login"
START_MARKER = "<!-- telegram-zalo-owner-login:start -->"
END_MARKER = "<!-- telegram-zalo-owner-login:end -->"


def execute(arguments, log_path=None, timeout=120):
    result = subprocess.run(arguments, capture_output=True, text=True, timeout=timeout)
    if log_path:
        log_path.write_text(result.stdout + result.stderr)
        log_path.chmod(0o600)
    if result.returncode:
        raise RuntimeError(f"Command failed (exit {result.returncode}); inspect the private deployment log.")
    return result.stdout


def atomic_write(destination, content):
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(dir=destination.parent, prefix=".owner-login-")
    try:
        with os.fdopen(descriptor, "w") as handle:
            handle.write(content)
        os.chmod(temporary, 0o600)
        os.replace(temporary, destination)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def write_json(destination, value):
    atomic_write(destination, json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def owner_ids(config):
    owners = set()
    for value in config.get("commands", {}).get("ownerAllowFrom", []):
        match = re.fullmatch(r"(?:telegram:)?([1-9]\d*)", str(value))
        if match:
            owners.add(match.group(1))
    return owners


def cli_json(output, key):
    decoder = json.JSONDecoder()
    for offset, character in enumerate(output):
        if character != "{":
            continue
        try:
            value, _ = decoder.raw_decode(output[offset:])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict) and key in value:
            return value
    raise RuntimeError("Expected structured CLI validation result is missing.")


def validate_runtime(base, backup=None):
    validated = execute(base + ["openclaw", "config", "validate", "--json"], backup / "validate.log" if backup else None)
    doctor = subprocess.run(base + ["openclaw", "plugins", "doctor", "--json"], capture_output=True, text=True, timeout=120)
    if backup:
        atomic_write(backup / "doctor.log", doctor.stdout + doctor.stderr)
    if cli_json(validated, "valid").get("valid") is not True:
        raise RuntimeError("Config validation failed.")
    result = cli_json(doctor.stdout, "pluginErrors")
    diagnostics = result.get("diagnostics", [])
    known_provenance_warning = bool(diagnostics) and all(
        item.get("level") == "warn" and item.get("pluginId") == "duckduckgo"
        and item.get("message", "").startswith("OpenClaw can't verify where this plugin came from.")
        for item in diagnostics
    ) and not any(result.get(key) for key in ["pluginErrors", "sourceShadowing", "compatibility", "configurationWarnings"])
    if result.get("pluginErrors") or (not known_provenance_warning and (doctor.returncode != 0 or result.get("ok") is not True)):
        raise RuntimeError("Plugin doctor reported an error; inspect the private log.")
    if known_provenance_warning:
        if doctor.returncode not in (0, 1):
            raise RuntimeError("Plugin doctor failed unexpectedly; inspect the private log.")
        print("WARNING: existing duckduckgo provenance diagnostic; no plugin errors. Trust/config unchanged.")


def select_account(accounts, requested, label):
    if requested and requested in accounts:
        return requested
    if not requested and len(accounts) == 1:
        return next(iter(accounts))
    raise RuntimeError(f"Select one configured {label} account explicitly.")


def snapshot_database(source, destination):
    with sqlite3.connect(f"file:{source}?mode=ro", uri=True) as original:
        with sqlite3.connect(destination) as backup:
            original.backup(backup)
    destination.chmod(0o600)


def main():
    parser = argparse.ArgumentParser(description="Deploy owner-only Telegram Zalo QR login on one Docker member.")
    parser.add_argument("--member")
    parser.add_argument("--container")
    parser.add_argument("--openclaw-root")
    parser.add_argument("--runtime-home", default="/root")
    parser.add_argument("--runtime-root")
    parser.add_argument("--agent", default="main")
    parser.add_argument("--telegram-account")
    parser.add_argument("--zalo-account")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--apply", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()
    container = args.container or (f"user-{args.member}" if args.member else None)
    if not container or not re.fullmatch(r"[A-Za-z0-9_.-]+", container):
        parser.error("Provide a valid --member or --container.")
    if args.member and not re.fullmatch(r"[A-Za-z0-9_-]+", args.member):
        parser.error("Invalid member name.")
    if not args.openclaw_root and not args.member:
        parser.error("Provide --openclaw-root for a custom container.")
    root = Path(args.openclaw_root or f"/root/Apps/member_vps/docker-users/data/{args.member}/root/.openclaw")
    if not root.is_absolute() or root.resolve() != root or not (root / "openclaw.json").is_file() or (root / "openclaw.json").is_symlink():
        raise RuntimeError("State root must be an existing absolute non-symlink directory.")
    runtime_home = Path(args.runtime_home)
    runtime_root = Path(args.runtime_root or str(runtime_home / ".openclaw"))
    if not runtime_home.is_absolute() or not runtime_root.is_absolute() or ".." in runtime_root.parts or ".." in runtime_home.parts:
        raise RuntimeError("Runtime paths must be absolute without parent traversal.")
    mounts = json.loads(execute(["docker", "inspect", "-f", "{{json .Mounts}}", container]))
    mapping_ok = False
    for mount in mounts:
        try:
            relative = root.relative_to(Path(mount["Source"]))
        except ValueError:
            continue
        if Path(mount["Destination"]) / relative == runtime_root:
            mapping_ok = True
    if not mapping_ok:
        raise RuntimeError("Host state root does not map to the requested runtime root in this container.")
    config = json.loads((root / "openclaw.json").read_text())
    owners = owner_ids(config)
    if not owners:
        raise RuntimeError("No numeric Telegram owners configured; this installer does not grant owners.")
    agent = config.get("agents", {}).get("entries", {}).get(args.agent)
    if not isinstance(agent, dict):
        raise RuntimeError("Canonical keyed agent is missing; do not create a new agent to grant access.")
    channels = config.get("channels", {})
    telegram = channels.get("telegram", {})
    zalo = channels.get("zalouser", {})
    telegram_accounts = telegram.get("accounts") or {"default": telegram}
    zalo_accounts = zalo.get("accounts") or {"default": zalo}
    telegram_account = select_account(telegram_accounts, args.telegram_account, "Telegram")
    zalo_account = select_account(zalo_accounts, args.zalo_account, "Zalo")
    for channel, account in [("telegram", telegram_account), ("zalouser", zalo_account)]:
        routes = {entry.get("agentId") for entry in config.get("bindings", [])
                  if entry.get("match", {}).get("channel") == channel
                  and entry.get("match", {}).get("accountId") == account}
        if routes != {args.agent}:
            raise RuntimeError(f"Selected {channel} account must already belong only to the selected agent.")
    workspace_runtime = Path(agent.get("workspace") or config.get("agents", {}).get("defaults", {}).get("workspace", ""))
    try:
        workspace = root / workspace_runtime.relative_to(runtime_root)
    except ValueError as error:
        raise RuntimeError("Supported workspace must be inside this runtime state root.") from error
    if workspace.resolve() != workspace or not workspace.is_dir():
        raise RuntimeError("Workspace is missing or symlinked.")
    base = ["docker", "exec", "-e", f"HOME={runtime_home}", "-e", f"OPENCLAW_STATE_DIR={runtime_root}",
            "-e", f"OPENCLAW_CONFIG_PATH={runtime_root}/openclaw.json", "-e", "OPENCLAW_PROFILE=", container]
    version = execute(base + ["openclaw", "--version"])
    if not re.search(r"\b2026\.9\.9\b", version):
        raise RuntimeError("Only exact tested OpenClaw 2026.9.9 is supported; validate SDK/CLI before porting.")
    supervisor = execute(base + ["supervisorctl", "status", "openclaw-gateway"])
    was_running = "RUNNING" in supervisor
    plugin_id = LEGACY_ID if LEGACY_ID in config.get("plugins", {}).get("entries", {}) else PLUGIN_ID
    plugin_directory = root / "tools" / ("telegram-zalo-login" if plugin_id == LEGACY_ID else PLUGIN_ID)
    if plugin_directory.resolve() != plugin_directory:
        raise RuntimeError("Plugin directory must not be symlinked.")
    settings = {"pluginId": plugin_id, "telegramAccount": telegram_account, "zaloAccount": zalo_account,
                "agentId": args.agent, "runtimeHome": str(runtime_home), "runtimeRoot": str(runtime_root)}
    runtime_directory = runtime_root / plugin_directory.relative_to(root)
    print(f"Target={container}; agent={args.agent}; configured Telegram owners={len(owners)}; plugin={plugin_id}")
    if args.dry_run:
        print("DRY RUN: mapped roots/accounts verified; no config/owner change, login or delivery.")
        return
    runtime_skill = workspace / "skills" / PLUGIN_ID / "SKILL.md"
    instructions = workspace / "AGENTS.md"
    if args.check:
        if json.loads((plugin_directory / "settings.json").read_text()) != settings:
            raise RuntimeError("Deployed settings differ from the selected runtime.")
        if (plugin_directory / "index.mjs").read_bytes() != (SKILL_ROOT / "assets" / "index.mjs").read_bytes():
            raise RuntimeError("Deployed plugin differs from skill asset.")
        if not config.get("plugins", {}).get("entries", {}).get(plugin_id, {}).get("enabled"):
            raise RuntimeError("Plugin not enabled.")
        if not runtime_skill.is_file() or START_MARKER not in instructions.read_text():
            raise RuntimeError("Runtime skill or managed guidance missing.")
        validate_runtime(base)
        print("CHECK PASS: deployed payload/settings, guidance, config and plugin doctor. No login/send.")
        return
    backup = Path("/root/_Backups/telegram-zalo-owner-login") / container / datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    backup.mkdir(parents=True, mode=0o700)
    affected = [root / "openclaw.json", instructions, runtime_skill] + [plugin_directory / name for name in
                ["index.mjs", "settings.json", "package.json", "openclaw.plugin.json"]]
    for destination in affected:
        if destination.is_symlink():
            raise RuntimeError("Refusing symlinked affected file.")
    with contextlib.ExitStack() as locks:
        label = args.member or container.removeprefix("user-")
        for name in [f"telegram-zalo-owner-login-{container}", f"member_{label}_gateway_supervisor",
                     f"member_{label}_zalouser", f"member_{label}_zalo_delivery"]:
            handle = locks.enter_context(open(f"/tmp/{name}.lock", "a"))
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        originals = {}
        for destination in affected:
            originals[destination] = destination.read_text() if destination.is_file() else None
            if destination.is_file():
                saved = backup / destination.relative_to(root)
                saved.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(destination, saved)
                saved.chmod(0o600)
        stopped = False
        state = root / "state" / "openclaw.sqlite"
        if state.resolve() != state:
            raise RuntimeError("Native state database must not be symlinked.")
        try:
            if was_running:
                execute(base + ["supervisorctl", "stop", "openclaw-gateway"], backup / "stop.log")
                stopped = True
            if state.is_file():
                snapshot_database(state, backup / "state-before.sqlite")
            write_json(plugin_directory / "settings.json", settings)
            atomic_write(plugin_directory / "index.mjs", (SKILL_ROOT / "assets" / "index.mjs").read_text())
            write_json(plugin_directory / "package.json", {"name": plugin_id, "version": "1.1.0", "type": "module",
                "files": ["index.mjs", "settings.json", "openclaw.plugin.json"],
                "openclaw": {"extensions": ["./index.mjs"], "compat": {"pluginApi": "2026.9.9", "minGatewayVersion": "2026.9.9"}}})
            write_json(plugin_directory / "openclaw.plugin.json", {"id": plugin_id, "name": "Telegram Owner Zalo QR Login",
                "description": "Private Zalo QR login for every configured Telegram owner.", "categories": ["other"],
                "activation": {"onStartup": True}, "contracts": {"tools": ["telegram_zalo_login_qr"]},
                "configSchema": {"type": "object", "additionalProperties": False, "properties": {}}})
            atomic_write(runtime_skill, (SKILL_ROOT / "references" / "runtime-SKILL.md").read_text())
            managed = START_MARKER + "\n## Telegram Zalo Owner QR Login\n\n" + (
                "This section supersedes earlier owner-specific QR instructions. For any existing Telegram owner in this bot's private chat, "
                "use `telegram_zalo_login_qr` with `confirm: true` only when explicitly asked to create a Zalo login QR. "
                "The plugin dynamically verifies ownership, sends the image only to the requesting owner, checks the receipt and waits up to 180 seconds. "
                "All configured owners may also use `/zaloqr` directly. Read the `telegram-zalo-owner-login` skill. "
                "Do not use generic exec for interactive login, broadcast QR, send it to groups, delete locks/credentials blindly, "
                "or claim listener connectivity from CLI login completion alone.\n") + END_MARKER
            old_instructions = originals[instructions] or ""
            if START_MARKER in old_instructions:
                if END_MARKER not in old_instructions:
                    raise RuntimeError("Managed guidance has an incomplete marker; manual review required.")
                updated = re.sub(re.escape(START_MARKER) + r".*?" + re.escape(END_MARKER), lambda match: managed, old_instructions, flags=re.S)
            else:
                updated = old_instructions.rstrip() + "\n\n" + managed + "\n"
            atomic_write(instructions, updated)
            execute(base + ["node", "--check", str(runtime_directory / "index.mjs")], backup / "syntax.log")
            execute(base + ["openclaw", "plugins", "install", "--link", str(runtime_directory), "--force", "--accept-capabilities"], backup / "install.log")
            validate_runtime(base, backup)
            if was_running:
                execute(base + ["supervisorctl", "start", "openclaw-gateway"], backup / "start.log")
                stopped = False
            write_json(backup / "result.json", {"container": container, "pluginId": plugin_id, "ownerCount": len(owners), "applied": True})
            print(f"APPLIED: all {len(owners)} configured Telegram owners; requester-only QR delivery. Backup={backup}")
        except Exception:
            if was_running and not stopped:
                execute(base + ["supervisorctl", "stop", "openclaw-gateway"], backup / "rollback-stop.log")
                stopped = True
            for destination, content in originals.items():
                if content is None:
                    destination.unlink(missing_ok=True)
                else:
                    atomic_write(destination, content)
            if (backup / "state-before.sqlite").is_file():
                with sqlite3.connect(backup / "state-before.sqlite") as original:
                    with sqlite3.connect(state) as current:
                        original.backup(current)
            if was_running and stopped:
                execute(base + ["supervisorctl", "start", "openclaw-gateway"], backup / "rollback-start.log")
            raise


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        raise SystemExit(f"Deployment stopped: {type(error).__name__}: {error}")
