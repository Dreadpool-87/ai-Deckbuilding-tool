"""Guard the reviewed English-output mobile Tester editions."""
from pathlib import Path
import hashlib
import unittest

ROOT = Path(__file__).resolve().parents[1]
ENGLISH_EDITIONS = {
    "MTG_Deck_Tester_v3.3_full.md":
        "31271f3d635e9c9bf0532edde70b0e46c9e645f9bdd3b3b43b08cc8773972f7b",
    "MTG_Deck_Tester_v3.4.2_full.md":
        "a6623ab594552061199ea57bc235e929a38598025c67df11082df6dd41e96c4e",
}


class UploadedTesterIntegrityTests(unittest.TestCase):
    def test_reviewed_english_prompt_bytes_are_preserved(self):
        base = ROOT / "prompts/casual/tester"
        for filename, expected in ENGLISH_EDITIONS.items():
            with self.subTest(version=filename):
                raw = (base / filename).read_bytes()
                self.assertEqual(hashlib.sha256(raw).hexdigest(), expected)
                self.assertIn(b"Answer in English" if filename.endswith("v3.3_full.md")
                              else b"English response", raw)

    def test_old_v32_git_blob_unchanged(self):
        raw = (ROOT / "prompts/casual/tester/MTG_Deck_Tester_v3.2_full.md").read_bytes()
        blob = hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()
        self.assertEqual(blob, "aae5ed6ea7f2a9a25b59ed3693ff0187f9c9e731")


if __name__ == "__main__":
    unittest.main()
