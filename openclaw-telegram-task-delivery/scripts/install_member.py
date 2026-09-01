#!/usr/bin/env python3
"""Install same-origin Telegram task delivery policy for one OpenClaw member."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile


TASK_BLOCK = """<!-- openclaw-telegram-task-delivery:start -->
## Telegram background task completion

- Treat the inbound requester session and its channel/account/conversation as the authoritative delivery destination. Never choose a task-result destination from an allowlist order, the default owner, or the most recent unrelated chat.
- Keep exactly one parent/coordinator responsible for external progress and completion messages. Child sessions and workers return results and artifacts to that coordinator; they do not send independently.
- When a child result is required before answering, call `sessions_spawn` and then `sessions_yield`. Do not end the parent turn with only a future-tense promise and rely on heartbeat to notice completion later.
- When a child completion or recovery event arrives, inspect the retained result and finish the handoff. Do not answer `NO_REPLY` while the requester has not received the result.
- Use `sessions_history` with one pagination style at a time; never combine `offset` and `messageId` in the same call.
- Before sending files, verify that every intended output exists, is readable, opens successfully, and matches the requested format/content. For DOCX/XLSX/PDF, inspect the generated document and render/preview when practical; a filename or unusually small file alone is not proof of completion.
- Send completion through `message` to the explicit Telegram account and exact DM/group/topic derived from the requester session. Require a real `messageId` and matching destination metadata.
- A task is complete only after the result and required attachments have a verified platform receipt. Internal child `deliveryStatus=delivered` is not external Telegram proof.
- If the verified `message` send succeeds, persist or retain its receipt when supported and end with exactly `NO_REPLY` so normal assistant output cannot duplicate it.
- If delivery fails or remains ambiguous, do not claim success. Check the exact destination and receipt, retry once when safe, then report the blocked state to the requester or configured owner.
- Scheduled heartbeat is not the primary completion path. Use the requester-session handoff first; let the delivery watchdog recover only genuinely missing post-completion outbound messages.
<!-- openclaw-telegram-task-delivery:end -->
"""

RELIABLE_MEDIA_BLOCK = """<!-- reliable-media-delivery:start -->
## Reliable media delivery

- Before sending media, confirm the intended local file exists, is readable, and is correct.
- Send with the platform-native tool to the explicit recipient, group, channel, and thread when applicable.
- Consider delivery successful only when the platform returns a real `messageId` and matching destination metadata.
- For media work expected to finish in under 10 seconds, skip a separate future-tense progress message; finish the work, then send the verified completion text and media together.
- If progress acknowledgement is needed, send it with the platform-native `message` tool and require a real `messageId` before starting `exec`, `process`, generation, conversion, or other file work.
- Never put future-tense progress text in normal assistant content in the same turn that launches tools and later sends media; channel runtimes may buffer and replay that text after the media.
- Use one stable request key and one outbound coordinator per request. Workers return artifacts to the coordinator instead of sending progress or results independently.
- Before every progress or completion send, re-read the request state. If it is already completed or has a recorded completion `messageId`, skip the send and return `NO_REPLY`.
- After the `message` tool successfully sends the completion text and media, respond with exactly `NO_REPLY` and no other assistant text.
- If delivery fails or is ambiguous, do not claim success; inspect safely, avoid duplicates, retry once when safe, then report the verified state.
- Follow workspace-specific delivery rules when they are more specific.
<!-- reliable-media-delivery:end -->
"""

TELEGRAM_BLOCK = """<!-- telegram-single-delivery:start -->
## Telegram single-delivery guard

- Derive one stable request key from the inbound chat/session and inbound message ID; do not use an outbound message ID as the only key.
- Allow one coordinator to send for each request. Workers return results to the coordinator and never send progress or completion independently.
- Track `pending -> progress_sent -> completed` and re-read the latest state immediately before every send.
- Send at most one progress message before completion and store its real platform message ID.
- Before completion, confirm there is no completion receipt or matching destination/payload fingerprint. After a verified send, store the receipt before marking completed.
- Drop every late progress callback or extra completion turn for an already completed request and return `NO_REPLY`.
- Detect duplicates by request key, purpose, destination, and payload fingerprint, not only Telegram message ID.
- For an ambiguous result, inspect receipts/history before one safe retry.
<!-- telegram-single-delivery:end -->
"""

HEARTBEAT_BLOCK = """<!-- openclaw-telegram-task-delivery-heartbeat:start -->
## Telegram task-delivery heartbeat rule

- Do not infer an old task completion from conversation history and announce it through the default heartbeat owner route.
- Normal background-task completion must resume the requester session and deliver to that exact Telegram origin.
- Act on a completion only when the runtime provides an explicit child-completion event or the delivery watchdog names the exact task/requester session.
- If there is no explicit recovery event requiring action, return `NO_REPLY`.
<!-- openclaw-telegram-task-delivery-heartbeat:end -->
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--container", required=True)
    parser.add_argument("--data-dir", required=True)
    parser.add_argument("--member-home", required=True)
    parser.add_argument("--agent-id", default="main")
    parser.add_argument("--account-id", required=True)
    parser.add_argument("--owner-id", required=True)
    parser.add_argument("--backup-root", default="/root/_Backups/openclaw-telegram-task-delivery")
    parser.add_argument("--runtime-root", default="/root/Automation/watchdog/openclaw_telegram_task_delivery")
    parser.add_argument("--install-cron", action="store_true")
    parser.add_argument("--apply", action="store_true")
    return parser.parse_args()


def require_safe_value(label: str, value: str, pattern: str) -> None:
    if not re.fullmatch(pattern, value):
        raise SystemExit(f"Invalid {label}")


def run(cmd: list[str], *, check: bool = True, capture: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, text=True, capture_output=capture, check=check)


def docker_openclaw(args: argparse.Namespace, command: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    cmd = ["docker", "exec", "-e", f"HOME={args.member_home}", args.container, "openclaw", *command]
    return run(cmd, check=check)


def append_block(text: str, marker: str, block: str) -> tuple[str, bool]:
    if marker in text:
        return text, False
    suffix = "" if not text or text.endswith("\n") else "\n"
    return f"{text}{suffix}\n{block.rstrip()}\n", True


def atomic_write(path: Path, content: str, mode: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(tmp_name, mode)
        os.replace(tmp_name, path)
    finally:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)


def copy_if_present(src: Path, dst: Path) -> None:
    if src.exists():
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)


def config_set(args: argparse.Namespace, path: str, value: object, apply: bool) -> None:
    encoded = json.dumps(value, ensure_ascii=True, separators=(",", ":"))
    dry = docker_openclaw(args, ["config", "set", path, encoded, "--strict-json", "--dry-run"], check=False)
    if dry.returncode != 0:
        raise SystemExit(f"Config dry-run failed for {path}: {dry.stderr.strip() or dry.stdout.strip()}")
    if apply:
        result = docker_openclaw(args, ["config", "set", path, encoded, "--strict-json"], check=False)
        if result.returncode != 0:
            raise SystemExit(f"Config write failed for {path}: {result.stderr.strip() or result.stdout.strip()}")


def main() -> int:
    args = parse_args()
    require_safe_value("container", args.container, r"[A-Za-z0-9_.-]+")
    require_safe_value("agent id", args.agent_id, r"[A-Za-z0-9_-]+")
    require_safe_value("account id", args.account_id, r"[A-Za-z0-9_-]+")
    require_safe_value("owner id", args.owner_id, r"[0-9]+")

    data_dir = Path(args.data_dir).resolve()
    config_path = data_dir / ".openclaw" / "openclaw.json"
    workspace = data_dir / ".openclaw" / "workspace"
    agents_path = workspace / "AGENTS.md"
    heartbeat_path = workspace / "HEARTBEAT.md"
    if not config_path.is_file() or not agents_path.is_file():
        raise SystemExit("Expected OpenClaw config/workspace files are missing")

    config = json.loads(config_path.read_text(encoding="utf-8"))
    account = (((config.get("channels") or {}).get("telegram") or {}).get("accounts") or {}).get(args.account_id)
    if not isinstance(account, dict):
        raise SystemExit("Telegram account does not exist in the target config")
    allow = {str(v) for v in (account.get("allowFrom") or [])}
    if args.owner_id not in allow:
        raise SystemExit("Selected owner is not in the target Telegram account allowFrom list")

    current_owners = [str(v) for v in ((config.get("commands") or {}).get("ownerAllowFrom") or [])]
    owner_ref = f"telegram:{args.owner_id}"
    owners = [owner_ref, *[v for v in current_owners if v != owner_ref]]

    tools = config.get("tools") or {}
    if "allow" in tools:
        tool_path = "tools.allow"
        tool_values = list(dict.fromkeys([*(tools.get("allow") or []), "message"]))
    else:
        tool_path = "tools.alsoAllow"
        tool_values = list(dict.fromkeys([*(tools.get("alsoAllow") or []), "message"]))

    heartbeat = dict((((config.get("agents") or {}).get("defaults") or {}).get("heartbeat") or {}))
    heartbeat["target"] = "owner"
    heartbeat["accountId"] = args.account_id

    # Validate every config mutation before creating the production backup.
    config_set(args, "commands.ownerAllowFrom", owners, False)
    config_set(args, tool_path, tool_values, False)
    config_set(args, "agents.defaults.heartbeat", heartbeat, False)

    agents_text = agents_path.read_text(encoding="utf-8")
    agent_changes: list[str] = []
    for marker, block, label in [
        ("<!-- openclaw-telegram-task-delivery:start -->", TASK_BLOCK, "task-delivery"),
        ("<!-- reliable-media-delivery:start -->", RELIABLE_MEDIA_BLOCK, "reliable-media"),
        ("<!-- telegram-single-delivery:start -->", TELEGRAM_BLOCK, "telegram-single-delivery"),
    ]:
        agents_text, changed = append_block(agents_text, marker, block)
        if changed:
            agent_changes.append(label)

    heartbeat_text = heartbeat_path.read_text(encoding="utf-8") if heartbeat_path.exists() else ""
    heartbeat_text, heartbeat_changed = append_block(
        heartbeat_text,
        "<!-- openclaw-telegram-task-delivery-heartbeat:start -->",
        HEARTBEAT_BLOCK,
    )

    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    member_name = data_dir.name
    backup_dir = Path(args.backup_root) / member_name / stamp
    runtime_root = Path(args.runtime_root)
    skill_root = Path(__file__).resolve().parents[1]
    workspace_skill = workspace / "skills" / skill_root.name
    cron_path = Path("/etc/cron.d") / f"openclaw-telegram-task-delivery-{member_name}"
    state_file = runtime_root / "state" / f"{member_name}.json"
    log_file = runtime_root / "logs" / f"{member_name}.log"

    print(f"mode={'apply' if args.apply else 'dry-run'}")
    print(f"target_member={member_name}")
    print(f"owner=telegram:{args.owner_id[:2]}***{args.owner_id[-2:]}")
    print(f"config_changes=commands.ownerAllowFrom,{tool_path},agents.defaults.heartbeat")
    print(f"agents_blocks={','.join(agent_changes) if agent_changes else 'already-present'}")
    print(f"heartbeat_block={'add' if heartbeat_changed else 'already-present'}")
    print(f"watchdog={'install' if args.install_cron else 'not-requested'}")

    if not args.apply:
        return 0

    backup_dir.mkdir(parents=True, mode=0o700)
    copy_if_present(config_path, backup_dir / "openclaw.json")
    copy_if_present(agents_path, backup_dir / "workspace" / "AGENTS.md")
    copy_if_present(heartbeat_path, backup_dir / "workspace" / "HEARTBEAT.md")
    copy_if_present(cron_path, backup_dir / "cron" / cron_path.name)
    os.chmod(backup_dir, 0o700)

    config_set(args, "commands.ownerAllowFrom", owners, True)
    config_set(args, tool_path, tool_values, True)
    config_set(args, "agents.defaults.heartbeat", heartbeat, True)

    atomic_write(agents_path, agents_text, agents_path.stat().st_mode & 0o777)
    heartbeat_mode = heartbeat_path.stat().st_mode & 0o777 if heartbeat_path.exists() else 0o644
    atomic_write(heartbeat_path, heartbeat_text, heartbeat_mode)

    if skill_root != workspace_skill.resolve():
        if workspace_skill.exists():
            shutil.rmtree(workspace_skill)
        workspace_skill.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(skill_root, workspace_skill)

    if args.install_cron:
        runtime_root.mkdir(parents=True, exist_ok=True)
        (runtime_root / "state").mkdir(mode=0o700, exist_ok=True)
        (runtime_root / "logs").mkdir(mode=0o700, exist_ok=True)
        shutil.copy2(skill_root / "scripts" / "watch_delivery.py", runtime_root / "watch_delivery.py")
        os.chmod(runtime_root / "watch_delivery.py", 0o755)
        if not state_file.exists():
            state = {"schemaVersion": 1, "installedAtMs": int(dt.datetime.now(dt.timezone.utc).timestamp() * 1000), "tasks": {}}
            atomic_write(state_file, json.dumps(state, indent=2) + "\n", 0o600)
        cron = (
            "SHELL=/bin/bash\n"
            "PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin\n"
            f"*/2 * * * * root /usr/bin/python3 {runtime_root}/watch_delivery.py "
            f"--container {args.container} --data-dir {data_dir} --member-home {args.member_home} "
            f"--agent-id {args.agent_id} --account-id {args.account_id} --state-file {state_file} --apply "
            f">> {log_file} 2>&1\n"
        )
        atomic_write(cron_path, cron, 0o644)

    validate = docker_openclaw(args, ["config", "validate"], check=False)
    if validate.returncode != 0:
        raise SystemExit(f"Final config validation failed; restore {backup_dir}")

    print(f"backup={backup_dir}")
    print(f"workspace_skill={workspace_skill}")
    if args.install_cron:
        print(f"cron={cron_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
