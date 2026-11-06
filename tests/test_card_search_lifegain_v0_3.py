"""Focused offline regression tests: collection-only lifegain v0.3 (synthetic Oracle fixtures)."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from collections import Counter


ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "tools" / "card_search.py"
SPEC = importlib.util.spec_from_file_location("mtg_card_search_lifegain_v03", PATH)
TOOL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(TOOL)


def card(name, rules, identity="W", types=None):
    return {
        "name": name, "text": rules, "manaValue": 2,
        "colorIdentity": list(identity),
        "types": types or ["Creature"], "subtypes": [],
        "supertypes": [], "keywords": [],
    }


class LifegainV03Tests(unittest.TestCase):
    def setUp(self):
        self.cards = {
            "Fixture Arrival Medic": [card("Fixture Arrival Medic",
                "Whenever a nontoken artifact enters under your control, you gain 2 life.")],
            "Fixture Life Counter": [card("Fixture Life Counter",
                "Whenever you gain life, put a +1/+1 counter on Fixture Life Counter.")],
            "Fixture Life Tribute": [card("Fixture Life Tribute",
                "Whenever you gain life, you may tap an untapped artifact.",
                "B", ["Enchantment"])],
            "Vito": [card("Vito",
                "Whenever you gain life, you may tap an untapped artifact.\n"
                "{4}: Other creatures you control gain lifelink until the end of combat.", "B")],
            "Fixture Cinder Remedy": [card("Fixture Cinder Remedy",
                "Fixture Cinder Remedy deals 1 damage to target creature. You gain 5 life.",
                "RW", ["Instant"])],
            "Fixture Relic Exile": [card("Fixture Relic Exile",
                "Exile target tapped artifact. Its controller gains 4 life.",
                "W", ["Instant"])],
            "Life Enemy": [card("Life Enemy",
                "Target opponent gains 4 life.", "U", ["Instant"])],
            "Life Friend": [card("Life Friend", "Lifelink", "W")],
            "Blood Burglar": [card("Blood Burglar", "While you control an Island, this creature has lifelink.", "B")],
            "Alchemist's Gift": [card("Alchemist's Gift",
                "Target creature gets +0/+3 and gains your choice of haste or lifelink until end of turn.", "B", ["Instant"])],
            "Leonin Warleader": [card("Leonin Warleader",
                "Whenever this creature blocks, create three 0/2 green Insect creature tokens with lifelink.")],
            "Fixture Dusk Keeper": [card("Fixture Dusk Keeper",
                "At the beginning of combat on your turn, if you gained life this turn, create a tapped 2/2 blue Bird creature token.", "WB")],
            "Fixture Threshold Keeper": [card("Fixture Threshold Keeper",
                "Lifelink\nAt the beginning of your upkeep, if you gained 4 or more life this turn, draw two cards.", "WB")],
            "Life Lands": [card("Life Lands", "When this land enters, you gain 1 life.", "W", ["Land"])],
            "Nightmare's Thirst": [card("Nightmare's Thirst",
                "You gain 2 life. Until your next turn, target creature gets -X/-X.", "B", ["Instant"])],
            "Cleric Class": [card("Cleric Class",
                "If you would gain life, gain 5 life instead.",
                "W", ["Enchantment"])],
            "Healing Salve": [card("Healing Salve", "Gain 7 life.", "W", ["Instant"])],
            "Life Gift": [card("Life Gift",
                "Creatures your opponents control gain lifelink until end of turn.",
                "U", ["Sorcery"])],
            "Counterspell": [card("Counterspell",
                "Counter target spell.", "U", ["Instant"])],
            "Disenchant": [card("Disenchant",
                "Destroy target tapped artifact.", "W", ["Instant"])],
            "Flavor Creature": [card("Flavor Creature",
                "Whenever you gain life, draw a card.", "G")],
            "Conflicting": [card("Conflicting", "You gain 2 life."),
                            card("Conflicting", "Nothing happens.")],
        }
        self.owned = Counter({name.casefold(): 2 for name in self.cards})
        self.owned["unowned ghost"] = 4

    def find(self, **kwargs):
        opts = dict(theme="lifegain", collection=self.owned, owned_only=True, limit=500)
        opts.update(kwargs)
        return TOOL.search(self.cards, **opts)

    def test_life_source_not_condition(self):
        rows = {r["name"]: r for r in self.find()["results"]}
        self.assertIn("core", rows["Fixture Arrival Medic"]["roles"])
        self.assertIn("enabler", rows["Fixture Arrival Medic"]["roles"])
        self.assertEqual(rows["Fixture Life Counter"]["roles"], ["payoff"])
        self.assertEqual(rows["Fixture Life Tribute"]["roles"], ["payoff"])
        self.assertEqual(rows["Flavor Creature"]["roles"], ["payoff"])

    def test_lifelink_is_life_source_and_grant_is_enabler(self):
        rows = {r["name"]: r for r in self.find()["results"]}
        self.assertIn("core", rows["Life Friend"]["roles"])
        self.assertIn("enabler", rows["Life Friend"]["roles"])
        self.assertIn("payoff", rows["Vito"]["roles"])
        self.assertIn("enabler", rows["Vito"]["roles"])
        self.assertNotIn("Life Gift", rows)

    def test_replacement_modifier_not_independent_source(self):
        rows = {r["name"]: r for r in self.find()["results"]}
        self.assertNotIn("core", rows["Cleric Class"]["roles"])
        self.assertIn("enabler", rows["Cleric Class"]["roles"])
        self.assertIn("core", rows["Healing Salve"]["roles"])
        self.assertIn("enabler", rows["Healing Salve"]["roles"])
        self.assertTrue(rows["Fixture Arrival Medic"]["role_evidence"]["core"]["conditional"])

    def test_synthetic_lifegain_variations(self):
        rows = {r["name"]: r for r in self.find()["results"]}
        self.assertIn("core", rows["Blood Burglar"]["roles"])
        self.assertTrue(rows["Blood Burglar"]["role_evidence"]["core"]["conditional"])
        self.assertEqual(rows["Alchemist's Gift"]["roles"], ["enabler"])
        self.assertEqual(rows["Leonin Warleader"]["roles"], ["enabler"])
        self.assertEqual(rows["Fixture Dusk Keeper"]["roles"], ["payoff"])
        self.assertIn("payoff", rows["Fixture Threshold Keeper"]["roles"])
        self.assertIn("interaction", rows["Nightmare's Thirst"]["roles"])

    def test_pair_ranking_threshold_and_modifier_guard(self):
        report = self.find(synergy=True, max_synergy_pairs=100)
        pairs = report["synergy_analysis"]["pairs"]
        self.assertTrue(pairs)
        self.assertFalse(any(p["source"] == "Cleric Class" for p in pairs))
        self.assertFalse(any(p["source"] == "Life Lands" for p in pairs[:15]))
        patrician = next(p for p in pairs if p["payoff"] == "Fixture Threshold Keeper")
        self.assertTrue(patrician["requires_threshold_check"])
        self.assertEqual(patrician["status"], "CANDIDATE_NOT_RULES_VERIFIED")

    def test_interaction_and_false_life_source(self):
        rows = {r["name"]: r for r in self.find(roles=["core", "payoff", "interaction"])["results"]}
        self.assertIn("interaction", rows["Fixture Relic Exile"]["roles"])
        self.assertNotIn("core", rows["Fixture Relic Exile"]["roles"])
        self.assertIn("interaction", rows["Fixture Cinder Remedy"]["roles"])
        self.assertIn("core", rows["Fixture Cinder Remedy"]["roles"])
        self.assertIn("interaction", rows["Counterspell"]["roles"])
        self.assertNotIn("core", rows["Counterspell"]["roles"])
        self.assertNotIn("Life Enemy", rows)

    def test_owned_only_and_any_color(self):
        result = TOOL.search(self.cards, theme="lifegain", roles=["interaction"],
                             collection=Counter({"counterspell": 1}),
                             owned_only=True, color_identity="ANY", limit=100)
        self.assertEqual([r["name"] for r in result["results"]], ["Counterspell"])
        self.assertEqual(result["results"][0]["owned_copies"], 1)
        with self.assertRaisesRegex(ValueError, "Color identity"):
            self.find(color_identity="NOT_A_COLOR")

    def test_all_5_roles_or_semantics(self):
        result = self.find(roles=["core", "enabler", "payoff", "interaction"])
        names = {r["name"] for r in result["results"]}
        self.assertIn("Fixture Arrival Medic", names)
        self.assertIn("Fixture Life Counter", names)
        self.assertIn("Counterspell", names)
        self.assertNotIn("Life Enemy", names)

    def test_bounded_synergy_and_provenance(self):
        report = self.find(roles=["core", "enabler", "payoff", "interaction"],
                           synergy=True, max_synergy_pairs=2, limit=1)
        synergy = report["synergy_analysis"]
        self.assertEqual(synergy["returned_pairs"], 2)
        self.assertTrue(synergy["truncated"])
        self.assertGreater(synergy["possible_pairs"], 2)
        self.assertEqual(report["returned_count"], 1)
        for pair in synergy["pairs"]:
            self.assertNotEqual(pair["source"], pair["payoff"])
            self.assertEqual(pair["confidence"], "HEURISTIC")
            self.assertEqual(pair["status"], "CANDIDATE_NOT_RULES_VERIFIED")
            self.assertIn("source_evidence", pair)
            self.assertIn("payoff_evidence", pair)
            self.assertIn(pair["source"].casefold(), self.owned)
            self.assertIn(pair["payoff"].casefold(), self.owned)

    def test_collection_leak_guard(self):
        self.owned = Counter({"fixture arrival medic": 1, "fixture life counter": 1})
        report = self.find(synergy=True)
        self.assertEqual(report["synergy_analysis"]["returned_pairs"], 1)
        pair = report["synergy_analysis"]["pairs"][0]
        self.assertEqual((pair["source"], pair["payoff"]), ("Fixture Arrival Medic", "Fixture Life Counter"))

    def test_synergy_restrictions(self):
        with self.assertRaisesRegex(ValueError, "requires --collection"):
            TOOL.search(self.cards, theme="lifegain", synergy=True)
        with self.assertRaisesRegex(ValueError, "supports --theme lifegain"):
            TOOL.search(self.cards, theme="deathtouch", collection=self.owned,
                        owned_only=True, synergy=True)
        with self.assertRaisesRegex(ValueError, "max_synergy_pairs"):
            self.find(synergy=True, max_synergy_pairs=501)

    def test_ambiguous_printing_not_silently_included(self):
        report = self.find()
        self.assertNotIn("Conflicting", {r["name"] for r in report["results"]})
        self.assertEqual(report["coverage"]["uncertain_role_variants"], 1)

    def test_cli_synthetic_csv_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            oracle, collection, output = base/"oracle.json", base/"collection.csv", base/"report.json"
            oracle.write_text(json.dumps({"data": self.cards, "meta": {"version": "fixture"}}), encoding="utf-8")
            collection.write_text("Name,Quantity\nFixture Arrival Medic,2\nFixture Life Counter,1\n"
                                  "Counterspell,1\nUnknown Fixture,1\n", encoding="utf-8")
            rc = TOOL.main(["--oracle", str(oracle), "--collection", str(collection),
                            "--owned-only", "--theme", "lifegain", "--identity", "ANY",
                            "--role", "core", "--role", "enabler", "--role", "payoff",
                            "--role", "interaction", "--synergy", "--max-synergy-pairs", "10",
                            "--format", "json", "--output", str(output)])
            self.assertEqual(rc, 0)
            report = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(report["tool_version"], "0.3.0")
            self.assertEqual(report["synergy_analysis"]["returned_pairs"], 1)
            self.assertEqual(report["collection_coverage"]["unresolved_name_count"], 1)
            self.assertIn("unknown fixture", report["collection_coverage"]["owned_names_absent_from_oracle"])

    def test_old_theme_deathtouch_no_generic_interaction_spam(self):
        cards = {"Viper": [card("Viper", "Deathtouch")],
                 "Blade": [card("Blade", "Destroy target creature.", "B", ["Instant"])]}
        result = TOOL.search(cards, theme="Deathtouch", limit=10)
        self.assertEqual([r["name"] for r in result["results"]], ["Viper"])


if __name__ == "__main__":
    unittest.main()
