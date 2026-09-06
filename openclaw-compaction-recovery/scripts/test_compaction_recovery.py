#!/usr/bin/env python3
"""Offline safety regression tests; no production or model calls."""

import contextlib
import copy
import io
import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import Mock

import audit_openclaw_compaction as guard


def fixture_config():
    return {
        "agents": {
            "defaults": {
                "contextTokens": 96000,
                "model": {"primary": "fixture/large"},
                "compaction": {
                    "mode": "safeguard", "reserveTokens": 16000,
                    "reserveTokensFloor": 12000, "keepRecentTokens": 12000,
                    "maxHistoryShare": 0.65, "recentTurnsPreserve": 4,
                    "timeoutSeconds": 180, "memoryFlush": {"enabled": True},
                },
            },
            "list": [{"id": "main"}],
        },
        "models": {"providers": {"fixture": {"apiKey": "TEST-ONLY-NEVER-VALID", "models": [{"id": "large", "contextWindow": 128000}]}}},
        "channels": {"telegram": {"enabled": True, "tokenFile": "/fixture/private-token"}},
        "tools": {"profile": "full"}, "session": {"dmScope": "per-channel-peer"},
    }


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.root = self.directory / "member/.openclaw"
        self.root.mkdir(parents=True)
        self.path = self.root / "openclaw.json"
        self.original = guard.encode(fixture_config())
        self.path.write_bytes(self.original)
        self.path.chmod(0o640)
        self.backup_root = self.directory / "backups"
        self.runtime = Mock()

    def apply(self):
        return guard.apply_target(self.root, self.runtime, guard.digest(self.path.read_bytes()), self.backup_root)

    def test_profile_preserves_unrelated_config_and_is_idempotent(self):
        original = fixture_config()
        candidate, report = guard.plan(original)
        self.assertTrue(report["eligible"])
        self.assertEqual(original, fixture_config())
        for key in ["models", "channels", "tools", "session"]:
            self.assertEqual(original[key], candidate[key])
        self.assertEqual(original["agents"]["list"], candidate["agents"]["list"])
        self.assertEqual(candidate["agents"]["defaults"]["compaction"]["reserveTokensFloor"], 24000)
        self.assertFalse(guard.plan(candidate)[1]["changes"])

    def test_never_weakens_a_stronger_existing_profile(self):
        config = fixture_config()
        config["agents"]["defaults"]["compaction"].update({
            "reserveTokens": 28000, "reserveTokensFloor": 28000,
            "timeoutSeconds": 900, "keepRecentTokens": 4000,
            "maxHistoryShare": 0.3, "recentTurnsPreserve": 1,
            "qualityGuard": {"enabled": True, "maxRetries": 0},
        })
        self.assertFalse(guard.plan(config)[1]["changes"])

    def test_small_agent_and_fallback_block_shared_defaults(self):
        for override in ["agent", "fallback"]:
            with self.subTest(override=override):
                config = fixture_config()
                config["models"]["providers"]["fixture"]["models"].append({"id": "small", "contextWindow": 16000})
                if override == "agent":
                    config["agents"]["list"].append({"id": "other", "model": "fixture/small"})
                else:
                    config["agents"]["defaults"]["model"]["fallbacks"] = ["fixture/small"]
                self.assertFalse(guard.plan(config)[1]["eligible"])

    def test_unknown_context_and_custom_compaction_require_review(self):
        for change in ["unknown", "provider", "disabled", "excessive-reserve"]:
            with self.subTest(change=change):
                config = fixture_config()
                defaults = config["agents"]["defaults"]
                if change == "unknown":
                    defaults["model"]["fallbacks"] = ["missing/model"]
                elif change == "provider":
                    defaults["compaction"]["provider"] = "custom"
                elif change == "disabled":
                    defaults["compaction"]["enabled"] = False
                else:
                    defaults["compaction"]["reserveTokens"] = 60000
                self.assertFalse(guard.plan(config)[1]["eligible"])

    def test_apply_backup_permissions_and_rollback_exact_bytes(self):
        metadata = self.path.stat()
        result = self.apply()
        backup = Path(result["backupDir"])
        self.assertEqual(self.path.stat().st_mode & 0o777, 0o640)
        self.assertEqual(self.path.stat().st_uid, metadata.st_uid)
        self.assertEqual(backup.stat().st_mode & 0o777, 0o700)
        self.assertEqual((backup / "openclaw.json").stat().st_mode & 0o777, 0o600)
        self.assertEqual((backup / "openclaw.json").read_bytes(), self.original)
        restored = guard.rollback_target(self.root, self.runtime, backup)
        self.assertEqual(restored["action"], "rolled-back")
        self.assertEqual(self.path.read_bytes(), self.original)

    def test_rerun_does_not_rewrite_config_or_create_new_backup(self):
        self.apply()
        before = self.path.stat()
        snapshots = list(self.backup_root.rglob("manifest.json"))
        result = self.apply()
        self.assertEqual(result["action"], "unchanged")
        self.assertEqual(self.path.stat().st_ino, before.st_ino)
        self.assertEqual(self.path.stat().st_mtime_ns, before.st_mtime_ns)
        self.assertEqual(list(self.backup_root.rglob("manifest.json")), snapshots)

    def test_prevalidation_failure_does_not_write_config(self):
        self.runtime.validate.side_effect = [None, guard.GuardError("candidate rejected")]
        with self.assertRaises(guard.GuardError):
            self.apply()
        self.assertEqual(self.path.read_bytes(), self.original)
        self.assertFalse(self.backup_root.exists())

    def test_postvalidation_failure_auto_restores_original(self):
        self.runtime.validate.side_effect = [None, None, guard.GuardError("post validation")]
        with self.assertRaisesRegex(guard.GuardError, "original config restored"):
            self.apply()
        self.assertEqual(self.path.read_bytes(), self.original)
        manifest = json.loads(next(self.backup_root.rglob("manifest.json")).read_text())
        self.assertEqual(manifest["status"], "auto-rolled-back")

    def test_stale_audit_hash_and_concurrent_writer_are_refused(self):
        with self.assertRaises(guard.GuardError):
            guard.apply_target(self.root, self.runtime, "wrong-hash", self.backup_root)
        external = self.original + b"\n"
        def concurrent_change(payload=None):
            if payload:
                self.path.write_bytes(external)
        self.runtime.validate.side_effect = concurrent_change
        with self.assertRaisesRegex(guard.GuardError, "changed during validation"):
            self.apply()
        self.assertEqual(self.path.read_bytes(), external)

    def test_rollback_refuses_new_edits_or_tampered_backup(self):
        backup = Path(self.apply()["backupDir"])
        applied = self.path.read_bytes()
        self.path.write_bytes(applied + b"\n")
        with self.assertRaisesRegex(guard.GuardError, "changed after apply"):
            guard.rollback_target(self.root, self.runtime, backup)
        self.path.write_bytes(applied)
        (backup / "openclaw.json").write_bytes(self.original + b"\n")
        with self.assertRaisesRegex(guard.GuardError, "checksum mismatch"):
            guard.rollback_target(self.root, self.runtime, backup)
        self.assertEqual(self.path.read_bytes(), applied)

    def test_config_file_symlink_and_ambiguous_json_are_refused(self):
        alternate = self.root / "other.json"
        self.path.rename(alternate)
        self.path.symlink_to(alternate)
        with self.assertRaises(guard.GuardError):
            guard.read_config(self.root)
        for payload in [b'{"same":1,"same":2}', b'{"value": NaN}', b'{"apiKey": "PRIVATE-FIXTURE", invalid}']:
            with self.subTest(payload=payload):
                with self.assertRaises(guard.GuardError) as result:
                    guard.decode(payload)
                self.assertNotIn("PRIVATE-FIXTURE", str(result.exception))

    def test_runtime_candidate_cleanup_on_failure(self):
        runtime = guard.Runtime(self.root)
        runtime.run = Mock(side_effect=guard.GuardError("schema mismatch"))
        with self.assertRaises(guard.GuardError):
            runtime.validate(self.original)
        self.assertFalse(list(self.root.glob(".compaction-candidate-*")))
        self.assertEqual(self.path.read_bytes(), self.original)

    def test_tail_log_counts_only_recent_events_without_raw_content(self):
        logs = self.root / "logs"
        logs.mkdir()
        now = datetime.now(timezone.utc)
        (logs / "gateway.log").write_text(
            (now - timedelta(days=3)).isoformat() + " Compaction timed out\n" +
            now.isoformat() + " context-overflow-midturn-precheck PRIVATE-LOG-CONTENT\n"
        )
        report = guard.inspect_target(self.root)
        self.assertEqual(report["recentLogs"]["counts"]["overflow"], 1)
        self.assertEqual(report["recentLogs"]["counts"]["timeout"], 0)
        self.assertNotIn("PRIVATE-LOG-CONTENT", json.dumps(report))
        self.assertNotIn("TEST-ONLY-NEVER-VALID", json.dumps(report))

    def test_fleet_apply_rejected_and_audit_does_not_write(self):
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(guard.main(["--all-members", "--apply"]), 2)
            before = self.path.stat()
            self.assertEqual(guard.main(["--openclaw-root", str(self.root), "--dry-run"]), 0)
        self.assertEqual(self.path.stat().st_mtime_ns, before.st_mtime_ns)
        self.assertEqual(self.path.read_bytes(), self.original)
        self.assertFalse((self.root / ".compaction-recovery.lock").exists())


if __name__ == "__main__":
    unittest.main()
