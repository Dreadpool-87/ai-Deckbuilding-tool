"""Synthetic regressions for explicit Casual unlimited-copy Oracle exceptions."""
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "casual_copy_validator", ROOT / "validator/MTG_Deck_Validator_v1.1.1.py"
)
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)


def oracle(name, *, special=False, text=None):
    return {
        "name": name,
        "manaValue": 2,
        "manaCost": "{1}{W}",
        "types": ["Creature"],
        "supertypes": [],
        "colorIdentity": ["W"],
        "text": text or "",
        "hasAlternativeDeckLimit": special,
    }


PLAINS = {
    "name": "Plains", "manaValue": 0, "types": ["Land"],
    "supertypes": ["Basic"], "colorIdentity": ["W"],
}
UNLIMITED_FIXTURE_TEXT = (
    "Whenever this creature blocks, scry 2.\n"
    "A deck can have any number of cards named Fixture Rally Cadet."
)


class CasualCopyExceptionTests(unittest.TestCase):
    def report(self, cards, deck_copies=5, owned_copies=5, mode="casual"):
        return VALIDATOR.validate(
            {name: owned_copies for name in cards},
            {"Plains": [PLAINS], **cards},
            {"Plains": (100 if mode == "commander" else 60) - deck_copies,
             next(iter(cards)): deck_copies},
            mode=mode, exact_60=(mode == "casual"),
        )

    def test_explicit_template_permits_five_owned_copies(self):
        report = self.report({
            "Fixture Rally Cadet": [oracle("Fixture Rally Cadet", special=True, text=UNLIMITED_FIXTURE_TEXT)]
        })
        self.assertEqual(report["status"], "PASS_WITH_LIMITATIONS", report["failures"])
        self.assertEqual(report["checks"]["copy_limit"], "PASS")
        self.assertEqual(report["checks"]["ownership"], "PASS")
        self.assertEqual(
            report["checks"]["special_deckbuilding_exceptions"],
            "PASS_EXPLICIT_UNLIMITED_COPY",
        )

    def test_unlimited_copy_text_does_not_grant_ownership(self):
        report = self.report({
            "Fixture Rally Cadet": [oracle("Fixture Rally Cadet", special=True, text=UNLIMITED_FIXTURE_TEXT)]
        }, owned_copies=4)
        self.assertEqual(report["checks"]["copy_limit"], "PASS")
        self.assertEqual(report["checks"]["ownership"], "FAIL")
        self.assertEqual(report["status"], "FAIL")

    def test_normal_five_copy_spell_still_fails(self):
        report = self.report({"Normal Creature": [oracle("Normal Creature")]})
        self.assertEqual(report["checks"]["copy_limit"], "FAIL")
        self.assertEqual(report["checks"]["ownership"], "PASS")
        self.assertEqual(report["status"], "FAIL")

    def test_exception_belonging_to_another_name_does_not_apply(self):
        report = self.report({
            "Imposter": [oracle(
                "Imposter", special=True,
                text="A deck can have any number of cards named Fixture Rally Cadet."
            )]
        })
        self.assertEqual(report["checks"]["copy_limit"], "UNVERIFIED")
        self.assertEqual(report["checks"]["special_deckbuilding_exceptions"], "UNVERIFIED")
        self.assertEqual(report["status"], "UNVERIFIED")

    def test_variant_disagreement_is_unverified_not_false_pass(self):
        report = self.report({
            "Fixture Rally Cadet": [
                oracle("Fixture Rally Cadet", special=True, text=UNLIMITED_FIXTURE_TEXT),
                oracle("Fixture Rally Cadet", special=False, text="Other Oracle wording."),
            ]
        })
        self.assertEqual(report["checks"]["copy_limit"], "UNVERIFIED")
        self.assertEqual(report["status"], "UNVERIFIED")

    def test_unknown_finite_alternative_is_not_treated_as_unlimited(self):
        report = self.report({
            "Fixture Five Cadets": [oracle(
                "Fixture Five Cadets", special=True,
                text="A deck can have up to five cards named Fixture Five Cadets."
            )]
        }, deck_copies=8, owned_copies=8)
        self.assertEqual(report["checks"]["copy_limit"], "UNVERIFIED")
        self.assertEqual(report["status"], "UNVERIFIED")

    def test_commander_mode_still_rejects_multiple_copies(self):
        report = self.report({
            "Fixture Rally Cadet": [oracle("Fixture Rally Cadet", special=True, text=UNLIMITED_FIXTURE_TEXT)]
        }, mode="commander")
        self.assertEqual(report["checks"]["copy_limit"], "FAIL")


if __name__ == "__main__":
    unittest.main()
