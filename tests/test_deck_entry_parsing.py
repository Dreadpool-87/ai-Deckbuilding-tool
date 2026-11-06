"""Run identical deck-entry regressions against both active parsers."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def load_script(path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


VALIDATOR = load_script(ROOT / "validator" / "MTG_Deck_Validator_v1.1.1.py")
SPELLBOOK = load_script(ROOT / "integrations" / "commander-spellbook" / "analyze.py")


class DeckEntryParsingTests(unittest.TestCase):
    def test_casual_entries_preserve_x_prefix_and_support_explicit_separators(self):
        entries = {
            "4 Xenagos, God of Revels": (4, "Xenagos, God of Revels"),
            "2 Xantid Swarm": (2, "Xantid Swarm"),
            "1 Xyris, the Writhing Storm": (1, "Xyris, the Writhing Storm"),
            "4x Lightning Bolt": (4, "Lightning Bolt"),
            "4 x Lightning Bolt": (4, "x Lightning Bolt"),
            "4× Lightning Bolt": (4, "Lightning Bolt"),
            "4×Lightning Bolt": (4, "Lightning Bolt"),
            "2 X Marks the Spot": (2, "X Marks the Spot"),
            "1 X": (1, "X"),
            "1x X": (1, "X"),
            "1 Plains": (1, "Plains"),
            "1 1996 World Champion": (1, "1996 World Champion"),
        }
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "deck.txt"
            for line, (quantity, name) in entries.items():
                with self.subTest(line=line):
                    path.write_text(f"Deck\n{line}\n", encoding="utf-8")
                    with self.subTest(parser="validator"):
                        self.assertEqual(VALIDATOR.parse_deck(path), ({name: quantity}, []))
                    with self.subTest(parser="spellbook"):
                        self.assertEqual(SPELLBOOK.read_deck(path), ({name: quantity}, {}))

    def test_commander_section_preserves_commander_name(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "deck.txt"
            path.write_text("Commander\n1 Xyris, the Writhing Storm\nDeck\n99 Island\n",
                            encoding="utf-8")
            commander = {"Xyris, the Writhing Storm": 1}
            deck = {**commander, "Island": 99}
            self.assertEqual(VALIDATOR.parse_deck(path), (deck, []))
            self.assertEqual(SPELLBOOK.read_deck(path), (deck, commander))

    def test_malformed_quantity_or_missing_name_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "deck.txt"
            for line in ("4", "44", "4x", "4×", "0 Plains", "-1 Plains",
                         "4.5 Plains", "4Xenagos", "4xLightning Bolt", "Plains"):
                with self.subTest(line=line):
                    path.write_text(line, encoding="utf-8")
                    cards, problems = VALIDATOR.parse_deck(path)
                    self.assertFalse(cards)
                    self.assertTrue(problems)
                    with self.assertRaises(ValueError):
                        SPELLBOOK.read_deck(path)

    def test_validator_cli_resolves_x_names_in_both_modes(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            deck = root / "deck.txt"
            collection = root / "collection.csv"
            oracle = root / "AtomicCards.json"
            xyris = "Xyris, the Writhing Storm"
            collection.write_text(f'Name,Quantity\n"{xyris}",1\n', encoding="utf-8")
            oracle.write_text(json.dumps({"data": {
                xyris: [{"name": xyris, "types": ["Creature"],
                         "supertypes": ["Legendary"], "manaValue": 5,
                         "manaCost": "{2}{G}{U}{R}", "colorIdentity": ["G", "U", "R"]}],
                "Island": [{"name": "Island", "types": ["Land"], "supertypes": ["Basic"],
                            "manaValue": 0, "colorIdentity": ["U"]}],
            }}), encoding="utf-8")
            command = [sys.executable, VALIDATOR.__file__, "--collection", str(collection),
                       "--oracle", str(oracle), "--deck", str(deck)]
            for mode, lands, options in (
                ("casual", 59, ["--exact-60"]),
                ("commander", 99, ["--commander", xyris]),
            ):
                with self.subTest(mode=mode):
                    deck.write_text(f"1 {xyris}\n{lands} Island\n", encoding="utf-8")
                    result = subprocess.run(command + ["--mode", mode, *options],
                                            capture_output=True, text=True, check=False)
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    report = json.loads(result.stdout)
                    self.assertEqual(report["status"], "PASS_WITH_LIMITATIONS")
                    self.assertEqual(report["checks"]["oracle_lookup"], "PASS")
                    self.assertEqual(report["checks"]["ownership"], "PASS")
