#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
import shutil
import stat
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath


START_MARKER = "<!-- openclaw-telegram-owner-approval:start -->"
END_MARKER = "<!-- openclaw-telegram-owner-approval:end -->"
HELPER_NAME = "approve_system_agent_from_telegram.sh"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Install or verify safe Telegram-owner approval for delegated OpenClaw proposals."
    )
    parser.add_argument("--openclaw-root")
    parser.add_argument("--runtime-openclaw-root")
    parser.add_argument("--workspace")
    parser.add_argument("--telegram-id", action="append", default=[])
    parser.add_argument("--account-id")
    parser.add_argument("--agent-id", default="main")
    parser.add_argument("--backup-dir")
    actions = parser.add_mutually_exclusive_group(required=True)
    actions.add_argument("--dry-run", action="store_true")
    actions.add_argument("--apply", action="store_true")
    actions.add_argument("--check", action="store_true")
    actions.add_argument("--rollback-manifest")
    return parser.parse_args()


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha256_file(path):
    return sha256_bytes(path.read_bytes()) if path.exists() else None


def ensure_absolute_directory(value, label, must_exist=True):
    path = Path(value).expanduser()
    if not path.is_absolute():
        raise ValueError(f"{label} must be absolute")
    if path.is_symlink():
        raise ValueError(f"{label} must not be a symlink")
    if must_exist and not path.is_dir():
        raise ValueError(f"{label} is not a directory")
    return path


def load_json(path):
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def string_values(value):
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if isinstance(item, (str, int))]


def resolve_agent(config, agent_id):
    agents = config.get("agents") if isinstance(config.get("agents"), dict) else {}
    entries = agents.get("entries") if isinstance(agents.get("entries"), dict) else {}
    if isinstance(entries.get(agent_id), dict):
        return entries[agent_id]
    listed = agents.get("list") if isinstance(agents.get("list"), list) else []
    matches = [entry for entry in listed if isinstance(entry, dict) and entry.get("id") == agent_id]
    if len(matches) == 1:
        return matches[0]
    raise ValueError(f"agent {agent_id!r} must exist exactly once")


def resolve_account_id(config, agent_id, explicit):
    bindings = config.get("bindings") if isinstance(config.get("bindings"), list) else []
    account_bindings = []
    peer_bindings = []
    for binding in bindings:
        if not isinstance(binding, dict) or binding.get("agentId") != agent_id:
            continue
        match = binding.get("match") if isinstance(binding.get("match"), dict) else {}
        if match.get("channel") != "telegram":
            continue
        if any(key in match for key in ("peer", "peerId", "chatId", "senderId")):
            peer_bindings.append(binding)
        elif match.get("accountId") is not None:
            account_bindings.append(str(match.get("accountId")))
    if peer_bindings:
        raise ValueError("peer-specific Telegram bindings must be unified before bridge install")
    unique = sorted(set(account_bindings))
    if explicit:
        if explicit not in unique:
            raise ValueError("explicit Telegram account is not canonically bound to the agent")
        account_id = explicit
    elif len(unique) == 1:
        account_id = unique[0]
    else:
        raise ValueError("Telegram account ID cannot be inferred uniquely")
    if account_bindings.count(account_id) != 1:
        raise ValueError("Telegram account must have exactly one account-level binding")
    return account_id


def resolve_runtime_workspace(config, agent, runtime_root):
    workspace = agent.get("workspace")
    if not isinstance(workspace, str) or not workspace.strip():
        defaults = config.get("agents", {}).get("defaults", {})
        workspace = defaults.get("workspace") if isinstance(defaults, dict) else None
    if not isinstance(workspace, str) or not workspace.startswith("/"):
        workspace = str(PurePosixPath(runtime_root) / "workspace")
    return workspace.rstrip("/")


def resolve_host_workspace(explicit, runtime_workspace, host_root, runtime_root):
    if explicit:
        return ensure_absolute_directory(explicit, "workspace")
    runtime_prefix = runtime_root.rstrip("/") + "/"
    if runtime_workspace == runtime_root.rstrip("/"):
        candidate = host_root
    elif runtime_workspace.startswith(runtime_prefix):
        candidate = host_root / runtime_workspace[len(runtime_prefix) :]
    else:
        candidate = Path(runtime_workspace)
    return ensure_absolute_directory(str(candidate), "workspace")


def nested_dict(value, *keys):
    current = value
    for key in keys:
        if not isinstance(current, dict):
            return {}
        current = current.get(key)
    return current if isinstance(current, dict) else {}


def owner_policy_missing(config, agent, account_id, telegram_ids):
    telegram = nested_dict(config, "channels", "telegram")
    account = nested_dict(telegram, "accounts", account_id)
    command_owners = string_values(nested_dict(config, "commands").get("ownerAllowFrom"))
    elevated = string_values(nested_dict(config, "tools", "elevated", "allowFrom").get("telegram"))
    top_allow = string_values(telegram.get("allowFrom"))
    account_allow = string_values(account.get("allowFrom"))
    top_approvers = string_values(nested_dict(telegram, "execApprovals").get("approvers"))
    account_approvers = string_values(nested_dict(account, "execApprovals").get("approvers"))
    tools_by_sender = nested_dict(agent, "tools").get("toolsBySender")
    tools_by_sender = tools_by_sender if isinstance(tools_by_sender, dict) else {}
    approvals = nested_dict(config, "approvals")
    missing = []
    for telegram_id in telegram_ids:
        checks = {
            "channels.telegram.allowFrom": telegram_id in top_allow,
            "channels.telegram.accounts.allowFrom": telegram_id in account_allow,
            "commands.ownerAllowFrom": f"telegram:{telegram_id}" in command_owners,
            "channels.telegram.execApprovals.approvers": telegram_id in top_approvers,
            "channels.telegram.accounts.execApprovals.approvers": telegram_id in account_approvers,
            "tools.elevated.allowFrom.telegram": telegram_id in elevated,
            "agent.tools.toolsBySender": tools_by_sender.get(f"channel:telegram:{telegram_id}") == {},
        }
        for kind in ("exec", "plugin"):
            targets = nested_dict(approvals, kind).get("targets")
            targets = targets if isinstance(targets, list) else []
            checks[f"approvals.{kind}.targets"] = any(
                isinstance(target, dict)
                and target.get("channel") == "telegram"
                and str(target.get("to")) == telegram_id
                and str(target.get("accountId")) == account_id
                for target in targets
            )
        missing.extend(path for path, present in checks.items() if not present)
    return sorted(set(missing))


def render_block(runtime_root, runtime_workspace, agent_id):
    helper_path = PurePosixPath(runtime_workspace) / "scripts" / HELPER_NAME
    return f"""{START_MARKER}
## OpenClaw proposal approval from Telegram owners

- Every verified exact owner synchronized into the owner layers is approval-authorized by default for Skill Workshop (`plugin`) and persistent `system-agent` proposals. This authority is explicit per proposal; it never means auto-apply or `approvalPolicy=auto`.
- Approve a persistent `system-agent` proposal only from a direct Telegram DM whose current sender is an exact `commands.ownerAllowFrom` owner; the proposal itself may have originated in a direct owner chat or an explicitly enabled Zalo group on the same canonical agent.
- Treat `duyệt`, `anh duyệt`, `approve`, `đồng ý áp dụng`, or equivalent wording as consent only for the specific proposal immediately before it. Never infer consent from a group, forwarded message, question, partial agreement, or another sender.
- Run `openclaw approvals pending --json` first. Require exactly one real pending `system-agent` record for agent `{agent_id}` whose source is a configured direct owner chat or explicitly enabled Zalo group and whose summary matches the approved change. A displayed proposal hash is not sufficient by itself.
- If the record is absent, expired, ambiguous, belongs to another session, or differs from the approved change, do not approve it and do not claim that Dashboard approval is pending.
- Check with `{helper_path} --openclaw-root {runtime_root} --telegram-id <CURRENT_OWNER_ID> --approval-id <REAL_PENDING_ID> --agent-id {agent_id} --check`; only after it passes, rerun with `--apply`.
- The helper uses Python 3's standard library and does not require `jq`. A missing runtime dependency must never be reported as a missing owner permission.
- In Zalo status, `dm:pairing` is the DM access policy, not an authentication result. Never claim that Zalo login expired from this field, a stale delivery error, or a retry warning alone; use the live channel probe/plugin authentication result.
- `system-agent` proposals always use `allow-once`, never `allow-always`. Verify the pending record disappears, validate config, inspect effective changed fields, and probe only the affected channel/service without sending a real message.
- Exec/plugin approvals continue to use native Telegram buttons or `/approve <id> allow-once`.
- Never expose tokens, credentials, cookies, raw approval storage, or unrelated pending requests.
{END_MARKER}"""


def merge_managed_block(existing, block):
    start_count = existing.count(START_MARKER)
    end_count = existing.count(END_MARKER)
    if start_count != end_count or start_count > 1:
        raise ValueError("AGENTS.md contains malformed approval bridge markers")
    if start_count == 1:
        start = existing.index(START_MARKER)
        end = existing.index(END_MARKER, start) + len(END_MARKER)
        return existing[:start] + block + existing[end:]
    prefix = existing.rstrip()
    return f"{prefix}\n\n{block}\n" if prefix else f"{block}\n"


def atomic_write(path, data, mode, uid, gid):
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temp_name, mode)
        if os.geteuid() == 0:
            os.chown(temp_name, uid, gid)
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def file_metadata(path, fallback_stat):
    if path.exists():
        current = path.stat()
        return stat.S_IMODE(current.st_mode), current.st_uid, current.st_gid
    return 0o644, fallback_stat.st_uid, fallback_stat.st_gid


def default_backup_dir():
    if os.geteuid() == 0:
        return Path("/root/_Backups/openclaw-telegram-approval-bridge")
    return Path.home() / ".openclaw-backups" / "telegram-approval-bridge"


def create_backup(backup_base, agents_path, helper_path, agents_after, helper_after):
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    operation_dir = backup_base / timestamp
    suffix = 0
    while operation_dir.exists():
        suffix += 1
        operation_dir = backup_base / f"{timestamp}-{suffix}"
    operation_dir.mkdir(parents=True, mode=0o700)
    os.chmod(operation_dir, 0o700)
    files = {}
    for label, path, after in (
        ("agents", agents_path, agents_after),
        ("helper", helper_path, helper_after),
    ):
        existed = path.exists()
        backup_name = f"{label}.before" if existed else None
        if existed:
            shutil.copy2(path, operation_dir / backup_name)
            os.chmod(operation_dir / backup_name, 0o600)
        metadata_path = path if existed else path.parent
        while not metadata_path.exists():
            metadata_path = metadata_path.parent
        current_stat = metadata_path.stat()
        files[label] = {
            "path": str(path),
            "existed": existed,
            "backup": backup_name,
            "beforeSha256": sha256_file(path),
            "afterSha256": sha256_bytes(after),
            "mode": stat.S_IMODE(current_stat.st_mode),
            "uid": current_stat.st_uid,
            "gid": current_stat.st_gid,
        }
    manifest = {
        "schemaVersion": 1,
        "operation": "openclaw-telegram-approval-bridge",
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "files": files,
    }
    manifest_path = operation_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    os.chmod(manifest_path, 0o600)
    return manifest_path


def rollback(manifest_value):
    manifest_path = Path(manifest_value).expanduser()
    if not manifest_path.is_absolute() or not manifest_path.is_file():
        raise ValueError("rollback manifest must be an absolute file path")
    manifest = load_json(manifest_path)
    if manifest.get("operation") != "openclaw-telegram-approval-bridge":
        raise ValueError("manifest operation does not match this installer")
    files = manifest.get("files") if isinstance(manifest.get("files"), dict) else {}
    for label in ("agents", "helper"):
        entry = files.get(label) if isinstance(files.get(label), dict) else None
        if not entry:
            raise ValueError("rollback manifest is incomplete")
        path = Path(entry.get("path", ""))
        if not path.is_absolute():
            raise ValueError("rollback target path is invalid")
        if sha256_file(path) != entry.get("afterSha256"):
            raise ValueError(f"rollback refused: {label} changed after apply")
    for label in ("agents", "helper"):
        entry = files[label]
        path = Path(entry["path"])
        if entry.get("existed"):
            backup_path = manifest_path.parent / entry["backup"]
            if not backup_path.is_file() or sha256_file(backup_path) != entry.get("beforeSha256"):
                raise ValueError(f"rollback backup for {label} is invalid")
            atomic_write(
                path,
                backup_path.read_bytes(),
                int(entry["mode"]),
                int(entry["uid"]),
                int(entry["gid"]),
            )
        else:
            path.unlink()
    print("status=rolled-back")
    print(f"manifest={manifest_path}")


def main():
    args = parse_args()
    if args.rollback_manifest:
        rollback(args.rollback_manifest)
        return
    if not args.openclaw_root:
        raise ValueError("--openclaw-root is required")
    if not args.telegram_id:
        raise ValueError("at least one --telegram-id is required")
    telegram_ids = []
    for telegram_id in args.telegram_id:
        if not telegram_id.isdigit():
            raise ValueError("Telegram IDs must be numeric")
        if telegram_id not in telegram_ids:
            telegram_ids.append(telegram_id)

    host_root = ensure_absolute_directory(args.openclaw_root, "openclaw root")
    runtime_root = (args.runtime_openclaw_root or str(host_root)).rstrip("/")
    if not runtime_root.startswith("/"):
        raise ValueError("runtime OpenClaw root must be absolute")
    config_path = host_root / "openclaw.json"
    config = load_json(config_path)
    agent = resolve_agent(config, args.agent_id)
    account_id = resolve_account_id(config, args.agent_id, args.account_id)
    runtime_workspace = resolve_runtime_workspace(config, agent, runtime_root)
    host_workspace = resolve_host_workspace(
        args.workspace, runtime_workspace, host_root, runtime_root
    )
    missing = owner_policy_missing(config, agent, account_id, telegram_ids)
    if missing:
        print("status=owner-policy-incomplete")
        for path in missing:
            print(f"missing={path}")
        raise SystemExit(2)

    agents_path = host_workspace / "AGENTS.md"
    helper_path = host_workspace / "scripts" / HELPER_NAME
    existing_agents = agents_path.read_text(encoding="utf-8") if agents_path.exists() else ""
    block = render_block(runtime_root, runtime_workspace, args.agent_id)
    desired_agents = merge_managed_block(existing_agents, block).encode("utf-8")
    helper_source = Path(__file__).with_name(HELPER_NAME).read_bytes()
    changes = []
    if not agents_path.exists() or agents_path.read_bytes() != desired_agents:
        changes.append("workspace.AGENTS.md")
    if not helper_path.exists() or helper_path.read_bytes() != helper_source:
        changes.append("workspace.approval-helper")
    elif stat.S_IMODE(helper_path.stat().st_mode) != 0o700:
        changes.append("workspace.approval-helper-mode")

    mode = "apply" if args.apply else "check" if args.check else "dry-run"
    print(f"mode={mode}")
    print(f"agent_id={args.agent_id}")
    print(f"account_id={account_id}")
    print(f"owner_count={len(telegram_ids)}")
    print(f"change_count={len(changes)}")
    for change in changes:
        print(f"change={change}")

    if args.check:
        if changes:
            print("status=not-compliant")
            raise SystemExit(2)
        print("status=compliant")
        return
    if args.dry_run:
        print("status=changes-required" if changes else "status=already-compliant")
        return
    if not changes:
        print("status=already-compliant")
        return

    workspace_stat = host_workspace.stat()
    agents_mode, agents_uid, agents_gid = file_metadata(agents_path, workspace_stat)
    helper_uid = agents_uid if agents_path.exists() else workspace_stat.st_uid
    helper_gid = agents_gid if agents_path.exists() else workspace_stat.st_gid
    backup_base = ensure_absolute_directory(
        args.backup_dir or str(default_backup_dir()), "backup directory", must_exist=False
    )
    backup_base.mkdir(parents=True, exist_ok=True)
    os.chmod(backup_base, 0o700)
    manifest_path = create_backup(
        backup_base, agents_path, helper_path, desired_agents, helper_source
    )
    atomic_write(agents_path, desired_agents, agents_mode, agents_uid, agents_gid)
    atomic_write(helper_path, helper_source, 0o700, helper_uid, helper_gid)
    if agents_path.read_bytes() != desired_agents or helper_path.read_bytes() != helper_source:
        raise RuntimeError("post-write verification failed")
    if stat.S_IMODE(helper_path.stat().st_mode) != 0o700:
        raise RuntimeError("helper mode verification failed")
    print("status=applied")
    print(f"manifest={manifest_path}")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(2)
