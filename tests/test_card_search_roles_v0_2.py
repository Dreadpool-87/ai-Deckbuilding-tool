"""Synthetic regression tests for Card Search v0.2 roles and existing API behavior."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

# Works in GitHub at tests/ and in the downloaded user package beside the script.
HERE = Path(__file__).resolve()
ROOT = HERE.parents[1] if (HERE.parents[1] / "tools/card_search.py").exists() else HERE.parent
TOOL_PATH = ROOT / "tools/card_search.py" if (ROOT / "tools/card_search.py").exists() else ROOT / "card_search.py"
SPEC = importlib.util.spec_from_file_location("card_search_roles_v02", TOOL_PATH)
TOOL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(TOOL)


def card(name, text, *, keyword=None, mana=2, identity=None, types=None, subtypes=None):
    return {
        "name": name, "text": text, "keywords": keyword,
        "manaValue": mana, "colorIdentity": ["B"] if identity is None else identity,
        "types": ["Creature"] if types is None else types,
        "subtypes": [] if subtypes is None else subtypes,
        "supertypes": [],
    }


class RoleSearchTests(unittest.TestCase):
    def setUp(self):
        self.cards = {
            "Poison Viper": [card("Poison Viper", "Deathtouch")],
            "Gift": [card("Gift", "Target tapped creature gains deathtouch until end of turn.", types=["Instant"])],
            "Self Imp": [card("Self Imp", "Flying\n{B}: This creature gains deathtouch until end of turn.")],
            "Triggered Snake": [card("Triggered Snake", "Deathtouch\nWhenever a creature you control with deathtouch attacks, put a stun counter on up to one target artifact.")],
            "Unrelated Archer": [card("Unrelated Archer", "Reach\nDeathtouch\nWhenever another nontoken creature dies, each opponent loses 2 life.")],
            "Damage Spell": [card("Damage Spell", "Target creature you control deals damage equal to its power to target creature with two or more counters on it.", types=["Sorcery"])],
            "Edge Spell": [card("Edge Spell", "Put two +1/+1 counters on target creature you control. Then that creature deals damage equal to its power to target creature with reach.", types=["Sorcery"])],
            "Removal Spell": [card("Removal Spell", "Removal Spell deals 3 damage to target creature.", types=["Instant"])],
            "Landfall Scout": [card("Landfall Scout", "Landfall — Whenever a land enters under your control, create a token.")],
            "Extra Lands": [card("Extra Lands", "You may play up to four additional lands this turn.")],
            "Unknown Theme": [card("Unknown Theme", "Tap a creature: do something.")],
            "Mixed Printings": [card("Mixed Printings", "Deathtouch"), card("Mixed Printings", "No abilities.")],
        }

    def test_direct_deathtouch_vs_granter(self):
        result = TOOL.search(self.cards, abilities=["Deathtouch"])
        found = {x["name"] for x in result["results"]}
        self.assertIn("Poison Viper", found)
        self.assertNotIn("Gift", found)
        self.assertNotIn("Self Imp", found)
        self.assertEqual(result["coverage"]["uncertain_variant_matches"], 1)

    def test_core_and_conditional_self_core(self):
        rows = {x["name"]: x for x in TOOL.search(self.cards, theme="Deathtouch", limit=100)["results"]}
        self.assertIn("core", rows["Poison Viper"]["roles"])
        self.assertIn("core", rows["Self Imp"]["roles"])
        self.assertTrue(rows["Self Imp"]["role_evidence"]["core"]["conditional"])
        self.assertNotIn("core", rows["Gift"]["roles"])

    def test_granting_is_enabler(self):
        row = TOOL.search(self.cards, theme="Deathtouch", roles=["enabler"], limit=100)
        self.assertEqual([x["name"] for x in row["results"]], ["Gift"])
        self.assertEqual(row["results"][0]["role_evidence"]["enabler"]["confidence"], "HEURISTIC")

    def test_payoff_must_reference_theme_in_trigger(self):
        rows = TOOL.search(self.cards, theme="Deathtouch", roles=["payoff"], limit=100)
        self.assertEqual([x["name"] for x in rows["results"]], ["Triggered Snake"])
        self.assertIn("with deathtouch attacks", rows["results"][0]["role_evidence"]["payoff"]["evidence"])

    def test_bite_and_edge_are_indirect_synergies(self):
        rows = TOOL.search(self.cards, theme="Deathtouch", roles=["synergy"], limit=100)
        names = {x["name"] for x in rows["results"]}
        self.assertEqual(names, {"Damage Spell", "Edge Spell"})
        self.assertNotIn("Removal Spell", names)

    def test_landfall_mechanic_and_extra_land_enabler(self):
        rows = {x["name"]:x for x in TOOL.search(self.cards, theme="Landfall", limit=100)["results"]}
        self.assertIn("core", rows["Landfall Scout"]["roles"])
        self.assertIn("enabler", rows["Extra Lands"]["roles"])

    def test_general_unknown_theme_text_fallback_without_exhaustive_claim(self):
        rows = TOOL.search(self.cards, theme="tap a creature", limit=100)
        self.assertEqual([x["name"] for x in rows["results"]], ["Unknown Theme"])
        self.assertEqual(rows["results"][0]["roles"], ["synergy"])
        self.assertTrue(any("not discoverable" in w.lower() for w in rows["limitations"]))

    def test_conflicting_printings_not_claimed_as_core(self):
        rows = TOOL.search(self.cards, theme="Deathtouch", limit=100)
        self.assertNotIn("Mixed Printings", {x["name"] for x in rows["results"]})
        self.assertEqual(rows["coverage"]["uncertain_role_variants"], 1)

    def test_owned_and_color_filters(self):
        owned = TOOL.Counter({"poison viper": 4, "gift": 1})
        out = TOOL.search(self.cards, theme="Deathtouch", owned_only=True,
                          collection=owned, color_identity="BG", limit=100)
        self.assertEqual({x["name"] for x in out["results"]}, {"Gift", "Poison Viper"})
        self.assertEqual(next(x for x in out["results"] if x["name"] == "Gift")["owned_copies"], 1)

    def test_pagination_and_role_counts(self):
        all_rows = TOOL.search(self.cards, theme="Deathtouch", limit=100)
        page_one = TOOL.search(self.cards, theme="Deathtouch", limit=2)
        page_two = TOOL.search(self.cards, theme="Deathtouch", limit=2, offset=2)
        self.assertEqual(page_one["total_matches"], all_rows["total_matches"])
        self.assertEqual(page_one["next_offset"], 2)
        self.assertTrue(page_one["truncated"])
        self.assertNotEqual({x["name"] for x in page_one["results"]},
                            {x["name"] for x in page_two["results"]})
        self.assertEqual(page_two["role_counts"], all_rows["role_counts"])

    def test_reject_incompatible_role_request(self):
        with self.assertRaisesRegex(ValueError, "requires --theme"):
            TOOL.search(self.cards, name="gift", roles=["core"])
        with self.assertRaisesRegex(ValueError, "Role must"):
            TOOL.search(self.cards, theme="deathtouch", roles=["notarole"])
        with self.assertRaisesRegex(ValueError, "Offset"):
            TOOL.search(self.cards, theme="deathtouch", offset=-1)

    def test_legacy_keyword_behavior(self):
        self.cards["Poison Viper"][0]["keywords"] = ["Deathtouch"]
        rows = TOOL.search(self.cards, keywords=["Deathtouch"])
        self.assertEqual([x["name"] for x in rows["results"]], ["Poison Viper"])

    def test_cli_json_and_csv_temp_files(self):
        with tempfile.TemporaryDirectory() as path:
            path = Path(path)
            oracle, collection, output = path / "db.json", path / "collection.csv", path / "results.json"
            oracle.write_text(json.dumps({"data": self.cards, "meta": {"version":"fixture"}}))
            collection.write_text("Name,Quantity\nPoison Viper,3\nGift,1\n", encoding="utf-8")
            rc = TOOL.main(["--oracle", str(oracle), "--collection", str(collection),
                            "--owned-only", "--theme", "Deathtouch", "--role", "core",
                            "--format", "json", "--output", str(output)])
            self.assertEqual(rc, 0)
            d = json.loads(output.read_text())
            self.assertEqual(d["oracle_version"], "fixture")
            self.assertEqual(d["total_matches"], 1)
            self.assertEqual(d["results"][0]["name"], "Poison Viper")


if __name__ == "__main__":
    unittest.main()
