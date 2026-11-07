"""End-to-end CLI tests with synthetic Oracle and inventory only.

These tests verify real Gateway/Validator subprocess execution, not strategic
deck quality and not a user-provided collection.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class OneCommandCliTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        directory = Path(temporary.name)
        cards = {
            "Plains": [{
                "name": "Plains", "types": ["Land"], "supertypes": ["Basic"],
                "colorIdentity": [], "manaValue": 0, "text": "{T}: Add {W}.",
            }],
            "Shock": [{
                "name": "Shock", "types": ["Instant"], "supertypes": [],
                "colorIdentity": ["R"], "manaValue": 1, "manaCost": "{R}",
                "text": "Shock deals 1 damage to target attacking creature.",
            }],
        }
        self.oracle = directory / "synthetic-oracle.json"
        self.oracle.write_text(json.dumps({"meta": {"version": "synthetic"},
                                           "data": cards}), encoding="utf-8")
        self.digest = hashlib.sha256(self.oracle.read_bytes()).hexdigest()
        self.collection = directory / "private-synthetic-collection.csv"
        self.collection.write_text("Name,Quantity\nShock,4\n", encoding="utf-8")
        self.deck = directory / "private-synthetic-deck.txt"
        self.deck.write_text("56 Plains\n4 Shock\n", encoding="utf-8")

    def invoke(self, *flags):
        process = subprocess.run(
            [sys.executable, "-m", "ai_deckbuilding_tool", *map(str, flags)],
            cwd=ROOT, text=True, capture_output=True, timeout=125,
        )
        self.assertTrue(process.stdout.strip(), process.stderr)
        report = json.loads(process.stdout)
        self.assertEqual(report["schema_version"], 1)
        self.assertFalse(report["validated"] and report["status"] != "VALIDATED_WITH_LIMITATIONS")
        return process.returncode, report

    def synthetic_flags(self):
        return ("--synthetic", "--oracle", self.oracle, "--oracle-sha256",
                self.digest, "--collection", self.collection)

    def test_doctor_without_oracle_is_explicitly_incomplete(self):
        code, report = self.invoke("doctor")
        self.assertEqual(code, 3)
        self.assertEqual(report["status"], "UNVERIFIED")
        self.assertEqual(report["reason_codes"], ["PINNED_ORACLE_NOT_SUPPLIED"])
        self.assertEqual(report["preflight"]["status"], "RUNTIME_COMPONENTS_PRESENT")
        self.assertEqual(report["next_action"], "PROVIDE_PINNED_ORACLE")

    def test_discovery_runs_real_child_and_never_claims_validation(self):
        code, report = self.invoke("discover", *self.synthetic_flags(), "--theme", "Shock")
        self.assertEqual(code, 0, report)
        self.assertEqual(report["status"], "CANDIDATES_NOT_VALIDATED")
        self.assertEqual(report["gateway"]["tool_execution"], "EXECUTED")
        self.assertEqual(report["gateway"]["child_exit_code"], 0)
        self.assertEqual(report["next_action"], "AI_BUILD_AND_SUBMIT_DECK")
        self.assertFalse(report["validated"])

    def test_valid_deck_executes_actual_gateway_and_validator(self):
        code, report = self.invoke("validate", *self.synthetic_flags(), "--deck", self.deck)
        self.assertEqual(code, 0, report)
        self.assertEqual(report["status"], "VALIDATED_WITH_LIMITATIONS")
        self.assertTrue(report["validated"])
        self.assertEqual(report["gateway"]["tool_execution"], "EXECUTED")
        self.assertEqual(report["gateway"]["child_exit_code"], 0)
        self.assertEqual(report["gateway"]["result"]["checks"]["copy_limit"], "PASS")
        self.assertEqual(report["next_action"], "AI_REVIEW_VALIDATED_DECK")

    def test_invalid_copy_count_requires_revision(self):
        self.deck.write_text("55 Plains\n5 Shock\n", encoding="utf-8")
        code, report = self.invoke("validate", *self.synthetic_flags(), "--deck", self.deck)
        self.assertEqual(code, 2, report)
        self.assertEqual(report["status"], "BLOCKED_INVALID_DECK")
        self.assertFalse(report["validated"])
        self.assertEqual(report["gateway"]["result"]["checks"]["copy_limit"], "FAIL")
        self.assertEqual(report["gateway"]["child_exit_code"], 1)
        self.assertEqual(report["next_action"], "AI_REVISE_DECK_AND_REVALIDATE")

    def test_real_mode_rejects_unpinned_oracle_without_validator_run(self):
        code, report = self.invoke(
            "validate", "--oracle", self.oracle, "--collection", self.collection,
            "--collection-confirmed", "--deck", self.deck,
        )
        self.assertEqual(code, 3, report)
        self.assertEqual(report["reason_codes"], ["PREFLIGHT_UNVERIFIED"])
        self.assertIsNone(report["gateway"])
        self.assertFalse(report["validated"])

    def test_synthetic_scope_refuses_false_collection_confirmation(self):
        code, report = self.invoke(
            "validate", *self.synthetic_flags(), "--collection-confirmed", "--deck", self.deck,
        )
        self.assertEqual(code, 2)
        self.assertEqual(report["reason_codes"], ["SYNTHETIC_COLLECTION_CANNOT_BE_CONFIRMED"])
        self.assertIsNone(report["gateway"])

    def test_wrong_arguments_fail_with_machine_readable_status(self):
        code, report = self.invoke("validate", "--definitely-not-an-option", "/secret/file")
        self.assertEqual(code, 2)
        self.assertEqual(report["status"], "INPUT_ERROR")
        self.assertEqual(report["reason_codes"], ["INVALID_ARGUMENTS"])
        self.assertNotIn("/secret/file", json.dumps(report))


if __name__ == "__main__":
    unittest.main()
