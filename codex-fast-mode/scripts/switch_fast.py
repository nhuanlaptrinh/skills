#!/usr/bin/env python3
"""Enable the Codex fast service tier without rewriting unrelated TOML."""

import argparse
import datetime
import json
import os
from pathlib import Path
import re
import stat
import sys
import tempfile
import tomllib


ASSIGNMENT = re.compile(
    r"^(?P<indent>[ \t]*)(?P<key>model|service_tier|model_catalog_json)[ \t]*=[ \t]*"
    r"(?:\"(?:[^\"\\]|\\.)*\"|'[^']*')(?P<suffix>[ \t]*(?:#.*)?)$"
)
MODEL_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._/-]{0,127}\Z")


def default_config():
    return Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex") / "config.toml"


def updated_content(original, model, catalog_path=None):
    parsed = tomllib.loads(original)
    desired = {"service_tier": "fast"}
    if model is not None:
        if not MODEL_ID.fullmatch(model):
            raise ValueError("Model ID không hợp lệ")
        desired["model"] = model
    if catalog_path is not None:
        desired["model_catalog_json"] = str(catalog_path)

    newline = "\r\n" if "\r\n" in original else "\n"
    lines = original.splitlines(keepends=True)
    section = next((index for index, line in enumerate(lines) if re.match(r"\s*\[", line)), len(lines))
    found = set()
    for index in range(section):
        body = lines[index].rstrip("\r\n")
        match = ASSIGNMENT.fullmatch(body)
        if not match or match.group("key") not in desired:
            continue
        key = match.group("key")
        found.add(key)
        ending = lines[index][len(body):]
        lines[index] = f'{match.group("indent")}{key} = {json.dumps(desired[key])}{match.group("suffix")}{ending}'

    missing = desired.keys() - found
    for key in missing:
        if key in parsed:
            raise ValueError(f"Không thể sửa an toàn giá trị TOML hiện có: {key}")
    if missing:
        insertion = "".join(f"{key} = {json.dumps(desired[key])}{newline}" for key in desired if key in missing)
        if section and not lines[section - 1].endswith(("\n", "\r")):
            lines[section - 1] += newline
        lines.insert(section, insertion)
    updated = "".join(lines)
    result = tomllib.loads(updated)
    expected = dict(parsed)
    expected.update(desired)
    if result != expected:
        raise ValueError("Không thể giữ nguyên các thiết lập TOML khác")
    return updated


def enable_fast(path, model, catalog_path=None):
    if path.is_symlink():
        raise ValueError("Không tự thay file cấu hình là symlink; chọn đường dẫn đích thực")
    exists = path.exists()
    if exists and not path.is_file():
        raise ValueError("Đường dẫn cấu hình không phải file")
    original = ""
    if exists:
        with path.open("r", encoding="utf-8", newline="") as stream:
            original = stream.read()
    updated = updated_content(original, model, catalog_path)
    if updated == original:
        return False, None

    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    backup = None
    if exists:
        suffix = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        backup = path.with_name(path.name + ".bak-" + suffix)
        descriptor = os.open(backup, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as stream:
            stream.write(original)
    descriptor, temporary = tempfile.mkstemp(prefix=".codex-fast-", dir=path.parent)
    try:
        os.chmod(temporary, stat.S_IMODE(path.stat().st_mode) if exists else 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as stream:
            stream.write(updated)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise
    return True, backup


def main():
    parser = argparse.ArgumentParser(description="Bật service_tier fast cho Codex")
    parser.add_argument("--config", type=Path, default=default_config())
    parser.add_argument("--model", help="Chỉ đổi model khi người dùng yêu cầu rõ")
    arguments = parser.parse_args()
    try:
        changed, backup = enable_fast(arguments.config.expanduser(), arguments.model)
    except (OSError, ValueError, tomllib.TOMLDecodeError) as error:
        print(f"Không cập nhật Codex: {error}", file=sys.stderr)
        return 1
    print(f"Cấu hình: {arguments.config.expanduser()}")
    print("service_tier: fast" + (" (đã sẵn có)" if not changed else ""))
    if arguments.model:
        print(f"model: {arguments.model}")
    if backup:
        print(f"Bản sao lưu: {backup}")
    print("Fast chỉ được yêu cầu; khả năng xử lý thực tế phụ thuộc provider và model.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
