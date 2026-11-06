"""Additional regressions for explicitly verified integrity bugs.

These do not replace or alter the original 41 regression tests.
"""
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


def load(module_name, relative_path):
    spec = importlib.util.spec_from_file_location(module_name, ROOT / relative_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


V = load("mtg_validator_new_safety", "validator/MTG_Deck_Validator_v1.1.1.py")
S = load("spellbook_new_safety", "integrations/commander-spellbook/analyze.py")


class ValidatorColorIdentitySafetyTests(unittest.TestCase):
    def test_only_single_oracle_color_letters_are_accepted(self):
        for colors in ([], ["W"], ["W", "U", "B", "R", "G"]):
            self.assertTrue(V.identity_valid({"colorIdentity": colors}))
        for colors in (["WU"], ["UB"], ["GARBAGE"], [1], ["R", "R"], "R", None):
            with self.subTest(colors=colors):
                self.assertFalse(V.identity_valid({"colorIdentity": colors}))

    def test_invalid_commander_color_identity_is_not_pass(self):
        leader = {"name": "Red Leader", "manaValue": 3, "manaCost": "{2}{R}",
                  "types": ["Creature"], "supertypes": ["Legendary"],
                  "colorIdentity": ["WU"], "leadershipSkills": {"commander": True}}
        mountain = {"name": "Mountain", "manaValue": 0, "manaCost": None,
                    "types": ["Land"], "supertypes": ["Basic"], "colorIdentity": ["R"]}
        report = V.validate({"Red Leader": 1},
                            {"Red Leader": [leader], "Mountain": [mountain]},
                            {"Red Leader": 1, "Mountain": 99},
                            mode="commander", commander="Red Leader")
        self.assertEqual(report["checks"]["commander_color_identity"], "UNVERIFIED")
        self.assertEqual(report["status"], "UNVERIFIED")


class CommanderSpellbookSafetyTests(unittest.TestCase):
    def setUp(self):
        variant = {
            "id": "requires-commander", "status": "OK", "spoiler": False,
            "requires": [], "identity": "R", "popularity": 1, "produces": [],
            "uses": [{"card": {"name": "Red Leader"}, "quantity": 1, "mustBeCommander": True}],
        }
        self.snapshot = {"variants": [variant], "timestamp": "synthetic", "version": "test"}
        self.deck = S.Counter({"Red Leader": 1, "Mountain": 99})

    def test_unknown_commander_does_not_yield_exact_candidate(self):
        result = S.analyze(self.deck, S.Counter(), self.snapshot, identity="R")
        self.assertEqual(result["total_exact_card_ingredient_candidates"], 0)
        self.assertEqual(result["counts"]["commander_unknown_variants"], 1)

    def test_known_commander_is_required_to_match(self):
        result = S.analyze(self.deck, S.Counter({"Red Leader": 1}), self.snapshot, identity="R")
        self.assertEqual(result["total_exact_card_ingredient_candidates"], 1)
        self.assertEqual(result["exact_card_ingredient_candidates"][0]["variant_id"],
                         "requires-commander")


if __name__ == "__main__":
    unittest.main()
