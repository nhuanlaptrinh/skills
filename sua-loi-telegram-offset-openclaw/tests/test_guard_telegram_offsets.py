import argparse
import importlib.util
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts/guard_telegram_offsets.py"
SPEC = importlib.util.spec_from_file_location("guard_telegram_offsets", SCRIPT)
GUARD = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(GUARD)


class TelegramOffsetGuardTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.config = self.root / "openclaw.json"
        self.db = self.root / "openclaw.sqlite"
        self.state = self.root / "guard.json"
        self.backups = self.root / "backups"
        self.config.write_text(
            json.dumps(
                {
                    "channels": {
                        "telegram": {
                            "accounts": {
                                "target": {"botToken": "123456:TEST"}
                            }
                        }
                    }
                }
            ),
            encoding="utf-8",
        )
        con = sqlite3.connect(self.db)
        con.executescript(
            """
            CREATE TABLE plugin_state_entries (
              plugin_id TEXT, namespace TEXT, entry_key TEXT, value_json TEXT,
              created_at INTEGER, expires_at INTEGER,
              PRIMARY KEY (plugin_id, namespace, entry_key)
            );
            CREATE TABLE channel_ingress_events (
              queue_name TEXT, event_id TEXT, channel_id TEXT, account_id TEXT,
              status TEXT, lane_key TEXT, payload_json TEXT, metadata_json TEXT,
              received_at INTEGER, updated_at INTEGER, claim_token TEXT,
              claim_owner TEXT, claimed_at INTEGER, attempts INTEGER,
              last_attempt_at INTEGER, last_error TEXT, failed_reason TEXT,
              failed_at INTEGER, completed_at INTEGER,
              PRIMARY KEY (queue_name, event_id)
            );
            """
        )
        con.commit()
        con.close()

    def tearDown(self):
        self.tempdir.cleanup()

    def args(self, apply=False):
        return argparse.Namespace(
            config=self.config,
            state_db=self.db,
            state_file=self.state,
            backup_dir=self.backups,
            gateway_unit="unit-that-does-not-exist.service",
            lock_file=self.root / "guard.lock",
            account_id=[],
            apply=apply,
        )

    def insert_offset(self, update_id):
        con = sqlite3.connect(self.db)
        con.execute(
            "INSERT INTO plugin_state_entries VALUES (?,?,?,?,?,?)",
            (
                "telegram",
                "telegram.update-offsets",
                "target",
                json.dumps({"version": 3, "lastUpdateId": update_id}),
                1,
                None,
            ),
        )
        con.commit()
        con.close()

    def insert_event(self, update_id, received_at):
        con = sqlite3.connect(self.db)
        con.execute(
            "INSERT INTO channel_ingress_events "
            "(queue_name,event_id,channel_id,account_id,status,lane_key,payload_json,"
            "metadata_json,received_at,updated_at,attempts) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (
                "telegram",
                f"{update_id:016d}",
                "telegram",
                "target",
                "completed",
                None,
                "{}",
                None,
                received_at,
                received_at,
                0,
            ),
        )
        con.commit()
        con.close()

    def test_newer_lower_update_id_is_repaired(self):
        self.insert_offset(300)
        self.insert_event(300, 1000)
        self.insert_event(200, 2000)
        result = GUARD.run(self.args(apply=True))
        self.assertEqual(result["repaired_accounts"], ["target"])
        con = sqlite3.connect(self.db)
        count = con.execute("SELECT count(*) FROM plugin_state_entries").fetchone()[0]
        con.close()
        self.assertEqual(count, 0)
        self.assertTrue(Path(result["backup_dir"]).is_dir())

    def test_api_root_change_is_repaired(self):
        self.insert_offset(300)
        self.state.write_text(
            json.dumps(
                {
                    "version": 1,
                    "accounts": {
                        "target": {
                            "api_root": "http://127.0.0.1:8081",
                            "bot_id": "123456",
                        }
                    },
                }
            ),
            encoding="utf-8",
        )
        result = GUARD.run(self.args(apply=True))
        self.assertEqual(result["repaired_accounts"], ["target"])
        self.assertIn("api-root-changed", result["accounts"][0]["reasons"])

    def test_normal_monotonic_offset_is_preserved(self):
        self.insert_offset(300)
        self.insert_event(300, 1000)
        result = GUARD.run(self.args(apply=True))
        self.assertEqual(result["repair_count"], 0)
        con = sqlite3.connect(self.db)
        count = con.execute("SELECT count(*) FROM plugin_state_entries").fetchone()[0]
        con.close()
        self.assertEqual(count, 1)

    def test_targeted_run_preserves_other_account_baselines(self):
        self.state.write_text(
            json.dumps(
                {
                    "version": 1,
                    "accounts": {
                        "other": {
                            "api_root": "https://api.telegram.org",
                            "bot_id": "999999",
                        }
                    },
                }
            ),
            encoding="utf-8",
        )
        args = self.args(apply=True)
        args.account_id = ["target"]
        GUARD.run(args)
        state = json.loads(self.state.read_text(encoding="utf-8"))
        self.assertIn("other", state["accounts"])
        self.assertIn("target", state["accounts"])


if __name__ == "__main__":
    unittest.main()
