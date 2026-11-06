"""Language-migration safeguards; run by existing offline Python regression CI."""
import ast
from pathlib import Path
import re
import unittest
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
PROMPTS = {
    "prompts/casual/builder/backup/MTG_Deck_Builder_v7.3_full.md": "Respond in English.",
    "prompts/casual/builder/stable/MTG_Deck_Builder_v7.4_full.md": "Respond in English.",
    "prompts/casual/builder/experimental/MTG_Deck_Builder_v7.4.1_full.md": "Respond in English.",
    "prompts/casual/tester/MTG_Deck_Tester_v3.2_full.md": "Answer in English;",
    "prompts/casual/tester/MTG_Deck_Tester_v3.3_full.md": "Answer in English;",
    "prompts/casual/tester/MTG_Deck_Tester_v3.4.2_full.md": "English response",
    "prompts/commander/builder/MTG_Commander_Builder_v4.2_full.md": "Respond in English,",
    "prompts/commander/tester/MTG_Commander_Tester_v4.2_full.md": "Respond in English;",
}
SYNTHETIC_DECKS = {
    "examples/Synthetic_Red_A.txt": "56 Mountain\n4 Lightning Bolt\n",
    "examples/Synthetic_Red_B.txt": "56 Mountain\n4 Shock\n",
    "integrations/forge/decks/Synthetic_Green.txt": "56 Forest\n4 Giant Growth\n",
}


class EnglishRepositoryIntegrityTests(unittest.TestCase):
    def test_only_synthetic_forge_fixtures_are_shipped(self):
        self.assertFalse((ROOT / "voorbeelden").exists())
        paths = list((ROOT / "examples").glob("*.txt"))
        paths += list((ROOT / "integrations/forge/decks").glob("*.txt"))
        self.assertEqual({path.relative_to(ROOT).as_posix() for path in paths}, set(SYNTHETIC_DECKS))
        for filename, expected in SYNTHETIC_DECKS.items():
            self.assertEqual((ROOT / filename).read_text(encoding="utf-8"), expected)

    def test_english_masterprompt_output_directives(self):
        for path, expected in PROMPTS.items():
            with self.subTest(prompt=path):
                content = (ROOT / path).read_text(encoding="utf-8")
                self.assertIn(expected, content)
                self.assertIsNone(re.search(
                    r"(?:Respond|Reply|Answer|Output|report) in Dutch|Dutch response", content, re.I
                ))
        # All eight versions are included in the English-language candidate.
        self.assertEqual(len(list((ROOT / "prompts").rglob("*_full.md"))), 8)

    def test_forge_scripts_use_new_example_paths(self):
        for path in ("integrations/forge/scripts/convert_decks.py",
                     "integrations/forge/scripts/run_poc.py"):
            text = (ROOT / path).read_text(encoding="utf-8")
            self.assertIn("examples", text)
            self.assertNotIn("voorbeelden", text)
            ast.parse(text, filename=path)

    def test_english_documentation_paths(self):
        expected = (
            "docs/MTGJSON_Automated_Backup.md",
            "docs/MTG_Validator_Guide.md",
            "docs/MTG_Validator_v1.1.1_Audit.md",
            "prompts/README.md",
            "integrations/forge/README.md",
            "integrations/commander-spellbook/README.md",
        )
        for path in expected:
            with self.subTest(path=path):
                self.assertTrue((ROOT / path).is_file())
        self.assertFalse((ROOT / "docs/MTGJSON_Automatische_Backup.md").exists())
        self.assertFalse((ROOT / "docs/MTG_Validator_Handleiding.md").exists())

    def test_markdown_local_links_exist(self):
        files = (
            "README.md", "prompts/README.md", "rules/README.md",
            "integrations/forge/README.md",
            "integrations/commander-spellbook/README.md",
            "docs/MTG_Validator_Guide.md",
            "docs/MTGJSON_Automated_Backup.md",
        )
        for rel in files:
            page = ROOT / rel
            content = page.read_text(encoding="utf-8")
            for target in re.findall(r"(?<!!)\[[^\]]+\]\(([^)\s]+)(?:\s+[^)]*)?\)", content):
                target = unquote(target.split("#", 1)[0])
                if not target or "://" in target or target.startswith(("mailto:", "#")):
                    continue
                resolved = (page.parent / target).resolve()
                if not resolved.is_relative_to(ROOT):
                    continue  # GitHub-generated URLs such as ../../releases
                with self.subTest(source=rel, target=target):
                    self.assertTrue(resolved.exists(), f"Broken Markdown link in {rel}: {target}")

    def test_core_python_remains_parseable(self):
        for rel in ("validator/MTG_Deck_Validator_v1.1.py",
                    "validator/MTG_Deck_Validator_v1.1.1.py",
                    "integrations/commander-spellbook/analyze.py",
                    "integrations/commander-spellbook/download_snapshot.py",
                    "integrations/forge/scripts/convert_decks.py",
                    "integrations/forge/scripts/run_poc.py"):
            with self.subTest(script=rel):
                ast.parse((ROOT / rel).read_text(encoding="utf-8"), filename=rel)


if __name__ == "__main__":
    unittest.main()
