"""Synthetic regression checks for optional Casual combo/synergy color screening."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "casual_color_report", ROOT / "tools/combo_synergy_report.py"
)
REPORT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(REPORT)


def card(name, text="", identity=None, basic=False):
    return {
        "name": name, "text": text, "manaCost": None if basic else "{1}{G}",
        "manaValue": 0 if basic else 2,
        "types": ["Land"] if basic else ["Creature"],
        "supertypes": ["Basic"] if basic else [],
        "colorIdentity": identity,
        "keywords": [],
    }


def variant(name, *cards):
    return {
        "id": name, "status": "OK", "spoiler": False, "requires": [],
        "uses": [{"card": {"name": n}, "quantity": 1} for n in cards],
        "identity": "G", "popularity": 1, "produces": [],
    }


class CasualColorScreenTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.oracle = root / "oracle.json"
        self.collection = root / "collection.csv"
        self.deck = root / "deck.txt"
        self.snapshot = root / "snapshot.json"
        cards = {
            "Forest": [card("Forest", identity=["G"], basic=True)],
            "Green Outlet": [card("Green Outlet", "Sacrifice a creature: Scry 1.", ["G"])],
            "Green Payoff": [card("Green Payoff",
                                "Whenever another nontoken creature dies, each opponent loses 2 life.",
                                ["G"])],
            "Black Payoff": [card("Black Payoff",
                                "Whenever another nontoken creature dies, each opponent loses 2 life.",
                                ["B"])],
            "Colorless Payoff": [card("Colorless Payoff",
                                    "Whenever another nontoken creature dies, each opponent loses 2 life.",
                                    [])],
        }
        self.oracle.write_text(json.dumps({"meta": {"version": "test"}, "data": cards}),
                               encoding="utf-8")
        self.collection.write_text(
            "Name,Quantity\nGreen Outlet,1\nGreen Payoff,1\n"
            "Black Payoff,1\nColorless Payoff,1\n",
            encoding="utf-8",
        )
        self.deck.write_text(
            "56 Forest\n1 Green Outlet\n1 Green Payoff\n"
            "1 Black Payoff\n1 Colorless Payoff\n", encoding="utf-8"
        )
        self.snapshot.write_text(json.dumps({
            "version": "test", "timestamp": "test",
            "variants": [
                variant("green", "Green Outlet", "Green Payoff"),
                variant("black", "Green Outlet", "Black Payoff"),
                variant("colorless", "Green Outlet", "Colorless Payoff"),
                variant("missing-oracle", "Green Outlet", "Unknown Oracle"),
            ],
        }), encoding="utf-8")

    def run_report(self, *, mode="collection", colors=None, commander=None):
        return REPORT.build_report(
            oracle=self.oracle, collection=self.collection, theme="sacrifice",
            mode=mode, deck=self.deck if mode != "collection" else None,
            commander=commander, snapshot=self.snapshot, colors=colors,
            limit=20,
        )

    def test_green_color_preference_filters_all_three_sources(self):
        result = self.run_report(colors="G")
        names = {r["name"] for r in result["card_search"]["results"]}
        self.assertIn("Green Outlet", names)
        self.assertIn("Green Payoff", names)
        self.assertIn("Colorless Payoff", names)
        self.assertNotIn("Black Payoff", names)
        for pair in result["synergies"]["pairs"]:
            self.assertNotEqual(pair["payoff"], "Black Payoff")
        exact = result["combos"]["exact_card_ingredient_candidates"]
        self.assertEqual({r["variant_id"] for r in exact}, {"green", "colorless"})
        self.assertEqual(result["combos"]["total_exact_card_ingredient_candidates"], 2)
        self.assertEqual(result["combos"]["total_one_card_missing_candidates"], 0)
        screen = result["combos"]["casual_color_screen"]
        self.assertEqual(screen["excluded_off_color_variants"], 1)
        self.assertEqual(screen["unverified_or_missing_oracle_variants"], 1)
        self.assertEqual(result["status"], "PARTIAL")
        self.assertEqual(result["selected_casual_colors"], "G")

    def test_casual_existing_deck_not_modified_or_invalidated_by_preference(self):
        frozen = self.deck.read_bytes()
        result = self.run_report(mode="casual", colors="G")
        self.assertEqual(result["validation"]["status"], "PASS_WITH_LIMITATIONS")
        self.assertEqual(self.deck.read_bytes(), frozen)
        self.assertNotIn(
            "black", {x["variant_id"] for x in
                      result["combos"]["exact_card_ingredient_candidates"]},
        )

    def test_unfiltered_default_keeps_existing_behavior(self):
        result = self.run_report()
        self.assertEqual(result["combos"]["total_exact_card_ingredient_candidates"], 3)
        self.assertEqual(result["combos"]["total_one_card_missing_candidates"], 1)
        self.assertIsNone(result["selected_casual_colors"])

    def test_invalid_color_and_commander_preference_are_rejected(self):
        with self.assertRaises(ValueError):
            self.run_report(colors="XX")
        with self.assertRaisesRegex(ValueError, "Casual"):
            self.run_report(mode="commander", colors="G", commander="Green Outlet")

    def test_cli_passes_color_preference(self):
        output = self.oracle.parent / "result.json"
        code = REPORT.main([
            "--oracle", str(self.oracle), "--collection", str(self.collection),
            "--theme", "sacrifice", "--colors", "G",
            "--snapshot", str(self.snapshot), "--output", str(output),
        ])
        self.assertEqual(code, 0)
        document = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(document["selected_casual_colors"], "G")
        self.assertEqual(document["combos"]["total_exact_card_ingredient_candidates"], 2)


if __name__ == "__main__":
    unittest.main()
