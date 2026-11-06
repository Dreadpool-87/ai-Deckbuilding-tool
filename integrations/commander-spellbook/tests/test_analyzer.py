import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

HERE = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('spellbook_analyzer', HERE / 'analyze.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def variant(id, uses, **kw):
    return dict(id=id, uses=[dict(card={'name': k}, quantity=v) for k, v in uses.items()],
                status='OK', requires=[], produces=[{'feature': {'name': 'Win the game'}}],
                identity='R', spoiler=False, popularity=1, **kw)


class ComboAnalysisTests(unittest.TestCase):
    def setUp(self):
        self.deck = module.Counter({'Mountain': 97, 'Commander X': 1, 'Combo A': 1, 'Combo B': 1})
        self.document = {'timestamp': '2026-10-14', 'version': 'test', 'variants': [
            variant('complete', {'Combo A': 1, 'Combo B': 1}),
            variant('near', {'Combo A': 1, 'Missing Piece': 1}),
            variant('double', {'Combo A': 1, 'Combo B': 2}),
            variant('absent', {'Missing 1': 1, 'Missing 2': 1}),
        ]}

    def analyze(self, **kwargs):
        return module.analyze(self.deck, module.Counter({'Commander X': 1}), self.document,
                              identity='R', **kwargs)

    def test_exact_and_near_and_repeated_quantity(self):
        o = self.analyze()
        self.assertEqual([v['variant_id'] for v in o['exact_card_ingredient_candidates']], ['complete'])
        self.assertEqual([v['variant_id'] for v in o['one_card_missing_candidates']], ['double', 'near'])
        self.assertEqual(o['total_one_card_missing_candidates'], 2)
        self.assertEqual(o['one_card_missing_candidates'][0]['missing_cards'], {'Combo B': 1})

    def test_template_never_declared_complete(self):
        v = variant('template', {'Combo A': 1})
        v['requires'] = [{'template': {'name': 'Any creature'}, 'quantity': 1}]
        self.document['variants'] = [v]
        r = self.analyze()
        self.assertEqual(r['total_exact_card_ingredient_candidates'], 0)
        self.assertEqual(r['counts']['template_variants_unverified'], 1)

    def test_status_example_public_and_draft_excluded(self):
        a, b = variant('example', {'Combo A': 1}), variant('draft', {'Combo B': 1})
        a['status'], b['status'] = 'E', 'D'
        self.document['variants'] = [a, b]
        self.assertEqual([x['variant_id'] for x in self.analyze()['exact_card_ingredient_candidates']], ['example'])

    def test_reject_mismatched_commander(self):
        a = variant('commander-only', {'Combo A': 1})
        a['uses'][0]['mustBeCommander'] = True
        self.document['variants'] = [a]
        self.assertEqual(self.analyze()['total_exact_card_ingredient_candidates'], 0)

    def test_identity_restricted(self):
        self.document['variants'][0]['identity'] = 'UB'
        r = self.analyze()
        self.assertEqual(r['total_exact_card_ingredient_candidates'], 0)
        self.assertEqual(r['counts']['outside_selected_identity'], 1)

    def test_unprovided_identity_is_explicit(self):
        r = module.analyze(self.deck, module.Counter(), self.document)
        self.assertIn('color_identity_not_provided', r['exact_card_ingredient_candidates'][0]['unverified_conditions'])
        self.assertIsNone(r['commander'])

    def test_duplicates_and_unknown_names(self):
        v = variant('repeat', {'Combo A': 1})
        v['uses'].append({'card': {'name': 'Combo A'}, 'quantity': 2})
        self.document['variants'] = [v]
        self.assertEqual(self.analyze()['total_exact_card_ingredient_candidates'], 0)

    def test_invalid_schema_skipped(self):
        self.document['variants'] = [variant('bad', {'Combo A': 1})]
        self.document['variants'][0]['uses'][0]['quantity'] = '1'
        self.assertEqual(self.analyze()['counts']['invalid_variants'], 1)

    def test_limit_does_not_lie_about_total(self):
        r = self.analyze(limit=0)
        self.assertEqual(len(r['exact_card_ingredient_candidates']), 0)
        self.assertEqual(r['total_exact_card_ingredient_candidates'], 1)

    def test_reject_wrong_commander_override(self):
        with self.assertRaises(ValueError):
            self.analyze(commander='Other Commander')

    def test_deck_sections_and_totals(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'deck.txt'
            p.write_text('Commander\n1 Commander X\nDeck\n98 Mountain\n1 Combo A\n', encoding='utf-8')
            cards, commander = module.read_deck(p)
            self.assertEqual(sum(cards.values()), 100)
            self.assertEqual(commander, {'Commander X': 1})

    def test_reject_sideboard(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'deck.txt'
            p.write_text('1 Test\nSideboard\n1 Evil', encoding='utf-8')
            with self.assertRaises(ValueError):
                module.read_deck(p)

    def test_file_io_snapshot_json_and_gz(self):
        import gzip
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'db.json.gz'
            with gzip.open(p, 'wt', encoding='utf-8') as f:
                json.dump(self.document, f)
            self.assertEqual(module.load_snapshot(p)['version'], 'test')

    def test_missing_variants_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'db.json'
            p.write_text('{}')
            with self.assertRaises(ValueError):
                module.load_snapshot(p)


if __name__ == '__main__':
    unittest.main()
