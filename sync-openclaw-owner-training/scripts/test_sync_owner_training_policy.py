#!/usr/bin/env python3
"""Small regression tests for sync_owner_training_policy.py."""

from __future__ import annotations

import importlib.util
import json
import pathlib
import tempfile
import unittest


SCRIPT = pathlib.Path(__file__).with_name("sync_owner_training_policy.py")
SPEC = importlib.util.spec_from_file_location("sync_owner_training_policy", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class PolicyTests(unittest.TestCase):
    def test_append_then_idempotent(self) -> None:
        first, operation = MODULE.render("# Workspace\n")
        self.assertEqual(operation, "append")
        self.assertIn(MODULE.START, first)
        second, operation = MODULE.render(first)
        self.assertEqual(operation, "replace")
        self.assertEqual(second, first)

    def test_reject_duplicate_markers(self) -> None:
        with self.assertRaises(SystemExit):
            MODULE.render(f"{MODULE.START}\n{MODULE.END}\n{MODULE.START}\n{MODULE.END}\n")

    def test_resolve_main_workspace_from_entries(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory) / ".openclaw"
            workspace = root / "workspace"
            workspace.mkdir(parents=True)
            (root / "openclaw.json").write_text(
                json.dumps({"agents": {"entries": {"main": {"workspace": str(workspace)}}}}),
                encoding="utf-8",
            )
            self.assertEqual(MODULE.main_workspace(MODULE.load_config(root)), workspace)


if __name__ == "__main__":
    unittest.main()
