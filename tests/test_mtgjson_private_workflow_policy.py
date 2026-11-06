"""Guardrails for private draft-only MTGJSON Release workflow."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
PRIVATE = ROOT / ".github/workflows/mtgjson-private-draft-bundle.yml"
VERIFY_ONLY = ROOT / ".github/workflows/mtgjson-atomic-update.yml"
BUNDLER = ROOT / "scripts/prepare_mtgjson_private_bundle.py"


class TestPrivateMtgjsonWorkflowPolicy(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workflow = PRIVATE.read_text(encoding="utf-8")
        cls.upstream = VERIFY_ONLY.read_text(encoding="utf-8")
        cls.bundler = BUNDLER.read_text(encoding="utf-8")

    def test_monthly_and_manual_triggers(self):
        self.assertIn('cron: "37 7 1 * *"', self.workflow)
        self.assertIn("workflow_dispatch:", self.workflow)

    def test_private_only_and_draft_only(self):
        self.assertIn("gh api", self.workflow)
        self.assertIn("'.private'", self.workflow)
        self.assertIn('= "true"', self.workflow)
        self.assertIn("--draft", self.workflow)
        self.assertNotIn("gh release edit", self.workflow)
        self.assertNotIn("--latest", self.workflow)

    def test_write_permission_is_job_scoped(self):
        self.assertIn("permissions:\n  contents: read", self.workflow)
        self.assertIn("    permissions:\n      contents: write", self.workflow)

    def test_all_four_upstream_gzip_sha_pairs_present(self):
        for filename in ("AtomicCards.json.gz", "cards.csv.gz",
                         "cardIdentifiers.csv.gz", "cardRulings.csv.gz"):
            self.assertIn(filename, self.workflow)
            self.assertIn(filename + ".sha256", self.workflow)
        for table in ("cards", "cardIdentifiers", "cardRulings"):
            self.assertIn('"' + table + '"', self.bundler)

    def test_old_atomic_verification_remains_read_only(self):
        self.assertIn("permissions:\n  contents: read", self.upstream)
        self.assertNotIn("gh release create", self.upstream)

    def test_two_snapshot_retention_is_present_and_bounded(self):
        self.assertIn("plan_mtgjson_private_retention.py", self.workflow)
        self.assertIn("gh api --paginate --slurp", self.workflow)
        self.assertIn("--recheck", self.workflow)
        self.assertIn("gh release download", self.workflow)
        self.assertIn("cmp -s", self.workflow)
        self.assertIn(".older[]", self.workflow)
        self.assertIn("gh api --method DELETE", self.workflow)
        self.assertIn("mtgjson-private-bundle-*", self.workflow)
        self.assertNotIn('gh release delete --yes', self.workflow)

    def test_release_includes_rights_notices(self):
        self.assertIn("MTGJSON-MIT.txt", self.workflow)
        self.assertIn("THIRD_PARTY_NOTICES.md", self.workflow)
        self.assertIn("manifest.json", self.workflow)


if __name__ == "__main__":
    unittest.main()
