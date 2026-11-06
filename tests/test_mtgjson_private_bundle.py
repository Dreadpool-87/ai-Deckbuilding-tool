"""Offline safety tests for the private MTGJSON four-dataset bundler."""
import gzip
import hashlib
import importlib.util
import io
from pathlib import Path
import tempfile
import unittest
from unittest import mock

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "prepare_mtgjson_private_bundle.py"
spec = importlib.util.spec_from_file_location("prepare_mtgjson_private_bundle", SCRIPT)
# The bundle module imports the sibling AtomicCards updater.
import sys
sys.path.insert(0, str(SCRIPT.parent))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def gzip_csv(payload):
    return gzip.compress(payload.encode("utf-8"))


class TestPrivateBundle(unittest.TestCase):
    def test_official_plain_digest(self):
        self.assertEqual(mod.parse_sha256(("A" * 64).encode(), "cards.csv.gz"), "a" * 64)

    def test_official_named_digest(self):
        self.assertEqual(mod.parse_sha256((("b" * 64) + " *cards.csv.gz").encode(), "cards.csv.gz"),
                         "b" * 64)

    def test_reject_bad_digest(self):
        with self.assertRaises(ValueError):
            mod.parse_sha256(b"unsafe", "cards.csv.gz")

    def test_reject_mismatched_digest_filename(self):
        with self.assertRaises(ValueError):
            mod.parse_sha256((("a" * 64) + " wrong.gz").encode(), "cards.csv.gz")

    def test_reject_extra_digest_text(self):
        with self.assertRaises(ValueError):
            mod.parse_sha256((("a" * 64) + " file.gz anything").encode(), "file.gz")

    def test_csv_acceptable_small_fixture(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "cards.csv.gz"
            path.write_bytes(gzip_csv("uuid,name\nid1,Shock\nid2,Mountain\n"))
            self.assertEqual(mod.validate_csv(path, 2), 2)

    def test_csv_reject_missing_uuid(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "cards.csv.gz"
            path.write_bytes(gzip_csv("name,code\nShock,1\n"))
            with self.assertRaises(ValueError):
                mod.validate_csv(path, 1)

    def test_csv_reject_bad_row_width(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "cards.csv.gz"
            path.write_bytes(gzip_csv("uuid,name\nid1,Shock,extra\n"))
            with self.assertRaises(ValueError):
                mod.validate_csv(path, 1)

    def test_csv_reject_missing_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "cards.csv.gz"
            path.write_bytes(gzip_csv("uuid,name\nid1,Shock\n"))
            with self.assertRaises(ValueError):
                mod.validate_csv(path, 2)

    def test_download_verifies_exact_digest(self):
        data = gzip_csv("uuid,name\nid1,Shock\nid2,Mountain\n")
        official = (hashlib.sha256(data).hexdigest() + "\n").encode("ascii")
        def fake_open(req, timeout):
            return io.BytesIO(official if req.full_url.endswith(".sha256") else data)
        with tempfile.TemporaryDirectory() as tmp, \
             mock.patch.object(mod, "TABLES", {"cards": (10000, 2)}), \
             mock.patch.object(mod, "MIN_ARCHIVE_BYTES", 1), \
             mock.patch.object(mod, "urlopen", side_effect=fake_open):
            out = mod.fetch_verified_csv("cards", Path(tmp))
            self.assertEqual(out["records"], 2)
            self.assertEqual((Path(tmp) / "cards.csv.gz.sha256").read_text().strip(),
                             hashlib.sha256(data).hexdigest())

    def test_download_rejects_checksum_mismatch(self):
        data = gzip_csv("uuid,name\nid1,Shock\n")
        wrong = ("f" * 64 + "\n").encode("ascii")
        def fake_open(req, timeout):
            return io.BytesIO(wrong if req.full_url.endswith(".sha256") else data)
        with tempfile.TemporaryDirectory() as tmp, \
             mock.patch.object(mod, "TABLES", {"cards": (10000, 1)}), \
             mock.patch.object(mod, "MIN_ARCHIVE_BYTES", 1), \
             mock.patch.object(mod, "urlopen", side_effect=fake_open):
            with self.assertRaises(ValueError):
                mod.fetch_verified_csv("cards", Path(tmp))
            self.assertFalse((Path(tmp) / "cards.csv.gz").exists())


if __name__ == "__main__":
    unittest.main()
