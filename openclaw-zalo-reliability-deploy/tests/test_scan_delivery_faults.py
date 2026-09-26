import json
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "scan_delivery_faults.py"


class ScannerTests(unittest.TestCase):
    def run_scan(self, message):
        now = datetime.now(timezone.utc).isoformat()
        with tempfile.NamedTemporaryFile("w", encoding="utf-8") as handle:
            handle.write(json.dumps({"time": now, "message": message}) + "\n")
            handle.flush()
            result = subprocess.run(
                [sys.executable, str(SCRIPT), handle.name, "--window", "300"],
                check=True,
                capture_output=True,
                text=True,
            )
        return json.loads(result.stdout)

    def test_successful_upload_is_not_a_fault(self):
        self.assertEqual(self.run_scan("upload completed successfully")["count"], 0)

    def test_stalled_upload_is_a_fault_without_leaking_line(self):
        result = self.run_scan("attachment upload timed out for private message id")
        self.assertEqual(result["categories"], {"upload_timeout": 1})
        self.assertNotIn("private", json.dumps(result))


if __name__ == "__main__":
    unittest.main()
