import json
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "scan_active_delivery.py"


class ActiveDeliveryTests(unittest.TestCase):
    def run_scan(self, message, timestamp=None):
        timestamp = timestamp or datetime.now(timezone.utc).isoformat()
        with tempfile.NamedTemporaryFile("w", encoding="utf-8") as handle:
            handle.write(json.dumps({"time": timestamp, "message": message}) + "\n")
            handle.flush()
            return subprocess.run(
                [sys.executable, str(SCRIPT), handle.name, "--window", "120"],
                capture_output=True, text=True,
            )

    def test_recent_upload_defers(self):
        result = self.run_scan("send_attempt_started attachment upload")
        self.assertEqual(result.returncode, 0)
        self.assertTrue(json.loads(result.stdout)["active"])

    def test_old_upload_does_not_defer(self):
        old = (datetime.now(timezone.utc).timestamp() - 300)
        from datetime import datetime as dt
        timestamp = dt.fromtimestamp(old, timezone.utc).isoformat()
        result = self.run_scan("attachment upload", timestamp)
        self.assertEqual(result.returncode, 1)
        self.assertFalse(json.loads(result.stdout)["active"])


if __name__ == "__main__":
    unittest.main()
