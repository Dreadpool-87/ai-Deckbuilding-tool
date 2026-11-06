"""Regression tests for conservative MTG Deck Validator v1.1.1 gates."""
import importlib.util
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("validator_111", ROOT / "validator" / "MTG_Deck_Validator_v1.1.1.py")
V = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(V)


def card(name, mv, types, color=None, supertype=(), skill=None):
    value = {"name": name, "manaValue": mv, "manaCost": "{R}" if mv else None,
             "types": list(types), "supertypes": list(supertype)}
    if color is not None:
        value["colorIdentity"] = list(color)
    if skill is not None:
        value["leadershipSkills"] = {"commander": skill}
    return value


MOUNTAIN = card("Mountain", 0, ["Land"], ["R"], ["Basic"])
SHOCK = card("Shock", 1, ["Instant"], ["R"])
LEADER = card("Red Leader", 3, ["Creature"], ["R"], ["Legendary"], True)


class Validator111SafetyTests(unittest.TestCase):
    def test_known_good_casual(self):
        r = V.validate({"Shock": 4}, {"Mountain": [MOUNTAIN], "Shock": [SHOCK]},
                       {"Mountain": 56, "Shock": 4}, exact_60=True)
        self.assertEqual(r["status"], "PASS_WITH_LIMITATIONS")
        self.assertEqual(r["mana_curve_nonlands"], {"1": 4})

    def test_mana_curve_integrity_with_actual_weighted_seven_plus_bin(self):
        spells = {
            "Zero Spell": card("Zero Spell", 0, ["Artifact"], ["R"]),
            "Cheap Spell": card("Cheap Spell", 1, ["Instant"], ["R"]),
            "Big Spell": card("Big Spell", 9, ["Sorcery"], ["R"]),
        }
        deck = {"Mountain": 54, "Zero Spell": 1, "Cheap Spell": 3, "Big Spell": 2}
        r = V.validate({"Zero Spell": 1, "Cheap Spell": 3, "Big Spell": 2},
                       {"Mountain": [MOUNTAIN], **{k: [v] for k, v in spells.items()}},
                       deck, exact_60=True)
        audit = r["mana_curve_integrity"]
        self.assertEqual(audit["status"], "ORACLE_ARITHMETIC_PASS")
        self.assertEqual(audit["bins"], {"0": 1, "1": 3, "2": 0, "3": 0,
                                         "4": 0, "5": 0, "6": 0, "7+": 2})
        self.assertEqual(audit["nonland_copies"], 6)
        self.assertEqual(audit["weighted_mana_value_total"], 21)
        self.assertEqual(audit["average_mana_value_fraction"], "7/2")
        self.assertEqual(audit["average_mana_value_rounded"], 3.5)
        self.assertEqual(
            sum(x["weighted_mana_value"] for x in audit["ledger"]), 21)
        self.assertEqual(r["mana_curve_nonlands"], {"0": 1, "1": 3, "9": 2})

    def test_mana_curve_integrity_missing_value_does_not_claim_pass(self):
        broken = dict(SHOCK, manaValue=None)
        r = V.validate({"Shock": 4}, {"Mountain": [MOUNTAIN], "Shock": [broken]},
                       {"Mountain": 56, "Shock": 4}, exact_60=True)
        audit = r["mana_curve_integrity"]
        self.assertEqual(r["checks"]["mana_curve"], "UNVERIFIED")
        self.assertEqual(audit["status"], "UNVERIFIED")
        self.assertIsNone(audit["ledger"])
        self.assertIsNone(audit["weighted_mana_value_total"])
        self.assertEqual(audit["unresolved_mana_values"], ["Shock"])

    def test_mana_curve_integrity_conflicting_oracle_variants_is_unverified(self):
        r = V.validate({"Shock": 4}, {"Mountain": [MOUNTAIN], "Shock": [SHOCK, dict(SHOCK, manaValue=3)]},
                       {"Mountain": 56, "Shock": 4}, exact_60=True)
        self.assertEqual(r["mana_curve_integrity"]["status"], "UNVERIFIED")
        self.assertIsNone(r["mana_curve_integrity"]["bins"])

    def test_all_lands_have_defined_empty_curve_but_no_average(self):
        r = V.validate({}, {"Mountain": [MOUNTAIN]}, {"Mountain": 60}, exact_60=True)
        audit = r["mana_curve_integrity"]
        self.assertEqual(audit["status"], "ORACLE_ARITHMETIC_PASS")
        self.assertEqual(audit["nonland_copies"], 0)
        self.assertEqual(audit["weighted_mana_value_total"], 0)
        self.assertIsNone(audit["average_mana_value_fraction"])
        self.assertIsNone(audit["average_mana_value_rounded"])

    def test_missing_types_is_not_pass(self):
        broken = dict(SHOCK, types=None)
        r = V.validate({"Shock": 4}, {"Mountain": [MOUNTAIN], "Shock": [broken]},
                       {"Mountain": 56, "Shock": 4}, exact_60=True)
        self.assertEqual(r["status"], "UNVERIFIED")
        self.assertEqual(r["checks"]["card_types"], "UNVERIFIED")
        self.assertEqual(r["checks"]["land_probability"], "UNVERIFIED")
        self.assertIsNone(r["lands_physical"])

    def test_missing_leader_identity_is_not_false_fail(self):
        broken = dict(LEADER)
        broken.pop("colorIdentity")
        r = V.validate({"Red Leader": 1}, {"Mountain": [MOUNTAIN], "Red Leader": [broken]},
                       {"Mountain": 99, "Red Leader": 1},
                       mode="commander", commander="Red Leader")
        self.assertEqual(r["status"], "UNVERIFIED")
        self.assertEqual(r["checks"]["commander_color_identity"], "UNVERIFIED")

    def test_missing_deck_card_identity_is_not_pass(self):
        broken = dict(SHOCK)
        broken.pop("colorIdentity")
        r = V.validate({"Red Leader": 1, "Shock": 1},
                       {"Mountain": [MOUNTAIN], "Red Leader": [LEADER], "Shock": [broken]},
                       {"Mountain": 98, "Red Leader": 1, "Shock": 1},
                       mode="commander", commander="Red Leader")
        self.assertEqual(r["checks"]["commander_color_identity"], "UNVERIFIED")
        self.assertEqual(r["status"], "UNVERIFIED")

    def test_known_off_identity_fails(self):
        green = card("Green Spell", 2, ["Instant"], ["G"])
        r = V.validate({"Red Leader": 1, "Green Spell": 1},
                       {"Mountain": [MOUNTAIN], "Red Leader": [LEADER], "Green Spell": [green]},
                       {"Mountain": 98, "Red Leader": 1, "Green Spell": 1},
                       mode="commander", commander="Red Leader")
        self.assertEqual(r["checks"]["commander_color_identity"], "FAIL")
        self.assertEqual(r["status"], "FAIL")

    def test_conflicting_commander_skills_not_pass(self):
        yes = card("Walker Leader", 3, ["Planeswalker"], ["R"], [], True)
        no = card("Walker Leader", 3, ["Planeswalker"], ["R"], [], False)
        r = V.validate({"Walker Leader": 1},
                       {"Mountain": [MOUNTAIN], "Walker Leader": [yes, no]},
                       {"Mountain": 99, "Walker Leader": 1},
                       mode="commander", commander="Walker Leader")
        self.assertEqual(r["status"], "UNVERIFIED")
        self.assertEqual(r["checks"]["commander_eligibility"], "UNVERIFIED")

    def test_conflicting_basic_land_exemption(self):
        nonbasic = dict(MOUNTAIN, supertypes=[])
        r = V.validate({}, {"Mountain": [MOUNTAIN, nonbasic]}, {"Mountain": 60}, exact_60=True)
        self.assertEqual(r["status"], "UNVERIFIED")
        self.assertEqual(r["checks"]["ownership"], "UNVERIFIED")
        self.assertEqual(r["checks"]["copy_limit"], "UNVERIFIED")

    def test_unlimited_standard_basic_lands(self):
        r = V.validate({}, {"Mountain": [MOUNTAIN]}, {"Mountain": 60}, exact_60=True)
        self.assertEqual(r["status"], "PASS_WITH_LIMITATIONS")

    def test_mismatched_name_is_fail(self):
        broken = dict(SHOCK, name="Not Shock")
        r = V.validate({"Shock": 4}, {"Mountain": [MOUNTAIN], "Shock": [broken]},
                       {"Mountain": 56, "Shock": 4}, exact_60=True)
        self.assertEqual(r["checks"]["oracle_lookup"], "FAIL")
        self.assertEqual(r["status"], "FAIL")

    def test_exact_23_land_probability(self):
        from math import comb
        expected = sum(comb(23, k) * comb(37, 7-k) for k in range(2, 6))
        p = V.exact_land_probability(60, 23)
        self.assertEqual(p.numerator * comb(60, 7), expected * p.denominator)

    def test_collection_csv_case_does_not_create_false_unowned_card(self):
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            collection = pathlib.Path(directory) / "synthetic.csv"
            collection.write_text("Name,Quantity\nshock,4\n", encoding="utf-8")
            owned = V.read_collection(collection)
            result = V.validate(owned, {"Mountain": [MOUNTAIN], "Shock": [SHOCK]},
                                {"Mountain": 56, "Shock": 4}, exact_60=True)
            self.assertEqual(result["status"], "PASS_WITH_LIMITATIONS", result["failures"])
            self.assertEqual(result["checks"]["ownership"], "PASS")

    def test_collection_printing_rows_with_different_case_are_summed(self):
        owned = {"Shock": 1, "shock": 2, "SHOCK": 1}
        result = V.validate(owned, {"Mountain": [MOUNTAIN], "Shock": [SHOCK]},
                            {"Mountain": 56, "Shock": 4}, exact_60=True)
        self.assertEqual(result["checks"]["ownership"], "PASS", result["failures"])

    def test_casefold_does_not_make_unrelated_or_insufficient_cards_owned(self):
        owned = {"shock": 2, "Shockwave": 100}
        result = V.validate(owned, {"Mountain": [MOUNTAIN], "Shock": [SHOCK]},
                            {"Mountain": 56, "Shock": 4}, exact_60=True)
        self.assertEqual(result["checks"]["ownership"], "FAIL")
        self.assertEqual(result["status"], "FAIL")
        self.assertIn('"owned": 2', " ".join(result["failures"]))

    def test_case_insensitive_ownership_does_not_bypass_copy_limit(self):
        result = V.validate({"shock": 5},
                            {"Mountain": [MOUNTAIN], "Shock": [SHOCK]},
                            {"Mountain": 55, "Shock": 5}, exact_60=True)
        self.assertEqual(result["checks"]["ownership"], "PASS")
        self.assertEqual(result["checks"]["copy_limit"], "FAIL")
        self.assertEqual(result["status"], "FAIL")

    def test_case_insensitive_ownership_does_not_relax_oracle_name_validation(self):
        result = V.validate({"shock": 4},
                            {"Mountain": [MOUNTAIN], "Shock": [SHOCK]},
                            {"Mountain": 56, "shock": 4}, exact_60=True)
        self.assertEqual(result["checks"]["oracle_lookup"], "FAIL")
        self.assertEqual(result["status"], "FAIL")

    def test_commander_owned_case_insensitively_still_checks_eligibility(self):
        result = V.validate({"red leader": 1},
                            {"Mountain": [MOUNTAIN], "Red Leader": [LEADER]},
                            {"Mountain": 99, "Red Leader": 1},
                            mode="commander", commander="Red Leader")
        self.assertEqual(result["status"], "PASS_WITH_LIMITATIONS", result["failures"])
        self.assertEqual(result["checks"]["commander_eligibility"], "PASS_BASIC_RULE")

if __name__ == "__main__":
    unittest.main()
