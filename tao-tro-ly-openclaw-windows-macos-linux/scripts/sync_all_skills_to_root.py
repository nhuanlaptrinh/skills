#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ctypes
import hashlib
import os
import platform
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path


IGNORED_NAMES = {
    ".git",
    ".hg",
    ".svn",
    ".DS_Store",
    "__pycache__",
    "node_modules",
}
IGNORED_SUFFIXES = {".pyc", ".pyo"}
EXPECTED_OPENCLAW_VERSION = "2026.7.1-2"


def is_admin() -> bool:
    if os.name == "nt":
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    return os.geteuid() == 0


def default_openclaw_root() -> Path:
    system = platform.system()
    if system == "Windows":
        profile = os.environ.get("USERPROFILE")
        if not profile:
            raise RuntimeError("Không xác định được USERPROFILE của Administrator")
        return Path(profile) / ".openclaw"
    if system == "Darwin":
        return Path("/var/root/.openclaw")
    return Path("/root/.openclaw")


def default_sources(openclaw_root: Path) -> list[Path]:
    root_home = openclaw_root.parent
    return [root_home / ".agents/skills", root_home / ".codex/skills"]


def discover_skills(source_root: Path) -> list[Path]:
    if not source_root.is_dir():
        return []
    candidates = []
    for child in sorted(source_root.iterdir(), key=lambda path: path.name):
        if child.name == ".system" and child.is_dir():
            candidates.extend(
                nested
                for nested in sorted(child.iterdir(), key=lambda path: path.name)
                if nested.is_dir() and (nested / "SKILL.md").is_file()
            )
        elif child.is_dir() and not child.name.startswith(".") and (child / "SKILL.md").is_file():
            candidates.append(child)
    return candidates


def copy_ignore(_directory: str, names: list[str]) -> set[str]:
    return {
        name
        for name in names
        if name in IGNORED_NAMES or Path(name).suffix.lower() in IGNORED_SUFFIXES
    }


def verify_skill(skill_dir: Path) -> None:
    if skill_dir.is_symlink():
        raise RuntimeError(f"Skill đích không được là symlink: {skill_dir.name}")
    if not (skill_dir / "SKILL.md").is_file():
        raise RuntimeError(f"Skill thiếu SKILL.md: {skill_dir.name}")
    for path in skill_dir.rglob("*"):
        if path.is_symlink():
            raise RuntimeError(f"Symlink không được phép trong skill {skill_dir.name}")
        if path.name in IGNORED_NAMES or path.suffix.lower() in IGNORED_SUFFIXES:
            raise RuntimeError(f"Artifact không được phép trong skill {skill_dir.name}")


def is_clean_skill(skill_dir: Path) -> bool:
    try:
        verify_skill(skill_dir)
    except RuntimeError:
        return False
    return True


def tree_digest(skill_dir: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(skill_dir.rglob("*"), key=lambda item: item.as_posix()):
        relative = path.relative_to(skill_dir)
        if any(part in IGNORED_NAMES for part in relative.parts):
            continue
        if path.suffix.lower() in IGNORED_SUFFIXES:
            continue
        digest.update(relative.as_posix().encode("utf-8"))
        if path.is_file():
            with path.open("rb") as handle:
                for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                    digest.update(chunk)
    return digest.hexdigest()


def selected_skills(source_roots: list[Path]) -> tuple[dict[str, Path], list[str]]:
    selected: dict[str, Path] = {}
    duplicates: list[str] = []
    for source_root in source_roots:
        for skill_dir in discover_skills(source_root):
            if skill_dir.name in selected:
                duplicates.append(skill_dir.name)
                continue
            selected[skill_dir.name] = skill_dir
    return selected, sorted(set(duplicates))


def sync_skills(openclaw_root: Path, source_roots: list[Path], check_only: bool) -> None:
    selected, duplicates = selected_skills(source_roots)
    if not selected:
        raise RuntimeError("Không tìm thấy skill nguồn có SKILL.md")

    destination_root = openclaw_root / "workspace/skills"
    if check_only:
        missing = [name for name in selected if not (destination_root / name / "SKILL.md").is_file()]
        if missing:
            raise RuntimeError(f"Thiếu {len(missing)} skill trong OpenClaw root")
        outdated = [
            name
            for name, source in selected.items()
            if tree_digest(source) != tree_digest(destination_root / name)
        ]
        if outdated:
            raise RuntimeError(f"Có {len(outdated)} skill chưa đồng bộ đúng source")
        for name in selected:
            verify_skill(destination_root / name)
        print(f"skills_check=ok total={len(selected)} duplicates={len(duplicates)}")
        return

    destination_root.mkdir(parents=True, exist_ok=True)
    if os.name != "nt":
        destination_root.chmod(0o700)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    backup_root = openclaw_root / "backups/skills-sync" / timestamp
    staging_root = Path(tempfile.mkdtemp(prefix=".skills-sync-", dir=destination_root))

    installed = 0
    unchanged = 0
    try:
        for name, source in selected.items():
            staged = staging_root / name
            target = destination_root / name
            backup = backup_root / name
            if target.is_dir() and is_clean_skill(target) and tree_digest(source) == tree_digest(target):
                unchanged += 1
                continue
            shutil.copytree(source, staged, ignore=copy_ignore)
            verify_skill(staged)
            if target.exists():
                backup.parent.mkdir(parents=True, exist_ok=True)
                target.replace(backup)
            try:
                staged.replace(target)
            except Exception:
                if backup.exists() and not target.exists():
                    backup.replace(target)
                raise
            installed += 1
    finally:
        shutil.rmtree(staging_root, ignore_errors=True)

    for name in selected:
        verify_skill(destination_root / name)
    print(
        f"skills_sync=ok installed={installed} unchanged={unchanged} "
        f"duplicates={len(duplicates)}"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Đồng bộ toàn bộ skill vào OpenClaw root và loại artifact runtime"
    )
    parser.add_argument("--openclaw-root", type=Path)
    parser.add_argument("--source", action="append", type=Path, default=[])
    parser.add_argument("--check", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not is_admin():
        raise RuntimeError("Phải chạy bằng quyền root/Administrator")
    if shutil.which("openclaw") is None:
        raise RuntimeError("Chưa cài OpenClaw; phải cài OpenClaw trước khi đồng bộ skill")
    version = subprocess.run(
        ["openclaw", "--version"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    if EXPECTED_OPENCLAW_VERSION not in version:
        raise RuntimeError(f"OpenClaw phải đúng version {EXPECTED_OPENCLAW_VERSION}")
    openclaw_root = (args.openclaw_root or default_openclaw_root()).resolve()
    source_roots = [path.resolve() for path in args.source] or default_sources(openclaw_root)
    if args.source:
        missing_sources = [path for path in source_roots if not path.is_dir()]
        if missing_sources:
            raise RuntimeError(f"Thiếu {len(missing_sources)} root nguồn skill")
    sync_skills(openclaw_root, source_roots, args.check)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"skills_sync=error type={type(error).__name__} message={error}", file=sys.stderr)
        raise SystemExit(1)
