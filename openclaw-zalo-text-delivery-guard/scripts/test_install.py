import importlib.util
from pathlib import Path
import tempfile
import unittest

specification = importlib.util.spec_from_file_location("zalo_guard_installer", Path(__file__).with_name("install.py"))
installer = importlib.util.module_from_spec(specification)
specification.loader.exec_module(installer)


def sources(gap="35e3"):
    return {
        "send": '''import { randomUUID } from "node:crypto";
const ZALO_TEXT_LIMIT = 2e3;
async function sendMessageZalouser(threadId, text, options = {}) {
\tconst { onDeliveryResult, ...transportOptions } = options;
\tconst prepared = text;
\treturn existingMediaSender(prepared, transportOptions);
}
''',
        "monitor": '''const existingImageCache = "preserve-original-URL";
function monitorMessage() {
\tconst normalizedTo = isGroup ? `zalouser:group:${chatId}` : `zalouser:${chatId}`;
\treturn { message: {
\t\t\tbodyForAgent: rawBody,
\t\t\trawBody,
\t\t\tcommandBody,
\t\t\tmedia: existingImageCache
\t} };
}
''',
        "low": f'''import {{ randomUUID }} from "node:crypto";
const LISTENER_WATCHDOG_MAX_GAP_MS = {gap};
function existingLowLevel() {{
\treturn {{
\t\t\terror: formatErrorMessage(error),
\t\t\treceipt: createZalouserSendReceipt({{
\t\t\t\tmessageId: textMessageId,
\t\t\t}})
\t}};
}}
''',
    }


class InstallerTests(unittest.TestCase):
    def test_scope_preserves_existing_image_and_media_code(self):
        original = sources()
        patched = installer.patch_sources(original, "/home/synthetic/.openclaw/tools/zalo-text-delivery-guard/guard.mjs")
        self.assertEqual(original, sources())
        self.assertIn("existingImageCache", patched["monitor"])
        self.assertIn("media: existingImageCache", patched["monitor"])
        self.assertIn("existingMediaSender(prepared, transportOptions)", patched["send"])
        self.assertIn("/home/synthetic/.openclaw/tools/", patched["send"])
        self.assertIn("180e3", patched["low"])

    def test_reapplication_is_identical(self):
        path = "/root/.openclaw/tools/zalo-text-delivery-guard/guard.mjs"
        patched = installer.patch_sources(sources(), path)
        self.assertEqual(installer.patch_sources(patched, path), patched)

    def test_partial_install_is_rejected(self):
        path = "/root/.openclaw/tools/zalo-text-delivery-guard/guard.mjs"
        patched = installer.patch_sources(sources(), path)
        patched["monitor"] = sources()["monitor"]
        with self.assertRaises(ValueError):
            installer.patch_sources(patched, path)

    def test_wrong_home_existing_install_is_rejected(self):
        patched = installer.patch_sources(sources(), "/root/.openclaw/tools/zalo-text-delivery-guard/guard.mjs")
        with self.assertRaises(ValueError):
            installer.patch_sources(patched, "/home/synthetic/.openclaw/tools/zalo-text-delivery-guard/guard.mjs")

    def test_changed_or_ambiguous_anchor_is_rejected(self):
        for variant in ["removed", "duplicate"]:
            original = sources()
            anchor = "\t\t\tbodyForAgent: rawBody,"
            original["monitor"] = original["monitor"].replace(anchor, "bodyForAgent: somethingElse," if variant == "removed" else anchor + "\n" + anchor)
            with self.assertRaises(ValueError):
                installer.patch_sources(original, "/root/.openclaw/tools/zalo-text-delivery-guard/guard.mjs")

    def test_existing_reviewed_watchdog_is_preserved(self):
        patched = installer.patch_sources(sources("180e3"), "/root/.openclaw/tools/zalo-text-delivery-guard/guard.mjs")
        self.assertEqual(patched["low"].count("const LISTENER_WATCHDOG_MAX_GAP_MS = 180e3;"), 1)

    def test_unreviewed_watchdog_is_rejected(self):
        with self.assertRaises(ValueError):
            installer.patch_sources(sources("300e3"), "/root/.openclaw/tools/zalo-text-delivery-guard/guard.mjs")

    def test_health_never_confuses_probe_success_with_running(self):
        healthy = installer.channel_health("- Zalo Personal default: configured, linked, running, connected, works\n- Telegram test: running, works")
        self.assertTrue(healthy["zalo"])
        self.assertTrue(healthy["telegram"])
        stopped = installer.channel_health("- Zalo Personal default: configured, stopped, health:not-running, works")
        self.assertFalse(stopped["zalo"])
        unauthenticated = installer.channel_health("- Zalo Personal default: not authenticated, Đăng nhập thất bại, stopped, probe failed")
        self.assertFalse(unauthenticated["zalo"])
        self.assertTrue(unauthenticated["zalo_authentication_failed"])

    def test_private_atomic_backup_writes_are_restrictive(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "snapshot.json"
            installer.atomic_write(path, b"synthetic-data", 0o600)
            self.assertEqual(path.read_bytes(), b"synthetic-data")
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertEqual(len(list(Path(directory).iterdir())), 1)


if __name__ == "__main__":
    unittest.main()
