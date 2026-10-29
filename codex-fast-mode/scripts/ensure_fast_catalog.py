#!/usr/bin/env python3
"""Add a case-sensitive model alias using Codex's own fast-capable catalog."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tomllib

from switch_fast import default_config, enable_fast


def supports_fast(model):
    return any(tier.get("id") == "priority" for tier in model.get("service_tiers", []) if isinstance(tier, dict))


def with_fast_alias(catalog, bundled, model_id):
    models = catalog.get("models")
    candidates = bundled.get("models")
    if not isinstance(models, list) or not isinstance(candidates, list):
        raise ValueError("Catalog model không hợp lệ")
    exact = next((item for item in models if isinstance(item, dict) and item.get("slug") == model_id), None)
    if exact and supports_fast(exact):
        return False
    source = next((item for item in models + candidates if isinstance(item, dict)
                   and isinstance(item.get("slug"), str) and item["slug"].casefold() == model_id.casefold()
                   and supports_fast(item)), None)
    if not source:
        raise ValueError("Codex chưa quảng bá fast cho model tương ứng; cập nhật Codex hoặc kiểm tra catalog của provider")
    if exact:
        exact["service_tiers"] = source["service_tiers"]
        if "additional_speed_tiers" in source:
            exact["additional_speed_tiers"] = source["additional_speed_tiers"]
    else:
        alias = dict(source)
        alias["slug"] = model_id
        models.append(alias)
    return True


def read_catalog(codex_bin, config_path, bundled=False):
    environment = os.environ.copy()
    environment["CODEX_HOME"] = str(config_path.parent)
    command = [codex_bin, "debug", "models"]
    if bundled:
        command.append("--bundled")
    result = subprocess.run(command, env=environment,
                            capture_output=True, text=True, timeout=30, check=False)
    if result.returncode:
        raise ValueError("Không đọc được catalog Codex; kiểm tra đúng CLI/phiên bản")
    return json.loads(result.stdout)


def ensure_catalog(config_path, codex_bin):
    if config_path.is_symlink() or not config_path.is_file():
        raise ValueError("Không tìm thấy file config thực hoặc config là symlink")
    config = tomllib.loads(config_path.read_text(encoding="utf-8"))
    model_id = config.get("model")
    if not isinstance(model_id, str) or not model_id:
        raise ValueError("Không có model mặc định trong config; xác định đúng model trước")
    bundled = read_catalog(codex_bin, config_path, bundled=True)
    original = config.get("model_catalog_json")
    if original is not None:
        if not isinstance(original, str):
            raise ValueError("model_catalog_json không phải đường dẫn")
        original_path = Path(original).expanduser()
        if not original_path.is_absolute():
            original_path = config_path.parent / original_path
        catalog = json.loads(original_path.read_text(encoding="utf-8"))
    else:
        catalog = read_catalog(codex_bin, config_path)
    if not with_fast_alias(catalog, bundled, model_id):
        return False, None, None
    payload = (json.dumps(catalog, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    digest = hashlib.sha256(payload).hexdigest()[:16]
    target = config_path.parent / f"codex-fast-catalog-{digest}.json"
    try:
        descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        if target.is_symlink() or target.read_bytes() != payload:
            raise ValueError("File catalog đích không an toàn hoặc không khớp")
    else:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
    changed, backup = enable_fast(config_path, None, target)
    return changed, target, backup


def main():
    parser = argparse.ArgumentParser(description="Khớp alias model Codex với catalog hỗ trợ fast")
    parser.add_argument("--config", type=Path, default=default_config())
    parser.add_argument("--codex-bin", default="codex", help="CLI Codex thực tế của máy khách")
    arguments = parser.parse_args()
    try:
        changed, catalog, backup = ensure_catalog(arguments.config.expanduser(), arguments.codex_bin)
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(f"Không thể xác nhận fast trong catalog: {error}", file=sys.stderr)
        return 1
    if catalog:
        print(f"Catalog riêng: {catalog}")
        if backup:
            print(f"Bản sao lưu config: {backup}")
        print("Catalog riêng là snapshot; đồng bộ lại khi muốn cập nhật danh sách model.")
    else:
        print("Model đã được catalog Codex quảng bá hỗ trợ fast.")
    print("Kiểm tra profile/phiên và hỗ trợ priority của gateway; không suy đoán kết quả backend.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
