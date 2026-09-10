#!/usr/bin/env python3
"""Safely update default and image models in a Docker member OpenClaw tree.

The script changes only model selection and model catalog entries. It never
prints credential values and never restarts a container.
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path


CONTEXT_WINDOW = 1_000_000
MAX_TOKENS = 384_000


def model_definition(model_id: str, *, vision: bool) -> dict:
    return {
        "id": model_id,
        "name": model_id,
        "contextWindow": CONTEXT_WINDOW,
        "maxTokens": MAX_TOKENS,
        "input": ["text", "image"] if vision else ["text"],
        "cost": {"input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0},
        "reasoning": True,
    }


def update_provider_models(provider: dict, default_id: str, vision_id: str) -> bool:
    models = provider.setdefault("models", [])
    changed = False
    for model_id, vision in ((default_id, False), (vision_id, True)):
        wanted = model_definition(model_id, vision=vision)
        current = next((m for m in models if m.get("id") == model_id), None)
        if current is None:
            models.append(wanted)
            changed = True
            continue
        # Keep provider-specific fields, but make capability metadata accurate.
        for key, value in wanted.items():
            if current.get(key) != value:
                current[key] = copy.deepcopy(value)
                changed = True
    return changed


def update_config(data: dict, provider_id: str, default_id: str, vision_id: str) -> tuple[bool, list[str]]:
    changes: list[str] = []
    provider_ref = f"{provider_id}/{default_id}"
    vision_ref = f"{provider_id}/{vision_id}"

    providers = data.setdefault("models", {}).setdefault("providers", {})
    provider = providers.get(provider_id)
    if not isinstance(provider, dict):
        raise ValueError(f"models.providers.{provider_id} is missing or not an object")
    if update_provider_models(provider, default_id, vision_id):
        changes.append(f"model catalog: {default_id}, {vision_id}")

    agents = data.setdefault("agents", {})
    defaults = agents.setdefault("defaults", {})
    default_model = defaults.setdefault("model", {})
    if default_model.get("primary") != provider_ref:
        default_model["primary"] = provider_ref
        changes.append("agents.defaults.model.primary")

    image_model = defaults.setdefault("imageModel", {})
    if image_model.get("primary") != vision_ref:
        image_model["primary"] = vision_ref
        changes.append("agents.defaults.imageModel.primary")

    media_models = defaults.setdefault("mediaModels", {})
    media_image = media_models.setdefault("image", {})
    if media_image.get("primary") != vision_ref:
        media_image["primary"] = vision_ref
        changes.append("agents.defaults.mediaModels.image.primary")

    policy = defaults.setdefault("modelPolicy", {})
    allowed = policy.setdefault("allow", [])
    for ref in (provider_ref, vision_ref):
        if ref not in allowed:
            allowed.append(ref)
            changes.append(f"agents.defaults.modelPolicy.allow += {ref}")

    entries = agents.setdefault("entries", {})
    for agent_id, entry in entries.items():
        if not isinstance(entry, dict):
            continue
        model = entry.setdefault("model", {})
        if model.get("primary") != provider_ref:
            model["primary"] = provider_ref
            changes.append(f"agents.entries.{agent_id}.model.primary")
    return bool(changes), changes


def write_json_atomic(path: Path, data: dict) -> None:
    mode = path.stat().st_mode & 0o777
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(tmp_name, mode)
        os.replace(tmp_name, path)
    finally:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)


def backup_files(paths: list[Path], member_dir: Path, backup_root: Path | None) -> Path:
    member_name = member_dir.name
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    destination = (backup_root or Path("/root/_Backups/openclaw-model-switch")) / member_name / stamp
    destination.mkdir(parents=True, exist_ok=False)
    for path in paths:
        relative = path.relative_to(member_dir)
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
    return destination


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--member-dir", type=Path, required=True, help="Persistent member directory")
    parser.add_argument("--provider", default="9r")
    parser.add_argument("--default-model", default="ds-v4-flash")
    parser.add_argument("--vision-model", default="ds-v4-flash-vision-exp")
    parser.add_argument("--backup-root", type=Path)
    parser.add_argument("--apply", action="store_true", help="Write changes; otherwise perform a dry run")
    args = parser.parse_args()

    member_dir = args.member_dir.resolve()
    config_path = member_dir / ".openclaw" / "openclaw.json"
    if not config_path.is_file():
        raise SystemExit(f"Config not found: {config_path}")
    with config_path.open(encoding="utf-8") as handle:
        original = json.load(handle)
    candidate = copy.deepcopy(original)
    changed, changes = update_config(candidate, args.provider, args.default_model, args.vision_model)

    cache_paths: list[Path] = []
    for agent_id in candidate.get("agents", {}).get("entries", {}):
        cache_path = member_dir / ".openclaw" / "agents" / agent_id / "agent" / "models.json"
        if not cache_path.is_file():
            continue
        with cache_path.open(encoding="utf-8") as handle:
            cache = json.load(handle)
        providers = cache.get("providers", {})
        provider = providers.get(args.provider)
        if not isinstance(provider, dict):
            continue
        if update_provider_models(provider, args.default_model, args.vision_model):
            cache_paths.append(cache_path)
            changes.append(f"agents/{agent_id}/agent/models.json model catalog")

    if not changes:
        print("No changes needed.")
        return 0
    print("Planned changes:")
    for change in changes:
        print(f"- {change}")
    print(f"default={args.provider}/{args.default_model}")
    print(f"vision={args.provider}/{args.vision_model}")
    if not args.apply:
        print("Dry run only; no files changed.")
        return 0

    backup_paths = [config_path, *cache_paths]
    backup_dir = backup_files(backup_paths, member_dir, args.backup_root)
    write_json_atomic(config_path, candidate)
    # Re-read each cache and apply the same provider-only catalog update.
    for cache_path in cache_paths:
        with cache_path.open(encoding="utf-8") as handle:
            cache = json.load(handle)
        provider = cache.get("providers", {}).get(args.provider)
        if isinstance(provider, dict):
            update_provider_models(provider, args.default_model, args.vision_model)
            write_json_atomic(cache_path, cache)
    print(f"Applied. Backup: {backup_dir}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise SystemExit(f"ERROR: {exc}")
