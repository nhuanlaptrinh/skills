#!/usr/bin/env python3
import importlib.util
import json
import os
from pathlib import Path
import sqlite3
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch


source = Path(__file__).with_name("install.py")
spec = importlib.util.spec_from_file_location("installer", source)
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        root = Path(self.directory.name)
        self.args = SimpleNamespace(
            container="user-fixture", member_label="fixture", member_home="/root",
            member_data_dir=root / "member", center_dir=root / "center",
            backup_root=root / "backup", agent="main", threshold=70000,
            idle_seconds=180, apply=False,
        )
        self.registry = {"unrelated": {"run_command": "true", "type": "python"}}
        self.cron = "15 6 * * * /usr/bin/true\n"

    def test_plan_preserves_unrelated_and_is_idempotent(self):
        key, updated, cron = installer.make_plan(self.args, self.registry, self.cron)
        self.assertEqual(updated["unrelated"], self.registry["unrelated"])
        self.assertIn(self.cron.strip(), cron)
        self.assertEqual(installer.make_plan(self.args, updated, cron), (key, updated, cron))
        self.assertEqual(cron.count("# BEGIN member_fixture_sessions_70k"), 1)

    def test_duplicate_scope_is_rejected(self):
        registry = {"another_job": {"run_command": "python3 rotate.py --container user-fixture --key-prefix agent:main:zalouser:"}}
        with self.assertRaisesRegex(RuntimeError, "already covers"):
            installer.make_plan(self.args, registry, self.cron)

    def test_conflicting_cron_block_is_rejected(self):
        cron = "# BEGIN member_fixture_sessions_70k\n* * * * * unexpected-command\n# END member_fixture_sessions_70k\n"
        with self.assertRaisesRegex(RuntimeError, "differs"):
            installer.make_plan(self.args, self.registry, cron)

    def test_dry_run_makes_no_files(self):
        with patch.object(installer, "arguments", return_value=self.args), \
             patch.object(installer, "verify_target"), \
             patch.object(installer, "crontab", return_value=self.cron):
            self.assertEqual(installer.main(), 0)
        self.assertFalse(self.args.center_dir.exists())
        self.assertFalse(self.args.backup_root.exists())

    def test_mount_mismatch_stops_before_rpc(self):
        home = self.args.member_data_dir / ".openclaw"
        (home / "state").mkdir(parents=True)
        (home / "openclaw.json").write_text("{}")
        (home / "state/openclaw.sqlite").touch()
        result = SimpleNamespace(returncode=0, stdout=json.dumps({
            "running": True, "mounts": [{"Destination": "/root", "Source": "/different/member"}],
        }))
        with patch.object(installer, "execute", return_value=result) as execute:
            with self.assertRaisesRegex(RuntimeError, "does not match"):
                installer.verify_target(self.args)
            self.assertEqual(execute.call_count, 1)

    def test_apply_backs_up_and_repeat_does_not_reschedule(self):
        home = self.args.member_data_dir / ".openclaw"
        (home / "state").mkdir(parents=True)
        (home / "openclaw.json").write_text("{}")
        with sqlite3.connect(home / "state/openclaw.sqlite") as database:
            database.execute("create table fixture (value text)")
            database.execute("insert into fixture values ('preserved')")
        path = self.args.center_dir / "project_config.json"
        installer.atomic_write(path, json.dumps(self.registry).encode())
        key, registry, cron = installer.make_plan(self.args, self.registry, self.cron)
        with patch.object(installer, "crontab", side_effect=[self.cron, cron]), \
             patch.object(installer, "execute", return_value=SimpleNamespace(returncode=0)) as execute:
            installer.apply_plan(self.args, path, key, registry, cron, self.cron)
            self.assertEqual(execute.call_count, 1)
        backups = list(self.args.backup_root.glob("*/*"))
        self.assertEqual(len(backups), 1)
        backup = backups[0]
        self.assertEqual((backup / "crontab.before").read_text(), self.cron)
        self.assertEqual((backup / "openclaw.json").stat().st_mode & 0o777, 0o600)
        with sqlite3.connect(backup / "openclaw.sqlite") as database:
            self.assertEqual(database.execute("select value from fixture").fetchone()[0], "preserved")
        self.assertTrue(os.access(self.args.center_dir / "run_project.sh", os.X_OK))
        with patch.object(installer, "crontab", return_value=cron), \
             patch.object(installer, "execute") as execute:
            installer.apply_plan(self.args, path, key, registry, cron, cron)
            execute.assert_not_called()


if __name__ == "__main__":
    unittest.main(verbosity=2)
