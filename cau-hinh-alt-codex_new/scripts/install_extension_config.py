#!/usr/bin/env python3
"""Validate and install Codex Extension credentials/config without exposing the key."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import time
import urllib.error
import urllib.request

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.10 fallback
    tomllib = None


SUPPORTED_FILES = ("auth.json", "config.toml")


class ValidationError(RuntimeError):
    """Raised when installation must stop before changing the target."""


def resolve_source(path_arg: str | None) -> Path:
    source = Path(path_arg).expanduser() if path_arg else Path(__file__).resolve().parent.parent
    source = source.resolve()
    if not (source / "SKILL.md").is_file():
        raise ValidationError(f"Không xác định được thư mục skill: {source}")
    for name in SUPPORTED_FILES:
        if not (source / name).is_file():
            raise ValidationError(f"Thiếu file nguồn {name}: {source / name}")
    return source


def resolve_target(path_arg: str | None) -> Path:
    if path_arg:
        target = Path(path_arg).expanduser()
    else:
        target = Path(os.environ.get("CODEX_HOME", "")).expanduser() if os.environ.get("CODEX_HOME") else Path.home() / ".codex"
    return target.resolve()


def is_within(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def load_auth(path: Path) -> tuple[dict, str]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValidationError(f"auth.json không hợp lệ: {type(exc).__name__}") from exc
    if not isinstance(data, dict):
        raise ValidationError("auth.json phải là một JSON object")
    key = data.get("OPENAI_API_KEY")
    if not isinstance(key, str) or not key.strip():
        raise ValidationError("auth.json thiếu OPENAI_API_KEY không rỗng")
    normalized = key.strip().lower().replace("-", "_").replace(" ", "_")
    if key.strip().startswith("<") or key.strip().endswith(">") or normalized in {
        "api_key",
        "api_key_here",
        "openai_api_key",
        "replace_me",
        "your_api_key",
    }:
        raise ValidationError("auth.json vẫn chứa placeholder thay vì API key thật")
    return data, key.strip()


def load_config(path: Path) -> tuple[dict, str, str]:
    text = path.read_text(encoding="utf-8")
    if tomllib is None:
        # Keep a useful validation path on Python 3.10 without adding a dependency.
        sections: dict[str, dict[str, str]] = {"": {}}
        current_section = ""
        for raw_line in text.splitlines():
            line = raw_line.split("#", 1)[0].strip()
            if not line:
                continue
            if line.startswith("[") and line.endswith("]"):
                current_section = line[1:-1].strip()
                sections.setdefault(current_section, {})
                continue
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            sections.setdefault(current_section, {})[key.strip()] = value.strip().strip('"').strip("'")

        top_level = sections[""]
        provider_match = top_level.get("model_provider", "")
        provider_values = sections.get(f"model_providers.{provider_match}", {})
        base_match = provider_values.get("base_url", "")
        auth_match = top_level.get("preferred_auth_method", "")
        store_match = top_level.get("cli_auth_credentials_store", "")
        requires_auth_match = provider_values.get("requires_openai_auth", "").lower()
        if (
            not provider_match
            or not base_match
            or auth_match != "apikey"
            or store_match != "file"
            or requires_auth_match != "true"
        ):
            raise ValidationError(
                "config.toml thiếu model_provider/base_url hoặc phải đặt preferred_auth_method=apikey, "
                "cli_auth_credentials_store=file và requires_openai_auth=true"
            )
        return {}, provider_match, base_match
    try:
        data = tomllib.loads(text)
    except (tomllib.TOMLDecodeError, TypeError) as exc:
        raise ValidationError(f"config.toml không hợp lệ: {type(exc).__name__}") from exc
    provider = data.get("model_provider")
    if not isinstance(provider, str) or not provider:
        raise ValidationError("config.toml thiếu model_provider")
    provider_config = data.get("model_providers", {}).get(provider)
    if not isinstance(provider_config, dict):
        raise ValidationError(f"config.toml thiếu model_providers.{provider}")
    base_url = provider_config.get("base_url")
    if not isinstance(base_url, str) or not base_url.strip():
        raise ValidationError(f"config.toml thiếu base_url cho provider {provider}")
    if data.get("preferred_auth_method") != "apikey":
        raise ValidationError("config.toml phải dùng preferred_auth_method=apikey")
    if data.get("cli_auth_credentials_store") != "file":
        raise ValidationError("config.toml phải dùng cli_auth_credentials_store=file để Extension đọc auth.json")
    if provider_config.get("requires_openai_auth") is not True:
        raise ValidationError(
            f"config.toml phải đặt model_providers.{provider}.requires_openai_auth=true "
            "để Codex gửi Authorization từ auth.json"
        )
    return data, provider, base_url.strip()


def gateway_probe(base_url: str, key: str, timeout: float) -> tuple[int, int]:
    models_url = base_url.rstrip("/") + "/models"
    request = urllib.request.Request(
        models_url,
        headers={"Authorization": f"Bearer {key}", "Accept": "application/json"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            status = int(response.status)
            response.read(256)
    except urllib.error.HTTPError as exc:
        if exc.code == 401:
            raise ValidationError("Gateway trả HTTP 401: OPENAI_API_KEY thiếu, sai hoặc chưa được gateway cấp quyền") from exc
        raise ValidationError(f"Gateway trả HTTP {exc.code} khi kiểm tra /models") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise ValidationError(f"Không kiểm tra được gateway: {type(exc).__name__}") from exc
    if status < 200 or status >= 300:
        raise ValidationError(f"Gateway trả HTTP {status} khi kiểm tra /models")

    # An empty Responses request must reach input validation, never the missing-key guard.
    responses_url = base_url.rstrip("/") + "/responses"
    responses_request = urllib.request.Request(
        responses_url,
        data=b"{}",
        headers={
            "Authorization": f"Bearer {key}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(responses_request, timeout=timeout) as response:
            responses_status = int(response.status)
            response.read(256)
    except urllib.error.HTTPError as exc:
        responses_status = int(exc.code)
        exc.read(256)
        if responses_status == 401:
            raise ValidationError("Gateway /responses trả HTTP 401: request vẫn thiếu hoặc không nhận OPENAI_API_KEY") from exc
        if responses_status not in (400, 422):
            raise ValidationError(f"Gateway trả HTTP {responses_status} khi kiểm tra xác thực /responses") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise ValidationError(f"Không kiểm tra được gateway /responses: {type(exc).__name__}") from exc
    if not (200 <= responses_status < 300 or responses_status in (400, 422)):
        raise ValidationError(f"Gateway trả HTTP {responses_status} khi kiểm tra xác thực /responses")
    return status, responses_status


def fingerprint(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def backup_existing(paths: list[Path], backup_dir: Path) -> list[Path]:
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S", time.gmtime())
    backups: list[Path] = []
    for path in paths:
        if not path.is_file():
            continue
        candidate = backup_dir / f"{path.name}.bak-{stamp}"
        suffix = 1
        while candidate.exists():
            candidate = backup_dir / f"{path.name}.bak-{stamp}-{suffix}"
            suffix += 1
        shutil.copy2(path, candidate)
        backups.append(candidate)
    return backups


def install(source: Path, target: Path, backup_dir: Path) -> list[Path]:
    target.mkdir(parents=True, exist_ok=True)
    backups = backup_existing([target / name for name in SUPPORTED_FILES], backup_dir)
    for name in SUPPORTED_FILES:
        destination = target / name
        shutil.copy2(source / name, destination)
        if os.name != "nt":
            destination.chmod(0o600)
    return backups


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Preflight và cài config Codex Extension an toàn")
    parser.add_argument("--source-dir", help="Thư mục chứa SKILL.md, auth.json và config.toml")
    parser.add_argument("--target-dir", help="CODEX_HOME đích; mặc định là CODEX_HOME hoặc ~/.codex")
    parser.add_argument("--backup-dir", help="Thư mục backup; mặc định theo ALT_CODEX_BACKUP_DIR/XDG_STATE_HOME")
    parser.add_argument("--timeout", type=float, default=20.0, help="Timeout kiểm tra gateway (giây)")
    parser.add_argument("--skip-gateway-check", action="store_true", help="Chỉ dùng khi offline; không xác nhận key với gateway")
    parser.add_argument("--check-only", action="store_true", help="Chỉ preflight, không copy file")
    parser.add_argument("--allow-outside-home", action="store_true", help="Cho phép target-dir ngoài home khi chỉ định rõ")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source = resolve_source(args.source_dir)
    target = resolve_target(args.target_dir)
    home = Path.home().resolve()
    configured_home = os.environ.get("CODEX_HOME")
    configured_target = Path(configured_home).expanduser().resolve() if configured_home else None
    if (
        args.target_dir
        and not is_within(target, home)
        and target != configured_target
        and not args.allow_outside_home
    ):
        raise ValidationError("target-dir nằm ngoài home; xác nhận rõ bằng --allow-outside-home nếu đây là CODEX_HOME hợp lệ")

    _, key = load_auth(source / "auth.json")
    _, provider, base_url = load_config(source / "config.toml")
    statuses = None
    if not args.skip_gateway_check:
        statuses = gateway_probe(base_url, key, args.timeout)

    if args.backup_dir:
        backup_dir = Path(args.backup_dir).expanduser()
    elif os.environ.get("ALT_CODEX_BACKUP_DIR"):
        backup_dir = Path(os.environ["ALT_CODEX_BACKUP_DIR"]).expanduser()
    elif os.environ.get("XDG_STATE_HOME"):
        backup_dir = Path(os.environ["XDG_STATE_HOME"]).expanduser() / "cau-hinh-alt-codex/backups"
    else:
        backup_dir = home / ".local/state/cau-hinh-alt-codex/backups"
    print(f"Source: {source}")
    print(f"Target CODEX_HOME: {target}")
    print(f"Provider: {provider}")
    print("requires_openai_auth: true")
    print("OPENAI_API_KEY: present")
    if statuses is None:
        print("Gateway checks: skipped")
    else:
        models_status, responses_status = statuses
        print(f"Gateway /models: HTTP {models_status}")
        print(f"Gateway /responses auth: accepted (HTTP {responses_status})")

    if args.check_only:
        print("Preflight OK; chưa copy file.")
        return 0

    backups = install(source, target, backup_dir)
    _, copied_key = load_auth(target / "auth.json")
    if fingerprint(copied_key) != fingerprint(key):
        raise ValidationError("auth.json đích không khớp source sau khi copy")
    load_config(target / "config.toml")
    print(f"Đã copy auth.json và config.toml vào {target}")
    if backups:
        print("Backup: " + ", ".join(str(path) for path in backups))
    print("Xác minh đích: OPENAI_API_KEY có và config.toml hợp lệ; không in giá trị key.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValidationError as exc:
        print(f"DỪNG: {exc}", file=sys.stderr)
        raise SystemExit(2)
