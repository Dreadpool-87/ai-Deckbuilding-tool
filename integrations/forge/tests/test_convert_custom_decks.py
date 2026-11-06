"""Offline regression tests: python3 -m unittest discover -s integrations/forge/tests -v"""
import hashlib
import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from convert_custom_decks import convert, parse_source, parse_dck


class CustomDeckTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name)
        (self.repo / "examples").mkdir()
        self.a = "examples/a.txt"
        self.b = "examples/b.txt"
        (self.repo / self.a).write_text("4 Shock\n56 Mountain\n", encoding="utf-8")
        (self.repo / self.b).write_text("4 Lightning Strike\n56 Mountain\n", encoding="utf-8")

    def digest(self, path):
        return hashlib.sha256((self.repo / path).read_bytes()).hexdigest()

    def test_roundtrip_and_checksums(self):
        result = convert(self.repo, self.repo / "output", self.a, self.b,
                         ("Deck_A", "Deck_B"), (self.digest(self.a), self.digest(self.b)))
        self.assertEqual(len(result["decks"]), 2)
        for entry in result["decks"]:
            self.assertEqual(entry["cards"], 60)
            self.assertEqual(parse_source(self.repo / entry["source"]),
                             parse_dck(self.repo / "output" / entry["forge_file"]))
            self.assertEqual(entry["original_sha256"], self.digest(entry["source"]))

    def test_wrong_hash_fails(self):
        with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
            convert(self.repo, self.repo / "out", self.a, self.b,
                    ("Deck_A", "Deck_B"), ("0" * 64, self.digest(self.b)))

    def test_over_four_nonbasic_fails(self):
        (self.repo / self.a).write_text("5 Shock\n55 Mountain\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "more than four"):
            parse_source(self.repo / self.a)

    def test_wrong_deck_size_fails(self):
        (self.repo / self.a).write_text("4 Shock\n55 Mountain\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "expected 60"):
            parse_source(self.repo / self.a)

    def test_duplicate_name_fails(self):
        (self.repo / self.a).write_text("4 Shock\n1 Shock\n55 Mountain\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "duplicate"):
            parse_source(self.repo / self.a)

    def test_traversal_fails(self):
        with self.assertRaises(ValueError):
            convert(self.repo, self.repo / "out", "../outside.txt", self.b,
                    ("Deck_A", "Deck_B"), ("0" * 64, self.digest(self.b)))


if __name__ == "__main__":
    unittest.main()
