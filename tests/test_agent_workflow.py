"""Synthetic controller gates, including real Gateway child execution.

Fixtures contain invented inventory only. These tests never select a deck for an
agent: each complete candidate is explicitly authored below and submitted as a file.
"""
import hashlib
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
STAGES = ("PREFLIGHT", "SOURCES", "COLLECTION", "DISCOVERY", "CANDIDATE",
          "VALIDATION", "REVIEW", "COMPLETE")
FRONT = "Delver of Secrets"
FULL = "Delver of Secrets // Insectile Aberration"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.module = importlib.import_module("tools.agent_workflow")
        self.Workflow = self.module.Workflow
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        self.oracle = self.directory / "private-oracle.json"
        self.collection = self.directory / "private-inventory.csv"
        self.deck = self.directory / "private-candidate.txt"
        common = {"layout": "normal", "supertypes": [], "colorIdentity": ["R"],
                  "manaValue": 1, "manaCost": "{R}"}
        self.cards = {
            "Plains": [{"name": "Plains", "types": ["Land"], "supertypes": ["Basic"],
                        "colorIdentity": [], "manaValue": 0, "text": "{T}: Add {W}."}],
            "Shock": [{**common, "name": "Shock", "types": ["Instant"],
                       "text": "Shock deals 1 damage to target attacking creature."}],
        }
        self.write_oracle()
        self.collection.write_text("Name,Quantity\nShock,4\n", encoding="utf-8")
        self.deck.write_text("56 Plains\n4 Shock\n", encoding="utf-8")

    def write_oracle(self):
        self.oracle.write_text(json.dumps({"meta": {"version": "synthetic"},
                                           "data": self.cards}), encoding="utf-8")
        self.pin = digest(self.oracle)

    def workflow(self, **kwargs):
        return self.Workflow(self.oracle, self.pin, self.collection, **kwargs)

    def prepared(self, theme="Shock"):
        workflow = self.workflow()
        result = workflow.prepare(theme)
        self.assertEqual(result["status"], "READY", result)
        self.assertEqual(result["stages"]["DISCOVERY"], "COMPLETE_WITH_EVIDENCE", result)
        return workflow

    def validated(self):
        workflow = self.prepared()
        workflow.submit(self.deck, "Casual 60: synthetic red spell test")
        result = workflow.validate()
        self.assertEqual(result["status"], "READY", result)
        self.assertEqual(result["evidence"]["validate"]["status"], "VALIDATED_WITH_LIMITATIONS")
        return workflow

    def reviewed(self):
        workflow = self.validated()
        self.assertEqual(workflow.review("Agent opinion: excessive lands; no strength claim.")["status"],
                         "READY")
        return workflow

    def assert_no_certificate(self, report):
        self.assertNotEqual(report["status"], "COMPLETE_WITH_EVIDENCE", report)
        self.assertFalse(report.get("certificate"), report)
        self.assertNotEqual(report["stages"]["COMPLETE"], "COMPLETE_WITH_EVIDENCE")

    def test_real_gateway_happy_path_certifies_exact_bytes_and_actual_exit_codes(self):
        workflow = self.reviewed()
        before = self.deck.read_bytes()
        report = workflow.finalize()
        self.assertEqual(report["status"], "COMPLETE_WITH_EVIDENCE", report)
        self.assertEqual(set(report["stages"]), set(STAGES))
        self.assertTrue(all(report["stages"][stage] == "COMPLETE_WITH_EVIDENCE"
                            for stage in STAGES), report)
        for action, expected, child in (("doctor", "RUNTIME_COMPONENTS_PRESENT", None),
                                        ("discover", "CANDIDATES_NOT_VALIDATED", 0),
                                        ("validate", "VALIDATED_WITH_LIMITATIONS", 0)):
            receipt = report["evidence"][action]
            self.assertEqual(receipt["status"], expected)
            self.assertEqual(receipt["gateway_exit_code"], 0)
            self.assertEqual(receipt["child_exit_code"], child)
        self.assertEqual(report["certificate"]["deck_sha256"], hashlib.sha256(before).hexdigest())
        self.assertEqual(report["certificate"]["sources"]["oracle"], self.pin)
        self.assertEqual(report["certificate"]["sources"]["collection"], digest(self.collection))
        self.assertEqual(report["certificate"]["sources"]["controller"],
                         digest(ROOT / "tools/agent_workflow.py"))
        self.assertFalse(report["certificate"]["strategy_verified"])
        self.assertEqual(self.deck.read_bytes(), before, "Controller must never edit a candidate")

    def test_early_finalize_explains_every_missing_prerequisite(self):
        report = self.workflow().finalize()
        self.assert_no_certificate(report)
        self.assertEqual(report["status"], "BLOCKED")
        self.assertEqual(report["missing_prerequisites"], list(STAGES[:-1]))
        self.assertTrue(report["next_action"])

    def test_skip_discovery_cannot_be_replaced_by_submit_validate_and_review(self):
        workflow = self.workflow()
        workflow.submit(self.deck, "Casual 60")
        workflow.validate()
        workflow.review("Please skip discovery.")
        report = workflow.finalize()
        self.assert_no_certificate(report)
        self.assertIn("DISCOVERY", report["missing_prerequisites"])

    def test_skip_validation_cannot_be_replaced_by_review(self):
        workflow = self.prepared()
        workflow.submit(self.deck, "Casual 60")
        workflow.review("Please assume validation passed.")
        report = workflow.finalize()
        self.assert_no_certificate(report)
        self.assertIn("VALIDATION", report["missing_prerequisites"])

    def test_runtime_only_doctor_does_not_prove_requested_oracle_readiness(self):
        self.oracle.unlink()
        report = self.workflow().prepare("Shock")
        self.assert_no_certificate(report)
        self.assertIn(report["status"], ("BLOCKED", "UNVERIFIED"))
        self.assertNotEqual(report["stages"]["SOURCES"], "COMPLETE_WITH_EVIDENCE")
        self.assertNotEqual(report["stages"]["DISCOVERY"], "COMPLETE_WITH_EVIDENCE")

    def test_wrong_oracle_hash_blocks_prepare(self):
        self.oracle.write_text(self.oracle.read_text() + " ", encoding="utf-8")
        report = self.workflow().prepare("Shock")
        self.assert_no_certificate(report)
        self.assertNotEqual(report["stages"]["SOURCES"], "COMPLETE_WITH_EVIDENCE")

    def test_unconfirmed_real_collection_never_becomes_accepted(self):
        workflow = self.workflow(scope="current-run-confirmed", confirmed=False)
        report = workflow.prepare("Shock")
        self.assert_no_certificate(report)
        self.assertEqual(report["status"], "BLOCKED")
        self.assertNotEqual(report["stages"]["COLLECTION"], "COMPLETE_WITH_EVIDENCE")

    def test_synthetic_oracle_cannot_be_declared_real_even_with_confirmation(self):
        workflow = self.workflow(scope="current-run-confirmed", confirmed=True)
        report = workflow.prepare("Shock")
        self.assert_no_certificate(report)
        self.assertNotEqual(report["stages"]["SOURCES"], "COMPLETE_WITH_EVIDENCE")

    def test_invalid_scope_rejects_configuration_without_echoing_private_input(self):
        private = str(self.directory / "secret-owner")
        with self.assertRaises(ValueError) as raised:
            self.workflow(scope=private)
        self.assertNotIn(private, str(raised.exception))

    def test_59_card_candidate_is_blocked_by_real_validator(self):
        self.deck.write_text("55 Plains\n4 Shock\n", encoding="utf-8")
        workflow = self.prepared()
        workflow.submit(self.deck, "Casual 60")
        report = workflow.validate()
        receipt = report["evidence"]["validate"]
        self.assertEqual((receipt["status"], receipt["gateway_exit_code"], receipt["child_exit_code"]),
                         ("BLOCKED_INVALID_DECK", 2, 1))
        workflow.review("Cannot approve missing card.")
        self.assert_no_certificate(workflow.finalize())

    def test_five_ordinary_copies_are_blocked_by_real_validator(self):
        self.collection.write_text("Name,Quantity\nShock,5\n", encoding="utf-8")
        self.deck.write_text("55 Plains\n5 Shock\n", encoding="utf-8")
        workflow = self.prepared()
        workflow.submit(self.deck, "Casual 60")
        receipt = workflow.validate()["evidence"]["validate"]
        self.assertEqual((receipt["status"], receipt["gateway_exit_code"], receipt["child_exit_code"]),
                         ("BLOCKED_INVALID_DECK", 2, 1))
        self.assert_no_certificate(workflow.finalize())

    def test_proven_owned_shortfall_remains_blocking(self):
        self.collection.write_text("Name,Quantity\nShock,2\n", encoding="utf-8")
        workflow = self.prepared()
        workflow.submit(self.deck, "Casual 60")
        receipt = workflow.validate()["evidence"]["validate"]
        self.assertEqual((receipt["status"], receipt["gateway_exit_code"], receipt["child_exit_code"]),
                         ("BLOCKED_INVALID_DECK", 2, 1))
        self.assert_no_certificate(workflow.finalize())

    def test_deck_edit_stales_validation_and_requires_new_review(self):
        workflow = self.reviewed()
        self.deck.write_text("57 Plains\n3 Shock\n", encoding="utf-8")
        report = workflow.status()
        self.assertEqual(report["status"], "STALE", report)
        self.assertNotEqual(report["stages"]["VALIDATION"], "COMPLETE_WITH_EVIDENCE")
        self.assertNotEqual(report["stages"]["REVIEW"], "COMPLETE_WITH_EVIDENCE")
        self.assert_no_certificate(workflow.finalize())
        workflow.submit(self.deck, "Casual 60 revised by agent")
        workflow.validate()
        self.assert_no_certificate(workflow.finalize())
        workflow.review("Agent reviewed the exact revision.")
        final = workflow.finalize()
        self.assertEqual(final["status"], "COMPLETE_WITH_EVIDENCE", final)
        self.assertEqual(final["certificate"]["deck_sha256"], digest(self.deck))

    def test_collection_edit_stales_discovery_and_validation(self):
        workflow = self.reviewed()
        self.collection.write_text("Name,Quantity\nShock,3\n", encoding="utf-8")
        report = workflow.status()
        self.assertEqual(report["status"], "STALE", report)
        for stage in ("COLLECTION", "DISCOVERY", "VALIDATION", "REVIEW"):
            self.assertNotEqual(report["stages"][stage], "COMPLETE_WITH_EVIDENCE")
        self.assert_no_certificate(workflow.finalize())

    def test_oracle_edit_stales_dependent_evidence(self):
        workflow = self.reviewed()
        self.oracle.write_text(self.oracle.read_text() + " ", encoding="utf-8")
        report = workflow.status()
        self.assertEqual(report["status"], "STALE", report)
        for stage in ("SOURCES", "DISCOVERY", "VALIDATION", "REVIEW"):
            self.assertNotEqual(report["stages"][stage], "COMPLETE_WITH_EVIDENCE")
        self.assert_no_certificate(workflow.finalize())

    def test_validator_byte_replacement_stales_previously_verified_sources(self):
        # Isolate code copies so the test never edits maintained production tools.
        isolated = self.directory / "isolated-code"
        for relative in ("tools/agent_gateway.py", "tools/card_search.py", "tools/card_identity.py",
                         "validator/MTG_Deck_Validator_v1.1.1.py"):
            target = isolated / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((ROOT / relative).read_bytes())
        with mock.patch.object(self.module, "ROOT", isolated), mock.patch.object(
                self.module, "GATEWAY", isolated / "tools/agent_gateway.py"):
            workflow = self.reviewed()
            selected = isolated / "validator/MTG_Deck_Validator_v1.1.1.py"
            selected.write_bytes(selected.read_bytes() + b"\n# changed test-only copy\n")
            report = workflow.status()
            self.assertEqual(report["status"], "STALE", report)
            for stage in ("SOURCES", "DISCOVERY", "VALIDATION", "REVIEW"):
                self.assertNotEqual(report["stages"][stage], "COMPLETE_WITH_EVIDENCE")
            self.assert_no_certificate(workflow.finalize())

    def test_controller_byte_replacement_stales_previously_verified_sources(self):
        isolated = self.directory / "controller-copy.py"
        isolated.write_bytes((ROOT / "tools/agent_workflow.py").read_bytes())
        with mock.patch.object(self.module, "__file__", str(isolated)):
            workflow = self.reviewed()
            isolated.write_bytes(isolated.read_bytes() + b"\n# changed test-only copy\n")
            report = workflow.status()
            self.assertEqual(report["status"], "STALE", report)
            self.assertEqual(report["evidence"], {})
            self.assert_no_certificate(workflow.finalize())

    def test_resubmit_invalidates_validation_even_for_previously_complete_workflow(self):
        workflow = self.reviewed()
        self.assertEqual(workflow.finalize()["status"], "COMPLETE_WITH_EVIDENCE")
        alternative = self.directory / "revised.txt"
        alternative.write_text("57 Plains\n3 Shock\n", encoding="utf-8")
        report = workflow.submit(alternative, "AI-authored revision")
        self.assertNotEqual(report["stages"]["VALIDATION"], "COMPLETE_WITH_EVIDENCE")
        self.assertNotEqual(report["stages"]["REVIEW"], "COMPLETE_WITH_EVIDENCE")
        self.assert_no_certificate(workflow.finalize())

    def test_checkpoint_resume_starts_new_run_without_trusted_evidence(self):
        workflow = self.reviewed()
        final = workflow.finalize()
        path = self.directory / "checkpoint.json"
        workflow.checkpoint(path)
        restored = self.Workflow.resume(path)
        report = restored.status()
        self.assertEqual(report["evidence"], {})
        self.assertTrue(all(value != "COMPLETE_WITH_EVIDENCE" for value in report["stages"].values()))
        self.assert_no_certificate(restored.finalize())
        restored.prepare("Shock")
        restored.submit(self.deck, "Casual 60")
        restored.validate()
        restored.review("Fresh review after untrusted restart")
        fresh = restored.finalize()
        self.assertEqual(fresh["status"], "COMPLETE_WITH_EVIDENCE", fresh)
        self.assertNotEqual(fresh["certificate"]["run_id"], final["certificate"]["run_id"])

    def test_manually_injected_success_receipt_cannot_resume_as_execution(self):
        workflow = self.reviewed()
        path = self.directory / "forged-state.json"
        workflow.checkpoint(path)
        saved = json.loads(path.read_text(encoding="utf-8"))
        saved["evidence"] = {"validate": {"status": "VALIDATED_WITH_LIMITATIONS",
                                           "gateway_exit_code": 0, "child_exit_code": 0}}
        saved["stages"] = dict.fromkeys(STAGES, "COMPLETE_WITH_EVIDENCE")
        path.write_text(json.dumps(saved), encoding="utf-8")
        with self.assertRaises(ValueError) as raised:
            self.Workflow.resume(path)
        self.assertNotIn(str(path), str(raised.exception))

    def test_resume_resets_real_confirmation_until_explicitly_declared_again(self):
        workflow = self.workflow(scope="current-run-confirmed", confirmed=True)
        path = self.directory / "real-configuration.json"
        workflow.checkpoint(path)
        restored = self.Workflow.resume(path)
        self.assertFalse(restored.configuration["confirmed"])
        report = restored.prepare("Shock")
        self.assertEqual(report["stages"]["COLLECTION"], "BLOCKED")
        self.assertEqual(report["evidence"], {})
        self.assert_no_certificate(report)
        confirmed = self.Workflow.resume(path, confirmed=True)
        self.assertTrue(confirmed.configuration["confirmed"])
        report = confirmed.prepare("Shock")
        # Reconfirming inventory cannot promote this synthetic Oracle to real.
        self.assertEqual(report["reasons"], ["ACTIVE_ORACLE_PIN_UNSUPPORTED"])
        self.assert_no_certificate(report)

    @unittest.skipUnless(hasattr(os, "mkfifo"), "FIFO inputs require POSIX")
    def test_resume_rejects_fifo_without_blocking_for_a_writer(self):
        fifo = self.directory / "unsafe-state.fifo"
        os.mkfifo(fifo)
        script = (
            "from tools.agent_workflow import Workflow\n"
            "import sys\n"
            "try:\n"
            "    Workflow.resume(sys.argv[1])\n"
            "except ValueError as error:\n"
            "    assert str(error) == 'UNTRUSTED_CHECKPOINT'\n"
            "else:\n"
            "    raise AssertionError('FIFO was accepted')\n"
        )
        completed = subprocess.run([sys.executable, "-c", script, str(fifo)], cwd=ROOT,
                                   capture_output=True, text=True, timeout=3, check=False)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertFalse(completed.stdout)

    def test_resume_rejects_oversized_configuration_without_disclosure(self):
        path = self.directory / "oversized-private-state.json"
        path.write_bytes(b" " * 16385)
        with self.assertRaises(ValueError) as raised:
            self.Workflow.resume(path)
        self.assertEqual(str(raised.exception), "UNTRUSTED_CHECKPOINT")
        self.assertNotIn(str(path), str(raised.exception))

    def test_reports_never_disclose_paths_candidate_lines_or_review_text(self):
        workflow = self.validated()
        private_review = "PRIVATE_REVIEW_SENTINEL_749834"
        workflow.review(private_review)
        serialized = json.dumps(workflow.finalize())
        self.assertNotIn(str(self.directory), serialized)
        self.assertNotIn("56 Plains", serialized)
        self.assertNotIn("4 Shock", serialized)
        self.assertNotIn(private_review, serialized)

    def test_optional_unexecuted_tools_never_appear_completed(self):
        workflow = self.reviewed()
        report = workflow.finalize()
        self.assertEqual(report["optional"], {"forge": "NOT_EXECUTED", "tester": "NOT_EXECUTED"})

    def test_returned_receipt_mutation_cannot_modify_internal_evidence(self):
        workflow = self.validated()
        report = workflow.status()
        report["evidence"]["validate"]["status"] = "FORGED"
        report["stages"]["REVIEW"] = "COMPLETE_WITH_EVIDENCE"
        self.assertEqual(workflow.status()["evidence"]["validate"]["status"],
                         "VALIDATED_WITH_LIMITATIONS")
        self.assert_no_certificate(workflow.finalize())

    def test_fresh_finalize_rejects_gateway_faults_despite_prior_valid_evidence(self):
        for fault in ("source-mismatch", "missing-child", "timeout", "malformed-json",
                      "wrong-child-exit", "wrong-gateway-exit", "not-executed",
                      "wrong-oracle-digest", "oversized-output", "missing-child-status",
                      "missing-checks", "false-positive-ownership"):
            with self.subTest(fault=fault):
                workflow = self.reviewed()
                bounded_process = workflow.support["_bounded_process"]

                def fail_validation(command, **kwargs):
                    if "validate" not in command:
                        return bounded_process(command, **kwargs)
                    if fault == "missing-child":
                        raise workflow.support["GatewayError"]("SUBPROCESS_NOT_STARTED")
                    if fault == "timeout":
                        raise workflow.support["GatewayError"]("SUBPROCESS_TIMEOUT", executed=True)
                    if fault == "malformed-json":
                        return subprocess.CompletedProcess(command, 0, b"{", b"private error")
                    if fault == "oversized-output":
                        return subprocess.CompletedProcess(command, 0,
                                                           b" " * (2 * 1024 * 1024 + 1), b"")
                    completed = bounded_process(command, **kwargs)
                    payload = json.loads(completed.stdout)
                    returncode = completed.returncode
                    if fault == "source-mismatch":
                        payload["sources"]["validator_sha256"] = "0" * 64
                    elif fault == "wrong-child-exit":
                        payload["child_exit_code"] = 3
                    elif fault == "wrong-gateway-exit":
                        returncode = 3
                    elif fault == "not-executed":
                        payload["executed"] = False
                        payload["tool_execution"] = "NOT_EXECUTED"
                    elif fault == "wrong-oracle-digest":
                        payload["sources"]["oracle_sha256"] = "0" * 64
                    elif fault == "missing-child-status":
                        payload["result"].pop("status")
                    elif fault == "missing-checks":
                        payload["result"].pop("checks")
                    elif fault == "false-positive-ownership":
                        payload["result"]["checks"]["ownership"] = "FAIL"
                    return subprocess.CompletedProcess(command, returncode,
                                                       json.dumps(payload).encode(), b"")

                with mock.patch.dict(workflow.support, _bounded_process=fail_validation):
                    report = workflow.finalize()
                self.assert_no_certificate(report)
                self.assertEqual(report["status"], "UNVERIFIED", report)
                self.assertNotIn("validate", report["evidence"],
                                 "Old validation must not survive a failed fresh invocation")
                self.assertNotEqual(report["stages"]["VALIDATION"], "COMPLETE_WITH_EVIDENCE")
                self.assertNotIn(str(self.directory), json.dumps(report))

    def test_repeated_discovery_returns_candidates_and_invalidates_downstream_evidence(self):
        workflow = self.reviewed()
        first = workflow.discover("Shock")
        self.assertEqual(first["status"], "READY", first)
        self.assertEqual([row["name"] for row in first["candidates"]], ["Shock"])
        self.assertEqual(first["candidates"][0]["owned_copies"], 4)
        self.assertNotIn("validate", first["evidence"])
        for stage in ("CANDIDATE", "VALIDATION", "REVIEW", "COMPLETE"):
            self.assertEqual(first["stages"][stage], "NOT_STARTED")
        self.assert_no_certificate(workflow.finalize())
        second = workflow.discover("Shock")
        self.assertEqual(second["status"], "READY", second)
        self.assertEqual([row["name"] for row in second["candidates"]], ["Shock"])
        workflow.submit(self.deck, "Casual 60 after new discovery")
        workflow.validate()
        workflow.review("Agent reassessed the newly discovered evidence")
        report = workflow.finalize()
        self.assertEqual(report["status"], "COMPLETE_WITH_EVIDENCE", report)

    def test_malformed_discovery_candidates_fail_closed_without_crashing(self):
        for malformed in ({"name": "Shock"}, None, [None]):
            with self.subTest(results=malformed):
                workflow = self.workflow()
                bounded_process = workflow.support["_bounded_process"]

                def invalid_candidates(command, **kwargs):
                    completed = bounded_process(command, **kwargs)
                    if "discover" not in command:
                        return completed
                    payload = json.loads(completed.stdout)
                    payload["result"]["results"] = malformed
                    return subprocess.CompletedProcess(command, completed.returncode,
                                                       json.dumps(payload).encode(), b"")

                with mock.patch.dict(workflow.support, _bounded_process=invalid_candidates):
                    report = workflow.prepare("Shock")
                self.assertEqual(report["status"], "UNVERIFIED", report)
                self.assertEqual(report["stages"]["DISCOVERY"], "UNVERIFIED")
                self.assertNotIn("discover", report["evidence"])
                self.assert_no_certificate(workflow.finalize())

    def test_missing_candidate_error_is_sanitized_and_blocks_completion(self):
        workflow = self.prepared()
        private = self.directory / "PRIVATE_OWNER_DECK_749834.txt"
        report = workflow.submit(private, "Casual 60")
        self.assert_no_certificate(report)
        self.assertNotIn(str(self.directory), json.dumps(report))
        self.assertNotIn(private.name, json.dumps(report))

    def test_long_review_is_rejected_without_echo_or_success(self):
        workflow = self.validated()
        private = "PRIVATE_REVIEW_749834" * 100000
        report = workflow.review(private)
        self.assertNotEqual(report["stages"]["REVIEW"], "COMPLETE_WITH_EVIDENCE")
        self.assert_no_certificate(workflow.finalize())
        self.assertNotIn("PRIVATE_REVIEW_749834", json.dumps(report))

    def delver_fixture(self, collection_rows, deck_lines):
        shared = {"name": FULL, "layout": "transform", "supertypes": [],
                  "colorIdentity": ["U"], "manaValue": 1}
        self.cards[FULL] = [
            {**shared, "faceName": FRONT, "side": "a", "types": ["Creature"],
             "manaCost": "{U}", "faceManaValue": 1, "text": "Look at the top card."},
            {**shared, "faceName": "Insectile Aberration", "side": "b", "types": ["Creature"],
             "faceManaValue": 0, "text": "Flying"}]
        self.write_oracle()
        self.collection.write_text("Name,Quantity\nShock,4\n" + collection_rows, encoding="utf-8")
        self.deck.write_text(deck_lines, encoding="utf-8")

    def test_canonical_inventory_resolves_front_face_candidate(self):
        self.delver_fixture(f"{FULL},4\n", f"56 Plains\n4 {FRONT}\n")
        workflow = self.prepared()
        workflow.submit(self.deck, "Casual 60 Delver front alias")
        receipt = workflow.validate()["evidence"]["validate"]
        self.assertEqual((receipt["status"], receipt["gateway_exit_code"], receipt["child_exit_code"]),
                         ("VALIDATED_WITH_LIMITATIONS", 0, 0))
        workflow.review("Agent review of multiface candidate")
        self.assertEqual(workflow.finalize()["status"], "COMPLETE_WITH_EVIDENCE")

    def test_mixed_front_and_canonical_labels_remain_unverified(self):
        self.delver_fixture(f"{FRONT},2\n{FULL},2\n", f"56 Plains\n4 {FRONT}\n")
        workflow = self.prepared()
        workflow.submit(self.deck, "Casual 60 mixed labels")
        receipt = workflow.validate()["evidence"]["validate"]
        self.assertEqual((receipt["status"], receipt["gateway_exit_code"], receipt["child_exit_code"]),
                         ("UNVERIFIED", 3, 3))
        self.assert_no_certificate(workflow.finalize())

    def test_uncertain_labels_do_not_hide_copy_limit_or_short_deck_failure(self):
        for lines in (f"55 Plains\n2 {FRONT}\n3 {FULL}\n", f"55 Plains\n4 {FRONT}\n"):
            with self.subTest(deck=lines):
                self.delver_fixture(f"{FRONT},2\n{FULL},2\n", lines)
                workflow = self.prepared()
                workflow.submit(self.deck, "Casual 60 invalid multiface candidate")
                receipt = workflow.validate()["evidence"]["validate"]
                self.assertEqual((receipt["status"], receipt["gateway_exit_code"], receipt["child_exit_code"]),
                                 ("BLOCKED_INVALID_DECK", 2, 1))
                self.assert_no_certificate(workflow.finalize())


if __name__ == "__main__":
    unittest.main()
