"""Offline tests for the official MTG rules source monitor."""
import importlib.util
import pathlib
import unittest

path = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "check_mtg_rules.py"
spec = importlib.util.spec_from_file_location("check_mtg_rules", path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class RulesSourceTests(unittest.TestCase):
    def test_sha256(self):
        self.assertEqual(len(module.sha(b"test")), 64)
        self.assertNotEqual(module.sha(b"test"), module.sha(b"changed"))

    def test_find_official_documents(self):
        html = b'<a href="https://media.wizards.com/rules.pdf">PDF</a><a href="/rules.docx">DOCX</a>'
        result = module.discover_rule_documents(html, "https://magic.wizards.com/en/rules")
        self.assertEqual(result["pdf"], "https://media.wizards.com/rules.pdf")
        self.assertEqual(result["docx"], "https://magic.wizards.com/rules.docx")

    def test_exclude_untrusted_document_host(self):
        html = b'<a href="https://example.com/rules.pdf">PDF</a>'
        self.assertEqual(module.discover_rule_documents(html, "https://magic.wizards.com/en/rules"), {})

    def test_exclude_non_https_document(self):
        html = b'<a href="http://media.wizards.com/rules.pdf">PDF</a>'
        self.assertEqual(module.discover_rule_documents(html, "https://magic.wizards.com/en/rules"), {})


    def test_rules_document_with_spaces_in_filename(self):
        html = b'<a href="https://media.wizards.com/2026/downloads/MagicCompRules 20260925.docx">DOCX</a>'
        result = module.discover_rule_documents(html, "https://magic.wizards.com/en/rules")
        self.assertEqual(result["docx"], "https://media.wizards.com/2026/downloads/MagicCompRules%2020260925.docx")

    def test_preserve_existing_url_encoding(self):
        url = "https://media.wizards.com/2026/MagicCompRules%2020260925.docx"
        self.assertEqual(module.encode_url(url), url)

    def test_encode_unicode_and_spaces(self):
        self.assertEqual(module.encode_url("https://media.wizards.com/a b/é.docx"),
                         "https://media.wizards.com/a%20b/%C3%A9.docx")

    def test_raw_html_only_changes_require_review_but_not_hard_failure(self):
        old = self._baseline()
        current = {k: dict(v) for k, v in old.items()}
        for key in ("comprehensive_rules", "commander_format", "banned_restricted"):
            current[key]["sha256"] = "b" * 64
            current[key]["bytes"] = 321
        self.assertEqual(module.classify_source_changes(old, current), "html_review")

    def test_official_pdf_change_is_blocking(self):
        old = self._baseline()
        current = {k: dict(v) for k, v in old.items()}
        current["comprehensive_rules_pdf"]["sha256"] = "c" * 64
        self.assertEqual(module.classify_source_changes(old, current), "blocking_review")

    def test_official_docx_disappearance_is_blocking(self):
        old = self._baseline()
        current = {k: dict(v) for k, v in old.items()}
        del current["comprehensive_rules_docx"]
        self.assertEqual(module.classify_source_changes(old, current), "blocking_review")

    def test_change_of_official_page_url_is_blocking(self):
        old = self._baseline()
        current = {k: dict(v) for k, v in old.items()}
        current["commander_format"]["url"] = "https://magic.wizards.com/en/other-page"
        self.assertEqual(module.classify_source_changes(old, current), "blocking_review")

    def test_absent_or_invalid_baseline_is_blocking(self):
        old = self._baseline()
        self.assertEqual(module.classify_source_changes({}, old), "blocking_review")
        self.assertEqual(module.classify_source_changes(old, old, "UNVERIFIED"), "blocking_review")

    def test_unchanged_snapshots(self):
        old = self._baseline()
        self.assertEqual(module.classify_source_changes(old, old), "unchanged")

    def test_unknown_new_source_and_corrupt_html_sha_are_blocking(self):
        old = self._baseline()
        current = {k: dict(v) for k, v in old.items()}
        current["new_rules_doc"] = {"url": "https://media.wizards.com/rules.txt",
                                    "sha256": "d" * 64, "bytes": 123}
        self.assertEqual(module.classify_source_changes(old, current), "blocking_review")
        current = {k: dict(v) for k, v in old.items()}
        current["banned_restricted"]["sha256"] = "malformed"
        self.assertEqual(module.classify_source_changes(old, current), "blocking_review")

    def test_monitor_workflow_displays_severity_without_writing_repo(self):
        workflow = (pathlib.Path(__file__).resolve().parents[1] /
                    ".github/workflows/mtg-rules-check.yml").read_text(encoding="utf-8")
        self.assertIn("steps.inspect.outputs.change_type", workflow)
        self.assertIn("env:\n          RULES_CHANGE_TYPE: ${{ steps.inspect.outputs.change_type }}", workflow)
        self.assertIn('[[ "$RULES_CHANGE_TYPE" == "html_review" ]]', workflow)
        self.assertIn("HTML_ONLY_REVIEW_REQUIRED", workflow)
        self.assertIn("BLOCKING_SOURCE_REVIEW_REQUIRED", workflow)
        self.assertIn("manual review required", workflow)
        self.assertIn("exit 0", workflow)
        self.assertIn("exit 1", workflow)

    @staticmethod
    def _baseline():
        keys = ["comprehensive_rules", "comprehensive_rules_pdf",
                "comprehensive_rules_docx", "commander_format", "banned_restricted"]
        return {key: {"url": "https://magic.wizards.com/en/" + key,
                      "sha256": "a" * 64, "bytes": 123}
                for key in keys}

    def test_monitor_workflow_cannot_push_to_main(self):
        workflow = (pathlib.Path(__file__).resolve().parents[1] /
                    ".github/workflows/mtg-rules-check.yml").read_text(encoding="utf-8")
        self.assertIn("\npermissions:\n  contents: read\n", workflow)
        self.assertIn("persist-credentials: false", workflow)
        self.assertNotIn("contents: write", workflow)
        self.assertNotIn("git push", workflow)
        self.assertNotIn("git commit", workflow)
        self.assertIn("git diff -- rules/manifest.json rules/CHANGELOG.md", workflow)
        self.assertIn("manual review required", workflow)
        self.assertIn("exit 1", workflow)


if __name__ == "__main__":
    unittest.main()
