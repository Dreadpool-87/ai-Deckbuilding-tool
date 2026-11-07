"""Offline tests for metadata-only MTGJSON AtomicCards pointer updates."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[1] / "scripts" / "record_mtgjson_atomic_pointer.py"
spec = importlib.util.spec_from_file_location("record_mtgjson_atomic_pointer", SOURCE)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class PointerTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.manifest = self.root / "verified-manifest.json"
        self.pointer = self.root / "data" / "mtgjson_atomic_latest.json"
        self.hashes = self.root / "SHA256SUMS.txt"
        self.hashes.write_text("0" * 64 + "  README.md\n", encoding="utf-8")
        self.upstream = {
            "version": "5.3.0+synthetic",
            "source": mod.SOURCE_URL,
            "sha256": "a" * 64,
            "compressed_bytes": 49 * 1024 * 1024,
            "card_names": 28000,
            "license": "https://mtgjson.com/license/",
        }
        self.write_manifest()

    def write_manifest(self):
        self.manifest.write_text(json.dumps(self.upstream), encoding="utf-8")

    def test_first_verified_snapshot_writes_only_small_pointer(self):
        self.assertTrue(mod.record(self.manifest, self.pointer, self.hashes,
                                   "2026-11-08T07:17:00Z"))
        output = json.loads(self.pointer.read_text(encoding="utf-8"))
        self.assertEqual(output["download_url"], mod.SOURCE_URL)
        self.assertEqual(output["checksum_url"], mod.CHECKSUM_URL)
        self.assertEqual(output["sha256"], "a" * 64)
        self.assertEqual(output["verified_at_utc"], "2026-11-08T07:17:00Z")
        self.assertTrue(output["download_url_is_mutable"])
        self.assertLess(self.pointer.stat().st_size, 2048)
        self.assertIn("data/mtgjson_atomic_latest.json", self.hashes.read_text())
        self.assertNotIn("AtomicCards.json.gz  ", self.hashes.read_text())

    def test_unchanged_weekly_snapshot_produces_no_metadata_changes(self):
        self.assertTrue(mod.record(self.manifest, self.pointer, self.hashes,
                                   "2026-11-08T07:17:00Z"))
        old_pointer = self.pointer.read_bytes()
        old_manifest = self.hashes.read_bytes()
        self.assertFalse(mod.record(self.manifest, self.pointer, self.hashes,
                                    "2026-11-15T07:17:00Z"))
        self.assertEqual(old_pointer, self.pointer.read_bytes())
        self.assertEqual(old_manifest, self.hashes.read_bytes())

    def test_same_version_new_hash_is_detected(self):
        mod.record(self.manifest, self.pointer, self.hashes, "2026-11-08T07:17:00Z")
        self.upstream["sha256"] = "b" * 64
        self.write_manifest()
        self.assertTrue(mod.record(self.manifest, self.pointer, self.hashes,
                                   "2026-11-15T07:17:00Z"))
        self.assertEqual(json.loads(self.pointer.read_text())["sha256"], "b" * 64)

    def test_new_version_is_detected(self):
        mod.record(self.manifest, self.pointer, self.hashes, "2026-11-08T07:17:00Z")
        self.upstream["version"] = "5.3.1"
        self.write_manifest()
        self.assertTrue(mod.record(self.manifest, self.pointer, self.hashes,
                                   "2026-11-15T07:17:00Z"))
        self.assertEqual(json.loads(self.pointer.read_text())["version"], "5.3.1")

    def test_refuses_untrusted_source_or_fake_coverage(self):
        for field, value in (("source", "https://example.com/AtomicCards.json.gz"),
                             ("sha256", "nope"),
                             ("compressed_bytes", 7),
                             ("card_names", 5),
                             ("license", "https://example.com/")):
            with self.subTest(field=field):
                old = self.upstream[field]
                self.upstream[field] = value
                self.write_manifest()
                with self.assertRaises(ValueError):
                    mod.record(self.manifest, self.pointer, self.hashes,
                               "2026-11-08T07:17:00Z")
                self.assertFalse(self.pointer.exists())
                self.upstream[field] = old
        self.write_manifest()

    def test_invalid_time_blocks_update(self):
        with self.assertRaises(ValueError):
            mod.record(self.manifest, self.pointer, self.hashes, "yesterday")
        self.assertFalse(self.pointer.exists())

    def test_corrupted_existing_pointer_fails_closed(self):
        self.pointer.parent.mkdir(parents=True, exist_ok=True)
        self.pointer.write_text('{"source":"untrusted"}', encoding="utf-8")
        with self.assertRaises(ValueError):
            mod.record(self.manifest, self.pointer, self.hashes,
                       "2026-11-08T07:17:00Z")

    def test_bad_checksums_manifest_fails_closed(self):
        self.hashes.write_text("not a manifest\n", encoding="utf-8")
        with self.assertRaises(ValueError):
            mod.record(self.manifest, self.pointer, self.hashes,
                       "2026-11-08T07:17:00Z")


if __name__ == "__main__":
    unittest.main()
