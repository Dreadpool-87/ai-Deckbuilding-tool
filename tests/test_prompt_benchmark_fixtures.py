"""Preflight fixed benchmark inputs with real tools; this does not test AI behavior."""
import csv
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MATERIALIZE = ROOT / "examples/prompt_benchmark/materialize.py"
GATEWAY = ROOT / "tools/agent_gateway.py"


class PromptBenchmarkPreflight(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        temp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(temp.cleanup)
        cls.directory = Path(temp.name)
        cls.inputs = cls.directory / "inputs"
        subprocess.run([sys.executable, str(MATERIALIZE), str(cls.inputs)], check=True)

    def test_inputs_are_byte_reproducible_and_offline_case_has_no_oracle(self):
        other = self.directory / "replica"
        subprocess.run([sys.executable, str(MATERIALIZE), str(other)], check=True)
        expected = {path.relative_to(self.inputs): path.read_bytes()
                    for path in self.inputs.rglob("*") if path.is_file()}
        actual = {path.relative_to(other): path.read_bytes()
                  for path in other.rglob("*") if path.is_file()}
        self.assertEqual(actual, expected)
        self.assertGreaterEqual(sum(path.name == "task.txt" for path in actual), 12)
        self.assertFalse((other / "B14-runtime-unavailable" / "oracle.json").exists())

    def test_same_supply_supports_independent_conflict_and_feasible_joint_allocation(self):
        folder = self.inputs / "B11-simultaneous"
        self.assertEqual((folder / "pool.csv").read_bytes(),
                         (self.inputs / "B13-independent" / "pool.csv").read_bytes())
        with (folder / "pool.csv").open(encoding="utf-8", newline="") as handle:
            owned = Counter({r["Name"]: int(r["Quantity"]) for r in csv.DictReader(handle)})
        first = Counter({name: 4 for name in list(owned)[:8]})
        second = Counter({name: 4 for name in list(owned)[8:16]})
        self.assertEqual(first.total(), 32)
        self.assertEqual(second.total(), 32)
        self.assertLessEqual(first + second, owned)
        self.assertFalse(first + first <= owned)

    def test_frozen_decks_distinguish_structural_pass_shortage_and_bad_prepare(self):
        scenarios = (
            ("T01-standard", 0, "VALIDATED_WITH_LIMITATIONS", 0, "PASS", "NOT_APPLICABLE"),
            ("T02-shortage", 2, "BLOCKED_INVALID_DECK", 1, "FAIL", "NOT_APPLICABLE"),
            ("T03-sequencing", 0, "VALIDATED_WITH_LIMITATIONS", 0, "PASS", "NOT_APPLICABLE"),
            ("T04-prepare", 3, "UNVERIFIED", 3, "PASS", "UNVERIFIED"),
        )
        for case, exit_code, status, child_code, ownership, prepare in scenarios:
            with self.subTest(case=case):
                folder = self.inputs / case
                oracle = folder / "oracle.json"
                digest = hashlib.sha256(oracle.read_bytes()).hexdigest()
                invocation = subprocess.run(
                    [sys.executable, str(GATEWAY), "validate", "--oracle", str(oracle),
                     "--oracle-sha256", digest, "--collection", str(folder / "pool.csv"),
                     "--collection-scope", "synthetic", "--deck", str(folder / "frozen.txt"),
                     "--exact-60"],
                    capture_output=True, check=False, timeout=10,
                )
                self.assertEqual(invocation.returncode, exit_code, invocation.stderr.decode())
                report = json.loads(invocation.stdout)
                self.assertTrue(report["executed"])
                self.assertEqual(report["status"], status)
                self.assertEqual(report["child_exit_code"], child_code)
                result = report["result"]
                self.assertEqual(result["checks"]["ownership"], ownership)
                self.assertEqual(result["prepare_layout_audit"]["status"], prepare)
                self.assertEqual(result["checks"]["mana_production_and_castability"], "NOT_CHECKED")
                if prepare == "UNVERIFIED":
                    self.assertNotEqual(result["mana_curve_integrity"]["status"],
                                        "ORACLE_ARITHMETIC_PASS")


if __name__ == "__main__":
    unittest.main()
