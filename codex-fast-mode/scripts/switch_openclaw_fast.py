#!/usr/bin/env python3
"""Request priority for one existing OpenClaw OpenAI-compatible chat model."""

import argparse
import copy
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import stat
import subprocess
import sys
import tempfile
import time


MINIMUM_VERSION = (2026, 10, 6)
BODY_KEYS = ("extra_body", "extraBody")


def default_config_path():
    if os.environ.get("OPENCLAW_CONFIG_PATH"):
        return Path(os.environ["OPENCLAW_CONFIG_PATH"]).expanduser()
    if os.environ.get("OPENCLAW_STATE_DIR"):
        return Path(os.environ["OPENCLAW_STATE_DIR"]).expanduser() / "openclaw.json"
    if os.environ.get("OPENCLAW_PROFILE"):
        raise ValueError("OPENCLAW_PROFILE is set; pass the selected instance path with --config")
    home = Path(os.environ.get("OPENCLAW_HOME") or Path.home()).expanduser()
    return home / ".openclaw" / "openclaw.json"


def object_value(parent, key, create=False):
    value = parent.get(key)
    if value is None and key not in parent and create:
        value = {}
        parent[key] = value
    if not isinstance(value, dict):
        raise ValueError(f"Expected an object at {key}; refusing to rewrite it")
    return value


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON keys; refusing to rewrite config")
        result[key] = value
    return result


def has_include(value):
    if isinstance(value, dict):
        return "$include" in value or any(has_include(item) for item in value.values())
    return isinstance(value, list) and any(has_include(item) for item in value)


def body_from(params):
    if params is None:
        return None
    if not isinstance(params, dict):
        raise ValueError("Expected params to be an object")
    present = [key for key in BODY_KEYS if key in params]
    if len(present) > 1:
        raise ValueError("Both extra_body aliases are set; resolve the conflict first")
    if not present:
        return None
    value = params[present[0]]
    if not isinstance(value, dict):
        raise ValueError("Existing extra_body is not an object")
    return value


def agent_entries(agents):
    entries = agents.get("entries")
    legacy = agents.get("list")
    if entries is not None and legacy is not None:
        raise ValueError("Both agent roster formats are present; resolve them first")
    if entries is not None:
        if not isinstance(entries, dict) or any(not isinstance(item, dict) for item in entries.values()):
            raise ValueError("Invalid agent entries")
        return list(entries.items())
    if legacy is not None:
        if not isinstance(legacy, list) or any(not isinstance(item, dict) for item in legacy):
            raise ValueError("Invalid agent list")
        return [(item.get("id"), item) for item in legacy]
    return []


def model_params(container, model_ref):
    models = container.get("models", {})
    if not isinstance(models, dict):
        raise ValueError("Expected agent models to be an object")
    model = models.get(model_ref, {})
    if not isinstance(model, dict):
        raise ValueError("Expected model settings to be an object")
    runtime = model.get("agentRuntime")
    if runtime is not None and (not isinstance(runtime, dict) or runtime.get("id") not in (None, "auto", "openclaw")):
        raise ValueError("This model uses a different agent runtime")
    return model.get("params")


def require_embedded(runtime):
    if runtime is not None and (not isinstance(runtime, dict) or runtime.get("id") not in (None, "auto", "openclaw")):
        raise ValueError("This provider or agent uses a different agent runtime")


def prepare_config(original, requested_model=None, agent_id=None):
    config = copy.deepcopy(original)
    if not isinstance(config, dict) or has_include(config):
        raise ValueError("Config must be an object without $include directives")
    agents = object_value(config, "agents")
    defaults = object_value(agents, "defaults")
    entries = agent_entries(agents)
    selected_agent = None
    if agent_id:
        matches = [entry for name, entry in entries if isinstance(name, str) and name.lower() == agent_id.lower()]
        if len(matches) != 1:
            raise ValueError("Agent not found uniquely in the OpenClaw config")
        selected_agent = matches[0]
        require_embedded(selected_agent.get("runtime"))
        if body_from(selected_agent.get("params")) is not None:
            raise ValueError("Agent-wide extra_body overrides per-model settings; inspect it before changing fast")
    primary = defaults.get("model")
    if selected_agent is not None and selected_agent.get("model"):
        primary = selected_agent["model"]
    if isinstance(primary, dict):
        primary = primary.get("primary")
    model_ref = requested_model or primary
    if not isinstance(model_ref, str) or "/" not in model_ref:
        raise ValueError("Specify the active provider/model with --model-ref")
    provider_id, model_id = model_ref.split("/", 1)
    if not provider_id or not model_id or model_ref != model_ref.strip():
        raise ValueError("Invalid provider/model reference")

    providers = object_value(object_value(config, "models"), "providers")
    provider = object_value(providers, provider_id)
    require_embedded(provider.get("agentRuntime"))
    model_params(defaults, f"{provider_id}/*")
    if selected_agent is not None:
        model_params(selected_agent, f"{provider_id}/*")
    declared = provider.get("models")
    if not isinstance(declared, list):
        raise ValueError("Provider model catalog is missing")
    matches = [model for model in declared if isinstance(model, dict) and model.get("id") == model_id]
    if len(matches) != 1:
        raise ValueError("Model must exist exactly once in the configured provider catalog")
    if matches[0].get("api", provider.get("api")) != "openai-completions":
        raise ValueError("This helper supports only openai-completions providers")

    sources = [defaults.get("params"), model_params(defaults, model_ref)]
    if selected_agent is not None:
        sources.append(model_params(selected_agent, model_ref))
    effective_body = {}
    for source in sources:
        body = body_from(source)
        if body is not None:
            effective_body = copy.deepcopy(body)
    effective_body["service_tier"] = "priority"

    target = selected_agent if selected_agent is not None else defaults
    target_models = object_value(target, "models", create=True)
    target_model = object_value(target_models, model_ref, create=True)
    params = object_value(target_model, "params", create=True)
    body_from(params)
    key = next((name for name in BODY_KEYS if name in params), "extra_body")
    params[key] = effective_body

    shadowed = []
    if selected_agent is None:
        for name, entry in entries:
            if body_from(model_params(entry, model_ref)) is not None or body_from(entry.get("params")) is not None:
                shadowed.append(str(name or "unknown"))
    return config, model_ref, shadowed


def cli_command(openclaw_bin=None, node=None, entry=None):
    if bool(node) != bool(entry):
        raise ValueError("--node and --openclaw-entry must be supplied together")
    if node:
        return [node, entry]
    executable = openclaw_bin or shutil.which("openclaw")
    if not executable:
        raise ValueError("OpenClaw CLI not found; specify --openclaw-bin or --node and --openclaw-entry")
    return [executable]


def check_version(command):
    try:
        result = subprocess.run(command + ["--version"], capture_output=True, text=True, timeout=40, check=False)
    except (OSError, subprocess.TimeoutExpired) as error:
        raise ValueError("Unable to run the specified OpenClaw CLI") from error
    match = re.search(r"\bOpenClaw\s+(\d+)\.(\d+)\.(\d+)", result.stdout)
    if result.returncode or not match or tuple(map(int, match.groups())) < MINIMUM_VERSION:
        raise ValueError("OpenClaw 2026.10.6 or newer is required for this helper")


def validate_candidate(command, candidate):
    env = os.environ.copy()
    env["OPENCLAW_CONFIG_PATH"] = str(candidate)
    try:
        result = subprocess.run(command + ["config", "validate", "--json"], env=env,
                                capture_output=True, timeout=60, check=False)
    except (OSError, subprocess.TimeoutExpired) as error:
        raise ValueError("Could not validate the candidate with OpenClaw") from error
    if result.returncode:
        raise ValueError("OpenClaw rejected the candidate config; no changes were applied")


def enable_fast(path, command, requested_model=None, agent_id=None):
    path = Path(path).expanduser().absolute()
    if path.is_symlink() or not path.is_file():
        raise ValueError("Config must be an existing regular file, not a symlink")
    check_version(command)
    original_bytes = path.read_bytes()
    try:
        original = json.loads(original_bytes.decode("utf-8-sig"), object_pairs_hook=unique_object)
    except (UnicodeError, json.JSONDecodeError) as error:
        raise ValueError("Config is not strict UTF-8 JSON; use a compatible manual workflow") from error
    config, model_ref, shadowed = prepare_config(original, requested_model, agent_id)
    if config == original:
        return False, None, model_ref, shadowed
    rendered = (json.dumps(config, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    descriptor, candidate_name = tempfile.mkstemp(prefix=".openclaw-fast-", suffix=".json", dir=path.parent)
    candidate = Path(candidate_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(rendered)
            stream.flush()
            os.fsync(stream.fileno())
        validate_candidate(command, candidate)
        if path.read_bytes() != original_bytes:
            raise ValueError("Config changed during validation; no changes were applied")
        backup = path.with_name(f"{path.name}.bak-fast-{time.strftime('%Y%m%d-%H%M%S')}-{secrets.token_hex(3)}")
        backup_fd = os.open(backup, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(backup_fd, "wb") as stream:
            stream.write(original_bytes)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(candidate, stat.S_IMODE(path.stat().st_mode))
        if path.read_bytes() != original_bytes:
            raise ValueError("Config changed before replacement; no changes were applied")
        os.replace(candidate, path)
        return True, backup, model_ref, shadowed
    finally:
        candidate.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description="Request priority for the existing OpenClaw chat model")
    parser.add_argument("--config", type=Path)
    parser.add_argument("--model-ref", help="Active provider/model; defaults to the configured primary")
    parser.add_argument("--agent", help="Restrict to this explicitly configured agent")
    parser.add_argument("--openclaw-bin", help="OpenClaw CLI for the selected instance")
    parser.add_argument("--node", help="Absolute Node executable, for private/native installations")
    parser.add_argument("--openclaw-entry", help="OpenClaw JavaScript entry, used together with --node")
    arguments = parser.parse_args()
    try:
        config_path = arguments.config or default_config_path()
        command = cli_command(arguments.openclaw_bin, arguments.node, arguments.openclaw_entry)
        changed, backup, model_ref, shadowed = enable_fast(config_path, command, arguments.model_ref, arguments.agent)
    except (OSError, ValueError) as error:
        print(f"Not applied: {error}", file=sys.stderr)
        return 1
    print(f"Model: {model_ref}")
    print("Request tier: priority" + (" (already configured)" if not changed else ""))
    if backup:
        print(f"Private backup: {backup}")
    if shadowed:
        print("Agent-specific settings may override this request: " + ", ".join(shadowed))
    print("Provider acceptance and actual priority processing are not verified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
