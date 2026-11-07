"""Synthetic CLI regressions distinguish unknown inventory from proven shortages."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
FRONT = 'Delver of Secrets'
BACK = 'Insectile Aberration'
FULL = FRONT + ' // ' + BACK


def fixture(layout='transform', front=FRONT, back=BACK):
    full = front + ' // ' + back
    common = {'name': full, 'layout': layout, 'supertypes': [],
              'colorIdentity': ['U'], 'manaValue': 1}
    a = dict(common, side='a', faceName=front, types=['Creature'],
             faceManaValue=1, manaCost='{U}', colors=['U'],
             text='At the beginning of your upkeep, you may look at the top card of your library.')
    b = dict(common, side='b', faceName=back, types=['Creature'],
             faceManaValue=0, colors=['U'], text='Flying')
    if layout == 'modal_dfc':
        b.update(types=['Land'], manaValue=0, text='{T}: Add {U}.')
    elif layout == 'adventure':
        b.update(types=['Instant'], manaCost='{U}', faceManaValue=1, text='Draw a card.')
    elif layout == 'split':
        a.update(types=['Instant'], manaValue=2)
        b.update(types=['Sorcery'], manaCost='{U}', faceManaValue=1, manaValue=2,
                 text='Draw a card.')
    elif layout == 'prepare':
        b.update(types=['Sorcery'], manaCost='{U}', faceManaValue=1, text='Draw a card.')
    island = {'name': 'Island', 'layout': 'normal', 'types': ['Land'],
              'supertypes': ['Basic'], 'colorIdentity': ['U'], 'manaValue': 0}
    bolt = {'name': 'Fixture Bolt', 'layout': 'normal', 'types': ['Instant'],
            'supertypes': [], 'colorIdentity': ['U'], 'manaValue': 1,
            'manaCost': '{U}', 'text': 'Draw a card.'}
    return {full: [a, b], 'Island': [island], 'Fixture Bolt': [bolt]}


class OwnershipEvidenceTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        self.oracle = self.directory / 'oracle.json'
        self.pool = self.directory / 'collection.csv'
        self.deck = self.directory / 'deck.txt'

    def run_tools(self, rows, entries, data=None):
        self.oracle.write_text(json.dumps(fixture() if data is None else data), encoding='utf-8')
        self.pool.write_text('Name,Quantity\n' + rows, encoding='utf-8')
        self.deck.write_text(entries, encoding='utf-8')
        direct = subprocess.run(
            [sys.executable, str(ROOT / 'validator/MTG_Deck_Validator_v1.1.1.py'),
             '--oracle', str(self.oracle), '--collection', str(self.pool),
             '--deck', str(self.deck), '--exact-60'],
            capture_output=True, text=True, timeout=15, check=False)
        self.assertFalse(direct.stderr, direct.stderr)
        report = json.loads(direct.stdout)
        self.assertEqual(direct.returncode,
                         {'PASS_WITH_LIMITATIONS': 0, 'UNVERIFIED': 3, 'FAIL': 1}[report['status']])
        gateway = subprocess.run(
            [sys.executable, str(ROOT / 'tools/agent_gateway.py'), 'validate',
             '--oracle', str(self.oracle),
             '--oracle-sha256', hashlib.sha256(self.oracle.read_bytes()).hexdigest(),
             '--collection', str(self.pool), '--collection-scope', 'synthetic',
             '--deck', str(self.deck), '--exact-60'],
            capture_output=True, text=True, timeout=15, check=False)
        self.assertFalse(gateway.stderr, gateway.stderr)
        wrapped = json.loads(gateway.stdout)
        self.assertEqual(wrapped['schema_version'], 1)
        self.assertEqual(wrapped['tool_execution'], 'EXECUTED')
        self.assertEqual(wrapped['child_exit_code'], direct.returncode)
        expected = {'PASS_WITH_LIMITATIONS': (0, 'VALIDATED_WITH_LIMITATIONS'),
                    'UNVERIFIED': (3, 'UNVERIFIED'), 'FAIL': (2, 'BLOCKED_INVALID_DECK')}
        self.assertEqual((gateway.returncode, wrapped['status']), expected[report['status']])
        for field in ('status', 'checks', 'failures', 'uncertainties',
                      'collection_coverage', 'identity_findings', 'collection_owned_copies',
                      'collection_owned_copies_basis'):
            self.assertEqual(wrapped['result'][field], report[field])
        return report

    def search(self, name=FRONT):
        result = subprocess.run(
            [sys.executable, str(ROOT / 'tools/card_search.py'), '--oracle', str(self.oracle),
             '--collection', str(self.pool), '--owned-only', '--name', name, '--format', 'json'],
            capture_output=True, text=True, timeout=15, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def assert_uncertain(self, report):
        self.assertEqual(report['status'], 'UNVERIFIED')
        self.assertEqual(report['checks']['ownership'], 'UNVERIFIED')
        self.assertFalse(report['failures'])
        self.assertTrue(report['uncertainties'])
        self.assertEqual(report['collection_coverage']['identity_status'], 'UNVERIFIED')

    def test_mixed_labels_quarantine_one_two_and_four_requested_copies(self):
        for quantity in (1, 2, 4):
            with self.subTest(quantity=quantity):
                report = self.run_tools(
                    f'{FRONT},2\n{FULL},2\n', f'{quantity} {FRONT}\n{60-quantity} Island\n')
                self.assert_uncertain(report)
                self.assertEqual(report['collection_owned_copies'], 4)
                self.assertEqual(report['collection_owned_copies_basis'],
                                 'RAW_DECLARED_CSV_QUANTITY_SUM_NOT_VERIFIED_PHYSICAL_TOTAL')
                self.assertEqual(report['checks']['copy_limit'], 'PASS')
                self.assertEqual(report['checks']['oracle_lookup'], 'PASS')
                self.assertEqual(report['identity_findings'][FRONT]['canonical_name'], FULL)
                discovered = self.search()
                self.assertEqual(discovered['results'], [])
                coverage = dict(discovered['collection_coverage'])
                expected = dict(report['collection_coverage'])
                # Card Search normalizes CSV label case before resolution.
                for field in ('unverified_owned_names', 'owned_names_absent_from_oracle'):
                    coverage[field] = [name.casefold() for name in coverage[field]]
                    expected[field] = [name.casefold() for name in expected[field]]
                self.assertEqual(coverage, expected)

    def test_proven_shortage_and_positive_canonical_inventory(self):
        shortage = self.run_tools(f'{FRONT},2\n', f'4 {FRONT}\n56 Island\n')
        self.assertEqual(shortage['checks']['ownership'], 'FAIL')
        self.assertTrue(any('Not enough owned copies' in value for value in shortage['failures']))
        self.assertIn('"owned": 2', ' '.join(shortage['failures']))
        sufficient = self.run_tools(f'{FULL},4\n', f'4 {FRONT}\n56 Island\n')
        self.assertEqual(sufficient['status'], 'PASS_WITH_LIMITATIONS')
        self.assertEqual(self.search()['results'][0]['owned_copies'], 4)

    def test_copy_limit_aggregates_deck_aliases_despite_uncertain_inventory(self):
        for quantity, expected in ((2, 'UNVERIFIED'), (3, 'FAIL')):
            with self.subTest(total=2+quantity):
                report = self.run_tools(f'{FRONT},2\n{FULL},2\n',
                                        f'2 {FRONT}\n{quantity} {FULL}\n{58-quantity} Island\n')
                self.assertEqual(report['status'], expected)
                self.assertEqual(report['checks']['ownership'], 'UNVERIFIED')
                self.assertEqual(report['checks']['copy_limit'], 'FAIL' if quantity == 3 else 'PASS')
                self.assertFalse(any('Not enough owned copies' in value for value in report['failures']))

    def test_independent_hard_failure_retains_overall_fail(self):
        rows = f'{FRONT},2\n{FULL},2\nFixture Bolt,1\n'
        report = self.run_tools(rows, f'4 {FRONT}\n55 Island\n')
        self.assertEqual(report['status'], 'FAIL')
        self.assertEqual(report['checks']['deck_size'], 'FAIL')
        self.assertEqual(report['checks']['ownership'], 'UNVERIFIED')
        report = self.run_tools(rows, f'4 {FRONT}\n2 Fixture Bolt\n54 Island\n')
        self.assertEqual(report['status'], 'FAIL')
        self.assertEqual(report['checks']['ownership'], 'FAIL')
        self.assertIn('Fixture Bolt', ' '.join(report['failures']))
        self.assertNotIn(f'"card": "{FULL}"', ' '.join(report['failures']))
        self.assertTrue(report['uncertainties'])

    def test_reverse_inventory_is_unverified_and_reverse_deck_stays_blocked(self):
        report = self.run_tools(f'{BACK},4\n', f'4 {FULL}\n56 Island\n')
        self.assert_uncertain(report)
        self.assertEqual(self.search()['results'], [])
        report = self.run_tools(f'{FULL},4\n', f'4 {BACK}\n56 Island\n')
        self.assertEqual(report['checks']['oracle_lookup'], 'FAIL')
        self.assertEqual(report['checks']['ownership'], 'UNVERIFIED')

    def test_ambiguous_alias_can_affect_several_canonical_candidates(self):
        data = fixture()
        second = fixture(front=FRONT, back='Other Reverse')
        data.update(second)
        for name in (FULL, FRONT + ' // Other Reverse'):
            with self.subTest(name=name):
                report = self.run_tools(f'{FRONT},4\n', f'4 {name}\n56 Island\n', data)
                self.assert_uncertain(report)

    def test_unrelated_unknown_inventory_does_not_poison_deck_checks(self):
        for quantity, expected in ((4, 'PASS_WITH_LIMITATIONS'), (2, 'FAIL')):
            with self.subTest(owned=quantity):
                report = self.run_tools(f'{FRONT},{quantity}\nUnrelated Unknown,9\n',
                                        f'4 {FRONT}\n56 Island\n')
                self.assertEqual(report['status'], expected)
                self.assertEqual(report['collection_coverage']['identity_status'], 'UNVERIFIED')

    def test_duplicate_rows_zero_aliases_and_blank_lines(self):
        report = self.run_tools(f'\n{FRONT},1\n{FRONT},1\n{FULL},0\n{BACK},0\n\n',
                                f'2 {FRONT}\n58 Island\n')
        self.assertEqual(report['status'], 'PASS_WITH_LIMITATIONS')
        self.assertEqual(report['collection_coverage']['identity_status'], 'MATCHED')
        shortage = self.run_tools(f'{FRONT},1\n{FRONT},1\n', f'4 {FRONT}\n56 Island\n')
        self.assertEqual(shortage['checks']['ownership'], 'FAIL')

    def test_verified_stock_is_sufficient_without_unproven_extra_labels(self):
        report = self.run_tools(f'{FULL},2\n{BACK},4\n', f'2 {FULL}\n58 Island\n')
        self.assertEqual(report['status'], 'PASS_WITH_LIMITATIONS')
        self.assertEqual(report['checks']['ownership'], 'PASS')
        self.assertEqual(report['collection_coverage']['identity_status'], 'UNVERIFIED')
        self.assertEqual(self.search()['results'][0]['owned_copies'], 2)
        report = self.run_tools(f'{FULL},2\n{BACK},4\n', f'4 {FULL}\n56 Island\n')
        self.assert_uncertain(report)

    def test_layouts_and_quoted_names_preserve_three_valued_stock(self):
        for layout in ('adventure', 'split', 'modal_dfc', 'prepare'):
            with self.subTest(layout=layout):
                front, back = 'Fixture, Visitor', 'Fixture Journey'
                full = front + ' // ' + back
                data = fixture(layout, front, back)
                report = self.run_tools(f'"{front}",2\n"{full}",2\n',
                                        f'4 {front}\n56 Island\n', data)
                self.assert_uncertain(report)
                report = self.run_tools(f'"{front}",2\n', f'4 {full}\n56 Island\n', data)
                self.assertEqual(report['checks']['ownership'], 'FAIL')
                report = self.run_tools(f'"{full}",4\n', f'4 {front}\n56 Island\n', data)
                self.assertEqual(report['status'], 'PASS_WITH_LIMITATIONS')

    def test_normal_single_face_control(self):
        report = self.run_tools('Fixture Bolt,2\nfixture bolt,2\n', '4 Fixture Bolt\n56 Island\n')
        self.assertEqual(report['status'], 'PASS_WITH_LIMITATIONS')
        report = self.run_tools('Fixture Bolt,2\n', '4 Fixture Bolt\n56 Island\n')
        self.assertEqual(report['checks']['ownership'], 'FAIL')

    def test_malformed_faces_cannot_authorize_ownership(self):
        data = deepcopy(fixture())
        data[FULL][1]['side'] = 'a'
        report = self.run_tools(f'{FRONT},4\n', f'4 {FRONT}\n56 Island\n', data)
        self.assertEqual(report['checks']['ownership'], 'UNVERIFIED')
        self.assertEqual(report['checks']['oracle_lookup'], 'FAIL')
        self.assertEqual(self.search()['results'], [])


if __name__ == '__main__':
    unittest.main()
