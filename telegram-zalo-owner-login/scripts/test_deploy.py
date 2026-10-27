import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import deploy


class CompatibilityTests(unittest.TestCase):
    def test_supported_releases_and_cli_formats(self):
        for version in ("2026.9.9", "2026.10.6"):
            for output in (version, f"OpenClaw {version} (fe06181)\n"):
                with self.subTest(output=output):
                    self.assertEqual(deploy.supported_core_version(output), version)

    def test_untested_releases_and_suffixes_are_rejected(self):
        for output in ("2026.9.8", "2026.9.10", "2026.10.5", "2026.10.7", "2027.1.1",
                       "2026.10.6-1", "2026.10.6-rc.1", "2026.9.9-beta.1",
                       "untrusted 2026.10.6", "", "2026.10.6\n2026.9.9"):
            with self.subTest(output=output):
                with self.assertRaisesRegex(RuntimeError, "Only tested OpenClaw"):
                    deploy.supported_core_version(output)

    def test_package_metadata_preserves_current_and_legacy_ids(self):
        for plugin_id in (deploy.PLUGIN_ID, deploy.LEGACY_ID):
            with self.subTest(plugin_id=plugin_id):
                package = deploy.package_metadata(plugin_id)
                self.assertEqual(package["name"], plugin_id)
                self.assertEqual(package["version"], "1.2.0")
                self.assertEqual(package["openclaw"]["extensions"], ["./index.mjs"])
                self.assertEqual(package["openclaw"]["compat"], {
                    "pluginApi": ">=2026.9.9 <=2026.10.6", "minGatewayVersion": "2026.9.9"})


class DeploymentChecks(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / ".openclaw"
        self.workspace = self.root / "workspace"
        self.workspace.mkdir(parents=True)
        self.config = {
            "commands": {"ownerAllowFrom": ["telegram:123456789"]},
            "agents": {"entries": {"main": {"workspace": "/root/.openclaw/workspace"}}},
            "channels": {"telegram": {"accounts": {"owner-bot": {}}},
                         "zalouser": {"accounts": {"default": {}}}},
            "bindings": [{"agentId": "main", "match": {"channel": channel, "accountId": account}}
                         for channel, account in (("telegram", "owner-bot"), ("zalouser", "default"))],
            "plugins": {"entries": {deploy.PLUGIN_ID: {"enabled": True}}},
        }
        self.save(self.root / "openclaw.json", self.config)
        self.version = "OpenClaw 2026.10.6 (fe06181)\n"
        self.output = io.StringIO()

    def save(self, destination, value):
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(value))

    def execute(self, arguments, log_path=None, timeout=120):
        if arguments[:2] == ["docker", "inspect"]:
            return json.dumps([{"Source": str(self.root), "Destination": "/root/.openclaw"}])
        if arguments[-2:] == ["openclaw", "--version"]:
            return self.version
        if arguments[-3:] == ["supervisorctl", "status", "openclaw-gateway"]:
            return "openclaw-gateway RUNNING pid 123, uptime 1:00:00\n"
        plugin_id = next(iter(self.config["plugins"]["entries"]))
        plugin = {"id": plugin_id, "status": "loaded", "enabled": True,
                  "toolNames": ["telegram_zalo_login_qr"]}
        if arguments[-4:] == ["openclaw", "plugins", "list", "--json"]:
            return json.dumps({"plugins": [plugin]})
        if arguments[-6:] == ["openclaw", "plugins", "inspect", plugin_id, "--runtime", "--json"]:
            return json.dumps({"plugin": plugin, "commands": ["zaloqr"]})
        if "openclaw/plugin-sdk/routing" in arguments[-2] if len(arguments) > 2 else False:
            accounts = json.loads(arguments[-1])
            return json.dumps([{"channel": a["channel"], "accountId": a["accountId"], "agentId": "main", "matchedBy": "binding"} for a in accounts])
        self.fail(f"Unexpected external command: {arguments}")

    def run_mode(self, mode):
        arguments = ["deploy.py", "--container", "user-test", "--openclaw-root", str(self.root), mode]
        with patch("sys.argv", arguments), patch.object(deploy, "execute", side_effect=self.execute), \
                patch.object(deploy, "validate_runtime") as validate, contextlib.redirect_stdout(self.output):
            deploy.main()
        return validate

    def install_fixture(self, plugin_id=deploy.PLUGIN_ID):
        self.config["plugins"]["entries"] = {plugin_id: {"enabled": True}}
        self.save(self.root / "openclaw.json", self.config)
        directory = self.root / "tools" / ("telegram-zalo-login" if plugin_id == deploy.LEGACY_ID else plugin_id)
        self.save(directory / "package.json", deploy.package_metadata(plugin_id))
        self.save(directory / "settings.json", {
            "pluginId": plugin_id, "telegramAccount": "owner-bot", "zaloAccount": "default",
            "agentId": "main", "runtimeHome": "/root", "runtimeRoot": "/root/.openclaw"})
        (directory / "index.mjs").write_bytes((deploy.SKILL_ROOT / "assets" / "index.mjs").read_bytes())
        skill = self.workspace / "skills" / deploy.PLUGIN_ID / "SKILL.md"
        skill.parent.mkdir(parents=True)
        skill.write_text((deploy.SKILL_ROOT / "references" / "runtime-SKILL.md").read_text())
        (self.workspace / "AGENTS.md").write_text(deploy.START_MARKER + "\n" + deploy.END_MARKER)
        return directory

    def test_dry_run_supports_both_releases_without_writes(self):
        for version in ("2026.9.9", "2026.10.6"):
            with self.subTest(version=version):
                self.version = f"OpenClaw {version} (fe06181)\n"
                before = {path: path.read_bytes() for path in self.root.rglob("*") if path.is_file()}
                self.run_mode("--dry-run").assert_not_called()
                after = {path: path.read_bytes() for path in self.root.rglob("*") if path.is_file()}
                self.assertEqual(before, after)
                self.assertIn(f"core={version}", self.output.getvalue())

    def test_dry_run_rejects_unknown_core(self):
        self.version = "OpenClaw 2026.10.7 (fe06181)\n"
        with self.assertRaisesRegex(RuntimeError, "Only tested OpenClaw"):
            self.run_mode("--dry-run")

    def test_check_accepts_updated_package(self):
        self.install_fixture()
        self.run_mode("--check").assert_called_once()
        self.assertIn("CHECK PASS", self.output.getvalue())

    def test_check_preserves_legacy_plugin(self):
        directory = self.install_fixture(deploy.LEGACY_ID)
        self.run_mode("--check").assert_called_once()
        self.assertTrue(directory.is_dir())
        self.assertFalse((self.root / "tools" / deploy.PLUGIN_ID).exists())

    def test_check_rejects_old_api_pin(self):
        directory = self.install_fixture()
        package = deploy.package_metadata(deploy.PLUGIN_ID)
        package["openclaw"]["compat"]["pluginApi"] = "2026.9.9"
        self.save(directory / "package.json", package)
        with self.assertRaisesRegex(RuntimeError, "compatibility metadata is outdated"):
            self.run_mode("--check")

    def test_check_rejects_unbounded_api_range(self):
        directory = self.install_fixture()
        package = deploy.package_metadata(deploy.PLUGIN_ID)
        package["openclaw"]["compat"]["pluginApi"] = ">=2026.9.9"
        self.save(directory / "package.json", package)
        with self.assertRaisesRegex(RuntimeError, "compatibility metadata is outdated"):
            self.run_mode("--check")

    def test_check_rejects_old_package_version(self):
        directory = self.install_fixture()
        package = deploy.package_metadata(deploy.PLUGIN_ID)
        package["version"] = "1.1.0"
        self.save(directory / "package.json", package)
        with self.assertRaisesRegex(RuntimeError, "package version.*outdated"):
            self.run_mode("--check")


class PluginLoadingChecks(unittest.TestCase):
    def test_runtime_load_requires_tool_and_command(self):
        for status, enabled, tools, commands, accepted in [
            ("loaded", True, ["telegram_zalo_login_qr"], ["zaloqr"], True),
            ("skipped", True, ["telegram_zalo_login_qr"], ["zaloqr"], False),
            ("loaded", False, ["telegram_zalo_login_qr"], ["zaloqr"], False),
            ("loaded", True, [], ["zaloqr"], False),
            ("loaded", True, ["telegram_zalo_login_qr"], [], False),
        ]:
            with self.subTest(status=status, tools=tools, commands=commands):
                plugin = {"id": deploy.PLUGIN_ID, "status": status, "enabled": enabled, "toolNames": tools}
                outputs = iter([json.dumps({"plugins": [plugin]}),
                                json.dumps({"plugin": plugin, "commands": commands})])
                if accepted:
                    deploy.validate_loaded_plugin(lambda arguments: next(outputs), deploy.PLUGIN_ID)
                else:
                    with self.assertRaises(RuntimeError):
                        deploy.validate_loaded_plugin(lambda arguments: next(outputs), deploy.PLUGIN_ID)


if __name__ == "__main__":
    unittest.main()
