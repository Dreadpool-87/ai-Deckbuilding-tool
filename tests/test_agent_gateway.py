"""Synthetic gateway integration tests; never use a real user's collection."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
GATEWAY = ROOT / "tools" / "agent_gateway.py"


class GatewayTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.dir = Path(self.temp.name)
        cards = {
            "Plains": [{"name": "Plains", "types": ["Land"], "supertypes": ["Basic"],
                        "colorIdentity": [], "manaValue": 0, "text": "{T}: Add {W}."}],
            "Shock": [{"name": "Shock", "types": ["Instant"], "supertypes": [],
                       "colorIdentity": ["R"], "manaValue": 1, "manaCost": "{R}",
                       "text": "Shock deals 1 damage to target attacking creature."}],
        }
        self.oracle = self.dir / "synthetic-oracle.json"
        self.oracle.write_text(json.dumps({"meta": {"version": "synthetic"}, "data": cards}))
        self.pin = hashlib.sha256(self.oracle.read_bytes()).hexdigest()
        self.collection = self.dir / "synthetic-collection.csv"
        self.collection.write_text("Name,Quantity\nShock,4\n", encoding="utf-8")
        self.deck = self.dir / "synthetic-deck.txt"
        self.deck.write_text("56 Plains\n4 Shock\n", encoding="utf-8")

    def invoke(self, *args):
        proc = subprocess.run([sys.executable, str(GATEWAY), *map(str, args)],
                              capture_output=True, text=True, cwd=str(ROOT), timeout=120)
        self.assertTrue(proc.stdout.strip(), proc.stderr)
        data = json.loads(proc.stdout)
        self.assert_envelope(data)
        return proc.returncode, data

    def mock_process(self, gateway, **kwargs):
        namespace = gateway["_dispatch"].__globals__
        return mock.patch.dict(namespace, _bounded_process=mock.Mock(**kwargs))

    def assert_envelope(self, data):
        self.assertEqual(data["schema_version"], 1)
        self.assertEqual(data["gateway_version"], "0.3.0-experimental")
        self.assertIn(data["action"], ("doctor", "discover", "validate", "UNKNOWN"))
        self.assertIn(data["status"], (
            "RUNTIME_COMPONENTS_PRESENT", "CANDIDATES_NOT_VALIDATED",
            "VALIDATED_WITH_LIMITATIONS", "BLOCKED_INVALID_DECK",
            "UNVERIFIED", "INPUT_ERROR"))
        self.assertIs(type(data["executed"]), bool)
        self.assertFalse(data["automatic_swap_authorized"])
        self.assertFalse(data["strategic_improvement_verified"])
        for key in ("sources", "evidence", "reason_codes", "uncertainties", "limitations"):
            self.assertIn(key, data)
        for key in ("oracle_sha256", "validator_sha256", "validator_profile", "collection_sha256",
                    "deck_sha256", "collection_scope", "ownership_authentication"):
            self.assertIn(key, data["sources"])
        for key in ("facts", "derivations", "hypotheses"):
            self.assertIsInstance(data["evidence"][key], list)
            for row in data["evidence"][key]:
                self.assertEqual(set(row), {"code", "basis", "scope"})
                self.assertTrue(all(row.values()))
        self.assertIsInstance(data["reason_codes"], list)
        self.assertIsInstance(data["uncertainties"], list)
        self.assertIsInstance(data["limitations"], list)
        self.assertEqual(data["executed"],
                         data["tool_execution"] in ("EXECUTED", "FAILED_AFTER_START"))
        if data["action"] == "doctor":
            self.assertFalse(data["executed"])
        if data["status"] == "INPUT_ERROR":
            self.assertFalse(data["executed"])
        if data["status"] in ("CANDIDATES_NOT_VALIDATED", "VALIDATED_WITH_LIMITATIONS",
                              "BLOCKED_INVALID_DECK"):
            self.assertTrue(data["executed"])

    def common(self):
        return ("--oracle", self.oracle, "--oracle-sha256", self.pin,
                "--collection", self.collection, "--collection-scope", "synthetic")

    def test_selected_default_profile_is_explicit_in_doctor_and_validate(self):
        code, doctor = self.invoke("doctor")
        self.assertEqual(code, 0, doctor)
        self.assertEqual(doctor["sources"]["validator_profile"], "github-main-v0.2")
        self.assertTrue(doctor["checks"]["validator"]["pin_matches"])
        code, data = self.invoke("validate", *self.common(), "--deck", self.deck)
        self.assertEqual(code, 0, data)
        self.assertEqual(data["sources"]["validator_profile"], "github-main-v0.2")
        self.assertEqual(data["sources"]["validator_sha256"],
                         doctor["checks"]["validator"]["sha256"])

    def test_doctor_explicit_oracle_mismatch_blocks_ready_status(self):
        code, data = self.invoke("doctor", "--oracle", self.oracle)
        self.assertEqual(code, 3)
        self.assertEqual(data["status"], "UNVERIFIED")
        self.assertFalse(data["checks"]["oracle"]["matches_slim_pin"])
        self.assertFalse(data["executed"])

    def test_nondefault_profile_requires_explicit_file(self):
        for action in ("doctor", "validate"):
            with self.subTest(action=action):
                args = ("doctor", "--validator-profile", "frozen-beta-20261022") if action == "doctor" else (
                    "validate", *self.common(), "--deck", self.deck,
                    "--validator-profile", "frozen-beta-20261022")
                code, data = self.invoke(*args)
                self.assertEqual(code, 2)
                self.assertEqual(data["status"], "INPUT_ERROR")
                self.assertEqual(data["reason_codes"], ["EXPLICIT_VALIDATOR_FILE_REQUIRED"])

    def test_wrong_profile_never_uses_default_validator_implicitly(self):
        main_validator = ROOT / "validator" / "MTG_Deck_Validator_v1.1.1.py"
        code, doctor = self.invoke("doctor", "--validator-file", main_validator,
                                   "--validator-profile", "project-prepare-candidate")
        self.assertEqual(code, 3)
        self.assertEqual(doctor["status"], "UNVERIFIED")
        self.assertFalse(doctor["checks"]["validator"]["pin_matches"])
        code, report = self.invoke(
            "validate", *self.common(), "--deck", self.deck,
            "--validator-file", main_validator,
            "--validator-profile", "project-prepare-candidate")
        self.assertEqual(code, 2)
        self.assertEqual(report["reason_codes"], ["VALIDATOR_SHA256_MISMATCH"])
        self.assertFalse(report["executed"])

    def test_external_copy_of_expected_validator_is_accepted_for_default_profile(self):
        original = ROOT / "validator" / "MTG_Deck_Validator_v1.1.1.py"
        external = self.dir / "verified-validator.py"
        external.write_bytes(original.read_bytes())
        code, data = self.invoke("validate", *self.common(), "--deck", self.deck,
                                 "--validator-profile", "github-main-v0.2",
                                 "--validator-file", external)
        self.assertEqual(code, 0, data)
        self.assertEqual(data["status"], "VALIDATED_WITH_LIMITATIONS")
        self.assertEqual(data["sources"]["validator_profile"], "github-main-v0.2")

    def test_validator_replacement_at_launch_cannot_change_executed_bytes(self):
        import runpy

        gateway = runpy.run_path(str(GATEWAY), run_name="test_gateway_import")
        original = (ROOT / "validator" / "MTG_Deck_Validator_v1.1.1.py").read_bytes()
        selected = self.dir / "selected-validator.py"
        selected.write_bytes(original)
        marker = self.dir / "replacement-executed"
        real_run = gateway["_bounded_process"]

        def replace_at_launch(command, **kwargs):
            selected.write_text(
                "from pathlib import Path\n"
                f"Path({str(marker)!r}).touch()\n"
                "print('{\"status\":\"PASS_WITH_LIMITATIONS\"}')\n",
                encoding="utf-8",
            )
            try:
                return real_run(command, **kwargs)
            finally:
                selected.write_bytes(original)

        args = gateway["_parser"]().parse_args(
            ["validate", *map(str, self.common()), "--deck", str(self.deck),
             "--validator-file", str(selected)])
        with self.mock_process(gateway, side_effect=replace_at_launch):
            status, result = gateway["_dispatch"](args)

        self.assertFalse(marker.exists(), "Unverified Validator bytes ran")
        self.assertEqual(status, "VALIDATED_WITH_LIMITATIONS")
        self.assertEqual(result["validator_sha256"], hashlib.sha256(original).hexdigest())
        self.assertEqual(result["result"]["checks"]["deck_size"], "PASS")


    def test_mutated_collection_during_child_execution_rejects_result(self):
        import contextlib
        import io
        import runpy
        import types
        gateway = runpy.run_path(str(GATEWAY), run_name="test_gateway_import")
        child = types.SimpleNamespace(returncode=0, stdout=b'{"results":[],"coverage":{}}',
                                      stderr=b"")
        def mutate(*args, **kwargs):
            self.collection.write_text("Name,Quantity\\nShock,1\\n", encoding="utf-8")
            return child
        output = io.StringIO()
        with self.mock_process(gateway, side_effect=mutate):
            with contextlib.redirect_stdout(output):
                code = gateway["main"](["discover", *map(str, self.common()),
                                        "--theme", "Shock"])
        result = json.loads(output.getvalue())
        self.assert_envelope(result)
        self.assertEqual(code, 3)
        self.assertEqual(result["status"], "UNVERIFIED")
        self.assertEqual(result["reason_codes"], ["SOURCE_CHANGED_DURING_EXECUTION"])
        self.assertEqual(result["tool_execution"], "FAILED_AFTER_START")
        self.assertEqual(result["evidence"]["facts"], [])

    def test_validator_path_symlink_is_rejected(self):
        link = self.dir / "validator-link.py"
        try:
            link.symlink_to(ROOT / "validator" / "MTG_Deck_Validator_v1.1.1.py")
        except (OSError, NotImplementedError):
            self.skipTest("Symlinks not available")
        code, report = self.invoke("validate", *self.common(), "--deck", self.deck,
                                   "--validator-file", link)
        self.assertEqual(code, 2)
        self.assertEqual(report["reason_codes"], ["UNSAFE_SYMLINK_PATH"])
        self.assertFalse(report["executed"])

    def test_profile_manifest_is_pinned_and_schema_records_selection(self):
        import runpy
        g = runpy.run_path(str(GATEWAY), run_name="test_gateway_import")
        self.assertEqual(set(g["VALIDATOR_PROFILES"]), {
            "github-main-v0.2", "project-prepare-candidate", "frozen-beta-20261022"})
        self.assertEqual(g["VALIDATOR_PROFILES"]["github-main-v0.2"], g["VALIDATOR_PIN"])
        schema = json.loads((ROOT / "schemas" / "agent_gateway_result_v1.schema.json").read_text())
        source = schema["properties"]["sources"]
        self.assertIn("validator_profile", source["required"])
        self.assertIn("frozen-beta-20261022",
                      source["properties"]["validator_profile"]["enum"])

    def test_doctor_never_claims_swap_readiness(self):
        code, data = self.invoke("doctor")
        self.assertEqual(code, 0)
        self.assertEqual(data["status"], "RUNTIME_COMPONENTS_PRESENT")
        self.assertFalse(data["executed"])
        self.assertTrue(data["checks"]["validator"]["pin_matches"])
        self.assertIsNone(data["child_exit_code"])

    def test_real_card_search_script_with_synthetic_fixture(self):
        code, data = self.invoke("discover", *self.common(), "--theme", "Shock", "--limit", 5)
        self.assertEqual(code, 0, data)
        self.assertEqual(data["status"], "CANDIDATES_NOT_VALIDATED")
        self.assertTrue(data["executed"])
        self.assertIsInstance(data["result"]["results"], list)
        self.assertNotIn("oracle_file", data["result"])
        self.assertEqual(data["oracle_pin_basis"], "CALLER_SPECIFIED_SYNTHETIC_TEST_PIN")

    def test_discovery_reports_unverified_collection_identity(self):
        oracle = json.loads(self.oracle.read_text(encoding="utf-8"))
        for canonical in ("First // Shared", "Second // Shared"):
            oracle["data"][canonical] = [{
                **oracle["data"]["Shock"][0], "name": canonical,
                "faceName": "Shared", "layout": "split",
            }]
        self.oracle.write_text(json.dumps(oracle), encoding="utf-8")
        self.pin = hashlib.sha256(self.oracle.read_bytes()).hexdigest()
        self.collection.write_text("Name,Quantity\nShared,4\n", encoding="utf-8")
        code, data = self.invoke("discover", *self.common(), "--theme", "Shock")
        self.assertEqual(code, 0, data)
        self.assertEqual(data["result"]["collection_coverage"]["identity_status"], "UNVERIFIED")
        self.assertEqual(data["result"]["results"], [])
        self.assertIn("COLLECTION_CARD_IDENTITY_UNVERIFIED", data["uncertainties"])

    def test_validator_with_complete_synthetic_60_card_deck(self):
        code, data = self.invoke("validate", *self.common(), "--deck", self.deck, "--exact-60")
        self.assertEqual(code, 0, data)
        self.assertEqual(data["status"], "VALIDATED_WITH_LIMITATIONS")
        self.assertEqual(data["result"]["status"], "PASS_WITH_LIMITATIONS")
        self.assertNotIn("source_collection", data["result"])
        self.assertEqual(data["result"]["deck_cards"], 60)

    def test_report_records_verified_source_and_actual_child_exit(self):
        for action, arguments, expected in (
                ("doctor", (), None),
                ("discover", (*self.common(), "--theme", "Shock"), 0),
                ("validate", (*self.common(), "--deck", self.deck), 0)):
            with self.subTest(action=action):
                code, report = self.invoke(action, *arguments)
                self.assertEqual(code, 0)
                self.assertEqual(report["child_exit_code"], expected)
                if action == "discover":
                    self.assertEqual(report["card_search_sha256"], hashlib.sha256(
                        (ROOT / "tools" / "card_search.py").read_bytes()).hexdigest())
                else:
                    self.assertEqual(report["validator_version"], "1.1.1")
        self.deck.write_text("55 Plains\n4 Shock\n", encoding="utf-8")
        code, report = self.invoke("validate", *self.common(), "--deck", self.deck)
        self.assertEqual(code, 2)
        self.assertEqual(report["child_exit_code"], 1)

    def test_malformed_collection_is_rejected_by_the_actual_validator(self):
        for row in ("Shock,NaN", "Shock,4,unexpected", ","):
            with self.subTest(row=row):
                self.collection.write_text(f"Name,Quantity\n{row}\n", encoding="utf-8")
                code, report = self.invoke("validate", *self.common(), "--deck", self.deck)
                self.assertEqual(code, 3, report)
                self.assertEqual(report["status"], "UNVERIFIED")
                self.assertEqual(report["tool_execution"], "FAILED_AFTER_START")
                self.assertEqual(report["child_exit_code"], 2)
                self.assertEqual(report["reason_codes"], ["SUBPROCESS_REPORTED_INPUT_ERROR"])
                self.assertEqual(report["sources"]["validator_profile"], "github-main-v0.2")
                self.assertTrue(report["sources"]["validator_sha256"])
                self.assertNotIn("result", report)

    def test_validator_reports_physical_collection_line_and_reason(self):
        validator = ROOT / "validator" / "MTG_Deck_Validator_v1.1.1.py"
        header = 'Name,Quantity,Note\nShock,4,"first\nsecond"\n'
        for suffix, expected in (
                ("Shock,invalid,note\n", "line 4: invalid Quantity"),
                ("Shock,1\n", "line 4: wrong number of fields"),
                ('"unterminated,4,note\n', "line 4: unexpected end of data")):
            with self.subTest(suffix=suffix):
                self.collection.write_text(header + suffix, encoding="utf-8")
                result = subprocess.run(
                    [sys.executable, str(validator), "--oracle", str(self.oracle),
                     "--collection", str(self.collection), "--deck", str(self.deck)],
                    capture_output=True, text=True, cwd=ROOT, timeout=120)
                self.assertEqual(result.returncode, 2)
                self.assertFalse(result.stdout)
                self.assertIn(expected, result.stderr)

    def test_missing_runtime_is_distinct_from_a_child_failure(self):
        import contextlib
        import io
        import runpy

        gateway = runpy.run_path(str(GATEWAY), run_name="test_gateway_import")
        stream = io.StringIO()
        with mock.patch.object(sys, "executable", str(self.dir / "unavailable-python")):
            with contextlib.redirect_stdout(stream):
                doctor_code = gateway["main"](["doctor"])
                validate_code = gateway["main"](
                    ["validate", *map(str, self.common()), "--deck", str(self.deck)])
        doctor, report = map(json.loads, stream.getvalue().splitlines())
        self.assertEqual(doctor_code, 3)
        self.assertEqual(doctor["checks"]["python_runtime"]["status"], "UNAVAILABLE")
        self.assertEqual(validate_code, 3)
        self.assertEqual(report["status"], "UNVERIFIED")
        self.assertEqual(report["tool_execution"], "NOT_EXECUTED")
        self.assertIsNone(report["child_exit_code"])
        self.assertEqual(report["reason_codes"], ["SUBPROCESS_NOT_STARTED"])
        self.assertTrue(report["sources"]["validator_sha256"])

    def test_child_ignores_python_startup_hooks(self):
        import os

        marker = self.dir / "sitecustomize-loaded"
        (self.dir / "sitecustomize.py").write_text(
            f"from pathlib import Path\nPath({str(marker)!r}).touch()\n", encoding="utf-8")
        with mock.patch.dict(os.environ, {"PYTHONPATH": str(self.dir)}):
            proc = subprocess.run(
                [sys.executable, "-I", str(GATEWAY), "discover", *map(str, self.common()),
                 "--theme", "Shock"], capture_output=True, text=True, cwd=ROOT, timeout=120)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertFalse(marker.exists())

    def test_invalid_deck_is_not_a_positive(self):
        self.deck.write_text("55 Plains\n4 Shock\n", encoding="utf-8")
        code, data = self.invoke("validate", *self.common(), "--deck", self.deck, "--exact-60")
        self.assertEqual(code, 2)
        self.assertEqual(data["status"], "BLOCKED_INVALID_DECK")
        self.assertEqual(data["result"]["checks"]["deck_size"], "FAIL")

    def test_tampered_oracle_is_rejected_before_subprocess(self):
        self.oracle.write_text(self.oracle.read_text() + " ", encoding="utf-8")
        code, data = self.invoke("discover", *self.common(), "--theme", "Shock")
        self.assertEqual(code, 2)
        self.assertEqual(data["reason"], "ORACLE_SHA256_MISMATCH")
        self.assertFalse(data["executed"])

    def test_unconfirmed_real_collection_is_rejected(self):
        code, data = self.invoke(
            "discover", "--oracle", self.oracle, "--oracle-sha256", self.pin,
            "--collection", self.collection, "--collection-scope", "current-run-confirmed",
            "--theme", "Shock")
        self.assertEqual(code, 2)
        self.assertEqual(data["reason"], "COLLECTION_CONFIRMATION_REQUIRED")

    def test_caller_pin_does_not_authorize_real_oracle(self):
        code, data = self.invoke(
            "discover", "--oracle", self.oracle, "--oracle-sha256", self.pin,
            "--collection", self.collection, "--collection-scope", "current-run-confirmed",
            "--collection-confirmed", "--theme", "Shock")
        self.assertEqual(code, 2)
        self.assertEqual(data["reason"], "ACTIVE_ORACLE_PIN_UNSUPPORTED")

    def test_reject_symlinked_input_without_processing(self):
        link = self.dir / "linked.csv"
        try:
            link.symlink_to(self.collection)
        except (OSError, NotImplementedError):
            self.skipTest("Symlinks unavailable")
        code, data = self.invoke(
            "discover", "--oracle", self.oracle, "--oracle-sha256", self.pin,
            "--collection", link, "--collection-scope", "synthetic", "--theme", "Shock")
        self.assertEqual(code, 2)
        self.assertEqual(data["reason"], "UNSAFE_SYMLINK_PATH")

    def test_missing_file_does_not_become_empty_inventory(self):
        code, data = self.invoke("discover", "--oracle", self.oracle, "--oracle-sha256", self.pin,
                                 "--collection", self.dir / "missing.csv",
                                 "--collection-scope", "synthetic", "--theme", "Shock")
        self.assertEqual(code, 2)
        self.assertEqual(data["reason"], "REQUIRED_INPUT_UNAVAILABLE")

    def test_invalid_cli_arguments_are_json_not_silent_stderr_only(self):
        code, data = self.invoke("discover", "--theme", "lifegain")
        self.assertEqual(code, 2)
        self.assertEqual(data["status"], "INPUT_ERROR")
        self.assertEqual(data["action"], "discover")
        self.assertEqual(data["tool_execution"], "NOT_EXECUTED")
        self.assertEqual(data["reason_codes"], ["INVALID_ARGUMENTS"])
        self.assertEqual(data["uncertainties"], ["NO_TRUSTED_RESULT", "SWAP_NOT_ASSESSED"])

    def test_synthetic_provenance_is_not_real_ownership_attestation(self):
        code, data = self.invoke("discover", *self.common(), "--theme", "Shock")
        self.assertEqual(code, 0, data)
        self.assertEqual(data["sources"]["collection_scope"], "synthetic")
        self.assertEqual(data["sources"]["oracle_sha256"], self.pin)
        self.assertEqual(data["sources"]["ownership_authentication"], "NOT_IMPLEMENTED")
        self.assertEqual(len(data["sources"]["collection_sha256"]), 64)
        self.assertIsNone(data["sources"]["deck_sha256"])
        self.assertEqual(data["evidence"]["derivations"], [])
        self.assertEqual(data["evidence"]["hypotheses"][0]["basis"], "CARD_SEARCH_V0_3")
        self.assertIn("CANDIDATES_NOT_DECK_VALIDATED", data["uncertainties"])

    def test_validated_has_deck_fingerprint_and_no_strategic_claim(self):
        code, data = self.invoke("validate", *self.common(), "--deck", self.deck)
        self.assertEqual(code, 0, data)
        self.assertEqual(data["sources"]["deck_sha256"],
                         hashlib.sha256(self.deck.read_bytes()).hexdigest())
        self.assertEqual(data["sources"]["validator_sha256"], data["validator_sha256"])
        self.assertEqual(data["evidence"]["facts"][0]["basis"], "LOCAL_SHA256")
        self.assertEqual(data["evidence"]["derivations"][0]["scope"],
                         "STRUCTURAL_VALIDATION_ONLY")
        self.assertEqual(data["evidence"]["hypotheses"], [])
        self.assertIn("STRATEGIC_IMPROVEMENT_UNVERIFIED", data["uncertainties"])

    def test_unverified_validator_is_not_turned_into_keep_or_pass(self):
        cards = json.loads(self.oracle.read_text(encoding="utf-8"))
        variant = dict(cards["data"]["Shock"][0])
        variant["manaValue"] = 2
        cards["data"]["Shock"].append(variant)
        self.oracle.write_text(json.dumps(cards), encoding="utf-8")
        self.pin = hashlib.sha256(self.oracle.read_bytes()).hexdigest()
        code, data = self.invoke("validate", *self.common(), "--deck", self.deck)
        self.assertEqual(code, 3, data)
        self.assertEqual(data["status"], "UNVERIFIED")
        self.assertEqual(data["result"]["status"], "UNVERIFIED")
        self.assertEqual(data["tool_execution"], "EXECUTED")
        self.assertIn("VALIDATOR_REPORTED_UNVERIFIED", data["reason_codes"])

    def test_contract_schema_is_parseable_and_restricts_positive_claims(self):
        schema = json.loads((ROOT / "schemas" / "agent_gateway_result_v1.schema.json").read_text())
        self.assertEqual(schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
        for key in ("schema_version", "status", "executed", "sources",
                    "evidence", "automatic_swap_authorized",
                    "strategic_improvement_verified"):
            self.assertIn(key, schema["required"])
        self.assertIs(schema["properties"]["automatic_swap_authorized"]["const"], False)
        self.assertIs(schema["properties"]["strategic_improvement_verified"]["const"], False)

    def test_duplicate_child_json_keys_and_nan_are_rejected(self):
        import contextlib
        import io
        import runpy
        import types
        gateway = runpy.run_path(str(GATEWAY), run_name="test_gateway_import")
        for bad, expected in (
                (b'{"status":"PASS","status":"FAIL"}', "SUBPROCESS_DUPLICATE_JSON_KEY"),
                (b'{"results":[],"coverage":{},"score":NaN}',
                 "SUBPROCESS_NONFINITE_JSON_NUMBER"),
                (b'{"results":[],"coverage":{},"score":1e400}',
                 "SUBPROCESS_NONFINITE_JSON_NUMBER")):
            with self.subTest(expected=expected):
                child = types.SimpleNamespace(returncode=0, stdout=bad, stderr=b"")
                stream = io.StringIO()
                with self.mock_process(gateway, return_value=child):
                    with contextlib.redirect_stdout(stream):
                        code = gateway["main"](["discover", *map(str, self.common()),
                                               "--theme", "Shock"])
                data = json.loads(stream.getvalue())
                self.assert_envelope(data)
                self.assertEqual(code, 3)
                self.assertEqual(data["status"], "UNVERIFIED")
                self.assertEqual(data["reason_codes"], [expected])
                self.assertEqual(data["tool_execution"], "FAILED_AFTER_START")

    def test_child_process_never_started_reports_unverified_not_input_error(self):
        import contextlib
        import io
        import runpy
        gateway = runpy.run_path(str(GATEWAY), run_name="test_gateway_import")
        stream = io.StringIO()
        with mock.patch("subprocess.Popen", side_effect=OSError("private detail")):
            with contextlib.redirect_stdout(stream):
                code = gateway["main"](["discover", *map(str, self.common()),
                                       "--theme", "Shock"])
        data = json.loads(stream.getvalue())
        self.assert_envelope(data)
        self.assertEqual(code, 3)
        self.assertEqual(data["status"], "UNVERIFIED")
        self.assertEqual(data["tool_execution"], "NOT_EXECUTED")
        self.assertEqual(data["reason_codes"], ["SUBPROCESS_NOT_STARTED"])
        self.assertNotIn("private detail", stream.getvalue())
        self.assertEqual(data["evidence"]["hypotheses"], [])

    def test_malformed_child_json_is_reported_as_execution_failure(self):
        import contextlib
        import io
        import runpy
        import types
        gateway = runpy.run_path(str(GATEWAY), run_name="test_gateway_import")
        child = types.SimpleNamespace(returncode=0, stdout=b"not-json", stderr=b"")
        stream = io.StringIO()
        with self.mock_process(gateway, return_value=child):
            with contextlib.redirect_stdout(stream):
                code = gateway["main"](["discover", *map(str, self.common()),
                                       "--theme", "Shock"])
        data = json.loads(stream.getvalue())
        self.assert_envelope(data)
        self.assertEqual(code, 3)
        self.assertEqual(data["status"], "UNVERIFIED")
        self.assertEqual(data["reason_codes"], ["SUBPROCESS_JSON_INVALID"])
        self.assertEqual(data["tool_execution"], "FAILED_AFTER_START")
        self.assertEqual(data["action"], "discover")



    def test_real_child_crash_timeout_and_output_cap(self):
        import runpy

        gateway = runpy.run_path(str(GATEWAY), run_name="test_gateway_import")
        namespace = gateway["_run"].__globals__
        fixture = self.dir / "synthetic-child.py"
        for script, expected, settings in (
                ("raise SystemExit(7)", "SUBPROCESS_JSON_INVALID", {}),
                ("import time; time.sleep(10)", "SUBPROCESS_TIMED_OUT", {"CHILD_TIMEOUT": 0.2}),
                ("print('X' * 100000)", "SUBPROCESS_OUTPUT_TOO_LARGE", {"MAX_STDOUT": 256}),
                ("import sys; print('X' * 100000, file=sys.stderr)",
                 "SUBPROCESS_OUTPUT_TOO_LARGE", {"MAX_STDERR": 256})):
            with self.subTest(reason=expected, script=script):
                fixture.write_text(script, encoding="utf-8")
                with mock.patch.dict(namespace, settings):
                    with self.assertRaises(gateway["GatewayError"]) as raised:
                        gateway["_run"](fixture, [], input_error_prefix=b"INPUT ERROR: ")
                self.assertEqual(raised.exception.reason, expected)
                self.assertTrue(raised.exception.executed)
                self.assertIsInstance(raised.exception.child_exit_code, int)
                if script == "raise SystemExit(7)":
                    self.assertEqual(raised.exception.child_exit_code, 7)

    def test_unhashable_validator_status_fails_closed(self):
        import contextlib
        import io
        import runpy

        gateway = runpy.run_path(str(GATEWAY), run_name="test_gateway_import")
        stream = io.StringIO()
        child = subprocess.CompletedProcess([], 0, stdout=b'{"status":[]}', stderr=b"")
        with self.mock_process(gateway, return_value=child), contextlib.redirect_stdout(stream):
            code = gateway["main"](
                ["validate", *map(str, self.common()), "--deck", str(self.deck)])
        data = json.loads(stream.getvalue())
        self.assertEqual(code, 3)
        self.assertEqual(data["tool_execution"], "FAILED_AFTER_START")
        self.assertEqual(data["child_exit_code"], 0)
        self.assertEqual(data["reason_codes"], ["VALIDATOR_STATUS_EXIT_CONTRADICTION"])

    def test_doctor_checks_pinned_card_search_and_rejects_mutated_code(self):
        import runpy
        gateway = runpy.run_path(str(GATEWAY), run_name="test_gateway_import")
        root_globals = gateway["_dispatch"].__globals__
        original = (ROOT / "tools" / "card_search.py").read_bytes()
        replacement = self.dir / "modified-card-search.py"
        replacement.write_bytes(original + b"\n# not the pinned Card Search bytes\n")
        root_globals["CARD_SEARCH"] = replacement
        # Exercise doctor without modifying production tool files.
        args = gateway["_parser"]().parse_args(["doctor"])
        status, info = gateway["_dispatch"](args)
        self.assertEqual(status, "UNVERIFIED")
        self.assertFalse(info["checks"]["card_search"]["pin_matches"])
        self.assertTrue(info["checks"]["validator"]["pin_matches"])
        self.assertEqual(gateway["CARD_SEARCH_PIN"], hashlib.sha256(original).hexdigest())

    def test_modified_card_search_is_blocked_before_subprocess(self):
        import contextlib
        import io
        import runpy
        gateway = runpy.run_path(str(GATEWAY), run_name="test_gateway_import")
        root_globals = gateway["_dispatch"].__globals__
        candidate = self.dir / "unapproved-card-search.py"
        candidate.write_bytes((ROOT / "tools" / "card_search.py").read_bytes() +
                              b"\n# this must not run\n")
        root_globals["CARD_SEARCH"] = candidate
        output = io.StringIO()
        with self.mock_process(gateway, side_effect=AssertionError("spawned unapproved code")):
            with contextlib.redirect_stdout(output):
                code = gateway["main"](["discover", *map(str, self.common()),
                                         "--theme", "Shock"])
        report = json.loads(output.getvalue())
        self.assertEqual(code, 2)
        self.assertEqual(report["status"], "INPUT_ERROR")
        self.assertFalse(report["executed"])
        self.assertEqual(report["reason_codes"], ["CARD_SEARCH_SHA256_MISMATCH"])

    def test_discover_executes_captured_code_even_when_original_is_swapped_at_launch(self):
        import runpy
        gateway = runpy.run_path(str(GATEWAY), run_name="test_gateway_import")
        root_globals = gateway["_dispatch"].__globals__
        original = (ROOT / "tools" / "card_search.py").read_bytes()
        candidate = self.dir / "selected-card-search.py"
        candidate.write_bytes(original)
        root_globals["CARD_SEARCH"] = candidate
        marker = self.dir / "unapproved-code-executed"
        real_run = gateway["_bounded_process"]
        executed_script = []

        def swap_at_launch(command, **kwargs):
            script = Path(command[5])
            executed_script.append(script)
            self.assertNotEqual(script, candidate)
            self.assertEqual(script.read_bytes(), original)
            candidate.write_text(
                "from pathlib import Path\n" + f"Path({str(marker)!r}).touch()\n",
                encoding="utf-8")
            try:
                return real_run(command, **kwargs)
            finally:
                candidate.write_bytes(original)

        args = gateway["_parser"]().parse_args(
            ["discover", *map(str, self.common()), "--theme", "Shock"])
        with self.mock_process(gateway, side_effect=swap_at_launch):
            status, result = gateway["_dispatch"](args)
        self.assertEqual(status, "CANDIDATES_NOT_VALIDATED")
        self.assertTrue(result["result"]["results"])
        self.assertFalse(marker.exists())
        self.assertEqual(len(executed_script), 1)
        self.assertFalse(executed_script[0].exists(), "Private code stage not cleaned")

    def test_inputs_are_snapshots_even_if_originals_are_replaced_at_launch(self):
        import runpy
        gateway = runpy.run_path(str(GATEWAY), run_name="test_gateway_import")
        real_run = gateway["_bounded_process"]
        originals = {p: p.read_bytes() for p in (self.oracle, self.collection, self.deck)}
        cases = (("discover", ["--theme", "Shock"], "CANDIDATES_NOT_VALIDATED"),
                 ("validate", ["--deck", str(self.deck), "--exact-60"],
                  "VALIDATED_WITH_LIMITATIONS"))
        for action, extra, expected in cases:
            observed = []

            def swap_inputs_at_launch(command, **kwargs):
                arg = list(map(str, command))
                indexes = (("--oracle", self.oracle), ("--collection", self.collection))
                if action == "validate":
                    indexes += (("--deck", self.deck),)
                for flag, original in indexes:
                    staged = Path(arg[arg.index(flag) + 1])
                    self.assertNotEqual(staged, original)
                    self.assertEqual(staged.read_bytes(), originals[original])
                    observed.append(staged)
                    original.write_bytes(b"untrusted replacement after snapshot\n")
                try:
                    reply = real_run(command, **kwargs)
                    self.assertEqual(reply.returncode, 0, reply.stderr)
                    return reply
                finally:
                    for path, saved in originals.items():
                        path.write_bytes(saved)

            args = gateway["_parser"]().parse_args(
                [action, *map(str, self.common()), *extra])
            with self.mock_process(gateway, side_effect=swap_inputs_at_launch):
                status, result = gateway["_dispatch"](args)
            self.assertEqual(status, expected)
            self.assertEqual(len(observed), 3 if action == "validate" else 2)
            for path in observed:
                self.assertFalse(path.exists(), "Private input snapshot leaked")
            self.assertEqual(result["oracle_sha256"], hashlib.sha256(originals[self.oracle]).hexdigest())
            self.assertEqual(result["collection_sha256"], hashlib.sha256(originals[self.collection]).hexdigest())

    def test_changed_original_after_snapshot_fails_closed_and_cleans_up(self):
        import contextlib
        import io
        import runpy
        gateway = runpy.run_path(str(GATEWAY), run_name="test_gateway_import")
        real_run = gateway["_bounded_process"]
        original = self.collection.read_bytes()
        staged_paths = []

        def permanently_change_original(command, **kwargs):
            args = list(map(str, command))
            snapshot = Path(args[args.index("--collection") + 1])
            staged_paths.append(snapshot)
            self.assertEqual(snapshot.read_bytes(), original)
            self.collection.write_bytes(b"Name,Quantity\nShock,0\n")
            reply = real_run(command, **kwargs)
            self.assertEqual(reply.returncode, 0, reply.stderr)
            return reply

        output = io.StringIO()
        try:
            with self.mock_process(gateway, side_effect=permanently_change_original):
                with contextlib.redirect_stdout(output):
                    code = gateway["main"](["discover", *map(str, self.common()),
                                             "--theme", "Shock"])
        finally:
            self.collection.write_bytes(original)
        report = json.loads(output.getvalue())
        self.assertEqual(code, 3)
        self.assertEqual(report["status"], "UNVERIFIED")
        self.assertEqual(report["reason_codes"], ["SOURCE_CHANGED_DURING_EXECUTION"])
        self.assertEqual(report["tool_execution"], "FAILED_AFTER_START")
        for p in staged_paths:
            self.assertFalse(p.exists(), "Private snapshot leaked after failure")

    def test_failed_child_output_cleans_code_and_input_snapshots(self):
        import contextlib
        import io
        import runpy
        import types
        gateway = runpy.run_path(str(GATEWAY), run_name="test_gateway_import")
        saved_paths = []

        def failed_child(command, **kwargs):
            args = list(map(str, command))
            saved_paths.extend([Path(args[5]), Path(args[args.index("--oracle") + 1]),
                                Path(args[args.index("--collection") + 1])])
            self.assertTrue(all(path.is_file() for path in saved_paths))
            return types.SimpleNamespace(returncode=0, stdout=b"not json", stderr=b"")

        output = io.StringIO()
        with self.mock_process(gateway, side_effect=failed_child):
            with contextlib.redirect_stdout(output):
                code = gateway["main"](["discover", *map(str, self.common()),
                                         "--theme", "Shock"])
        report = json.loads(output.getvalue())
        self.assertEqual(code, 3)
        self.assertEqual(report["reason_codes"], ["SUBPROCESS_JSON_INVALID"])
        self.assertEqual(report["tool_execution"], "FAILED_AFTER_START")
        self.assertTrue(saved_paths)
        self.assertTrue(all(not path.exists() for path in saved_paths))
        self.assertNotIn(str(saved_paths[0].parent), output.getvalue())


    def test_gzip_oracle_snapshots_keep_the_loader_format(self):
        import gzip
        compressed = self.dir / "synthetic-oracle.json.gz"
        with gzip.open(compressed, "wb") as handle:
            handle.write(self.oracle.read_bytes())
        digest = hashlib.sha256(compressed.read_bytes()).hexdigest()
        args = ("--oracle", compressed, "--oracle-sha256", digest,
                "--collection", self.collection, "--collection-scope", "synthetic")
        rc, report = self.invoke("discover", *args, "--theme", "Shock")
        self.assertEqual(rc, 0, report)
        self.assertEqual(report["status"], "CANDIDATES_NOT_VALIDATED")
        self.assertTrue(report["result"]["results"])
        rc, report = self.invoke("validate", *args, "--deck", self.deck)
        self.assertEqual(rc, 0, report)
        self.assertEqual(report["result"]["status"], "PASS_WITH_LIMITATIONS")

    def test_successful_outputs_never_expose_private_snapshot_paths(self):
        for action, extra in (("discover", ("--theme", "Shock")),
                              ("validate", ("--deck", self.deck))):
            with self.subTest(action=action):
                code, result = self.invoke(action, *self.common(), *extra)
                self.assertEqual(code, 0, result)
                rendered = json.dumps(result, sort_keys=True)
                self.assertNotIn("mtg-agent-gateway-", rendered)
                self.assertNotIn(str(self.oracle), rendered)
                self.assertNotIn(str(self.collection), rendered)
                self.assertNotIn(str(self.deck), rendered)


if __name__ == "__main__":
    unittest.main()
