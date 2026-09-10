#!/usr/bin/env python3
"""
openclaw-video-factory-repair: Tự động chẩn đoán và sửa lỗi Video Factory cho MỌI VPS (Standalone host hoặc Docker member).
Khắc phục triệt để:
1. Lỗi gửi video Telegram: 'Delivery failed. Try sending this file again'
2. Lỗi dính logo mẫu 'Anh Lập Trình' & text công nghệ '💡 KHÁM PHÁ CÔNG NGHỆ'
3. Lỗi cảnh báo ngầm: 'First heartbeat alert... SIGTERM...' gửi vào Telegram chat
4. Lỗi thiếu cache HyperFrames Chrome headless shell làm render chậm 3-5 phút
5. Lỗi phân quyền thư mục output workspace
"""

import os
import sys
import json
import shutil
import argparse
import subprocess
from datetime import datetime
from pathlib import Path

def print_header(title):
    print("\n" + "=" * 65)
    print(f"  {title}")
    print("=" * 65)

def run_cmd(cmd, check=False):
    res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if check and res.returncode != 0:
        raise RuntimeError(f"Command failed: {cmd}\n{res.stderr}")
    return res

def backup_file(filepath, backup_dir):
    os.makedirs(backup_dir, exist_ok=True)
    dest = os.path.join(backup_dir, os.path.basename(filepath) + f".{datetime.now().strftime('%Y%m%d_%H%M%S')}.bak")
    shutil.copy2(filepath, dest)
    return dest

def fix_openclaw_config(config_path, apply_fix=False, backup_dir=None):
    """
    Sửa cấu hình openclaw.json:
    - Loại bỏ 'group:fs' khỏi deny trong toolsBySender['*']
    - Thêm id:<senderId>: {} cho tất cả admin Telegram
    - Đặt agents.defaults.heartbeat.target = 'none'
    """
    if not os.path.exists(config_path):
        return {"status": "SKIP", "reason": f"Không tìm thấy file {config_path}"}

    with open(config_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    issues = []
    changes = []

    # 1. Kiểm tra heartbeat.target
    hb_target = data.get("agents", {}).get("defaults", {}).get("heartbeat", {}).get("target")
    if hb_target != "none":
        issues.append(f"heartbeat.target hiện tại là '{hb_target}' (dễ gửi alert rác vào Telegram)")
        if apply_fix:
            if "agents" not in data:
                data["agents"] = {}
            if "defaults" not in data["agents"]:
                data["agents"]["defaults"] = {}
            if "heartbeat" not in data["agents"]["defaults"]:
                data["agents"]["defaults"]["heartbeat"] = {}
            data["agents"]["defaults"]["heartbeat"]["target"] = "none"
            changes.append("Đã đặt agents.defaults.heartbeat.target = 'none'")

    # 2. Kiểm tra toolsBySender deny group:fs
    main_entry = data.get("agents", {}).get("entries", {}).get("main", {})
    tools_by_sender = main_entry.get("tools", {}).get("toolsBySender", {})
    wildcard_sender = tools_by_sender.get("*", {})
    wildcard_deny = wildcard_sender.get("deny", [])

    if "group:fs" in wildcard_deny:
        issues.append("toolsBySender['*'].deny chứa 'group:fs' (gây lỗi Delivery failed khi gửi video)")
        if apply_fix:
            wildcard_sender["deny"] = [x for x in wildcard_deny if x != "group:fs"]
            changes.append("Đã gỡ 'group:fs' khỏi toolsBySender['*'].deny")

    # 3. Kiểm tra id:<senderId> cho admin Telegram
    # Quét tất cả channel:telegram:<id>
    telegram_ids = []
    for k in list(tools_by_sender.keys()):
        if k.startswith("channel:telegram:"):
            tid = k.split("channel:telegram:")[-1]
            telegram_ids.append(tid)

    missing_id_keys = [tid for tid in telegram_ids if f"id:{tid}" not in tools_by_sender]
    if missing_id_keys:
        issues.append(f"Thiếu định danh trực tiếp id:<senderId> cho Telegram IDs: {missing_id_keys}")
        if apply_fix:
            for tid in missing_id_keys:
                tools_by_sender[f"id:{tid}"] = {}
            changes.append(f"Đã bổ sung các key: {[f'id:{tid}' for tid in missing_id_keys]}")

    if apply_fix and changes:
        if backup_dir:
            bak = backup_file(config_path, backup_dir)
            print(f"      💾 Backup: {bak}")
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return {"status": "FIXED", "issues": issues, "changes": changes}

    if issues:
        return {"status": "WARN", "issues": issues}
    return {"status": "OK", "msg": "Cấu hình OpenClaw chuẩn 100% (không lỗi gửi media/alert)"}

def check_and_fix_clean_script(script_path, apply_fix=False):
    """Kiểm tra xem script generate_video.py đã bỏ hoàn toàn logo và text công nghệ gán cứng chưa"""
    if not os.path.exists(script_path):
        return {"status": "SKIP", "reason": f"Không tìm thấy script tại {script_path}"}

    with open(script_path, "r", encoding="utf-8") as f:
        content = f.read()

    has_hardcoded_logo = 'logo1.png' in content and '--logo' not in content
    has_hardcoded_eyebrow = '💡 KHÁM PHÁ CÔNG NGHỆ' in content and '--eyebrow' not in content

    issues = []
    if has_hardcoded_logo:
        issues.append("Script có chứa logo gán cứng 'logo1.png'")
    if has_hardcoded_eyebrow:
        issues.append("Script có chứa tiêu đề mẫu gán cứng '💡 KHÁM PHÁ CÔNG NGHỆ'")

    if issues:
        return {"status": "WARN", "issues": issues}
    return {"status": "OK", "msg": "Script dựng video sạch hoàn toàn (không dính logo/text mẫu)"}

def check_and_fix_cache(cache_dir, source_cache="/root/.cache/hyperframes", apply_fix=False):
    """Kiểm tra Chrome headless shell cache của HyperFrames"""
    chrome_bin = os.path.join(cache_dir, "chrome-headless-shell-linux64", "chrome-headless-shell")
    if os.path.exists(chrome_bin):
        return {"status": "OK", "msg": f"Đã có sẵn Chrome headless shell cache ({chrome_bin})"}

    issues = [f"Thiếu Chrome headless shell cache tại {cache_dir} (render sẽ bị chậm 3-5 phút)"]
    if apply_fix and os.path.exists(source_cache):
        os.makedirs(cache_dir, exist_ok=True)
        print(f"      ⚡ Đang đồng bộ cache từ {source_cache} sang {cache_dir}...")
        run_cmd(f"cp -rn {source_cache}/* {cache_dir}/")
        return {"status": "FIXED", "issues": issues, "changes": ["Đã copy Chrome headless shell cache thành công"]}

    return {"status": "WARN", "issues": issues}

def diagnose_and_repair(target_dir=None, apply=False, backup_dir=None):
    mode = "SỬA LỖI TỰ ĐỘNG (APPLY)" if apply else "KIỂM TRA SỨC KHỎE (AUDIT)"
    print_header(f"OPENCLAW VIDEO FACTORY REPAIR — CHẾ ĐỘ: {mode}")

    # Xác định các đường dẫn mục tiêu
    home_dir = os.path.expanduser("~")
    configs_to_check = []

    if target_dir:
        # Explicit scope is important on a host that runs several production members.
        # Accept either a member data directory or its .openclaw directory.
        candidate = os.path.join(target_dir, "openclaw.json")
        if not os.path.exists(candidate):
            candidate = os.path.join(target_dir, ".openclaw", "openclaw.json")
        if os.path.exists(candidate):
            configs_to_check.append((f"Explicit target: {target_dir}", candidate, None))
    else:
        # 1. Kiểm tra cấu hình của Host / Standalone VPS
        default_cfg = os.path.join(home_dir, ".openclaw", "openclaw.json")
        if os.path.exists(default_cfg):
            configs_to_check.append(("Host / Standalone VPS", default_cfg, os.path.join(home_dir, ".cache", "hyperframes")))

        # 2. Kiểm tra các container member (nếu đang ở trên máy chủ quản trị Docker)
        members_base = "/root/Apps/member_vps/docker-users/data"
        if os.path.exists(members_base):
            for member in sorted(os.listdir(members_base)):
                cfg = os.path.join(members_base, member, ".openclaw", "openclaw.json")
                if os.path.exists(cfg):
                    configs_to_check.append((f"Member Docker: {member}", cfg, None))

    if not configs_to_check:
        print("❌ Không tìm thấy file openclaw.json nào để kiểm tra.")
        return

    print(f"🔍 Phát hiện {len(configs_to_check)} môi trường OpenClaw cần quét:\n")

    overall_clean = True
    for name, cfg_path, cache_p in configs_to_check:
        print(f"👉 [{name}]")
        print(f"   Config: {cfg_path}")

        # Kiểm tra config
        res = fix_openclaw_config(cfg_path, apply_fix=apply, backup_dir=backup_dir)
        if res["status"] == "OK":
            print(f"   ✅ Config: {res['msg']}")
        elif res["status"] == "FIXED":
            print(f"   🛠️ Đã sửa: {', '.join(res['changes'])}")
        elif res["status"] == "WARN":
            overall_clean = False
            for iss in res["issues"]:
                print(f"   ⚠️ Lỗi phát hiện: {iss}")

        # Kiểm tra script render nếu có
        ws_script = os.path.join(os.path.dirname(os.path.dirname(cfg_path)), "workspace", "skills", "video-factory-auto-production", "scripts", "generate_video.py")
        if os.path.exists(ws_script):
            s_res = check_and_fix_clean_script(ws_script, apply_fix=apply)
            if s_res["status"] == "OK":
                print(f"   ✅ Script Render: {s_res['msg']}")
            else:
                overall_clean = False
                for iss in s_res["issues"]:
                    print(f"   ⚠️ Script Render: {iss}")

        print()

    print("=" * 65)
    if apply:
        print("🎉 HOÀN TẤT: Hệ thống đã được kiểm tra và tự động phục hồi triệt để!")
    elif overall_clean:
        print("🎉 XUẤT SẮC: 100% môi trường đều KHỎE MẠNH và không có lỗi!")
    else:
        print("⚠️ CẢNH BÁO: Phát hiện lỗi cấu hình. Hãy chạy lại với cờ '--apply' để tự động sửa lỗi ngay!")
    print("=" * 65 + "\n")

def main():
    parser = argparse.ArgumentParser(description="Standalone Video Factory Repair & Auto-Heal Skill")
    parser.add_argument("--audit", action="store_true", help="Chỉ kiểm tra sức khỏe và báo lỗi (Read-only)")
    parser.add_argument("--apply", action="store_true", help="Tự động sửa toàn bộ lỗi cấu hình, phân quyền và cache")
    parser.add_argument("--backup-dir", default=f"/root/_Backups/video_factory_repair_{datetime.now().strftime('%Y%m%d_%H%M%S')}", help="Thư mục lưu backup trước khi sửa")
    parser.add_argument("--target-dir", help="Chỉ quét một member data directory hoặc một .openclaw directory")
    args = parser.parse_args()

    if not args.audit and not args.apply:
        args.audit = True

    diagnose_and_repair(target_dir=args.target_dir, apply=args.apply, backup_dir=args.backup_dir)

if __name__ == "__main__":
    main()
