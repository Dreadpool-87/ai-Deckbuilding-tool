"""Offline tests for the independent MTGJSON card discovery tool."""
import contextlib
import gzip
import io
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("mtg_card_search", ROOT / "tools/card_search.py")
TOOL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(TOOL)


def card(name, text, keywords, *, identity=None, types=None, subtypes=None,
         mv=2, supertypes=None):
    return {
        "name": name, "text": text, "keywords": keywords,
        "colorIdentity": identity if identity is not None else ["B"],
        "types": types if types is not None else ["Creature"],
        "subtypes": subtypes if subtypes is not None else ["Snake"],
        "manaValue": mv, "supertypes": supertypes if supertypes is not None else [],
    }


class CardSearchTests(unittest.TestCase):
    def setUp(self):
        self.cards = {
            "Fynn, the Fangbearer": [card(
                "Fynn, the Fangbearer", "Deathtouch\nWhenever a creature with deathtouch you control deals combat damage to an opponent, that player gets a poison counter.",
                ["Deathtouch"], identity=["G"], mv=2)],
            "Grave Viper": [card(
                "Grave Viper", "Reach, deathtouch", ["Reach", "Deathtouch"], mv=3)],
            "Gift of Poison": [card(
                "Gift of Poison", "Target tapped creature gains deathtouch until end of turn.",
                ["Deathtouch"], types=["Instant"], subtypes=[], mv=1)],
            "Elvish Mystic": [card(
                "Elvish Mystic", "{T}: Add {G}.", [], identity=["G"],
                subtypes=["Elf", "Druid"], mv=1)],
            "Swamp": [card("Swamp", "{T}: Add {B}.", [], identity=[],
                           types=["Land"], subtypes=["Swamp"], supertypes=["Basic"], mv=0)],
            "Conflicted Snake": [
                card("Conflicted Snake", "Deathtouch", ["Deathtouch"]),
                card("Conflicted Snake", "Flying", ["Flying"]),
            ],
            "Unknown Ability": [card("Unknown Ability", None, ["Deathtouch"])],
        }

    def test_printed_deathtouch_does_not_include_granters(self):
        result = TOOL.search(self.cards, abilities=["Deathtouch"], card_type="Creature")
        self.assertEqual([x["name"] for x in result["results"]],
                         ["Fynn, the Fangbearer", "Grave Viper"])
        self.assertEqual(result["coverage"]["uncertain_variant_matches"], 2)

    def test_keyword_metadata_can_include_granters(self):
        result = TOOL.search(self.cards, keywords=["Deathtouch"])
        self.assertIn("Gift of Poison", [x["name"] for x in result["results"]])

    def test_oracle_text_matches_granting_spells(self):
        result = TOOL.search(self.cards, oracle_text=["gains deathtouch"])
        self.assertEqual([x["name"] for x in result["results"]], ["Gift of Poison"])

    def test_composable_filters(self):
        r = TOOL.search(self.cards, abilities=["Deathtouch"], color_identity="BG",
                        max_mv=2)
        self.assertEqual([c["name"] for c in r["results"]], ["Fynn, the Fangbearer"])

    def test_subtype_name_minimum_mana(self):
        r = TOOL.search(self.cards, subtype="Elf", name="MYSTIC", min_mv=1)
        self.assertEqual([c["name"] for c in r["results"]], ["Elvish Mystic"])

    def test_owned_only_uses_exact_collection(self):
        owned = TOOL.Counter({"grave viper": 2, "gift of poison": 1})
        r = TOOL.search(self.cards, keywords=["Deathtouch"], collection=owned, owned_only=True)
        self.assertEqual([x["name"] for x in r["results"]], ["Gift of Poison", "Grave Viper"])
        self.assertEqual(r["results"][1]["owned_copies"], 2)

    def test_basic_land_unlimited_policy(self):
        owned = TOOL.Counter()
        r = TOOL.search(self.cards, card_type="Land", owned_only=True, collection=owned)
        self.assertEqual([x["name"] for x in r["results"]], ["Swamp"])
        self.assertTrue(r["results"][0]["unlimited_basic_by_project_policy"])

    def test_different_printings_not_arbitrarily_selected(self):
        r = TOOL.search(self.cards, abilities=["Deathtouch"])
        self.assertNotIn("Conflicted Snake", [x["name"] for x in r["results"]])
        self.assertEqual(r["coverage"]["uncertain_variant_matches"], 2)

    def test_search_requires_filter(self):
        with self.assertRaisesRegex(ValueError, "at least one"):
            TOOL.search(self.cards)

    def test_owned_only_needs_collection(self):
        with self.assertRaisesRegex(ValueError, "requires --collection"):
            TOOL.search(self.cards, abilities=["Deathtouch"], owned_only=True)

    def test_invalid_limit_mana_and_colors(self):
        for kwargs in ({"limit": 0}, {"min_mv": 5, "max_mv": 1},
                       {"color_identity": "Blue"}, {"min_mv": -1}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                TOOL.search(self.cards, name="a", **kwargs)

    def test_result_limit_tracks_true_total(self):
        r = TOOL.search(self.cards, abilities=["Deathtouch"], limit=1)
        self.assertEqual(r["total_matches"], 2)
        self.assertEqual(r["returned_count"], 1)
        self.assertEqual(r["status"], "SEARCH_RESULTS_NOT_A_CONSTRUCTED_DECK")

    def test_collection_csv_duplicates_and_errors(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "owned.csv"
            path.write_text("Name,Quantity\nGrave Viper,2\ngrave viper,3\n", encoding="utf-8")
            self.assertEqual(TOOL.read_collection(path)["grave viper"], 5)
            path.write_text("Name,Quantity\nGrave Viper,-2\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                TOOL.read_collection(path)

    def test_tribal_subtype_and_oracle_evidence_are_separate(self):
        self.cards["Fixture Recruiter"] = [card(
            "Fixture Recruiter", "Other Elves you control get +1/+1.", [],
            subtypes=["Human"])]
        self.cards["Fixture Vanilla Elf"] = [card(
            "Fixture Vanilla Elf", None, [], subtypes=["Elf"])]
        self.cards["Fixture Kindred Spell"] = [card(
            "Fixture Kindred Spell", None, [], types=["Kindred", "Instant"],
            subtypes=["Elf"])]
        rows = {row["name"]: row for row in TOOL.search(
            self.cards, theme="Elf tribal")["results"]}
        self.assertEqual(set(rows), {"Elvish Mystic", "Fixture Vanilla Elf", "Fixture Recruiter"})
        self.assertEqual(rows["Elvish Mystic"]["theme_match_basis"], ["CREATURE_SUBTYPE"])
        self.assertEqual(rows["Fixture Recruiter"]["theme_match_basis"], ["ORACLE_TEXT"])
        self.assertEqual(rows["Fixture Vanilla Elf"]["role_evidence"]["core"]["confidence"],
                         "HEURISTIC")
        self.assertEqual(rows["Fixture Vanilla Elf"]["role_evidence"]["core"]["basis"],
                         "CREATURE_SUBTYPE")
        self.assertEqual(rows["Fixture Recruiter"]["role_evidence"]["synergy"]["basis"],
                         "ORACLE_TEXT")
        self.assertEqual(TOOL.search(self.cards, name="Fynn", theme="Deathtouch")
                         ["results"][0]["role_evidence"]["payoff"]["basis"], "DIRECT_SYNERGY_CANDIDATE")

    def test_tribal_payoff_does_not_match_substring_in_unrelated_trigger(self):
        data = {"Fixture Scribe": [card(
            "Fixture Scribe",
            "Whenever you target yourself, draw a card.\nCreate an Elf token.",
            [], subtypes=["Human"])]}
        result = TOOL.search(data, theme="Elf tribal")["results"][0]
        self.assertNotIn("payoff", result["roles"])
        self.assertEqual(result["theme_match_basis"], ["ORACLE_TEXT"])

    def test_face_names_resolve_to_one_card_without_inventing_face_data(self):
        for layout in ("split", "modal_dfc", "transform", "adventure", "flip", "prepare"):
            with self.subTest(layout=layout):
                full = "Fixture Front // Fixture Reverse"
                variants = [
                    dict(card(full, "Flying", ["Flying"]), layout=layout,
                         faceName="Fixture Front", side="a"),
                    dict(card(full, "Trample", ["Trample"]), layout=layout,
                         faceName="Fixture Reverse", side="b"),
                ]
                owned = TOOL.Counter({"fixture front": 2})
                result = TOOL.search({full: variants}, name="Fixture Reverse", collection=owned,
                                     owned_only=True)
                self.assertEqual([(row["name"], row["owned_copies"]) for row in result["results"]],
                                 [(full, 2)])
                self.assertEqual(result["collection_coverage"]["unresolved_name_count"], 0)
                filtered = TOOL.search({full: variants}, name="Fixture Front", abilities=["Flying"])
                self.assertEqual(filtered["results"], [])
                self.assertEqual(filtered["coverage"]["uncertain_variant_matches"], 1)

    def test_ambiguous_faces_and_missing_face_metadata_do_not_establish_ownership(self):
        first = "Fixture Front // Shared Face"
        second = "Other Front // Shared Face"
        incomplete = "Unknown Front // Undeclared Face"
        data = {
            first: [dict(card(first, "", []), faceName="Shared Face", layout="split")],
            second: [dict(card(second, "", []), faceName="Shared Face", layout="transform")],
            incomplete: [dict(card(incomplete, "", []), layout="split")],
        }
        for name in ("shared face", "undeclared face"):
            with self.subTest(name=name):
                report = TOOL.search(data, name=name, collection=TOOL.Counter({name: 2}),
                                     owned_only=True)
                self.assertEqual(report["results"], [])
                self.assertEqual(report["name_identity"]["status"], "UNVERIFIED")
                self.assertEqual(report["collection_coverage"]["identity_status"], "UNVERIFIED")
                self.assertEqual(report["collection_coverage"]["unverified_owned_names"], [name])
        self.assertEqual(TOOL.search(data, name="Fixture Front//Shared Face")["results"][0]["name"],
                         first)
        data["Shared Face"] = [card("Shared Face", "", [])]
        self.assertEqual(TOOL.search(data, name="Shared Face")["results"], [])

    def test_contradictory_atomic_names_block_face_and_full_ownership(self):
        full = "Fixture Front // Fixture Reverse"
        data = {full: [
            dict(card(full, "", []), faceName="Fixture Front", layout="transform"),
            dict(card("Unrelated Card", "", []), faceName="Fixture Reverse", layout="transform"),
        ]}
        report = TOOL.search(data, name="Fixture Front", collection=TOOL.Counter({
            "fixture front": 2, full.casefold(): 1,
        }), owned_only=True)
        self.assertEqual(report["results"], [])
        self.assertEqual(report["name_identity"]["status"], "UNVERIFIED")
        self.assertEqual(report["collection_coverage"]["unresolved_name_count"], 2)

    def test_contradictory_or_unsupported_face_metadata_blocks_alias_ownership(self):
        full = "Fixture Front // Fixture Reverse"
        front = dict(card(full, "", []), faceName="Fixture Front", layout="transform", side="a")
        back = dict(card(full, "", []), faceName="Fixture Reverse", layout="transform", side="b")
        for variants in (
            [front, dict(back, side="a")],
            [front, dict(back, layout="split")],
            [front, dict(back, faceName="Unrelated Face")],
            [dict(front, layout="normal")],
            [dict(front, side="b")],
        ):
            with self.subTest(variants=variants):
                result = TOOL.search({full: variants}, name="Fixture Front", owned_only=True,
                                     collection=TOOL.Counter({"fixture front": 1}))
                self.assertEqual(result["results"], [])
                self.assertEqual(result["name_identity"]["status"], "UNVERIFIED")
                self.assertEqual(result["collection_coverage"]["unresolved_name_count"], 1)
        slim = dict(card(full, "", []), faceName="Fixture Front")
        report = TOOL.search({full: [slim]}, name="Fixture Front", owned_only=True,
                             collection=TOOL.Counter({"fixture front": 1}))
        self.assertEqual(report["results"], [])
        self.assertEqual(report["collection_coverage"]["identity_status"], "UNVERIFIED")

    def test_contradictory_record_name_contends_with_other_canonical_key(self):
        data = {
            "Fixture Alpha": [card("Fixture Alpha", "", [])],
            "Fixture Beta": [card("Fixture Alpha", "", [])],
        }
        report = TOOL.search(data, name="Fixture Alpha", owned_only=True,
                             collection=TOOL.Counter({"fixture alpha": 1}))
        self.assertEqual(report["results"], [])
        self.assertEqual(report["name_identity"]["candidate_names"], ["Fixture Alpha", "Fixture Beta"])
        self.assertEqual(report["collection_coverage"]["unresolved_name_count"], 1)

    def test_csv_diagnostics_fail_closed_and_include_physical_line(self):
        cases = {
            "Name,Quantity\n,\n": "line 2.*Name",
            "Name,Quantity\nFixture,-2\n": "line 2.*Quantity",
            "Name,Quantity\nFixture\n": "line 2.*fields",
            "Name,Quantity\nFixture,1,unexpected\n": "line 2.*fields",
            'Name,Quantity\n"unclosed,1\n': "line 2.*unexpected end",
            'Name,Quantity\n"Two\nLine",1\nBad,no\n': "line 4.*Quantity",
            "Name,Quantity,Quantity\nFixture,1,2\n": "line 1.*duplicate",
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "owned.csv"
            for contents, pattern in cases.items():
                with self.subTest(contents=contents):
                    path.write_text(contents, encoding="utf-8")
                    with self.assertRaisesRegex(ValueError, pattern):
                        TOOL.read_collection(path)

    def test_invalid_oracle_color_shape_does_not_claim_identity(self):
        malformed = card("Broken Color", "", [], identity=[["B"]])
        result = TOOL.search({"Broken Color": [malformed]}, name="Broken")
        self.assertIsNone(result["results"][0]["color_identity"])

    def test_malformed_collection_cli_does_not_write_results(self):
        with tempfile.TemporaryDirectory() as tmp:
            oracle, collection, output = [Path(tmp) / name
                                          for name in ("oracle.json", "owned.csv", "result.json")]
            oracle.write_text(json.dumps({"data": self.cards}), encoding="utf-8")
            collection.write_text("Name,Quantity\nGrave Viper,1\n,\n", encoding="utf-8")
            with contextlib.redirect_stderr(io.StringIO()) as stderr:
                result = TOOL.main(["--oracle", str(oracle), "--collection", str(collection),
                                    "--owned-only", "--name", "Viper", "--output", str(output)])
            self.assertEqual(result, 2)
            self.assertIn("line 3: Name is empty", stderr.getvalue())
            self.assertFalse(output.exists())

    def test_atomic_rejects_duplicate_canonical_keys_and_metadata_fields(self):
        cases = (
            ('{"data":{"Fixture":[],"Fixture":[]}}', "Fixture"),
            ('{"data":{"Fixture":[{"faceName":"First","faceName":"Second"}]}}', "faceName"),
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "AtomicCards.json"
            for contents, key in cases:
                with self.subTest(key=key):
                    path.write_text(contents, encoding="utf-8")
                    with self.assertRaisesRegex(ValueError, "Duplicate Oracle JSON key.*" + key):
                        TOOL.read_atomic(path)

    def test_atomic_gzip_load(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "AtomicCards.json.gz"
            with gzip.open(path, "wt", encoding="utf-8") as f:
                json.dump({"meta": {"version": "test-1"}, "data": self.cards}, f)
            db, metadata = TOOL.read_atomic(path)
            self.assertEqual(metadata["version"], "test-1")
            self.assertEqual(len(db), len(self.cards))

    def test_human_report_not_decklist(self):
        r = TOOL.search(self.cards, abilities=["Deathtouch"], limit=2)
        output = TOOL.human_report(r)
        self.assertIn("NOT a deck", output)
        self.assertIn("Fynn, the Fangbearer", output)

    def test_cli_generates_json_result(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "AtomicCards.json"
            dest = Path(tmp) / "report.json"
            path.write_text(json.dumps({"data": self.cards, "meta": {"version": "test"}}))
            exitcode = TOOL.main(["--oracle", str(path), "--ability", "Deathtouch",
                                  "--type", "Creature", "--format", "json",
                                  "--output", str(dest)])
            self.assertEqual(exitcode, 0)
            output = json.loads(dest.read_text())
            self.assertEqual(output["total_matches"], 2)
            self.assertEqual(output["oracle_version"], "test")


if __name__ == "__main__":
    unittest.main()
