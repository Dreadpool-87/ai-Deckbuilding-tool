"""Synthetic tests for Git-history scanner, without storing real credentials."""
import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "public_history_scanner", ROOT / "scripts/audit_public_history.py")
H = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(H)


class HistoryAuditTests(unittest.TestCase):
    def run_git(self, location, *args):
        subprocess.run(["git", "-C", str(location), *args], check=True,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def init(self, location):
        self.run_git(location, "init")
        self.run_git(location, "config", "user.email", "fixture@example.invalid")
        self.run_git(location, "config", "user.name", "Synthetic Tester")

    def test_clean_history_has_no_pattern_hits(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            self.init(path)
            (path / "README.md").write_text("Synthetic test project\n", encoding="utf-8")
            self.run_git(path, "add", ".")
            self.run_git(path, "commit", "-m", "Initial clean synthetic fixture")
            r = H.scan(path)
            self.assertEqual(r["status"], "NO_PATTERN_HITS")
            self.assertGreaterEqual(r["blobs_scanned"], 1)

    def test_deleted_token_remains_detectable_in_history(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            self.init(path)
            token = "ghp_" + "A" * 36  # synthetic, constructed at runtime
            (path / "old-config.txt").write_text("token: '" + token + "'\n", encoding="utf-8")
            self.run_git(path, "add", ".")
            self.run_git(path, "commit", "-m", "Old synthetic fixture")
            (path / "old-config.txt").unlink()
            self.run_git(path, "add", "-A")
            self.run_git(path, "commit", "-m", "Remove old fixture")
            r = H.scan(path)
            self.assertEqual(r["status"], "POTENTIAL_ISSUES")
            self.assertTrue(any(x["kind"] == "github_token" for x in r["findings"]))
            self.assertNotIn(token, str(r))

    def test_historical_private_csv_path_is_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            self.init(path)
            (path / "my_collection.csv").write_text("Name,Quantity\nSample,1\n", encoding="utf-8")
            self.run_git(path, "add", ".")
            self.run_git(path, "commit", "-m", "Synthetic inventory path")
            result = H.scan(path)
            self.assertTrue(any(x["kind"] == "sensitive_historical_path"
                                for x in result["findings"]))


if __name__ == "__main__":
    unittest.main()
