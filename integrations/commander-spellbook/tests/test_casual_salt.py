"""Spellbook offline adapter: synthetic casual 60, collection and salt regressions."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from collections import Counter


MODULE_PATH = Path(__file__).resolve().parents[1] / 'analyze.py'
SPEC = importlib.util.spec_from_file_location('spellbook_casual_salt', MODULE_PATH)
MOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)


def variant(key, requirements, *, salt=None, votes=None, commander=False):
    return {
        'id': key, 'status': 'OK', 'spoiler': False, 'requires': [],
        'uses': [
            {'card': {'name': name}, 'quantity': qty,
             **({'mustBeCommander': True} if commander and idx == 0 else {})}
            for idx, (name, qty) in enumerate(requirements.items())
        ],
        'produces': [{'feature': {'name': 'Infinite mana'}}],
        'salt': salt, 'saltVoteCount': votes, 'identity': 'BW',
        'description': 'Repeat the activated ability, with prerequisites.',
        'notablePrerequisites': 'The cards must be on the battlefield.',
        'popularity': 3,
    }


class CasualSaltTests(unittest.TestCase):
    def setUp(self):
        self.deck = Counter({'Plains': 56, 'Combo A': 2, 'Combo B': 2})
        self.data = {'timestamp': 'fixture-time', 'version': 'fixture', 'variants': [
            variant('normal', {'Combo A': 1, 'Combo B': 1}, salt=2.5, votes=7),
            variant('commander-only', {'Combo A': 1}, commander=True),
            variant('one-missing', {'Combo A': 1, 'Combo C': 1}, salt=None),
        ]}

    def test_exact_and_missing_on_casual_60(self):
        r = MOD.analyze(self.deck, Counter(), self.data, scope='casual60')
        self.assertEqual(r['analysis_scope'], 'casual60')
        self.assertEqual([x['variant_id'] for x in r['exact_card_ingredient_candidates']], ['normal'])
        self.assertEqual([x['variant_id'] for x in r['one_card_missing_candidates']], ['one-missing'])
        self.assertEqual(r['counts']['requires_commander_excluded'], 1)
        self.assertIsNone(r['commander'])

    def test_no_commander_and_not_60_rejected(self):
        with self.assertRaisesRegex(ValueError, 'exactly 60'):
            MOD.analyze(Counter({'Plains': 59}), Counter(), self.data, scope='casual60')
        with self.assertRaisesRegex(ValueError, 'must not specify a Commander'):
            MOD.analyze(self.deck, Counter({'Combo A': 1}), self.data, scope='casual60')
        with self.assertRaisesRegex(ValueError, 'identity'):
            MOD.analyze(self.deck, Counter(), self.data, scope='casual60', identity='WB')

    def test_combo_salt_score_not_a_card_score(self):
        r = MOD.analyze(self.deck, Counter(), self.data, scope='casual60')
        combo = r['exact_card_ingredient_candidates'][0]
        self.assertEqual(combo['combo_salt']['score'], 2.5)
        self.assertEqual(combo['combo_salt']['vote_count'], 7)
        self.assertEqual(combo['card_salt'], {})
        self.assertEqual(combo['combo_salt']['scale'], [0, 4])
        self.assertIn('not win rate', combo['combo_salt']['meaning'])

    def test_undefined_and_invalid_salt_not_zero(self):
        for score in (None, True, 6, '3'):
            d = {'variants': [variant('x', {'Combo A': 1}, salt=score)]}
            r = MOD.analyze(self.deck, Counter(), d, scope='casual60')
            self.assertIsNone(r['exact_card_ingredient_candidates'][0]['combo_salt']['score'])

    def test_mixed_case_collection_ingredients(self):
        inventory = Counter({'combo a': 2, 'COMBO B': 1})
        d = {'variants': [variant('x', {'Combo A': 1, 'Combo B': 1})]}
        r = MOD.analyze(inventory, Counter(), d, scope='collection')
        self.assertEqual(r['total_exact_card_ingredient_candidates'], 1)
        self.assertEqual(r['analysis_scope'], 'collection')

    def test_card_salt_requires_attribution(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'scores.csv'
            p.write_text('Name,SaltScore,Source,AsOf\nCombo A,2.0,Example User-Supplied Survey,2026-10-01\n', encoding='utf-8')
            scores = MOD.read_card_salt_csv(p)
            self.assertEqual(scores['combo a']['source'], 'Example User-Supplied Survey')
            r = MOD.analyze(self.deck, Counter(), self.data,
                            scope='casual60', card_salt_scores=scores)
            result = r['exact_card_ingredient_candidates'][0]
            self.assertEqual(result['card_salt']['Combo A']['score'], 2.0)
            self.assertEqual(result['combo_salt']['score'], 2.5)
            p.write_text('Name,SaltScore,Source\nCombo A,9,Example\n', encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'outside 0..4'):
                MOD.read_card_salt_csv(p)
            p.write_text('Name,SaltScore,Source\nCombo A,2,\n', encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'Source required'):
                MOD.read_card_salt_csv(p)

    def test_collection_reader_reuses_card_search(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'owned.csv'
            path.write_text('Name,Quantity\nCombo A,2\nCombo A,1\nCombo B,1\n', encoding='utf-8')
            result = MOD.read_owned_collection(path)
            self.assertEqual(result['combo a'], 3)
            self.assertEqual(result['combo b'], 1)

    def test_joint_combo_and_lifegain_synergy_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            deck = root / 'deck.txt'
            spellbook = root / 'spellbook.json'
            oracle = root / 'oracle.json'
            output = root / 'joint.json'
            deck.write_text('56 Plains\n2 Combo A\n2 Combo B\n', encoding='utf-8')
            spellbook.write_text(json.dumps(self.data), encoding='utf-8')
            def card(name, rules):
                return {
                    'name': name, 'text': rules, 'keywords': [],
                    'types': ['Creature'], 'subtypes': [], 'supertypes': [],
                    'manaValue': 2, 'colorIdentity': ['W'],
                }
            oracle.write_text(json.dumps({'data': {
                'Combo A': [card('Combo A', 'Whenever another creature enters, you gain 1 life.')],
                'Combo B': [card('Combo B', 'Whenever you gain life, put a +1/+1 counter on Combo B.')],
                'Plains': [dict(card('Plains', '{T}: Add {W}.'), types=['Land'], supertypes=['Basic'])],
            }, 'meta': {'version': 'synthetic'}}), encoding='utf-8')
            args = ['--deck', str(deck), '--snapshot', str(spellbook),
                    '--mode', 'casual60', '--oracle', str(oracle),
                    '--theme', 'lifegain', '--output', str(output)]
            self.assertEqual(MOD.main(args), 0)
            result = json.loads(output.read_text(encoding='utf-8'))
            self.assertEqual(result['total_exact_card_ingredient_candidates'], 1)
            self.assertEqual(result['theme_candidates']['total_matches'], 2)
            self.assertEqual(result['theme_candidates']['synergy_analysis']['returned_pairs'], 1)
            self.assertEqual(result['theme_candidates']['inventory_name_coverage']
                             ['distinct_names_not_in_oracle'], 0)
            self.assertEqual(MOD.main(['--deck', str(deck), '--snapshot', str(spellbook),
                                       '--mode', 'casual60', '--oracle', str(oracle)]), 2)

    def test_cli_realistic_json_without_private_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            deck = root/'deck.txt'
            snapshot = root/'variants.json'
            output = root/'result.json'
            deck.write_text('56 Plains\n2 Combo A\n2 Combo B\n', encoding='utf-8')
            snapshot.write_text(json.dumps(self.data), encoding='utf-8')
            self.assertEqual(MOD.main(['--deck', str(deck), '--mode', 'casual60',
                                      '--snapshot', str(snapshot), '--output', str(output)]), 0)
            report = json.loads(output.read_text(encoding='utf-8'))
            self.assertEqual(report['analysis_scope'], 'casual60')
            self.assertEqual(report['total_exact_card_ingredient_candidates'], 1)
            self.assertEqual(report['input_type'], 'decklist_txt')
            self.assertNotIn('deck_path', report)
            self.assertNotIn(str(root), output.read_text(encoding='utf-8'))
            self.assertEqual(MOD.main(['--deck', str(deck), '--mode', 'collection',
                                      '--snapshot', str(snapshot)]), 2)


if __name__ == '__main__':
    unittest.main()
