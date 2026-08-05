#!/usr/bin/env python3
import argparse
import json
import re
import socket
import sys
from dataclasses import asdict, dataclass
from pathlib import Path


DEFAULT_BASE_DIR = Path("/root/Automation/facebook/01_Mess_Fanpage")
DEFAULT_SOURCE = DEFAULT_BASE_DIR / "01_mes_op_oplw"
DEFAULT_OPENCLAW_CONFIG = Path("/root/.openclaw/openclaw.json")
DEFAULT_DISPATCHER = DEFAULT_BASE_DIR / "messenger_dispatcher/app.py"


@dataclass
class Check:
    level: str
    name: str
    detail: str


def port_is_listening(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.2)
        return sock.connect_ex(("127.0.0.1", port)) == 0


def next_free_port(start, stop=8999):
    for port in range(max(start, 1024), stop + 1):
        if not port_is_listening(port):
            return port
    return None


def file_contains(path, needle):
    try:
        return needle in path.read_text(encoding="utf-8", errors="replace")
    except (OSError, UnicodeError):
        return False


def tree_contains(roots, needle):
    matches = []
    for root in roots:
        if not root.exists():
            continue
        candidates = [root] if root.is_file() else root.rglob("*")
        for path in candidates:
            if path.is_file() and file_contains(path, needle):
                matches.append(str(path))
    return matches


def messenger_agent_ids(config_path):
    if not config_path.is_file():
        return set(), None
    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return set(), type(exc).__name__

    agents = data.get("agents", {})
    values = []
    if isinstance(agents, dict):
        if isinstance(agents.get("list"), list):
            values = agents["list"]
        else:
            values = [{"id": key} for key in agents]
    elif isinstance(agents, list):
        values = agents

    result = set()
    for item in values:
        if isinstance(item, dict):
            agent_id = str(item.get("id", "")).strip()
            if agent_id.startswith("messenger-"):
                result.add(agent_id)
    return result, None


def add(checks, condition, ok_detail, bad_level, bad_detail, name):
    if condition:
        checks.append(Check("OK", name, ok_detail))
    else:
        checks.append(Check(bad_level, name, bad_detail))


def parse_args():
    parser = argparse.ArgumentParser(
        description="Read-only preflight for a new Messenger Fanpage bot."
    )
    parser.add_argument("--code", required=True, help="Short code, e.g. dvtl")
    parser.add_argument("--port", required=True, type=int, help="Local bot port")
    parser.add_argument(
        "--knowledge-root", required=True, type=Path, help="Knowledge directory"
    )
    parser.add_argument(
        "--mode", choices=("direct", "dispatcher"), default="direct"
    )
    parser.add_argument("--public-route", help="Public webhook path")
    parser.add_argument("--course-env", type=Path, help="Optional shared env path")
    parser.add_argument("--base-dir", type=Path, default=DEFAULT_BASE_DIR)
    parser.add_argument("--source-project", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--openclaw-config", type=Path, default=DEFAULT_OPENCLAW_CONFIG)
    parser.add_argument("--dispatcher-app", type=Path, default=DEFAULT_DISPATCHER)
    parser.add_argument("--json", action="store_true", help="Print JSON output")
    return parser.parse_args()


def main():
    args = parse_args()
    raw_code = args.code.strip().lower()
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{1,31}", raw_code):
        print("ERROR: --code must use 2-32 lowercase letters, digits, _ or -", file=sys.stderr)
        return 2
    if not 1024 <= args.port <= 65535:
        print("ERROR: --port must be between 1024 and 65535", file=sys.stderr)
        return 2

    folder_code = raw_code.replace("-", "_")
    agent_code = raw_code.replace("_", "-")
    project_name = f"01_mes_op_{folder_code}"
    target = args.base_dir / project_name
    unit_name = f"{project_name}.service"
    unit_path = Path("/etc/systemd/system") / unit_name
    agent_id = f"messenger-{agent_code}"
    workspace = Path(f"/root/.openclaw/workspace_messenger_{folder_code}")
    public_route = args.public_route or f"/messenger-{agent_code}/webhook/facebook"

    checks = []
    expected_source_files = (
        "app/main.py",
        "app/settings.py",
        "app/chatbot.py",
        "app/facebook.py",
        "app/database.py",
        "app/knowledge.py",
        "tests/test_core.py",
        ".env.example",
        "README.md",
    )
    missing_source = [
        relative
        for relative in expected_source_files
        if not (args.source_project / relative).is_file()
    ]
    add(
        checks,
        not missing_source,
        f"template ready: {args.source_project}",
        "ERROR",
        f"missing template files: {', '.join(missing_source)}",
        "source_project",
    )
    add(
        checks,
        not target.exists(),
        f"target is available: {target}",
        "CONFLICT",
        f"target already exists: {target}",
        "target_project",
    )
    add(
        checks,
        args.knowledge_root.is_dir(),
        f"knowledge root exists: {args.knowledge_root}",
        "ERROR",
        f"knowledge root missing: {args.knowledge_root}",
        "knowledge_root",
    )
    if args.course_env:
        add(
            checks,
            args.course_env.is_file(),
            f"shared env exists: {args.course_env}",
            "WARN",
            f"shared env missing: {args.course_env}",
            "course_env",
        )
    add(
        checks,
        not port_is_listening(args.port),
        f"port is free: 127.0.0.1:{args.port}",
        "CONFLICT",
        f"port is already listening: 127.0.0.1:{args.port}",
        "local_port",
    )
    checks.append(
        Check(
            "INFO",
            "next_free_port",
            str(next_free_port(max(args.port, 8811)) or "none-found"),
        )
    )
    add(
        checks,
        not unit_path.exists(),
        f"unit name is available: {unit_name}",
        "CONFLICT",
        f"unit already exists: {unit_path}",
        "systemd_unit",
    )
    add(
        checks,
        not workspace.exists(),
        f"workspace path is available: {workspace}",
        "CONFLICT",
        f"workspace already exists: {workspace}",
        "openclaw_workspace",
    )

    agent_ids, config_error = messenger_agent_ids(args.openclaw_config)
    if config_error:
        checks.append(
            Check(
                "WARN",
                "openclaw_config",
                f"could not parse config ({config_error}); inspect manually",
            )
        )
    else:
        add(
            checks,
            agent_id not in agent_ids,
            f"agent id is available: {agent_id}",
            "CONFLICT",
            f"agent already exists: {agent_id}",
            "openclaw_agent",
        )

    nginx_roots = (
        Path("/etc/nginx/sites-available"),
        Path("/etc/nginx/conf.d"),
    )
    nginx_matches = tree_contains(nginx_roots, public_route)
    add(
        checks,
        not nginx_matches,
        f"public route is available: {public_route}",
        "CONFLICT",
        f"public route already appears in: {', '.join(nginx_matches)}",
        "nginx_route",
    )

    if args.mode == "dispatcher":
        add(
            checks,
            args.dispatcher_app.is_file(),
            f"dispatcher found: {args.dispatcher_app}",
            "ERROR",
            f"dispatcher missing: {args.dispatcher_app}",
            "dispatcher",
        )
        if args.dispatcher_app.is_file():
            target_env = str(target / ".env")
            target_url = f"http://127.0.0.1:{args.port}/webhook/facebook"
            dispatcher_conflict = file_contains(
                args.dispatcher_app, target_env
            ) or file_contains(args.dispatcher_app, target_url)
            add(
                checks,
                not dispatcher_conflict,
                "dispatcher route slot is available",
                "CONFLICT",
                "dispatcher already references target env or port",
                "dispatcher_route",
            )

    summary = {
        "code": raw_code,
        "project": str(target),
        "unit": unit_name,
        "port": args.port,
        "mode": args.mode,
        "public_route": public_route,
        "agent_id": agent_id,
        "workspace": str(workspace),
        "checks": [asdict(check) for check in checks],
    }
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(f"Messenger Fanpage preflight: {project_name}")
        for check in checks:
            print(f"[{check.level}] {check.name}: {check.detail}")

    blocking = {"ERROR", "CONFLICT"}
    return 2 if any(check.level in blocking for check in checks) else 0


if __name__ == "__main__":
    raise SystemExit(main())

