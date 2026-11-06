"""Smoke-check the actual Validator CLI / JSON handoff, without private inventory."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "validator" / "MTG_Deck_Validator_v1.1.1.py"


def card(name, mana_value, types, supertypes=()):
    return {"name": name, "manaValue": mana_value,
            "manaCost": None if "Land" in types else "{R}",
            "types": list(types), "supertypes": list(supertypes),
            "colorIdentity": [] if "Land" in types else ["R"]}


class CasualValidatorHandoffTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.folder = Path(tmp.name)
        self.oracle = self.folder / "oracle.json"
        self.collection = self.folder / "collection.csv"
        self.deck = self.folder / "baseline.txt"
        self.report = self.folder / "report.json"
        self.cards = {
            "Mountain": [card("Mountain", 0, ["Land"], ["Basic"])],
            "Fixture Bolt": [card("Fixture Bolt", 1, ["Instant"])],
            "Fixture Dragon": [card("Fixture Dragon", 8, ["Creature"])],
        }
        self.oracle.write_text(json.dumps({"meta": {"version": "synthetic"}, "data": self.cards}),
                               encoding="utf-8")
        # Different printings / duplicate rows are deliberately aggregated.
        self.collection.write_text("Name,Quantity\nFixture Bolt,1\nFixture Bolt,3\nFixture Dragon,3\n",
                                   encoding="utf-8")
        self.deck.write_text("53 Mountain\n4 Fixture Bolt\n3 Fixture Dragon\n",
                             encoding="utf-8")

    def invoke(self):
        return subprocess.run([
            sys.executable, str(VALIDATOR),
            "--collection", str(self.collection),
            "--oracle", str(self.oracle),
            "--deck", str(self.deck), "--mode", "casual", "--exact-60",
            "--output", str(self.report),
        ], capture_output=True, text=True, check=False, timeout=20)

    def test_real_cli_json_pass_and_frozen_baseline(self):
        before = self.deck.read_bytes()
        result = self.invoke()
        self.assertEqual(result.returncode, 0, result.stderr)
        output = json.loads(self.report.read_text(encoding="utf-8"))
        self.assertEqual(json.loads(result.stdout), output)
        self.assertEqual(output["status"], "PASS_WITH_LIMITATIONS")
        self.assertEqual(output["checks"]["ownership"], "PASS")
        self.assertEqual(output["checks"]["mana_curve"], "PASS")
        self.assertEqual(output["deck_cards"], 60)
        integrity = output["mana_curve_integrity"]
        self.assertEqual(integrity["status"], "ORACLE_ARITHMETIC_PASS")
        self.assertEqual(integrity["bins"], {
            "0": 0, "1": 4, "2": 0, "3": 0, "4": 0,
            "5": 0, "6": 0, "7+": 3,
        })
        self.assertEqual(integrity["nonland_copies"], 7)
        self.assertEqual(integrity["weighted_mana_value_total"], 28)
        self.assertEqual(integrity["average_mana_value_fraction"], "4")
        self.assertEqual(integrity["average_mana_value_rounded"], 4.0)
        self.assertEqual(sum(r["weighted_mana_value"] for r in integrity["ledger"]), 28)
        self.assertEqual(self.deck.read_bytes(), before)

    def test_real_cli_does_not_relabel_unverified_curve_as_pass(self):
        self.cards["Fixture Dragon"] = [card("Fixture Dragon", None, ["Creature"])]
        self.oracle.write_text(json.dumps({"meta": {"version": "synthetic"}, "data": self.cards}),
                               encoding="utf-8")
        result = self.invoke()
        self.assertEqual(result.returncode, 3, result.stderr)
        output = json.loads(self.report.read_text(encoding="utf-8"))
        self.assertEqual(output["status"], "UNVERIFIED")
        self.assertEqual(output["checks"]["mana_curve"], "UNVERIFIED")
        integrity = output["mana_curve_integrity"]
        self.assertEqual(integrity["status"], "UNVERIFIED")
        self.assertIsNone(integrity["average_mana_value_rounded"])
        self.assertEqual(integrity["unresolved_mana_values"], ["Fixture Dragon"])


if __name__ == "__main__":
    unittest.main()
