"""End-to-end KISS tests: existing modules are imported, never rewritten."""
from collections import Counter
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

BASE = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("combo_synergy_v05", BASE / "tools/combo_synergy_report.py")
MOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)


def card(name, text, types=("Creature",), basics=False, legendary=False, identity=("B",)):
    return {
        "name": name, "text": text, "types": list(types),
        "supertypes": (["Basic"] if basics else ["Legendary"] if legendary else []),
        "subtypes": [], "manaValue": 0 if basics else 2,
        "colorIdentity": list(identity),
        "keywords": [], "leadershipSkills": {"commander": True} if legendary else {},
    }


def variant(vid, cards, *, commander_required=False):
    return {
        "id": vid, "status": "OK", "spoiler": False, "requires": [],
        "uses": [
            {"card": {"name": name}, "quantity": count,
             **({"mustBeCommander": True} if commander_required and name == "Commander X" else {})}
            for name, count in cards.items()
        ],
        "identity": "B", "produces": [{"feature": {"name": "Draw a card"}}],
        "salt": None, "saltVoteCount": 0, "popularity": 1,
    }


class CombinedReportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)
        self.oracle = self.path / "oracle.json"
        self.collection = self.path / "private.csv"
        self.deck = self.path / "deck.txt"
        self.snapshot = self.path / "spellbook.json"
        self.cards = {
            "Swamp": [card("Swamp", "{T}: Add {B}.", types=("Land",), basics=True,
                           identity=())],
            "Sac Outlet": [card("Sac Outlet", "Sacrifice a creature: Scry 1.")],
            "Death Payoff": [card("Death Payoff",
                                  "Whenever another nontoken creature dies, each opponent loses 2 life.")],
            "Commander X": [card("Commander X", "When this creature enters, draw a card.",
                                   legendary=True)],
        }
        self.oracle.write_text(json.dumps({
            "meta": {"version": "synthetic"}, "data": self.cards
        }), encoding="utf-8")
        self.collection.write_text(
            "Name,Quantity\nSac Outlet,1\nDeath Payoff,1\nCommander X,1\n",
            encoding="utf-8",
        )
        self.snapshot.write_text(json.dumps({
            "version": "fixture", "timestamp": "fixture-time",
            "variants": [
                variant("pair", {"Sac Outlet": 1, "Death Payoff": 1}),
                variant("basic", {"Sac Outlet": 1, "Swamp": 1}),
                variant("commander", {"Commander X": 1, "Sac Outlet": 1},
                        commander_required=True),
            ],
        }), encoding="utf-8")

    def run_report(self, *, mode="collection", deck=None, snapshot=None,
                   theme="sacrifice", commander=None):
        return MOD.build_report(
            oracle=self.oracle, collection=self.collection, theme=theme,
            mode=mode, deck=deck, commander=commander, snapshot=snapshot,
            limit=20,
        )

    def test_collection_keeps_basic_unlimited_only_in_combo_screen(self):
        result = self.run_report(snapshot=self.snapshot)
        self.assertEqual(result["status"], "COMPLETED_WITH_LIMITATIONS")
        self.assertEqual(result["selection_scope"], "ACTIVE_COLLECTION")
        self.assertEqual(result["synergies"]["returned_pairs"], 1)
        self.assertEqual(
            {x["variant_id"] for x in result["combos"]["exact_card_ingredient_candidates"]},
            {"pair", "basic"},
        )
        self.assertEqual(result["combos"]["counts"]["requires_commander_excluded"], 1)
        self.assertIn("Swamp", result["collection_basic_policy"]["virtual_basic_names"])
        self.assertNotIn("Swamp", MOD.load_module("search", [
            BASE/"tools/card_search.py"]).read_collection(self.collection))
        self.assertIsNone(result["combos"]["deck_size"])  # no fabricated deck size
        self.assertEqual(result["combos"]["collection_owned_copies"], 3)
        self.assertNotIn(str(self.path), json.dumps(result))
        self.assertEqual(result["validation"]["status"], "NOT_APPLICABLE_TO_COLLECTION")

    def test_without_snapshot_only_combo_is_skipped(self):
        result = self.run_report()
        self.assertEqual(result["status"], "PARTIAL")
        self.assertEqual(result["combos"]["status"], "NOT_EXECUTED")
        self.assertEqual(result["synergies"]["returned_pairs"], 1)
        self.assertTrue(result["card_search"]["results"])

    def test_no_snapshot_never_loads_optional_spellbook_module(self):
        from unittest.mock import patch
        original = MOD.load_module

        def load_if_needed(name, candidates):
            if name == "spellbook":
                raise AssertionError("Optional Spellbook import was not needed")
            return original(name, candidates)

        with patch.object(MOD, "load_module", side_effect=load_if_needed):
            result = self.run_report()
        self.assertEqual(result["status"], "PARTIAL")
        self.assertEqual(result["synergies"]["returned_pairs"], 1)

    def test_casual_60_with_snapshot_and_ownership(self):
        self.deck.write_text("58 Swamp\n1 Sac Outlet\n1 Death Payoff\n", encoding="utf-8")
        result = self.run_report(mode="casual", deck=self.deck, snapshot=self.snapshot)
        self.assertEqual(result["status"], "COMPLETED_WITH_LIMITATIONS", result["validation"])
        self.assertEqual(result["validation"]["status"], "PASS_WITH_LIMITATIONS")
        self.assertEqual(result["combos"]["analysis_scope"], "casual60")
        self.assertEqual(result["combos"]["total_exact_card_ingredient_candidates"], 2)
        self.assertEqual(result["synergies"]["returned_pairs"], 1)
        self.assertEqual(result["selection_scope"], "SUBMITTED_DECK")

    def test_casual_61_remains_legal_but_combo_not_executed(self):
        self.deck.write_text("59 Swamp\n1 Sac Outlet\n1 Death Payoff\n", encoding="utf-8")
        result = self.run_report(mode="casual", deck=self.deck, snapshot=self.snapshot)
        self.assertEqual(result["validation"]["status"], "PASS_WITH_LIMITATIONS")
        self.assertEqual(result["status"], "PARTIAL")
        self.assertEqual(result["combos"]["status"], "NOT_EXECUTED")
        self.assertIn("exactly 60", result["combos"]["reason"])

    def test_commander_100_identity_and_commander_only_combo(self):
        self.deck.write_text(
            "Commander\n1 Commander X\nDeck\n97 Swamp\n1 Sac Outlet\n1 Death Payoff\n",
            encoding="utf-8",
        )
        result = self.run_report(mode="commander", deck=self.deck,
                                 commander="Commander X", snapshot=self.snapshot)
        self.assertEqual(result["validation"]["status"], "PASS_WITH_LIMITATIONS", result["validation"])
        self.assertEqual(result["commander_identity_from_oracle"], "B")
        self.assertEqual(result["combos"]["analysis_scope"], "commander")
        self.assertEqual(result["combos"]["total_exact_card_ingredient_candidates"], 3)

    def test_unowned_nonbasic_blocks_all_analyses(self):
        self.collection.write_text("Name,Quantity\nDeath Payoff,1\n", encoding="utf-8")
        self.deck.write_text("58 Swamp\n1 Sac Outlet\n1 Death Payoff\n", encoding="utf-8")
        result = self.run_report(mode="casual", deck=self.deck, snapshot=self.snapshot)
        self.assertEqual(result["status"], "BLOCKED_INVALID_DECK")
        self.assertEqual(result["card_search"]["status"], "NOT_EXECUTED")
        self.assertEqual(result["combos"]["status"], "NOT_EXECUTED")
        self.assertEqual(result["validation"]["checks"]["ownership"], "FAIL")

    def test_lifegain_reuses_existing_pair_search_not_new_profile(self):
        self.cards["Life Source"] = [card("Life Source",
            "Whenever another creature enters the battlefield under your control, you gain 1 life.")]
        self.cards["Life Payoff"] = [card("Life Payoff",
            "Whenever you gain life, put a +1/+1 counter on this creature.")]
        self.oracle.write_text(json.dumps({
            "meta": {"version": "synthetic"}, "data": self.cards}), encoding="utf-8")
        self.collection.write_text(
            "Name,Quantity\nLife Source,2\nLife Payoff,1\n", encoding="utf-8")
        result = self.run_report(theme="lifegain")
        self.assertEqual(result["synergies"]["returned_pairs"], 1)
        self.assertEqual(result["synergies"]["status"],
                         "BOUNDED_SYNERGY_CANDIDATES_NOT_VERIFIED_COMBOS")

    def test_unknown_theme_does_not_invent_pair_engine(self):
        result = self.run_report(theme="unrecognized hypothetical effect")
        self.assertEqual(result["synergies"]["status"], "UNSUPPORTED_PAIR_PROFILE")
        self.assertEqual(result["status"], "PARTIAL")

    def test_input_gates_and_corrupt_snapshot_fail_fast(self):
        with self.assertRaisesRegex(ValueError, "requires --deck"):
            self.run_report(mode="casual")
        with self.assertRaisesRegex(ValueError, "Commander mode requires"):
            self.run_report(mode="commander", deck=self.deck)
        with self.assertRaises((OSError, ValueError)):
            self.run_report(snapshot=self.path / "missing_spellbook.gz")

    def test_cli_output_and_no_data_leak(self):
        outfile = self.path / "report.json"
        code = MOD.main([
            "--oracle", str(self.oracle), "--collection", str(self.collection),
            "--theme", "sacrifice", "--snapshot", str(self.snapshot),
            "--output", str(outfile),
        ])
        self.assertEqual(code, 0)
        doc = json.loads(outfile.read_text(encoding="utf-8"))
        self.assertEqual(doc["version"], "0.5.0")
        self.assertNotIn(str(self.path), outfile.read_text(encoding="utf-8"))
        self.assertEqual(
            self.collection.read_text(encoding="utf-8"),
            "Name,Quantity\nSac Outlet,1\nDeath Payoff,1\nCommander X,1\n",
        )

    def test_cli_casual_lifecycle_without_and_with_snapshot_then_blocks_bad_deck(self):
        """Run the actual v0.5 CLI, preserving separate validation/combos statuses."""
        outfile = self.path / "casual_report.json"
        cli = ["--oracle", str(self.oracle), "--collection", str(self.collection),
               "--mode", "casual", "--deck", str(self.deck),
               "--theme", "sacrifice", "--output", str(outfile)]

        # Builder handoff: a *synthetic* 60-card list, not a personal inventory.
        self.deck.write_text("58 Swamp\n1 Sac Outlet\n1 Death Payoff\n", encoding="utf-8")
        code_without_snapshot = MOD.main(cli)
        report = json.loads(outfile.read_text(encoding="utf-8"))
        self.assertEqual(code_without_snapshot, 0)
        self.assertEqual(report["status"], "PARTIAL")
        self.assertEqual(report["validation"]["status"], "PASS_WITH_LIMITATIONS")
        self.assertEqual(report["combos"]["status"], "NOT_EXECUTED")
        self.assertGreaterEqual(report["synergies"]["returned_pairs"], 1)
        self.assertEqual(report["selection_scope"], "SUBMITTED_DECK")

        # Explicit optional Spellbook snapshot exercises the complete v0.5 path.
        code_with_snapshot = MOD.main(cli + ["--snapshot", str(self.snapshot)])
        report = json.loads(outfile.read_text(encoding="utf-8"))
        self.assertEqual(code_with_snapshot, 0)
        self.assertEqual(report["status"], "COMPLETED_WITH_LIMITATIONS")
        self.assertEqual(report["validation"]["status"], "PASS_WITH_LIMITATIONS")
        self.assertIn(
            "pair",
            {v["variant_id"] for v in report["combos"]["exact_card_ingredient_candidates"]},
        )

        # Invalid ownership must BLOCK the downstream engines, not return a combo.
        self.deck.write_text("58 Swamp\n2 Sac Outlet\n", encoding="utf-8")
        code_invalid = MOD.main(cli + ["--snapshot", str(self.snapshot)])
        report = json.loads(outfile.read_text(encoding="utf-8"))
        self.assertEqual(code_invalid, 2)
        self.assertEqual(report["status"], "BLOCKED_INVALID_DECK")
        self.assertEqual(report["validation"]["checks"]["ownership"], "FAIL")
        self.assertEqual(report["card_search"]["status"], "NOT_EXECUTED")
        self.assertEqual(report["synergies"]["status"], "NOT_EXECUTED")
        self.assertEqual(report["combos"]["status"], "NOT_EXECUTED")
        self.assertNotIn(str(self.path), outfile.read_text(encoding="utf-8"))



    def test_independent_decks_reuse_owned_cards_without_consuming_inventory(self):
        """Three successive decks validate against the same unchanged active pool."""
        saved_collection = self.collection.read_bytes()
        examples = [
            ("casual", None, "58 Swamp\n1 Sac Outlet\n1 Death Payoff\n"),
            ("casual", None, "59 Swamp\n1 Sac Outlet\n"),
            ("commander", "Commander X",
             "98 Swamp\n1 Commander X\n1 Sac Outlet\n"),
        ]
        for mode, leader, text in examples:
            with self.subTest(mode=mode, commander=leader, deck=text):
                self.deck.write_text(text, encoding="utf-8")
                result = self.run_report(mode=mode, commander=leader, deck=self.deck)
                self.assertEqual(result["validation"]["status"], "PASS_WITH_LIMITATIONS",
                                 result["validation"])
                self.assertEqual(result["selection_scope"], "SUBMITTED_DECK")
                self.assertEqual(self.collection.read_bytes(), saved_collection)
        self.assertEqual(self.collection.read_bytes(), saved_collection)


if __name__ == "__main__":
    unittest.main()
