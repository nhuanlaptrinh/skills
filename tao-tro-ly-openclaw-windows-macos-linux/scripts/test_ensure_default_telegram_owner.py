#!/usr/bin/env python3

import json
import os
import pathlib
import sqlite3
import subprocess
import tempfile
import unittest


SCRIPT = pathlib.Path(__file__).with_name("ensure_default_telegram_owner.py")
ADAPTER = pathlib.Path(__file__).with_name("native_approvals.py")


def config_fixture():
    return {
        "agents": {
            "entries": {
                "main": {
                    "workspace": "/root/.openclaw/workspace",
                    "agentDir": "/root/.openclaw/agents/main/agent",
                    "tools": {"exec": {}},
                }
            }
        },
        "channels": {"telegram": {"accounts": {"demo": {}}}},
        "commands": {
            "ownerDisplay": "raw",
            "ownerDisplaySecret": "legacy-fixture",
        },
        "tools": {},
        "bindings": [],
    }


def create_native_db(root: pathlib.Path, document: dict) -> pathlib.Path:
    database = root / "state" / "openclaw.sqlite"
    database.parent.mkdir(parents=True)
    connection = sqlite3.connect(database)
    try:
        connection.execute(
            "CREATE TABLE exec_approvals_config ("
            "config_key TEXT PRIMARY KEY, raw_json TEXT NOT NULL, "
            "socket_path TEXT, has_socket_token INTEGER NOT NULL, "
            "default_security TEXT, default_ask TEXT, default_ask_fallback TEXT, "
            "auto_allow_skills INTEGER, agent_count INTEGER NOT NULL, "
            "allowlist_count INTEGER NOT NULL, updated_at_ms INTEGER NOT NULL)"
        )
        raw = json.dumps(document, indent=2) + "\n"
        connection.execute(
            "INSERT INTO exec_approvals_config VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("current", raw, None, 0, "allowlist", "on-miss", "deny", 0, 0, 0, 1),
        )
        connection.commit()
    finally:
        connection.close()
    return database


class EnsureOwnerTests(unittest.TestCase):
    def run_helper(
        self,
        root: pathlib.Path,
        *extra: str,
        env: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        process_environment = os.environ.copy()
        if env:
            process_environment.update(env)
        return subprocess.run(
            [
                "python3",
                str(SCRIPT),
                "--openclaw-root",
                str(root),
                "--account-id",
                "demo",
                "--agent-id",
                "main",
                "--owner-id",
                "123456789",
                *extra,
            ],
            check=False,
            capture_output=True,
            text=True,
            env=process_environment,
        )

    def test_native_apply_does_not_materialize_legacy_file(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary) / ".openclaw"
            root.mkdir()
            (root / "openclaw.json").write_text(
                json.dumps(config_fixture()), encoding="utf-8"
            )
            create_native_db(
                root,
                {
                    "version": 1,
                    "defaults": {
                        "security": "allowlist",
                        "ask": "on-miss",
                        "askFallback": "deny",
                    },
                    "agents": {},
                },
            )
            result = self.run_helper(root, "--apply", "--backup-dir", str(root / "backups"))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse((root / "exec-approvals.json").exists())
            self.assertIn("state/openclaw.sqlite#exec_approvals_config", result.stdout)
            config = json.loads((root / "openclaw.json").read_text(encoding="utf-8"))
            self.assertNotIn("ownerDisplay", config["commands"])
            self.assertNotIn("ownerDisplaySecret", config["commands"])
            check = self.run_helper(root, "--check")
            self.assertEqual(check.returncode, 0, check.stderr)
            self.assertIn("status=compliant", check.stdout)

    def test_native_socket_token_is_preserved(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary) / ".openclaw"
            root.mkdir()
            (root / "openclaw.json").write_text(
                json.dumps(config_fixture()), encoding="utf-8"
            )
            create_native_db(
                root,
                {
                    "version": 1,
                    "socket": {
                        "path": str(root / "exec-approvals.sock"),
                        "token": "fixture-native-socket-token",
                    },
                    "defaults": {
                        "security": "allowlist",
                        "ask": "on-miss",
                        "askFallback": "deny",
                    },
                    "agents": {},
                },
            )
            result = self.run_helper(root, "--apply", "--backup-dir", str(root / "backups"))
            self.assertEqual(result.returncode, 0, result.stderr)
            output = root / "export.json"
            exported = subprocess.run(
                ["python3", str(ADAPTER), "export", "--root", str(root), "--output", str(output)],
                check=True,
                capture_output=True,
                text=True,
            )
            self.assertNotIn("fixture-native-socket-token", exported.stdout)
            document = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(document["socket"]["token"], "fixture-native-socket-token")

    def test_native_apply_falls_back_when_openclaw_binary_is_missing(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary) / ".openclaw"
            root.mkdir()
            (root / "openclaw.json").write_text(
                json.dumps(config_fixture()), encoding="utf-8"
            )
            create_native_db(
                root,
                {
                    "version": 1,
                    "defaults": {
                        "security": "allowlist",
                        "ask": "on-miss",
                        "askFallback": "deny",
                    },
                    "agents": {},
                },
            )
            missing_binary = str(root / "missing-openclaw")
            result = self.run_helper(
                root,
                "--apply",
                "--backup-dir",
                str(root / "backups"),
                env={"OPENCLAW_BIN": missing_binary},
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse((root / "exec-approvals.json").exists())
            check = self.run_helper(root, "--check")
            self.assertEqual(check.returncode, 0, check.stderr)
            self.assertIn("status=compliant", check.stdout)

    def test_legacy_apply_keeps_json_backend(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary) / ".openclaw"
            root.mkdir()
            (root / "openclaw.json").write_text(
                json.dumps(config_fixture()), encoding="utf-8"
            )
            (root / "exec-approvals.json").write_text(
                json.dumps(
                    {
                        "version": 1,
                        "defaults": {
                            "security": "allowlist",
                            "ask": "on-miss",
                            "askFallback": "deny",
                        },
                        "agents": {},
                    }
                ),
                encoding="utf-8",
            )
            result = self.run_helper(root, "--apply", "--backup-dir", str(root / "backups"))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((root / "exec-approvals.json").is_file())
            self.assertIn("host_approvals=" + str(root / "exec-approvals.json"), result.stdout)


if __name__ == "__main__":
    unittest.main()
