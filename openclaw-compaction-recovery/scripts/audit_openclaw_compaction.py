#!/usr/bin/env python3
"""Read-only fleet audit and explicitly scoped compaction configuration transactions."""

from __future__ import annotations

import argparse
import copy
import fcntl
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path


DATA_ROOT = Path("/root/Apps/member_vps/docker-users/data")
BACKUP_ROOT = Path("/root/_Backups/openclaw-compaction-recovery")
PROFILE = {
    "keepRecentTokens": (8000, min),
    "recentTurnsPreserve": (2, min),
    "timeoutSeconds": (600, max),
}
UNSUPPORTED_LEGACY_KEYS = {"reserveTokens", "reserveTokensFloor", "maxHistoryShare"}
EVENTS = {
    "overflow": "context-overflow-midturn-precheck",
    "compact_failed": "Auto-compaction failed",
    "timeout": "Compaction timed out",
    "blocked": "livenessState=blocked",
}


class GuardError(Exception):
    pass


def digest(payload):
    return hashlib.sha256(payload).hexdigest()


def decode(payload):
    def reject_constant(value):
        raise GuardError("Non-finite number in JSON")

    def unique_keys(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise GuardError("Duplicate JSON keys require manual review")
            result[key] = value
        return result

    try:
        result = json.loads(payload, parse_constant=reject_constant, object_pairs_hook=unique_keys)
    except (ValueError, UnicodeError):
        raise GuardError("Invalid JSON; JSON5 requires native/manual handling") from None
    if not isinstance(result, dict):
        raise GuardError("Expected a JSON object")
    return result


def read_config(root):
    path = root / "openclaw.json"
    if path.is_symlink() or not path.is_file():
        raise GuardError("Config must be an existing regular file, not a file symlink")
    if path.stat().st_size > 4 * 1024 * 1024:
        raise GuardError("Config too large for automatic processing")
    payload = path.read_bytes()
    return payload, decode(payload)


def number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def model_refs(value):
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [value.get("primary")] + value.get("fallbacks", [])
    return [None]


def configured_agents(config):
    agents = config.get("agents", {})
    listed, entries = agents.get("list", []), agents.get("entries", {})
    if not isinstance(listed, list) or not isinstance(entries, dict):
        raise GuardError("Invalid agents list/entries shape")
    if listed and entries:
        raise GuardError("Both agents.list and agents.entries are configured; review native migration")
    if any(not isinstance(value, dict) for value in [*listed, *entries.values()]):
        raise GuardError("Agent configuration must be an object")
    return listed or [dict(value, id=key) for key, value in entries.items()] or [{"id": "main"}]


def plan(config):
    defaults = config.get("agents", {}).get("defaults", {})
    current = defaults.get("compaction", {})
    if not isinstance(current, dict):
        raise GuardError("Compaction must be an object")
    agents = configured_agents(config)
    blockers = []
    if config.get("agents", {}).get("list"):
        blockers.append("Legacy agents.list is unsupported by the installed schema; migrate with native tooling")
    capacity = defaults.get("contextTokens")
    if capacity is not None and (not number(capacity) or capacity < 80000):
        blockers.append("Configured context cap must be a valid number of at least 80000")
    if UNSUPPORTED_LEGACY_KEYS.intersection(current):
        blockers.append("Legacy reserve/history keys are unsupported by this profile; review installed schema without silently deleting them")
    if current.get("provider") or current.get("model"):
        blockers.append("Custom compaction provider/model requires individual review")
    if current.get("enabled") is False or current.get("mode") not in (None, "safeguard"):
        blockers.append("Disabled or non-safeguard compaction requires individual review")
    quality_before = current.get("qualityGuard", {})
    midturn_before = current.get("midTurnPrecheck", {})
    if not isinstance(quality_before, dict) or not isinstance(midturn_before, dict):
        raise GuardError("Quality guard and mid-turn precheck must be objects")
    if quality_before.get("enabled") is False:
        blockers.append("Explicitly disabled quality guard requires individual review")
    model_windows = []
    refs = model_refs(defaults.get("model"))
    for agent in agents:
        if "model" in agent:
            refs.extend(model_refs(agent["model"]))
        if "contextTokens" in agent and not number(agent["contextTokens"]):
            blockers.append("Invalid per-agent context cap")
        elif number(agent.get("contextTokens")):
            capacity = min(capacity, agent["contextTokens"]) if number(capacity) else agent["contextTokens"]
        if agent.get("harness") or agent.get("compaction"):
            blockers.append("Per-agent harness/compaction override requires individual review")
    for ref in set(refs):
        if not isinstance(ref, str) or "/" not in ref:
            blockers.append("Unresolved primary/fallback model; do not guess its context window")
            continue
        provider, model_id = ref.split("/", 1)
        catalog = config.get("models", {}).get("providers", {}).get(provider, {}).get("models", [])
        windows = [entry.get("contextWindow") for entry in catalog if entry.get("id") == model_id]
        if len(windows) != 1 or not number(windows[0]) or windows[0] <= 0:
            blockers.append("Unknown or ambiguous primary/fallback model window")
        else:
            model_windows.append(windows[0])
    if model_windows:
        capacity = min([capacity] + model_windows) if number(capacity) else min(model_windows)
    if not model_windows or not number(capacity) or capacity < 80000:
        blockers.append("At least one agent/model is too small or unknown for the 80k-minimum baseline")
    candidate = copy.deepcopy(config)
    proposed = candidate.setdefault("agents", {}).setdefault("defaults", {}).setdefault("compaction", {})
    changes = {}
    if current.get("mode") is None:
        proposed["mode"] = "safeguard"
        changes["mode"] = {"before": None, "after": "safeguard"}
    for key, (baseline, combine) in PROFILE.items():
        value = current.get(key)
        minimum = 0 if key == "recentTurnsPreserve" else 1
        if value is not None and (not isinstance(value, int) or isinstance(value, bool) or value < minimum):
            blockers.append("Invalid numeric compaction setting")
            continue
        desired = combine(value, baseline) if value is not None else baseline
        proposed[key] = desired
        if value != desired:
            changes[key] = {"before": value, "after": desired}
    quality = proposed.setdefault("qualityGuard", {})
    retries = quality_before.get("maxRetries", 1)
    if not isinstance(retries, int) or isinstance(retries, bool) or retries < 0:
        blockers.append("Invalid quality retry setting")
        retries = 1
    for key, desired in {"enabled": True, "maxRetries": min(retries, 1)}.items():
        quality[key] = desired
        if quality_before.get(key) != desired:
            changes["qualityGuard." + key] = {"before": quality_before.get(key), "after": desired}
    proposed.setdefault("midTurnPrecheck", {})["enabled"] = True
    if midturn_before.get("enabled") is not True:
        changes["midTurnPrecheck.enabled"] = {"before": midturn_before.get("enabled"), "after": True}
    return candidate, {
        "eligible": not blockers, "blockers": sorted(set(blockers)),
        "scope": "agents.defaults.compaction; all agents inheriting these defaults",
        "agents": [entry.get("id") for entry in agents],
        "smallestContextBudget": capacity, "changes": changes,
        "profile": "schema-compatible-2026.8.2",
        "contextBudgetSource": "configured-cap-and-catalog" if defaults.get("contextTokens") is not None else "catalog; no context cap written",
        "requiresRuntimeValidation": True,
    }


def recent_errors(root):
    result = {"windowHours": 24, "maximumBytesScanned": 2097152, "counts": dict.fromkeys(EVENTS, 0)}
    path = root / "logs/gateway.log"
    if not path.is_file():
        result["available"] = False
        return result
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    with path.open("rb") as stream:
        stream.seek(max(0, path.stat().st_size - result["maximumBytesScanned"]))
        tail = stream.read(result["maximumBytesScanned"]).decode("utf-8", errors="replace")
    for line in tail.splitlines():
        match = re.search(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})", line)
        if not match:
            continue
        stamp = datetime.fromisoformat(match.group().replace("Z", "+00:00"))
        if stamp < cutoff:
            continue
        for name, pattern in EVENTS.items():
            if pattern in line:
                result["counts"][name] += 1
                result["lastEventUtc"] = stamp.isoformat()
    result["available"] = True
    return result


def session_metadata(root):
    results = []
    for registry in sorted((root / "agents").glob("*/sessions/sessions.json")):
        if registry.stat().st_size > 4 * 1024 * 1024:
            results.append({"agent": registry.parent.parent.name, "status": "registry-too-large; use native CLI"})
            continue
        records = decode(registry.read_bytes())
        sizes = []
        for entry in list(records.values())[:500]:
            if isinstance(entry, dict) and isinstance(entry.get("sessionFile"), str):
                transcript = registry.parent / Path(entry["sessionFile"]).name
                if transcript.is_file() and not transcript.is_symlink():
                    sizes.append(transcript.stat().st_size)
        results.append({"agent": registry.parent.parent.name, "registryEntries": len(records), "largestReferencedTranscriptBytes": max(sizes, default=0)})
    return results or [{"status": "no JSON registry; inspect native session CLI, possibly SQLite"}]


def target_name(root):
    try:
        relative = root.resolve().relative_to(DATA_ROOT)
        return relative.parts[0] if relative.parts else root.name
    except ValueError:
        return root.parent.name


def inspect_target(root):
    payload, config = read_config(root)
    candidate, report = plan(config)
    return report | {
        "root": str(root), "target": target_name(root),
        "configSha256": digest(payload), "recentLogs": recent_errors(root),
        "sessions": session_metadata(root), "configuredVersionMarker": config.get("meta", {}).get("lastTouchedVersion"),
    }


def is_member_root(root):
    return DATA_ROOT in root.resolve().parents


def member_roots():
    return sorted({root.resolve() for pattern in ("*/.openclaw", "*/root/.openclaw", "*/home/*/.openclaw")
                   for root in DATA_ROOT.glob(pattern) if (root / "openclaw.json").is_file()})


class Runtime:
    def __init__(self, root, container=None, runtime_root=None, binary="openclaw"):
        self.root = root
        self.container = container
        self.runtime_root = Path(runtime_root) if runtime_root else root
        self.binary = binary
        if is_member_root(root) and not container:
            raise GuardError("Member runtime requires explicit --container; inspect Docker mounts first")
        if container and not runtime_root:
            raise GuardError("Docker runtime requires explicit --runtime-root from inspected mounts")
        if not self.runtime_root.is_absolute():
            raise GuardError("Runtime root must be absolute")

    def run(self, arguments, config_path):
        environment = {"OPENCLAW_CONFIG_PATH": str(config_path), "OPENCLAW_STATE_DIR": str(self.runtime_root), "HOME": str(self.runtime_root.parent)}
        if self.container:
            command = ["docker", "exec"]
            for key, value in environment.items():
                command.extend(["-e", key + "=" + value])
            command.extend([self.container, self.binary, *arguments])
            env = None
        else:
            command = [self.binary, *arguments]
            env = os.environ | environment
        try:
            result = subprocess.run(command, env=env, capture_output=True, timeout=60)
        except (OSError, subprocess.TimeoutExpired):
            raise GuardError("Runtime command unavailable or timed out; no raw output exposed") from None
        if result.returncode:
            raise GuardError("Runtime schema validation failed; inspect privately, no raw output exposed")

    def verify_mapping(self, expected_hash):
        if not self.container:
            if self.runtime_root.resolve() != self.root:
                raise GuardError("Local runtime root does not match selected config root")
            return
        try:
            result = subprocess.run(["docker", "exec", self.container, "sha256sum", str(self.runtime_root / "openclaw.json")], capture_output=True, timeout=20)
        except (OSError, subprocess.TimeoutExpired):
            raise GuardError("Cannot verify Docker mount/config mapping") from None
        if result.returncode or result.stdout.decode(errors="replace").split()[:1] != [expected_hash]:
            raise GuardError("Docker runtime config does not match the selected host config")

    def validate(self, payload=None):
        if payload is None:
            self.run(["config", "validate"], self.runtime_root / "openclaw.json")
            return
        descriptor, name = tempfile.mkstemp(prefix=".compaction-candidate-", suffix=".json", dir=self.root)
        temporary = Path(name)
        try:
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(payload)
            metadata = (self.root / "openclaw.json").stat()
            os.chmod(temporary, 0o600)
            os.chown(temporary, metadata.st_uid, metadata.st_gid)
            self.run(["config", "validate"], self.runtime_root / temporary.name)
        finally:
            temporary.unlink(missing_ok=True)


def encode(config):
    return (json.dumps(config, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode()


@contextmanager
def target_lock(root):
    descriptor = os.open(root / ".compaction-recovery.lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise GuardError("Another recovery transaction is active") from None
        yield
    finally:
        os.close(descriptor)


def atomic_write(path, payload, expected_hash):
    metadata = path.stat()
    descriptor, name = tempfile.mkstemp(prefix=".compaction-write-", dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, metadata.st_mode & 0o777)
        os.chown(temporary, metadata.st_uid, metadata.st_gid)
        if path.is_symlink() or digest(path.read_bytes()) != expected_hash:
            raise GuardError("Config changed concurrently; refusing to overwrite")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def save_manifest(backup, manifest):
    path = backup / "manifest.json"
    path.write_bytes(encode(manifest))
    os.chmod(path, 0o600)


def apply_target(root, runtime, expected_hash, backup_root=BACKUP_ROOT):
    with target_lock(root):
        original, config = read_config(root)
        if digest(original) != expected_hash:
            raise GuardError("Config differs from reviewed --expect-sha256; audit again")
        candidate, report = plan(config)
        if not report["eligible"]:
            raise GuardError("Ineligible target: " + "; ".join(report["blockers"]))
        runtime.verify_mapping(expected_hash)
        runtime.validate()
        if not report["changes"]:
            return report | {"action": "unchanged", "backupDir": None, "requiresRuntimeValidation": False, "runtimeSchemaValid": True}
        payload = encode(candidate)
        runtime.validate(payload)
        if digest((root / "openclaw.json").read_bytes()) != expected_hash:
            raise GuardError("Config changed during validation; audit again")
        identifier = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
        backup = backup_root / root.parent.name / identifier
        backup.mkdir(parents=True, mode=0o700, exist_ok=False)
        os.chmod(backup, 0o700)
        (backup / "openclaw.json").write_bytes(original)
        os.chmod(backup / "openclaw.json", 0o600)
        manifest = {"root": str(root), "sha256Before": expected_hash, "sha256After": digest(payload), "changes": report["changes"], "status": "prepared"}
        save_manifest(backup, manifest)
        atomic_write(root / "openclaw.json", payload, expected_hash)
        try:
            runtime.validate()
        except GuardError:
            atomic_write(root / "openclaw.json", original, digest(payload))
            manifest["status"] = "auto-rolled-back"
            save_manifest(backup, manifest)
            raise GuardError("Post-write validation failed; original config restored") from None
        manifest["status"] = "applied"
        save_manifest(backup, manifest)
        return report | {"action": "applied", "backupDir": str(backup), "configSha256": digest(payload), "requiresRuntimeValidation": False, "runtimeSchemaValid": True, "runtimeReload": "verify separately; no restart performed"}


def rollback_target(root, runtime, backup):
    if backup.is_symlink() or backup.stat().st_mode & 0o077 or backup.stat().st_uid != os.geteuid():
        raise GuardError("Backup must be a private directory owned by the current user")
    manifest_path, original_path = backup / "manifest.json", backup / "openclaw.json"
    if manifest_path.is_symlink() or original_path.is_symlink():
        raise GuardError("Backup files must not be symlinks")
    manifest = decode(manifest_path.read_bytes())
    original = original_path.read_bytes()
    if manifest.get("root") != str(root) or digest(original) != manifest.get("sha256Before"):
        raise GuardError("Backup target or original checksum mismatch")
    if manifest.get("status") != "applied":
        raise GuardError("Backup transaction is not in applied state")
    decode(original)
    with target_lock(root):
        current, config = read_config(root)
        expected_hash = manifest.get("sha256After")
        if digest(current) != expected_hash:
            raise GuardError("Config changed after apply; refusing destructive rollback")
        runtime.verify_mapping(expected_hash)
        runtime.validate(original)
        atomic_write(root / "openclaw.json", original, expected_hash)
        try:
            runtime.validate()
        except GuardError:
            atomic_write(root / "openclaw.json", current, digest(original))
            raise GuardError("Rollback validation failed; pre-rollback config restored") from None
        manifest["status"] = "rolled-back"
        save_manifest(backup, manifest)
    return {"action": "rolled-back", "root": str(root), "configSha256": digest(original)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--audit", "--dry-run", action="store_true")
    mode.add_argument("--apply", action="store_true")
    mode.add_argument("--rollback", action="store_true")
    selector = parser.add_mutually_exclusive_group(required=True)
    selector.add_argument("--all-members", action="store_true")
    selector.add_argument("--member")
    selector.add_argument("--openclaw-root", type=Path)
    parser.add_argument("--container")
    parser.add_argument("--runtime-root", type=Path)
    parser.add_argument("--openclaw-bin", default="openclaw")
    parser.add_argument("--validate-candidate", action="store_true")
    parser.add_argument("--accept-defaults-scope", action="store_true")
    parser.add_argument("--expect-sha256")
    parser.add_argument("--backup-root", type=Path, default=BACKUP_ROOT)
    parser.add_argument("--backup-dir", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.all_members and (args.apply or args.rollback or args.validate_candidate):
            raise GuardError("Fleet audit only; validate/apply/rollback one explicitly selected target at a time")
        if args.member and (Path(args.member).name != args.member or args.member in {".", ".."}):
            raise GuardError("Member must be a directory basename")
        if args.all_members:
            roots = member_roots()
        elif args.openclaw_root:
            roots = [args.openclaw_root]
        else:
            member_dir = (DATA_ROOT / args.member).resolve()
            roots = [root for root in member_roots() if member_dir in root.parents]
            if len(roots) != 1:
                raise GuardError("Member has missing or ambiguous runtime roots; use verified --openclaw-root")
        roots = [root.resolve() for root in roots]
        if not roots:
            raise GuardError("No targets found")
        reports, failed = [], False
        for root in roots:
            try:
                if args.apply or args.rollback or args.validate_candidate:
                    runtime = Runtime(root, args.container, args.runtime_root, args.openclaw_bin)
                if args.apply:
                    if not args.accept_defaults_scope or not args.expect_sha256:
                        raise GuardError("Apply requires --accept-defaults-scope and reviewed --expect-sha256")
                    report = apply_target(root, runtime, args.expect_sha256, args.backup_root)
                elif args.rollback:
                    if not args.backup_dir:
                        raise GuardError("Rollback requires --backup-dir")
                    report = rollback_target(root, runtime, args.backup_dir)
                else:
                    report = inspect_target(root)
                    if args.validate_candidate:
                        if not report["eligible"]:
                            raise GuardError("Ineligible profile; review audit before runtime validation")
                        runtime.verify_mapping(report["configSha256"])
                        candidate, details = plan(read_config(root)[1])
                        runtime.validate(encode(candidate))
                        report["candidateSchemaValid"] = True
                reports.append(report | {"root": str(root), "target": target_name(root)})
            except (GuardError, OSError, TypeError, AttributeError, ValueError) as error:
                failed = True
                message = str(error) if isinstance(error, GuardError) else "Input/runtime error (" + type(error).__name__ + "); inspect privately"
                reports.append({"root": str(root), "action": "error", "error": message})
        if args.json:
            print(json.dumps(reports, ensure_ascii=False, indent=2))
        else:
            for report in reports:
                print(json.dumps({key: report[key] for key in ["root", "action", "eligible", "blockers", "configSha256", "backupDir", "error", "candidateSchemaValid"] if key in report}))
                if "changes" in report:
                    print("  proposed fields: " + (", ".join(report["changes"]) or "none"))
        return int(failed)
    except GuardError as error:
        print(json.dumps({"error": str(error)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
