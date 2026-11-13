"""Standalone synthetic adapter tests; no MCP SDK, Oracle or network required."""
import json
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

from integrations.mcp import bridge


class BridgeTests(unittest.TestCase):
    def test_confirmation_required_without_process(self):
        with patch.object(bridge.subprocess, "run") as run:
            result = bridge.execute("discover", "Name,Quantity\nShock,4", theme="burn", confirmed=False)
            self.assertEqual(result["reason_codes"], ["CURRENT_RUN_COLLECTION_CONFIRMATION_REQUIRED"])
            run.assert_not_called()

    def test_bad_inputs_rejected_before_process(self):
        with patch.object(bridge.subprocess, "run") as run:
            self.assertEqual(bridge.execute("validate", "Name,Quantity\nShock,4",
                                            decklist="", confirmed=True)["status"], "UNVERIFIED")
            self.assertEqual(bridge.execute("discover", "Name,Quantity\nShock,4",
                                            theme="x" * 257, confirmed=True)["reason_codes"],
                             ["THEME_REQUIRED_OR_TOO_LONG"])
            run.assert_not_called()

    def test_real_cli_shape_and_private_temp_cleanup(self):
        paths = []

        def fake_run(args, **kwargs):
            self.assertIn("--collection-confirmed", args)
            self.assertEqual(kwargs["stdin"], subprocess.DEVNULL)
            csv_path = Path(args[args.index("--collection") + 1])
            deck_path = Path(args[args.index("--deck") + 1])
            self.assertIn("Shock,4", csv_path.read_text())
            self.assertIn("4 Shock", deck_path.read_text())
            paths.extend([csv_path, deck_path])
            return subprocess.CompletedProcess(args, 0, stdout=json.dumps({
                "action": "validate", "status": "VALIDATED_WITH_LIMITATIONS",
                "validated": True,
                "gateway": {"status": "VALIDATED_WITH_LIMITATIONS",
                            "tool_execution": "EXECUTED", "executed": True},
            }).encode(), stderr=b"")

        with patch.object(bridge.subprocess, "run", side_effect=fake_run):
            result = bridge.execute("validate", "Name,Quantity\nShock,4",
                                    decklist="4 Shock", confirmed=True)
        self.assertEqual(result["status"], "VALIDATED_WITH_LIMITATIONS")
        self.assertEqual(result["cli_exit_code"], 0)
        self.assertTrue(all(not p.exists() for p in paths))

    def test_invalid_deck_preserved_as_blocked(self):
        report = {"action": "validate", "status": "BLOCKED_INVALID_DECK", "validated": False}
        with patch.object(bridge.subprocess, "run", return_value=subprocess.CompletedProcess(
            [], 2, stdout=json.dumps(report).encode(), stderr=b"")):
            result = bridge.execute("validate", "Name,Quantity\nShock,4",
                                    decklist="5 Shock", confirmed=True)
        self.assertEqual(result["status"], "BLOCKED_INVALID_DECK")
        self.assertFalse(result["validated"])

    def test_fake_success_rejected(self):
        fake = {"action": "validate", "status": "VALIDATED_WITH_LIMITATIONS", "validated": True}
        with patch.object(bridge.subprocess, "run", return_value=subprocess.CompletedProcess(
            [], 2, stdout=json.dumps(fake).encode(), stderr=b"")):
            result = bridge.execute("validate", "Name,Quantity\nShock,4",
                                    decklist="4 Shock", confirmed=True)
        self.assertEqual(result["reason_codes"], ["CLI_RESULT_CONTRACT_MISMATCH"])

    def test_no_gateway_evidence_never_counts_as_validation(self):
        fake = {"action": "validate", "status": "VALIDATED_WITH_LIMITATIONS", "validated": True}
        with patch.object(bridge.subprocess, "run", return_value=subprocess.CompletedProcess(
            [], 0, stdout=json.dumps(fake).encode(), stderr=b"")):
            result = bridge.execute("validate", "Name,Quantity\nShock,4",
                                    decklist="4 Shock", confirmed=True)
        self.assertEqual(result["reason_codes"], ["GATEWAY_EXECUTION_EVIDENCE_MISSING"])

    def test_timeout_not_misreported_as_validation(self):
        with patch.object(bridge.subprocess, "run", side_effect=subprocess.TimeoutExpired("python", 240)):
            result = bridge.execute("discover", "Name,Quantity\nShock,4",
                                    theme="burn", confirmed=True)
        self.assertEqual(result["tool_execution"], "FAILED_AFTER_START")
        self.assertFalse(result["validated"])


if __name__ == "__main__":
    unittest.main()
