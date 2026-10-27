"""Install the owner QR tool in one existing native instance; never manage services."""

import argparse
import datetime
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

from deploy import package_metadata, supported_core_version, validate_loaded_plugin


SKILL_ROOT = Path(__file__).resolve().parents[1]
PLUGIN_ID = "telegram-zalo-owner-login"


def write_json(destination, document):
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(dir=destination.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(document, stream, ensure_ascii=False, indent=2)
        os.chmod(temporary, 0o600)
        os.replace(temporary, destination)
    finally:
        Path(temporary).unlink(missing_ok=True)


def selected_settings(config, root, home, node, cli_entry, telegram_account, zalo_account, agent):
    owners = config.get("commands", {}).get("ownerAllowFrom", [])
    if not any(re.fullmatch(r"(?:telegram:)?[1-9][0-9]*", str(owner)) for owner in owners):
        raise ValueError("No numeric Telegram owner; do not infer ownership from public access")
    if "vuhoainam-telegram-zalo-login" in config.get("plugins", {}).get("entries", {}):
        raise ValueError("Legacy QR command exists; migrate it explicitly to avoid duplicate registration")
    if agent not in config.get("agents", {}).get("entries", {}):
        raise ValueError("Selected agent does not exist")
    for channel, account in (("telegram", telegram_account), ("zalouser", zalo_account)):
        provider = config.get("channels", {}).get(channel, {})
        accounts = provider.get("accounts") or {"default": provider}
        if not provider or account not in accounts or accounts[account].get("enabled") is False:
            raise ValueError("Selected channel account is missing or disabled")
        routes = {binding.get("agentId") for binding in config.get("bindings", [])
                  if binding.get("match", {}).get("channel") == channel
                  and binding.get("match", {}).get("accountId") == account}
        if routes != {agent}:
            raise ValueError("Selected accounts must bind only to the selected agent")
    return {"pluginId": PLUGIN_ID, "runtimeRoot": str(root), "runtimeHome": str(home),
            "agentId": agent, "telegramAccount": telegram_account, "zaloAccount": zalo_account,
            "cliCommand": str(node), "cliPrefix": [str(cli_entry)]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("root", "home", "node", "cli-entry"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--telegram-account", required=True)
    parser.add_argument("--zalo-account", default="default")
    parser.add_argument("--agent", default="main")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--apply", action="store_true")
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--ensure", action="store_true")
    args = parser.parse_args()
    root, home, node, cli_entry = args.root, args.home, args.node, args.cli_entry
    for item in (root, home, node, cli_entry):
        if not item.is_absolute() or item.is_symlink() or not item.exists():
            raise ValueError("Require existing absolute, non-symlink paths")
    config_path = root / "openclaw.json"
    if config_path.is_symlink():
        raise ValueError("Refusing symlinked configuration")
    config = json.loads(config_path.read_text(encoding="utf-8-sig"))
    settings = selected_settings(config, root, home, node, cli_entry,
                                 args.telegram_account, args.zalo_account, args.agent)
    plugin = root / "tools" / PLUGIN_ID
    if plugin.resolve() != plugin:
        raise ValueError("Refusing symlinked plugin path")
    if any((plugin / name).is_symlink() for name in ("settings.json", "index.mjs", "package.json", "openclaw.plugin.json")):
        raise ValueError("Refusing symlinked plugin files")
    environment = {**os.environ, "HOME": str(home), "OPENCLAW_STATE_DIR": str(root),
                   "OPENCLAW_CONFIG_PATH": str(config_path)}
    for variable in ("OPENCLAW_HOME", "OPENCLAW_PROFILE"):
        environment.pop(variable, None)

    def run(arguments):
        result = subprocess.run([str(node), str(cli_entry), *arguments], env=environment,
                                capture_output=True, text=True, timeout=120)
        if result.returncode:
            raise RuntimeError("Native QR plugin CLI step failed; existing secrets must not be printed")
        return result.stdout

    supported_core_version(run(["--version"]))
    expected_package = package_metadata(PLUGIN_ID)
    if args.ensure and (plugin / "settings.json").is_file() and (plugin / "index.mjs").is_file():
        matching = json.loads((plugin / "settings.json").read_text()) == settings
        matching = matching and (plugin / "index.mjs").read_bytes() == (SKILL_ROOT / "assets/index.mjs").read_bytes()
        matching = matching and (plugin / "package.json").is_file()
        matching = matching and json.loads((plugin / "package.json").read_text()) == expected_package
        if matching and config.get("plugins", {}).get("entries", {}).get(PLUGIN_ID, {}).get("enabled"):
            validate_loaded_plugin(run, PLUGIN_ID)
            print("native_owner_qr=unchanged_final_probe_required")
            return
    run(["config", "validate", "--json"])
    if args.dry_run:
        print("native_owner_qr=ready_no_changes")
        return
    if args.check:
        if json.loads((plugin / "package.json").read_text()) != expected_package:
            raise ValueError("Native QR package compatibility metadata is outdated")
        if json.loads((plugin / "settings.json").read_text()) != settings:
            raise ValueError("Native QR settings do not match the selected instance")
        if (plugin / "index.mjs").read_bytes() != (SKILL_ROOT / "assets/index.mjs").read_bytes():
            raise ValueError("Native QR asset differs from manifest")
        if not config.get("plugins", {}).get("entries", {}).get(PLUGIN_ID, {}).get("enabled"):
            raise ValueError("Native QR plugin is not enabled")
        run(["plugins", "doctor", "--json"])
        validate_loaded_plugin(run, PLUGIN_ID)
        print("native_owner_qr=verified_pending_live_test")
        return
    backup = root / "backups" / ("owner-qr-" + datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"))
    backup.mkdir(parents=True, mode=0o700)
    shutil.copy2(config_path, backup / "openclaw.json")
    (backup / "openclaw.json").chmod(0o600)
    existed = plugin.exists()
    if existed:
        shutil.copytree(plugin, backup / "plugin")
    try:
        write_json(plugin / "settings.json", settings)
        shutil.copy2(SKILL_ROOT / "assets/index.mjs", plugin / "index.mjs")
        write_json(plugin / "package.json", expected_package)
        write_json(plugin / "openclaw.plugin.json", {"id": PLUGIN_ID, "name": "Telegram Owner Zalo QR Login",
                   "categories": ["other"], "activation": {"onStartup": True},
                   "contracts": {"tools": ["telegram_zalo_login_qr"]},
                   "configSchema": {"type": "object", "additionalProperties": False, "properties": {}}})
        run(["plugins", "install", "--link", str(plugin), "--force", "--accept-capabilities"])
        run(["plugins", "enable", PLUGIN_ID])
        run(["config", "validate", "--json"])
        run(["plugins", "doctor", "--json"])
        validate_loaded_plugin(run, PLUGIN_ID)
    except Exception:
        shutil.copy2(backup / "openclaw.json", config_path)
        shutil.rmtree(plugin)
        if existed:
            shutil.copytree(backup / "plugin", plugin)
        raise
    print("native_owner_qr=installed_plugin_reload_required")


if __name__ == "__main__":
    main()
