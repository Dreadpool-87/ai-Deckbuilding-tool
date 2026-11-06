"""Synthetic, deterministic regressions for bounded Synergy Engine v0.4."""
from collections import Counter
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("mtg_synergy_v04", ROOT / "tools" / "synergy_engine.py")
MOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)


def card(name, text, types=("Creature",), identity=("B",), mana=2):
    return {
        "name": name, "text": text, "manaValue": mana,
        "colorIdentity": list(identity), "types": list(types),
        "keywords": [], "subtypes": [], "supertypes": [],
    }


CASES = {
    "sacrifice": (
        ("Sacrifice Outlet", "Sacrifice a creature: Scry 1."),
        ("Death Payoff", "Whenever another creature dies, target opponent loses 1 life."),
    ),
    "tokens": (
        ("Token Maker", "Create two 1/1 white Soldier creature tokens."),
        ("Token Payoff", "Whenever a creature enters the battlefield under your control, you gain 1 life."),
    ),
    "proliferate": (
        ("Counter Spreader", "Proliferate.\nDraw a card."),
        ("Counter Maker", "Put a +1/+1 counter on target creature you control."),
    ),
    "blink": (
        ("Blinker", "Exile target tapped creature you control, then return it to the battlefield under its owner's control."),
        ("ETB Payoff", "When this creature enters the battlefield, draw a card."),
    ),
    "artifacts": (
        ("Treasure Maker", "Create a Treasure token."),
        ("Artifact Payoff", "Whenever an artifact enters the battlefield under your control, each opponent loses 1 life."),
    ),
    "spellslinger": (
        ("Shock", "Shock deals 1 damage to target tapped creature."),
        ("Spell Payoff", "Whenever you cast an instant or sorcery spell, create a token."),
    ),
    "landfall": (
        ("Land Ramp", "You may play an additional land this turn."),
        ("Landfall Payoff", "Landfall — Whenever a land enters the battlefield under your control, draw a card."),
    ),
    "counters": (
        ("Counter Provider", "At the beginning of combat on your turn, put two +1/+1 counters on target tapped creature you control."),
        ("Counter Payoff", "Whenever one or more +1/+1 counters are put on a creature you control, draw a card."),
    ),
}


class SynergyProfileTests(unittest.TestCase):
    def fixture(self, theme):
        a, b = CASES[theme]
        cards = {
            a[0]: [card(*a, types=("Instant",) if theme == "spellslinger" else ("Creature",))],
            b[0]: [card(*b)],
            "Unowned Source": [card("Unowned Source", a[1])],
        }
        owned = Counter({a[0].casefold(): 1, b[0].casefold(): 2})
        return cards, owned, a[0], b[0]

    def test_all_eight_profiles_match_valid_owned_pair(self):
        for theme in CASES:
            with self.subTest(theme=theme):
                cards, owned, a, b = self.fixture(theme)
                result = MOD.analyze(cards, owned, theme=theme)
                self.assertEqual(result["possible_pairs"], 1, result)
                self.assertEqual(result["returned_pairs"], 1, result)
                pair = result["pairs"][0]
                self.assertEqual((pair["source"], pair["payoff"]), (a, b))
                self.assertEqual((pair["source_owned_copies"], pair["payoff_owned_copies"]), (1, 2))
                self.assertEqual(pair["status"], "POSSIBLE_SYNERGY_NOT_RULES_VERIFIED")
                self.assertTrue(pair["source_evidence"])
                self.assertTrue(pair["payoff_evidence"])
                self.assertNotIn("Unowned Source", str(result))

    def test_known_false_positive_exclusions(self):
        cards = {
            "False Sac": [card("False Sac", "Whenever you sacrifice another creature, draw a card.")],
            "False Proliferate": [card("False Proliferate", "Whenever you proliferate, draw a card.")],
            "Opponent Only": [card("Opponent Only", "Target opponent sacrifices a creature.")],
        }
        owned = Counter({k.casefold(): 1 for k in cards})
        sac = MOD.analyze(cards, owned, theme="sacrifice")
        self.assertEqual(sac["source_count"], 0)
        prol = MOD.analyze(cards, owned, theme="proliferate")
        self.assertEqual(prol["source_count"], 0)

    def test_blink_requires_actual_exile_and_return_of_permanent(self):
        # A graveyard self-reanimation cost also says exile/return/battlefield,
        # but is NOT a blink source. Regression from real MTGJSON audit.
        cards = {
            "Bone Dragon": [card("Bone Dragon",
                "Exile four artifact cards from your graveyard: Return Bone Dragon from your graveyard to the battlefield with two stun counters.")],
            "ETB Payoff": [card("ETB Payoff", "When this creature enters the battlefield, draw a card.")],
        }
        owned = Counter({"bone dragon": 1, "etb payoff": 1})
        result = MOD.analyze(cards, owned, theme="blink")
        self.assertEqual(result["source_count"], 0)
        self.assertEqual(result["possible_pairs"], 0)

    def test_counter_replacement_payoff_is_not_counter_source(self):
        cards = {
            "Counter Provider": [card("Counter Provider",
                "At the beginning of combat on your turn, put two +1/+1 counters on target tapped creature you control.")],
            "Conclave Mentor": [card("Conclave Mentor",
                "If one or more +1/+1 counters would be put on a tapped creature you control, put that many plus two +1/+1 counters on it instead.")],
        }
        owned = Counter({"counter provider": 1, "conclave mentor": 1})
        result = MOD.analyze(cards, owned, theme="counters")
        self.assertEqual(result["source_count"], 1)
        self.assertEqual(result["payoff_count"], 1)
        self.assertEqual(result["possible_pairs"], 1)


    def test_token_replacement_is_not_independent_source(self):
        cards = {
            "Fixture Token Replacement": [card(
                "Fixture Token Replacement",
                "If you would create a tapped token, "
                "instead create three tapped tokens of that kind.",
                types=("Enchantment",),
            )],
            "Token Maker": [card("Token Maker", "Create a 1/1 green Saproling creature token.")],
            "ETB Payoff": [card(
                "ETB Payoff", "Whenever a creature enters under your control, draw a card.")],
        }
        owned = Counter({name.casefold(): 1 for name in cards})
        result = MOD.analyze(cards, owned, theme="tokens")
        self.assertEqual(result["source_count"], 1)
        self.assertEqual(result["possible_pairs"], 1)
        self.assertEqual(result["pairs"][0]["source"], "Token Maker")

    def test_artifact_replacement_is_not_independent_source(self):
        cards = {
            "Academy Manufactor": [card(
                "Academy Manufactor",
                "If you would create a Clue token during combat, instead create two Food tokens.",
                types=("Artifact", "Creature"),
            )],
            "Sai, Master Thopterist": [card(
                "Sai, Master Thopterist",
                "Whenever you cast a blue artifact spell, create a 0/2 colorless Servo "
                "artifact creature token with vigilance.",
            )],
            "Artifact Payoff": [card(
                "Artifact Payoff",
                "Whenever an artifact enters under your control, deal 1 damage to each opponent.",
            )],
        }
        owned = Counter({name.casefold(): 1 for name in cards})
        result = MOD.analyze(cards, owned, theme="artifacts")
        self.assertEqual(result["source_count"], 1)
        self.assertEqual(result["pairs"][0]["source"], "Sai, Master Thopterist")

    def test_landfall_multiple_extra_lands(self):
        cards = {
            "Azusa, Lost but Seeking": [card(
                "Azusa, Lost but Seeking",
                "You may play three additional lands on each of your turns.",
            )],
            "Landfall Payoff": [card(
                "Landfall Payoff", "Landfall — Whenever a land you control enters, draw a card.",
            )],
        }
        owned = Counter({name.casefold(): 1 for name in cards})
        result = MOD.analyze(cards, owned, theme="landfall")
        self.assertEqual(result["source_count"], 1)
        self.assertEqual(result["possible_pairs"], 1)

    def test_land_self_etb_excluded_for_creature_blink(self):
        cards = {
            "Ephemerate": [card(
                "Ephemerate",
                "Exile target tapped creature you control, then return it to the battlefield "
                "under its owner's control.",
                types=("Instant",),
            )],
            "Bloodfell Caves": [card(
                "Bloodfell Caves", "This land enters tapped.\nWhen this land enters, you gain 6 life.",
                types=("Land",),
            )],
            "Ravenous Chupacabra": [card(
                "Ravenous Chupacabra",
                "When this creature enters, destroy up to one target tapped creature.",
            )],
        }
        owned = Counter({name.casefold(): 1 for name in cards})
        result = MOD.analyze(cards, owned, theme="blink")
        self.assertEqual(result["source_count"], 1)
        self.assertEqual(result["payoff_count"], 1)
        self.assertEqual(result["pairs"][0]["payoff"], "Ravenous Chupacabra")

    def test_unknown_theme_fails_explicitly(self):
        cards, owned, _, _ = self.fixture("blink")
        with self.assertRaisesRegex(ValueError, "Unsupported pair profile"):
            MOD.analyze(cards, owned, theme="unimplementedcombo")
        with self.assertRaisesRegex(ValueError, "between 1 and 500"):
            MOD.analyze(cards, owned, theme="blink", limit=501)

    def test_bounded_pagination_preserves_totals_and_distributes_sources(self):
        cards = {}
        owned = Counter()
        for i in range(20):
            name = "Blinker " + str(i)
            cards[name] = [card(name, CASES["blink"][0][1])]
            owned[name.casefold()] = 1
        for i in range(10):
            name = "Payoff " + str(i)
            cards[name] = [card(name, CASES["blink"][1][1])]
            owned[name.casefold()] = 1
        report = MOD.analyze(cards, owned, theme="blink", limit=6)
        self.assertEqual(report["possible_pairs"], 200)
        self.assertEqual(report["returned_pairs"], 6)
        self.assertTrue(report["truncated"])
        self.assertEqual(len({x["source"] for x in report["pairs"]}), 6)

    def test_unknown_cards_and_conflicting_oracle(self):
        cards, owned, a, b = self.fixture("blink")
        cards[a] = [card(a, CASES["blink"][0][1]), card(a, "No relevant ability.")]
        owned["missing card"] = 2
        report = MOD.analyze(cards, owned, theme="blink")
        self.assertEqual(report["source_count"], 0)
        self.assertEqual(report["uncertainties"]["conflicting_oracle_variants"], 1)
        self.assertEqual(report["collection_coverage"]["distinct_owned_names_absent_from_oracle"], 1)

    def test_color_filter_and_any(self):
        cards, owned, a, b = self.fixture("blink")
        cards[b][0]["colorIdentity"] = ["U"]
        self.assertEqual(MOD.analyze(cards, owned, theme="blink", color_identity="B")["payoff_count"], 0)
        self.assertEqual(MOD.analyze(cards, owned, theme="blink", color_identity="ANY")["possible_pairs"], 1)

    def test_mutual_roles_do_not_pair_with_self(self):
        name = "Double Duty"
        text = "Sacrifice a creature: Draw a card.\nWhenever another creature dies, you gain 1 life."
        cards = {name: [card(name, text)]}
        report = MOD.analyze(cards, Counter({name.casefold(): 4}), theme="sacrifice")
        self.assertEqual(report["possible_pairs"], 0)
        self.assertEqual(report["returned_pairs"], 0)

    def test_cli_fixture_and_current_collection_csv(self):
        cards, owned, a, b = self.fixture("sacrifice")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            oracle = root / "oracle.json"
            collection = root / "collection.csv"
            output = root / "output.json"
            oracle.write_text(json.dumps({"data": cards, "meta": {"version": "fixture"}}), encoding="utf-8")
            collection.write_text("Name,Quantity\n"+a+",1\n"+b+",2\n", encoding="utf-8")
            self.assertEqual(MOD.main(["--oracle", str(oracle), "--collection", str(collection),
                                       "--theme", "sacrifice", "--output", str(output)]), 0)
            result = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(result["oracle_version"], "fixture")
            self.assertEqual(result["returned_pairs"], 1)
            self.assertEqual(result["collection_coverage"]["distinct_owned_names_absent_from_oracle"], 0)


if __name__ == "__main__":
    unittest.main()
