#!/usr/bin/env python3
import argparse
import os
import shutil
import sys
from pathlib import Path


def excluded(directory, names):
    skipped = []
    for name in names:
        lower = name.lower()
        if (
            os.path.islink(os.path.join(directory, name))
            or lower in (".git", "__pycache__", "auth.json", ".env")
            or lower.startswith((".env.", "auth.json."))
            or lower.endswith((".pem", ".key", ".p12", ".pfx", ".pyc"))
        ):
            skipped.append(name)
    return skipped


def main():
    parser = argparse.ArgumentParser(description="Install a sanitized skill copy into an isolated profile.")
    parser.add_argument("--source-skill", required=True)
    parser.add_argument("--codex-home", required=True)
    args = parser.parse_args()
    source = Path(args.source_skill).expanduser().resolve()
    home = Path(args.codex_home).expanduser().resolve()
    if (source / "SKILL.md").is_symlink() or not (source / "SKILL.md").is_file():
        parser.error("Source must contain SKILL.md")
    if not (home / "config.toml").is_file():
        parser.error("Destination must be an existing Codex profile")
    target = home / "skills" / "cau-hinh-alt-codex"
    if target.parent.resolve() != target.parent:
        parser.error("Destination skills directory must not resolve outside the profile")
    if target.exists() or target.is_symlink():
        parser.error("Destination already exists; back it up before an explicit update")
    if os.path.commonpath((str(source), str(target))) in (str(source), str(target)):
        parser.error("Source and destination must not contain one another")
    print("Destination skill: " + str(target), flush=True)
    target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    shutil.copytree(str(source), str(target), ignore=excluded)
    print("Installed skill copy; excluded credential-named files and symbolic links.")


if __name__ == "__main__":
    try:
        main()
    except OSError as error:
        print("Skill installation failed: " + str(error), file=sys.stderr)
        sys.exit(1)
