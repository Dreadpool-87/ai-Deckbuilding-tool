"""Validator CLI documentation contract (synthetic, no collection data)."""
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "validator" / "MTG_Deck_Validator_v1.1.1.py"


class ValidatorCliUsageContractTests(unittest.TestCase):
    def test_docstring_usage_references_current_entrypoint(self):
        source = VALIDATOR.read_text(encoding="utf-8")
        self.assertIn("Usage: python validator/MTG_Deck_Validator_v1.1.1.py --help", source)
        self.assertNotIn("Usage: python MTG_Deck_Validator_v1.1.py --help", source)

    def test_current_cli_help_executes(self):
        completed = subprocess.run(
            [sys.executable, str(VALIDATOR), "--help"],
            text=True, capture_output=True, timeout=15,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("--oracle", completed.stdout)
        self.assertIn("--mode", completed.stdout)
        self.assertIn("--output", completed.stdout)


if __name__ == "__main__":
    unittest.main()
