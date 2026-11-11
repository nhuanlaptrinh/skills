#!/usr/bin/env python3
import argparse
import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import urlsplit


def main():
    parser = argparse.ArgumentParser(description="Create an isolated API-only Codex profile.")
    parser.add_argument("--profile-id", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--provider", default="router")
    parser.add_argument("--env-key", help="Name of an existing environment variable, not its value")
    parser.add_argument("--profile-root", default=os.environ.get("ALT_CODEX_PROFILE_ROOT"))
    args = parser.parse_args()

    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", args.profile_id) or ".." in args.profile_id or args.profile_id.endswith("."):
        parser.error("Invalid profile ID")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", args.model):
        parser.error("Invalid model ID")
    if not re.fullmatch(r"[A-Za-z0-9_-]+", args.provider):
        parser.error("Invalid provider ID")
    if args.env_key and not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", args.env_key):
        parser.error("Invalid environment variable name")
    if any(ord(character) < 32 for character in args.base_url):
        parser.error("Invalid base URL")
    try:
        url = urlsplit(args.base_url)
        if url.scheme not in ("http", "https") or not url.hostname or url.username is not None or url.password is not None:
            parser.error("Base URL must be an absolute HTTP(S) URL without credentials")
        _ = url.port
    except ValueError:
        parser.error("Invalid base URL")

    state_home = os.environ.get("XDG_STATE_HOME") or str(Path.home() / ".local" / "state")
    root = Path(args.profile_root or Path(state_home) / "your-product" / "codex-profiles").expanduser().resolve()
    profile = root / args.profile_id
    codex_home = profile / ".codex"
    if profile.resolve() != profile or codex_home.resolve() != codex_home:
        parser.error("Profile path resolves outside its intended root")
    config_path = codex_home / "config.toml"
    print("Destination CODEX_HOME: " + str(codex_home), flush=True)
    codex_home.mkdir(mode=0o700, parents=True, exist_ok=True)
    lines = [
        "model_provider = " + json.dumps(args.provider),
        "model = " + json.dumps(args.model),
        'forced_login_method = "api"',
        'cli_auth_credentials_store = "file"',
        "",
        "[model_providers." + args.provider + "]",
        "name = " + json.dumps(args.provider),
        "base_url = " + json.dumps(args.base_url),
    ]
    if args.env_key:
        lines.append("env_key = " + json.dumps(args.env_key))
    lines.append('wire_api = "responses"')
    try:
        descriptor = os.open(str(config_path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        parser.error("Config already exists; preserve and update it explicitly")
    with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as config:
        config.write("\n".join(lines) + "\n")
    if args.env_key:
        print("AuthStatus: env_key_reference_not_verified")
        print("Environment variable in current process: " + ("set" if os.environ.get(args.env_key) else "missing"))
    else:
        print("AuthStatus: not_configured_by_this_script")
    print("No API key, browser data, or authentication file was copied.")


if __name__ == "__main__":
    try:
        main()
    except OSError as error:
        print("Profile setup failed: " + str(error), file=sys.stderr)
        sys.exit(1)
