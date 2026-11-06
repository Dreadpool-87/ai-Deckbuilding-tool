"""Offline third-party attribution safeguards; not a legal compliance certification."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class AttributionIntegrityTests(unittest.TestCase):
    def test_root_disclaimer_and_publication_gate(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("THIRD_PARTY_NOTICES.md", readme)
        self.assertIn("PUBLIC_RELEASE_CHECKLIST.md", readme)
        for document in (readme, (ROOT / "THIRD_PARTY_NOTICES.md").read_text(encoding="utf-8")):
            self.assertIn("unofficial", document)
            self.assertIn("not affiliated with, sponsored by, or endorsed by Wizards of the Coast", document)
        self.assertIn("PUBLIC_TEST_PREVIEW", readme)

    def test_credit_correct_upstream_creators(self):
        notice = (ROOT / "THIRD_PARTY_NOTICES.md").read_text(encoding="utf-8")
        for expected in (
            "Card-Forge/forge",
            "forge-2.0.15",
            "Zach Halpern",
            "Commander Spellbook",
            "2023 Commander-Spellbook",
            "Wizards of the Coast LLC",
            "Research references, not bundled dependencies",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, notice)

    def test_upstream_license_texts_preserved(self):
        forge = (ROOT / "third_party_licenses/Forge-GPL-3.0.txt").read_text(encoding="utf-8")
        mtgjson = (ROOT / "third_party_licenses/MTGJSON-MIT.txt").read_text(encoding="utf-8")
        spellbook = (ROOT / "third_party_licenses/Commander-Spellbook-MIT.txt").read_text(encoding="utf-8")
        self.assertIn("GNU GENERAL PUBLIC LICENSE", forge)
        self.assertIn("Version 3, 29 June 2007", forge)
        self.assertIn("Copyright © 2018 – Present, Zach Halpern", mtgjson)
        self.assertIn('THE SOFTWARE IS PROVIDED "AS IS"', mtgjson)
        self.assertIn("Copyright (c) 2023 Commander-Spellbook", spellbook)

    def test_integration_credits_and_source_access_checklist(self):
        checklist = (ROOT / "docs/PUBLIC_RELEASE_CHECKLIST.md").read_text(encoding="utf-8")
        for expected in ("Corresponding Source", "forge-runtime-2.0.15", "mtgjson-atomic-", "Git history"):
            self.assertIn(expected, checklist)
        for relative in (
            "integrations/forge/README.md",
            "integrations/commander-spellbook/README.md",
            "docs/MTGJSON_Automated_Backup.md",
        ):
            with self.subTest(relative=relative):
                self.assertIn(
                    "THIRD_PARTY_NOTICES.md",
                    (ROOT / relative).read_text(encoding="utf-8"),
                )


    def test_upstream_only_workflows_do_not_rehost_assets(self):
        forge = (ROOT / ".github/workflows/forge-runtime-download.yml").read_text(encoding="utf-8")
        smoke = (ROOT / ".github/workflows/forge-smoke.yml").read_text(encoding="utf-8")
        mtgjson = (ROOT / ".github/workflows/mtgjson-atomic-update.yml").read_text(encoding="utf-8")
        self.assertIn("github.com/Card-Forge/forge/releases/download/", forge)
        self.assertIn("Download pinned Forge directly from Card-Forge upstream", smoke)
        self.assertIn("python scripts/update_mtgjson_atomic.py", mtgjson)
        for content in (forge, smoke, mtgjson):
            self.assertNotIn("gh release create", content)
            self.assertNotIn("gh release download", content)
            self.assertNotIn("contents: write", content)


if __name__ == "__main__":
    unittest.main()
