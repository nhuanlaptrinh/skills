#!/usr/bin/env python3
"""Set OpenClaw Full Exec & Auto-Approval (Phe duyet khong can hoi duyet).

Configures OpenClaw agent tools.exec to full/off:
- openclaw.json: tools.exec = { host: "gateway", mode: "full", strictInlineEval: false }
- exec_approvals (sqlite/legacy): security = "full", ask = "off", askFallback = "full", autoAllowSkills = true
- Optional: Add/sync a Telegram user ID and/or Zalo user ID as co-owner across all owner layers.
"""

import argparse
import datetime
import json
import os
import pathlib
import shutil
import subprocess
import sys

from native_approvals import (
    ApprovalSnapshot,
    NativeApprovalsError,
    backup_approvals,
    load_approvals,
    save_approvals,
)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Cau hinh OpenClaw tu dong phe duyet lenh terminal khong can hoi qua Telegram hoac Zalo."
    )
    parser.add_argument("--member", help="Ten member VPS (vi du: avata, nguyenpho, nndungct)")
    parser.add_argument("--openclaw-root", help="Duong dan goc .openclaw tren host")
    parser.add_argument("--container", help="Ten docker container (mac dinh: user-<member>)")
    parser.add_argument("--runtime-home", help="Thu muc HOME trong container (mac dinh tu dong xac dinh)")
    parser.add_argument("--agent", default="main", help="Agent ID can cau hinh (mac dinh: main)")
    parser.add_argument("--telegram-id", help="ID Telegram chu so huu hoac dong chu so huu can cap toan quyen")
    parser.add_argument("--zalo-id", help="ID Zalo chu so huu hoac dong chu so huu can cap toan quyen")
    parser.add_argument("--dry-run", action="store_true", help="Kiem tra truoc cac thay doi ma khong ghi file")
    parser.add_argument("--apply", action="store_true", help="Ghi backup, cap nhat cau hinh, validate va reload gateway")
    parser.add_argument("--check", action="store_true", help="Kiem tra tinh trang hien tai")
    parser.add_argument("--backup-base", default="/root/_Backups/openclaw-auto-approval", help="Thu muc goc luu backup")
    return parser.parse_args()


def resolve_paths(args):
    member = args.member
    if member:
        cand1 = pathlib.Path(f"/root/Apps/member_vps/docker-users/data/{member}/.openclaw")
        cand2 = pathlib.Path(f"/root/Apps/member_vps/docker-users/data/{member}/root/.openclaw")
        if cand1.is_dir() and (cand1 / "openclaw.json").is_file():
            root = cand1
            default_runtime_home = f"/home/{member}"
        elif cand2.is_dir() and (cand2 / "openclaw.json").is_file():
            root = cand2
            default_runtime_home = "/root"
        else:
            root = cand1
            default_runtime_home = f"/home/{member}"
        container = args.container or f"user-{member}"
        runtime_home = args.runtime_home or default_runtime_home
    else:
        root = pathlib.Path(args.openclaw_root or "/root/.openclaw")
        container = args.container
        runtime_home = args.runtime_home or "/root"

    config_file = root / "openclaw.json"

    if not config_file.is_file():
        print(f"ERROR: Khong tim thay file openclaw.json tai {config_file}", file=sys.stderr)
        sys.exit(1)

    return root, config_file, container, runtime_home


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json_atomic(path, data):
    tmp_path = str(path) + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")
    os.replace(tmp_path, path)


def get_agent_entry(config: dict, agent_id: str) -> dict:
    agents = config.setdefault("agents", {})
    if "entries" in agents and isinstance(agents["entries"], dict):
        return agents["entries"].setdefault(agent_id, {})
    if "list" in agents and isinstance(agents["list"], list):
        for entry in agents["list"]:
            if isinstance(entry, dict) and entry.get("id") == agent_id:
                return entry
        new_entry = {"id": agent_id}
        agents["list"].append(new_entry)
        return new_entry
    return agents.setdefault("entries", {}).setdefault(agent_id, {})


def main():
    args = parse_args()
    if not (args.dry_run or args.apply or args.check):
        print("ERROR: Vui long chon mot trong cac tuy chon: --dry-run, --apply, hoac --check", file=sys.stderr)
        sys.exit(1)

    root, config_file, container, runtime_home = resolve_paths(args)
    agent_id = args.agent
    telegram_id = args.telegram_id
    zalo_id = args.zalo_id

    # 1. Inspect current config
    config = load_json(config_file)
    target_agent = get_agent_entry(config, agent_id)
    tools = target_agent.setdefault("tools", {})
    exec_cfg = tools.setdefault("exec", {})

    exec_before = {
        "host": exec_cfg.get("host"),
        "mode": exec_cfg.get("mode"),
        "strictInlineEval": exec_cfg.get("strictInlineEval"),
    }

    # Approvals before
    try:
        snapshot = load_approvals(root)
        agent_app_before = snapshot.document.get("agents", {}).get(agent_id, {})
    except Exception:
        snapshot = None
        agent_app_before = {}

    app_before = {
        "security": agent_app_before.get("security"),
        "ask": agent_app_before.get("ask"),
        "askFallback": agent_app_before.get("askFallback"),
        "autoAllowSkills": agent_app_before.get("autoAllowSkills"),
    }

    # Co-owner checks if telegram_id provided
    owner_diff = []
    if telegram_id:
        tg_accounts = config.get("channels", {}).get("telegram", {}).get("accounts", {})
        acc_key = next(iter(tg_accounts.keys()), "main")
        acc = tg_accounts.get(acc_key, {})

        cmds = config.setdefault("commands", {})
        owner_allow = cmds.setdefault("ownerAllowFrom", [])
        if f"telegram:{telegram_id}" not in owner_allow:
            owner_diff.append(f"commands.ownerAllowFrom: them telegram:{telegram_id}")

        approvals = config.setdefault("approvals", {})
        exec_targets = approvals.setdefault("exec", {}).setdefault("targets", [])
        if not any(t.get("to") == telegram_id for t in exec_targets):
            owner_diff.append(f"approvals.exec.targets: them to={telegram_id}")

        plugin_targets = approvals.setdefault("plugin", {}).setdefault("targets", [])
        if not any(t.get("to") == telegram_id for t in plugin_targets):
            owner_diff.append(f"approvals.plugin.targets: them to={telegram_id}")

        elevated = config.setdefault("tools", {}).setdefault("elevated", {})
        elevated_tg = elevated.setdefault("allowFrom", {}).setdefault("telegram", [])
        if telegram_id not in elevated_tg:
            owner_diff.append(f"tools.elevated.allowFrom.telegram: them {telegram_id}")

        sender_map = tools.setdefault("toolsBySender", {})
        if f"channel:telegram:{telegram_id}" not in sender_map or sender_map[f"channel:telegram:{telegram_id}"] != {}:
            owner_diff.append(f"toolsBySender: cap full profile cho channel:telegram:{telegram_id}")

        allow_from = acc.setdefault("allowFrom", [])
        if telegram_id not in allow_from:
            owner_diff.append(f"telegram.accounts.{acc_key}.allowFrom: them {telegram_id}")

        group_allow = acc.setdefault("groupAllowFrom", [])
        if telegram_id not in group_allow:
            owner_diff.append(f"telegram.accounts.{acc_key}.groupAllowFrom: them {telegram_id}")

    # Co-owner checks if zalo_id provided
    zalo_diff = []
    if zalo_id:
        channels = config.setdefault("channels", {})
        zalouser = channels.setdefault("zalouser", {})
        zalo_allow = zalouser.setdefault("allowFrom", [])
        if zalo_id not in zalo_allow:
            zalo_diff.append(f"channels.zalouser.allowFrom: them {zalo_id}")

        cmds = config.setdefault("commands", {})
        owner_allow = cmds.setdefault("ownerAllowFrom", [])
        if f"zalouser:{zalo_id}" not in owner_allow:
            zalo_diff.append(f"commands.ownerAllowFrom: them zalouser:{zalo_id}")

        elevated = config.setdefault("tools", {}).setdefault("elevated", {})
        elevated_zalo = elevated.setdefault("allowFrom", {}).setdefault("zalouser", [])
        if zalo_id not in elevated_zalo:
            zalo_diff.append(f"tools.elevated.allowFrom.zalouser: them {zalo_id}")

        sender_map = tools.setdefault("toolsBySender", {})
        if f"channel:zalouser:{zalo_id}" not in sender_map or sender_map[f"channel:zalouser:{zalo_id}"] != {}:
            zalo_diff.append(f"toolsBySender: cap full profile cho channel:zalouser:{zalo_id}")

        group_allow = zalouser.get("groupAllowFrom")
        if isinstance(group_allow, list) and zalo_id not in group_allow:
            zalo_diff.append(f"channels.zalouser.groupAllowFrom: them {zalo_id}")

    # Check compliance
    exec_compliant = (
        exec_before.get("host") == "gateway"
        and exec_before.get("mode") == "full"
        and exec_before.get("strictInlineEval") is False
    )
    app_compliant = (
        app_before.get("security") == "full"
        and app_before.get("ask") == "off"
    )

    if args.check:
        print(f"target_member: {args.member or 'custom'}")
        print(f"openclaw_root: {root}")
        print(f"agent: {agent_id}")
        print(f"config_exec: {exec_before}")
        print(f"approval_policy: {app_before}")
        if telegram_id:
            print(f"co_owner_status_telegram ({telegram_id}): {'chua day du' if owner_diff else 'day du toan quyen'}")
            if owner_diff:
                for d in owner_diff:
                    print(f"  - thieu: {d}")
        if zalo_id:
            print(f"co_owner_status_zalo ({zalo_id}): {'chua day du' if zalo_diff else 'day du toan quyen'}")
            if zalo_diff:
                for d in zalo_diff:
                    print(f"  - thieu: {d}")
        if exec_compliant and app_compliant and (not telegram_id or not owner_diff) and (not zalo_id or not zalo_diff):
            print("check: PASS (Da cau hinh Full Exec & Phe duyet tu dong thanh cong)")
            sys.exit(0)
        else:
            print("check: FAIL (Chua dat cau hinh Full Exec hoac thieu quyen chu so huu)")
            sys.exit(1)

    if args.dry_run:
        print("=== DRY RUN (Ke hoach thay doi) ===")
        print(f"Target member: {args.member or 'custom'}")
        print(f"Agent ID: {agent_id}")
        print(f"Exec hien tai: {exec_before}")
        print(f"Exec du kien:  {{'host': 'gateway', 'mode': 'full', 'strictInlineEval': False}}")
        print(f"Approval hien tai: {app_before}")
        print(f"Approval du kien:  {{'security': 'full', 'ask': 'off', 'askFallback': 'full', 'autoAllowSkills': True}}")
        if telegram_id:
            print(f"Co-owner Telegram ID: {telegram_id}")
            if owner_diff:
                for d in owner_diff:
                    print(f"  + {d}")
            else:
                print("  (Co-owner Telegram ID da co day du tat ca cac lop quyen)")
        if zalo_id:
            print(f"Co-owner Zalo ID: {zalo_id}")
            if zalo_diff:
                for d in zalo_diff:
                    print(f"  + {d}")
            else:
                print("  (Co-owner Zalo ID da co day du tat ca cac lop quyen)")
        print("=== KET THUC DRY RUN ===")
        sys.exit(0)

    # APPLY
    if args.apply:
        ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        target_name = args.member or "host"
        backup_dir = pathlib.Path(args.backup_base) / target_name / ts
        backup_dir.mkdir(parents=True, exist_ok=True)

        shutil.copy2(config_file, backup_dir / "openclaw.json")
        if snapshot:
            backup_approvals(snapshot, backup_dir, label="pre-auto-approval")
        print(f"Backup da tao tai: {backup_dir}")

        # Update openclaw.json
        exec_cfg["host"] = "gateway"
        exec_cfg["mode"] = "full"
        exec_cfg["strictInlineEval"] = False

        if telegram_id:
            tg_accounts = config.get("channels", {}).get("telegram", {}).get("accounts", {})
            acc_key = next(iter(tg_accounts.keys()), "main")
            acc = tg_accounts.get(acc_key, {})

            cmds = config.setdefault("commands", {})
            owner_allow = cmds.setdefault("ownerAllowFrom", [])
            if f"telegram:{telegram_id}" not in owner_allow:
                owner_allow.append(f"telegram:{telegram_id}")

            approvals = config.setdefault("approvals", {})
            exec_targets = approvals.setdefault("exec", {}).setdefault("targets", [])
            if not any(t.get("to") == telegram_id for t in exec_targets):
                exec_targets.append({"channel": "telegram", "to": telegram_id, "accountId": acc_key})

            plugin_targets = approvals.setdefault("plugin", {}).setdefault("targets", [])
            if not any(t.get("to") == telegram_id for t in plugin_targets):
                plugin_targets.append({"channel": "telegram", "to": telegram_id, "accountId": acc_key})

            elevated = config.setdefault("tools", {}).setdefault("elevated", {})
            elevated_tg = elevated.setdefault("allowFrom", {}).setdefault("telegram", [])
            if telegram_id not in elevated_tg:
                elevated_tg.append(telegram_id)

            sender_map = tools.setdefault("toolsBySender", {})
            sender_map[f"channel:telegram:{telegram_id}"] = {}

            allow_from = acc.setdefault("allowFrom", [])
            if telegram_id not in allow_from:
                allow_from.append(telegram_id)

            group_allow = acc.setdefault("groupAllowFrom", [])
            if telegram_id not in group_allow:
                group_allow.append(telegram_id)

        if zalo_id:
            channels = config.setdefault("channels", {})
            zalouser = channels.setdefault("zalouser", {})
            zalo_allow = zalouser.setdefault("allowFrom", [])
            if zalo_id not in zalo_allow:
                zalo_allow.append(zalo_id)

            cmds = config.setdefault("commands", {})
            owner_allow = cmds.setdefault("ownerAllowFrom", [])
            if f"zalouser:{zalo_id}" not in owner_allow:
                owner_allow.append(f"zalouser:{zalo_id}")

            elevated = config.setdefault("tools", {}).setdefault("elevated", {})
            elevated_zalo = elevated.setdefault("allowFrom", {}).setdefault("zalouser", [])
            if zalo_id not in elevated_zalo:
                elevated_zalo.append(zalo_id)

            sender_map = tools.setdefault("toolsBySender", {})
            sender_map[f"channel:zalouser:{zalo_id}"] = {}

            group_allow = zalouser.get("groupAllowFrom")
            if isinstance(group_allow, list) and zalo_id not in group_allow:
                group_allow.append(zalo_id)

        save_json_atomic(config_file, config)
        print("Da cap nhat openclaw.json thanh cong.")

        # Update approvals via native_approvals
        if snapshot:
            new_doc = json.loads(json.dumps(snapshot.document))
            agents_doc = new_doc.setdefault("agents", {})
            agent_doc = agents_doc.setdefault(agent_id, {})
            agent_doc["security"] = "full"
            agent_doc["ask"] = "off"
            agent_doc["askFallback"] = "full"
            agent_doc["autoAllowSkills"] = True
            if "allowlist" not in agent_doc:
                agent_doc["allowlist"] = []

            save_approvals(snapshot, new_doc, config_path=config_file, runtime_home=runtime_home)
            print("Da cap nhat native approvals thanh cong.")

        # Validate config
        if container:
            val_cmd = [
                "docker", "exec",
                "-e", f"HOME={runtime_home}",
                "-i", container,
                "openclaw", "config", "validate"
            ]
            res = subprocess.run(val_cmd, capture_output=True, text=True)
            if res.returncode != 0:
                print(f"ERROR: openclaw config validate that bai: {res.stderr or res.stdout}", file=sys.stderr)
                print("Dang rollback...", file=sys.stderr)
                shutil.copy2(backup_dir / "openclaw.json", config_file)
                sys.exit(1)
            print("openclaw config validate: HOP LE.")

            # Restart gateway via supervisor
            restart_cmd = ["docker", "exec", container, "supervisorctl", "restart", "openclaw-gateway"]
            res = subprocess.run(restart_cmd, capture_output=True, text=True)
            if res.returncode == 0:
                print("openclaw-gateway da khoi dong lai thanh cong duoi Supervisor.")
            else:
                print(f"Warning: restart openclaw-gateway bao loi: {res.stderr or res.stdout}", file=sys.stderr)
        else:
            res = subprocess.run(["openclaw", "config", "validate"], capture_output=True, text=True)
            if res.returncode != 0:
                print("ERROR: Config validate that bai, rollback...", file=sys.stderr)
                shutil.copy2(backup_dir / "openclaw.json", config_file)
                sys.exit(1)
            print("openclaw config validate: HOP LE.")

        print("=== APPLY HOAN TAT THANH CONG ===")


if __name__ == "__main__":
    main()
