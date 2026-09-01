#!/usr/bin/env python3
import json
import os
import stat
import subprocess
import tempfile
import time
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
INSTALLER = SCRIPT_DIR / "install_approval_bridge.py"
HELPER = SCRIPT_DIR / "approve_system_agent_from_telegram.sh"


def compliant_config(workspace, telegram_id="123456789", account_id="main"):
    owner_key = f"channel:telegram:{telegram_id}"
    target = {"channel": "telegram", "to": telegram_id, "accountId": account_id}
    return {
        "agents": {
            "defaults": {"workspace": str(workspace)},
            "entries": {
                "main": {
                    "workspace": str(workspace),
                    "tools": {"toolsBySender": {owner_key: {}, "*": {"deny": ["group:runtime"]}}},
                }
            },
        },
        "bindings": [
            {"agentId": "main", "match": {"channel": "telegram", "accountId": account_id}}
        ],
        "channels": {
            "telegram": {
                "allowFrom": [telegram_id],
                "execApprovals": {"approvers": [telegram_id], "target": "dm"},
                "accounts": {
                    account_id: {
                        "allowFrom": [telegram_id],
                        "execApprovals": {"approvers": [telegram_id], "target": "dm"},
                    }
                },
            }
        },
        "commands": {"ownerAllowFrom": [f"telegram:{telegram_id}"]},
        "tools": {"elevated": {"allowFrom": {"telegram": [telegram_id]}}},
        "approvals": {
            "exec": {"targets": [target]},
            "plugin": {"targets": [target]},
        },
    }


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / ".openclaw"
        self.workspace = self.root / "workspace"
        self.workspace.mkdir(parents=True)
        (self.workspace / "AGENTS.md").write_text("# Existing\n", encoding="utf-8")
        (self.root / "openclaw.json").write_text(
            json.dumps(compliant_config(self.workspace)), encoding="utf-8"
        )
        self.backups = Path(self.temp.name) / "backups"

    def tearDown(self):
        self.temp.cleanup()

    def run_installer(self, action, extra=None, check=True):
        command = [
            "python3",
            str(INSTALLER),
            "--openclaw-root",
            str(self.root),
            "--runtime-openclaw-root",
            str(self.root),
            "--workspace",
            str(self.workspace),
            "--telegram-id",
            "123456789",
            "--account-id",
            "main",
            "--agent-id",
            "main",
            "--backup-dir",
            str(self.backups),
            action,
        ]
        if extra:
            command.extend(extra)
        return subprocess.run(command, text=True, capture_output=True, check=check)

    def test_apply_check_idempotent_and_rollback(self):
        dry_run = self.run_installer("--dry-run")
        self.assertIn("status=changes-required", dry_run.stdout)
        applied = self.run_installer("--apply")
        self.assertIn("status=applied", applied.stdout)
        manifest_line = next(
            line for line in applied.stdout.splitlines() if line.startswith("manifest=")
        )
        manifest = Path(manifest_line.split("=", 1)[1])
        agents_text = (self.workspace / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("openclaw-telegram-owner-approval:start", agents_text)
        helper = self.workspace / "scripts" / HELPER.name
        self.assertTrue(helper.is_file())
        self.assertEqual(stat.S_IMODE(helper.stat().st_mode), 0o700)
        checked = self.run_installer("--check")
        self.assertIn("status=compliant", checked.stdout)
        reapplied = self.run_installer("--apply")
        self.assertIn("status=already-compliant", reapplied.stdout)
        rollback = subprocess.run(
            ["python3", str(INSTALLER), "--rollback-manifest", str(manifest)],
            text=True,
            capture_output=True,
            check=True,
        )
        self.assertIn("status=rolled-back", rollback.stdout)
        self.assertEqual((self.workspace / "AGENTS.md").read_text(encoding="utf-8"), "# Existing\n")
        self.assertFalse(helper.exists())

    def test_owner_policy_missing_fails_closed(self):
        config_path = self.root / "openclaw.json"
        config = json.loads(config_path.read_text(encoding="utf-8"))
        config["commands"]["ownerAllowFrom"] = []
        config_path.write_text(json.dumps(config), encoding="utf-8")
        result = self.run_installer("--dry-run", check=False)
        self.assertEqual(result.returncode, 2)
        self.assertIn("status=owner-policy-incomplete", result.stdout)
        self.assertFalse((self.workspace / "scripts" / HELPER.name).exists())

    def test_helper_check_apply_flow(self):
        fixture = Path(self.temp.name) / "helper"
        bin_dir = fixture / "bin"
        bin_dir.mkdir(parents=True)
        config_path = fixture / "openclaw.json"
        config_path.write_text(
            json.dumps({"commands": {"ownerAllowFrom": ["telegram:123456789"]}}),
            encoding="utf-8",
        )
        state_path = fixture / "state.json"
        state_path.write_text(
            json.dumps(
                {
                    "approvals": [
                        {
                            "id": "system-agent:test",
                            "kind": "system-agent",
                            "agentId": "main",
                            "sessionKey": "agent:main:telegram:direct:123456789",
                            "expiresAtMs": int(time.time() * 1000) + 600000,
                            "summary": "OpenClaw change: set config demo=true",
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        fake_openclaw = bin_dir / "openclaw"
        fake_openclaw.write_text(
            """#!/usr/bin/env bash
set -euo pipefail
state=${FAKE_APPROVAL_STATE:?}
if [[ ${1:-} == approvals && ${2:-} == pending ]]; then
  cat "$state"
elif [[ ${1:-} == approvals && ${2:-} == resolve ]]; then
  printf '{"approvals":[]}\\n' >"$state"
  printf '{"applied":true,"approval":{"status":"allowed"}}\\n'
elif [[ ${1:-} == config && ${2:-} == validate ]]; then
  printf 'Config valid\\n'
else
  exit 90
fi
""",
            encoding="utf-8",
        )
        fake_openclaw.chmod(0o700)
        environment = os.environ.copy()
        environment["PATH"] = f"{bin_dir}:{environment['PATH']}"
        environment["FAKE_APPROVAL_STATE"] = str(state_path)
        base = [
            str(HELPER),
            "--openclaw-root",
            str(fixture),
            "--telegram-id",
            "123456789",
            "--approval-id",
            "system-agent:test",
            "--agent-id",
            "main",
        ]
        checked = subprocess.run(base + ["--check"], env=environment, text=True, capture_output=True, check=True)
        self.assertIn("status=pending", checked.stdout)
        applied = subprocess.run(base + ["--apply"], env=environment, text=True, capture_output=True, check=True)
        self.assertIn("status=allowed", applied.stdout)
        self.assertEqual(json.loads(state_path.read_text(encoding="utf-8")), {"approvals": []})


if __name__ == "__main__":
    unittest.main()
