"""Regression tests for delayed MTGJSON metadata PR publication.

A successful verification may wait in the Actions queue while a maintainer
merges its pointer. The queued job must never create another PR for the same
snapshot, and must not overwrite a newer verified snapshot.
"""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "check_mtgjson_pointer_pr.py"
spec = importlib.util.spec_from_file_location("check_mtgjson_pointer_pr", SCRIPT)
pointer_gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pointer_gate)


class PointerPrGateTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.folder = Path(temp.name)
        self.proposed = self.folder / "proposed.json"
        self.current = self.folder / "main.json"
        self.base = {
            "schema_version": 1,
            "source": "MTGJSON",
            "dataset": "AtomicCards.json.gz",
            "download_url": pointer_gate.URL,
            "checksum_url": pointer_gate.DIGEST_URL,
            "download_url_is_mutable": True,
            "version": "5.3.0+20261106",
            "sha256": "a" * 64,
            "verified_at_utc": "2026-11-07T14:12:30Z",
        }
        self.write(self.proposed, self.base)

    def write(self, path, data):
        path.write_text(json.dumps(data), encoding="utf-8")

    def decide(self):
        return pointer_gate.proposal_decision(
            pointer_gate.load_pointer(self.proposed),
            pointer_gate.load_pointer(self.current),
        )

    def test_first_verified_snapshot_requires_proposal(self):
        self.assertEqual(pointer_gate.proposal_decision(
            pointer_gate.load_pointer(self.proposed), None), "PROPOSE")

    def test_same_snapshot_merged_while_job_queued_is_no_op(self):
        # Reproduces delayed run 42380484687, after PR #10 was merged.
        self.write(self.current, self.base)
        self.assertEqual(self.decide(), "ALREADY_ON_MAIN")
        newer_time = {**self.base, "verified_at_utc": "2026-11-07T14:30:44Z"}
        self.write(self.proposed, newer_time)
        self.assertEqual(self.decide(), "ALREADY_ON_MAIN")

    def test_newer_snapshot_on_main_blocks_old_verification(self):
        self.write(self.current, {**self.base,
                                  "sha256": "b" * 64,
                                  "version": "5.3.0+20261107",
                                  "verified_at_utc": "2026-11-07T14:15:00Z"})
        self.assertEqual(self.decide(), "SUPERSEDED_BY_MAIN")

    def test_same_timestamp_different_checksum_is_ambiguous_and_blocked(self):
        self.write(self.current, {**self.base, "sha256": "b" * 64})
        self.assertEqual(self.decide(), "SUPERSEDED_BY_MAIN")

    def test_genuinely_newer_snapshot_is_proposed(self):
        self.write(self.current, self.base)
        self.write(self.proposed, {**self.base,
                                   "sha256": "b" * 64,
                                   "verified_at_utc": "2026-11-08T07:17:00Z"})
        self.assertEqual(self.decide(), "PROPOSE")

    def test_new_version_proposed_only_when_verified_later(self):
        self.write(self.current, self.base)
        self.write(self.proposed, {**self.base,
                                   "version": "5.3.0+20261107",
                                   "verified_at_utc": "2026-11-08T07:17:00Z"})
        self.assertEqual(self.decide(), "PROPOSE")

    def test_corrupt_current_main_not_ignored(self):
        for invalid in (
            "{bad-json",
            '{"schema_version":1,"schema_version":1}',
            json.dumps({**self.base, "download_url": "https://example.invalid/archive"}),
            json.dumps({**self.base, "sha256": "nonsense"}),
            json.dumps({**self.base, "verified_at_utc": "yesterday"}),
        ):
            with self.subTest(invalid=invalid[:50]):
                self.current.write_text(invalid, encoding="utf-8")
                with self.assertRaises(ValueError):
                    self.decide()

    def test_workflow_rechecks_main_before_branch_and_before_pr(self):
        source = (ROOT / ".github/workflows/mtgjson-atomic-update.yml").read_text(encoding="utf-8")
        self.assertIn('verified_at_utc: ${{ steps.export.outputs.verified_at_utc }}', source)
        self.assertIn('VERIFIED_AT_UTC: ${{ needs.verify.outputs.verified_at_utc }}', source)
        self.assertIn('--verified-at "$VERIFIED_AT_UTC"', source)
        self.assertIn("git fetch --no-tags origin main", source)
        self.assertIn("scripts/check_mtgjson_pointer_pr.py", source)
        self.assertEqual(source.count('decision="$(check_current_main)"'), 2)
        self.assertLess(source.index('decision="$(check_current_main)"'),
                        source.index('git switch -c "$branch"'))
        self.assertGreater(source.rindex('decision="$(check_current_main)"'),
                           source.index('git push origin "$branch"'))
        self.assertLess(source.rindex('decision="$(check_current_main)"'),
                        source.index("gh pr create --base main"))
        self.assertNotIn("actions/upload-artifact", source)
        self.assertNotIn("gh release create", source)


if __name__ == "__main__":
    unittest.main()
