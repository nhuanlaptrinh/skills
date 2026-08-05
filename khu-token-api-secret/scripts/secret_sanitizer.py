#!/usr/bin/env python3
"""Scan and optionally replace common secrets in text files."""

from __future__ import annotations

import argparse
import os
import re
from pathlib import Path


SECRET_PLACEHOLDER = "Nhap_API_Cua_Ban"
EMAIL_PLACEHOLDER = "email_cua_ban@example.com"
PASSWORD_PLACEHOLDER = "Nhap_Mat_Khau_Cua_Ban"
SAFE_EMAILS = {
    EMAIL_PLACEHOLDER,
    "author@example.com",
    "example@example.com",
    "test@example.com",
    "user@example.com",
}

EXCLUDED_DIRS = {
    ".git",
    ".hg",
    ".svn",
    "venv",
    ".venv",
    "node_modules",
    "__pycache__",
    "zalo-chrome-profile",
    "chrome-profile",
    "user-data-dir",
}

TEXT_SUFFIXES = {
    ".env",
    ".json",
    ".yaml",
    ".yml",
    ".py",
    ".js",
    ".ts",
    ".tsx",
    ".jsx",
    ".md",
    ".txt",
    ".toml",
    ".ini",
    ".cfg",
    ".ps1",
    ".sh",
    ".bat",
    ".csv",
}

PATTERNS = [
    ("openai_key", re.compile(r"sk-proj-[A-Za-z0-9_-]+|sk-[A-Za-z0-9_-]{20,}"), SECRET_PLACEHOLDER),
    ("google_api_key", re.compile(r"AIza[0-9A-Za-z_-]{25,}"), SECRET_PLACEHOLDER),
    ("github_token", re.compile(r"gh[pousr]_[0-9A-Za-z_]{20,}|github_pat_[A-Za-z0-9_]+"), SECRET_PLACEHOLDER),
    ("slack_token", re.compile(r"xox[baprs]-[0-9A-Za-z-]{10,}"), SECRET_PLACEHOLDER),
    ("telegram_bot_token", re.compile(r"\b[0-9]{7,}:[A-Za-z0-9_-]{25,}\b"), SECRET_PLACEHOLDER),
    ("bearer_token", re.compile(r"(?i)(bearer\s+)[A-Za-z0-9._~+/=-]{20,}"), r"\1" + SECRET_PLACEHOLDER),
    ("assigned_secret", re.compile(r"(?i)((api[_-]?key|token|secret|client_secret|access_token|refresh_token|botToken)\s*[:=]\s*[\"'])([^\"'\r\n]{6,})([\"'])"), r"\1" + SECRET_PLACEHOLDER + r"\4"),
    ("password_assignment", re.compile(r"(?i)((password|passwd|mat_khau|mật khẩu)\s*[:=]\s*[\"'])([^\"'\r\n]{3,})([\"'])"), r"\1" + PASSWORD_PLACEHOLDER + r"\4"),
    ("email", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"), EMAIL_PLACEHOLDER),
]


def is_text_candidate(path: Path) -> bool:
    if path.name.lower() in {".env", ".env.local", ".env.production"}:
        return True
    return path.suffix.lower() in TEXT_SUFFIXES


def iter_files(root: Path):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDED_DIRS]
        current = Path(dirpath)
        for filename in filenames:
            path = current / filename
            if is_text_candidate(path):
                yield path


def read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        try:
            return path.read_text(encoding="utf-8-sig")
        except UnicodeDecodeError:
            return None


def scan_or_fix(path: Path, fix: bool) -> int:
    text = read_text(path)
    if text is None:
        return 0

    total = 0
    new_text = text
    for name, pattern, replacement in PATTERNS:
        matches = [
            match
            for match in pattern.finditer(new_text)
            if should_report(name, match.group(0))
        ]
        if matches:
            total += len(matches)
            print(f"{path}: {name}: {len(matches)}")
            if fix:
                new_text = pattern.sub(replacement, new_text)

    if fix and new_text != text:
        path.write_text(new_text, encoding="utf-8", newline="")
    return total


def should_report(name: str, value: str) -> bool:
    if SECRET_PLACEHOLDER in value or PASSWORD_PLACEHOLDER in value:
        return False
    if name == "email":
        lower_value = value.lower()
        if lower_value == "git@github.com":
            return False
        return lower_value not in SAFE_EMAILS and not lower_value.endswith("@example.com")
    return EMAIL_PLACEHOLDER not in value


def main() -> int:
    parser = argparse.ArgumentParser(description="Scan and sanitize common secrets in text files.")
    parser.add_argument("--path", default=".", help="Root path to scan")
    parser.add_argument("--scan", action="store_true", help="Only scan and report")
    parser.add_argument("--fix", action="store_true", help="Replace detected values with placeholders")
    args = parser.parse_args()

    if args.scan == args.fix:
        parser.error("Choose exactly one of --scan or --fix")

    root = Path(args.path).resolve()
    total = 0
    for path in iter_files(root):
        total += scan_or_fix(path, args.fix)

    if total == 0:
        print("OK: no matching secret patterns found.")
    else:
        print(f"Found {total} matching value(s).")
        if args.fix:
            print("Sanitized matching text files. Review git diff before committing.")
    return 1 if total and args.scan else 0


if __name__ == "__main__":
    raise SystemExit(main())
