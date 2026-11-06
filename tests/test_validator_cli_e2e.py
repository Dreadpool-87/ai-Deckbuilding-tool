"""Offline end-to-end CLI regression: CSV -> compressed Oracle -> deck -> JSON."""
import gzip
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]


class ValidatorCLIEndToEndTests(unittest.TestCase):
    def test_cli_full_csv_gzip_deck_to_json_report_and_insufficient_ownership(self):
        with tempfile.TemporaryDirectory() as folder:
            root = pathlib.Path(folder)
            collection = root / "collection.csv"
            oracle = root / "AtomicCards.json.gz"
            deck = root / "deck.txt"
            output = root / "report.json"
            collection.write_text("Name,Quantity,Edition code\nshock,4,SYN\n", encoding="utf-8")
            deck.write_text("56 Plains\n4 Shock\n", encoding="utf-8")
            mock_oracle = {"meta": {"version": "synthetic"}, "data": {
                "Plains": [{"name": "Plains", "types": ["Land"],
                            "supertypes": ["Basic"], "manaValue": 0, "colorIdentity": ["W"]}],
                "Shock": [{"name": "Shock", "types": ["Instant"],
                           "supertypes": [], "manaValue": 1, "manaCost": "{R}",
                           "colorIdentity": ["R"]}],
            }}
            with gzip.open(oracle, "wt", encoding="utf-8") as stream:
                json.dump(mock_oracle, stream)
            args = [sys.executable, str(ROOT / "validator" / "MTG_Deck_Validator_v1.1.1.py"),
                    "--collection", str(collection), "--oracle", str(oracle),
                    "--deck", str(deck), "--exact-60", "--output", str(output)]
            completed = subprocess.run(args, capture_output=True, text=True, check=False)
            self.assertEqual(completed.returncode, 0, completed.stderr + completed.stdout)
            report = json.loads(completed.stdout)
            self.assertEqual(report, json.loads(output.read_text(encoding="utf-8")))
            self.assertEqual(report["status"], "PASS_WITH_LIMITATIONS")
            self.assertEqual(report["checks"]["ownership"], "PASS")
            self.assertEqual(report["checks"]["oracle_lookup"], "PASS")
            self.assertEqual(report["checks"]["land_probability"], "PASS_EXACT")
            self.assertEqual(report["deck_cards"], 60)
            self.assertEqual(report["lands_physical"], 56)

            collection.write_text("Name,Quantity,Edition code\nshock,3,SYN\n", encoding="utf-8")
            insufficient = subprocess.run(args, capture_output=True, text=True, check=False)
            self.assertEqual(insufficient.returncode, 1, insufficient.stderr)
            failing_report = json.loads(insufficient.stdout)
            self.assertEqual(failing_report["status"], "FAIL")
            self.assertEqual(failing_report["checks"]["ownership"], "FAIL")
            self.assertEqual(failing_report["checks"]["oracle_lookup"], "PASS")


if __name__ == "__main__":
    unittest.main()
