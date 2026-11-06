#!/usr/bin/env python3
"""18 original offline regression tests; runnable discovery filename. No personal data."""
import importlib.util
import pathlib
import tempfile
import unittest
from fractions import Fraction

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("mtg_validator", ROOT / "validator" / "MTG_Deck_Validator_v1.1.py")
V = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(V)

def card(name, mana, mv, types, colors=(), supertypes=(), eligible=None):
    return {"name": name, "manaCost": mana, "manaValue": mv,
            "types": list(types), "supertypes": list(supertypes),
            "colorIdentity": list(colors),
            "leadershipSkills": {} if eligible is None else {"commander": eligible}}

DB = {
    "Mountain": [card("Mountain", None, 0, ["Land"], ["R"], ["Basic"])],
    "Forest": [card("Forest", None, 0, ["Land"], ["G"], ["Basic"])],
    "Shock": [card("Shock", "{R}", 1, ["Instant"], ["R"])],
    "Ember Hauler": [card("Ember Hauler", "{R}{R}", 2, ["Creature"], ["R"])],
    "Banefire": [card("Banefire", "{X}{R}", 1, ["Sorcery"], ["R"])],
    "Llanowar Elves": [card("Llanowar Elves", "{G}", 1, ["Creature"], ["G"])],
    "Ruby Captain": [card("Ruby Captain", "{1}{R}", 2, ["Creature"], ["R"], ["Legendary"], True)],
    "Bicolored Creature": [card("Bicolored Creature", "{G}{R}", 2, ["Creature"], ["G", "R"])],
    "Artifact Creature": [card("Artifact Creature", "{2}", 2, ["Artifact", "Creature"])],
}

class MTGDeckValidatorTests(unittest.TestCase):
    def test_exact_land_prob(self):
        p = V.exact_land_probability(60, 21)
        self.assertIsInstance(p, Fraction)
        self.assertAlmostEqual(float(p) * 100, 77.69884703257, places=9)
        self.assertEqual(V.exact_land_probability(60, 0), Fraction(0, 1))

    def test_casual_60_and_costs_and_curve(self):
        out = V.validate({"Shock": 4}, DB, {"Mountain": 56, "Shock": 4}, exact_60=True)
        self.assertEqual(out["status"], "PASS_WITH_LIMITATIONS")
        self.assertEqual(out["mana_curve_nonlands"], {"1": 4})
        self.assertEqual(out["lands_physical"], 56)
        self.assertEqual(out["printed_mana_costs"]["Shock"], "{R}")

    def test_less_than_60_rejected(self):
        out = V.validate({"Shock": 4}, DB, {"Mountain": 55, "Shock": 4})
        self.assertEqual(out["status"], "FAIL")
        self.assertEqual(out["checks"]["deck_size"], "FAIL")

    def test_61_allowed_only_without_exact_60(self):
        deck = {"Mountain": 57, "Shock": 4}
        self.assertEqual(V.validate({"Shock": 4}, DB, deck)["status"], "PASS_WITH_LIMITATIONS")
        self.assertEqual(V.validate({"Shock": 4}, DB, deck, exact_60=True)["status"], "FAIL")

    def test_five_copies_even_when_owned(self):
        out = V.validate({"Shock": 8}, DB, {"Mountain": 55, "Shock": 5})
        self.assertEqual(out["checks"]["ownership"], "PASS")
        self.assertEqual(out["checks"]["copy_limit"], "FAIL")

    def test_owned_one_nonbasic_cannot_use_two(self):
        out = V.validate({"Shock": 1}, DB, {"Mountain": 58, "Shock": 2})
        self.assertEqual(out["checks"]["ownership"], "FAIL")
        self.assertEqual(out["checks"]["copy_limit"], "PASS")

    def test_standard_basics_unlimited_even_if_unowned(self):
        self.assertEqual(V.validate({}, DB, {"Mountain": 60})["status"], "PASS_WITH_LIMITATIONS")

    def test_unknown_card_never_passes(self):
        out = V.validate({"Fake card": 4}, DB, {"Mountain": 56, "Fake card": 4})
        self.assertEqual(out["status"], "FAIL")
        self.assertEqual(out["checks"]["oracle_lookup"], "FAIL")

    def test_commander_100_identity_and_eligibility(self):
        deck = {"Ruby Captain": 1, "Mountain": 99}
        out = V.validate({"Ruby Captain": 1}, DB, deck, mode="commander", commander="Ruby Captain")
        self.assertEqual(out["status"], "PASS_WITH_LIMITATIONS")
        self.assertEqual(out["checks"]["commander_eligibility"], "PASS_BASIC_RULE")
        self.assertEqual(out["checks"]["commander_color_identity"], "PASS")
        self.assertEqual(out["checks"]["commander_count"], "PASS")
        deck = {"Ruby Captain": 1, "Mountain": 98, "Bicolored Creature": 1}
        out = V.validate({"Ruby Captain": 1, "Bicolored Creature": 1}, DB, deck,
                         mode="commander", commander="Ruby Captain")
        self.assertEqual(out["status"], "FAIL")
        self.assertEqual(out["checks"]["commander_color_identity"], "FAIL")

    def test_commander_not_owned(self):
        out = V.validate({}, DB, {"Ruby Captain": 1, "Mountain": 99},
                         mode="commander", commander="Ruby Captain")
        self.assertEqual(out["checks"]["ownership"], "FAIL")

    def test_commander_101_rejected(self):
        out = V.validate({"Ruby Captain": 1}, DB, {"Ruby Captain": 1, "Mountain": 100},
                         mode="commander", commander="Ruby Captain")
        self.assertEqual(out["checks"]["deck_size"], "FAIL")

    def test_commander_missing(self):
        self.assertEqual(V.validate({}, DB, {"Mountain": 100}, mode="commander")["status"], "FAIL")

    def test_artifact_creature_primary_count_not_double(self):
        out = V.validate({"Artifact Creature": 1}, DB, {"Artifact Creature": 1, "Mountain": 59})
        self.assertEqual(out["card_types_primary_exclusive"], {"Land": 59, "Creature": 1})
        self.assertEqual(out["card_types_overlapping"]["Artifact"], 1)
        self.assertEqual(out["card_types_overlapping"]["Creature"], 1)

    def test_oracle_variant_ambiguity_unverified(self):
        db = dict(DB)
        db["Shock"] = [dict(DB["Shock"][0]), card("Shock", "{1}{R}", 2, ["Instant"], ["R"])]
        out = V.validate({"Shock": 4}, db, {"Shock": 4, "Mountain": 56})
        self.assertEqual(out["status"], "UNVERIFIED")
        self.assertEqual(out["checks"]["mana_curve"], "UNVERIFIED")

    def test_parser_skips_headers_but_rejects_sideboard(self):
        with tempfile.TemporaryDirectory() as td:
            p = pathlib.Path(td) / "deck.txt"
            p.write_text("Deck\nCreatures (4)\n4x Shock\n56 Mountain\n", encoding="utf-8")
            deck, bad = V.parse_deck(p)
            self.assertFalse(bad)
            self.assertEqual(sum(deck.values()), 60)
            p.write_text("Deck\n56 Mountain\n4 Shock\nSideboard\n1 Shock\n", encoding="utf-8")
            deck, bad = V.parse_deck(p)
            self.assertTrue(any("sideboard" in x for x in bad))
            self.assertEqual(sum(deck.values()), 60)
            self.assertEqual(V.validate({"Shock": 4}, DB, deck, parse_errors=bad)["status"], "FAIL")

    def test_collection_duplicate_rows_and_invalid_quantities(self):
        with tempfile.TemporaryDirectory() as td:
            p = pathlib.Path(td) / "owned.csv"
            p.write_text("Name,Quantity\nShock,1\nShock,2\nMountain,0\n", encoding="utf-8")
            self.assertEqual(V.read_collection(p)["Shock"], 3)
            p.write_text("Name,Quantity\nShock,-1\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                V.read_collection(p)

    def test_mana_cost_red_red_not_generic(self):
        out = V.validate({"Ember Hauler": 4}, DB, {"Mountain": 56, "Ember Hauler": 4})
        self.assertEqual(out["printed_mana_costs"]["Ember Hauler"], "{R}{R}")

    def test_exact_60_commander_disallows_unused_commander_flag(self):
        self.assertEqual(V.validate({}, DB, {"Mountain": 60}, commander="Ruby Captain")["status"], "FAIL")

if __name__ == "__main__":
    unittest.main(verbosity=2)
