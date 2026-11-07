"""Cross-tool regressions with synthetic ownership and Atomic-style face records."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / 'validator/MTG_Deck_Validator_v1.1.1.py'
validate = runpy.run_path(str(VALIDATOR))['validate']
search = runpy.run_path(str(ROOT / 'tools/card_search.py'))['search']
FRONT = 'Fixture Front'
BACK = 'Fixture Back'
FULL = f'{FRONT} // {BACK}'
ISLAND = {'name': 'Island', 'layout': 'normal', 'types': ['Land'],
          'supertypes': ['Basic'], 'colorIdentity': ['U'], 'manaValue': 0}


def oracle(layout='transform'):
    a = {'name': FULL, 'side': 'a', 'faceName': FRONT, 'layout': layout,
         'types': ['Creature'], 'colorIdentity': ['U'], 'manaValue': 1,
         'faceManaValue': 1, 'manaCost': '{U}', 'text': 'Flying'}
    b = dict(a, side='b', faceName=BACK, types=['Land'], manaCost=None,
             faceManaValue=0, text='')
    if layout == 'modal_dfc':
        b['manaValue'] = 0
    return {'Island': [ISLAND], FULL: [a, b]}


class PhysicalIdentityTests(unittest.TestCase):
    def test_front_alias_and_combined_name_share_copy_limit(self):
        for layout in ('transform', 'modal_dfc', 'adventure', 'flip'):
            data = oracle(layout)
            owned = Counter({FRONT: 5})
            report = validate(owned, data, Counter({FULL: 2, FRONT: 2, 'Island': 56}))
            self.assertEqual(report['status'], 'PASS_WITH_LIMITATIONS')
            self.assertEqual(report['lands_physical'], 56)
            self.assertEqual(report['mana_curve_nonlands'], {'1': 4})
            self.assertEqual(report['printed_mana_costs'], {FULL: '{U}', 'Island': None})
            report = validate(owned, data, Counter({FULL: 2, FRONT: 3, 'Island': 55}))
            self.assertEqual(report['checks']['copy_limit'], 'FAIL')

    def test_mixed_inventory_names_never_add_and_back_is_not_ownership(self):
        data = oracle()
        for owned in (Counter({FRONT: 2, FULL: 2}), Counter({BACK: 4})):
            deck = Counter({FULL: 4, 'Island': 56})
            self.assertNotEqual(validate(owned, data, deck)['status'], 'PASS_WITH_LIMITATIONS')
            result = search(data, name=FRONT, collection=owned, owned_only=True)
            self.assertEqual(result['results'], [])
            self.assertEqual(result['collection_coverage']['identity_status'], 'UNVERIFIED')

    def test_back_name_is_discoverable_but_cannot_be_a_deck_entry(self):
        data = oracle()
        self.assertEqual(search(data, name=BACK)['results'][0]['name'], FULL)
        report = validate(Counter({FULL: 4}), data, Counter({BACK: 4, 'Island': 56}))
        self.assertNotEqual(report['status'], 'PASS_WITH_LIMITATIONS')

    def test_reversible_basics_do_not_shadow_ordinary_basics(self):
        data = oracle()
        name = 'Island // Island'
        data[name] = [dict(ISLAND, name=name, faceName='Island', side=side,
                           layout='reversible_card') for side in ('a', 'b')]
        report = validate(Counter({FRONT: 4}), data, Counter({FRONT: 4, 'Island': 56}))
        self.assertEqual(report['status'], 'PASS_WITH_LIMITATIONS')
        self.assertEqual(report['lands_physical'], 56)
        report = validate(Counter(), data, Counter({name: 60}))
        self.assertEqual(report['identity_findings'][name]['status'], 'UNSUPPORTED_LAYOUT')

    def test_single_key_cannot_claim_multiface_characteristics(self):
        data = oracle()
        data['Bad'] = [dict(ISLAND, name='Bad', layout='modal_dfc')]
        report = validate(Counter({'Bad': 1}), data, Counter({'Bad': 1, 'Island': 59}))
        self.assertNotEqual(report['status'], 'PASS_WITH_LIMITATIONS')
        self.assertIsNone(report['lands_physical'])

    def test_front_display_does_not_depend_on_record_order(self):
        data = oracle('modal_dfc')
        data[FULL].reverse()
        row = search(data, name=BACK)['results'][0]
        self.assertEqual((row['types'], row['mana_value'], row['oracle_text']),
                         (['Creature'], 1, 'Flying'))
        data[FULL] = data[FULL][1:]
        report = search(data, name=FRONT)
        self.assertEqual(report['results'], [])
        self.assertEqual(report['name_identity']['status'], 'UNVERIFIED')

    def test_malformed_front_facts_cannot_pass_commander(self):
        for malformed in ({'supertypes': 'Not Legendary'},
                          {'faceManaValue': True}, {'manaCost': ''},
                          {'leadershipSkills': {'commander': 'yes'}}):
            with self.subTest(malformed=malformed):
                data = oracle()
                data[FULL][0].update(malformed)
                report = validate(Counter({FRONT: 1}), data,
                                  Counter({FRONT: 1, 'Island': 99}),
                                  mode='commander', commander=FRONT)
                self.assertNotEqual(report['status'], 'PASS_WITH_LIMITATIONS')
                self.assertIsNone(report['lands_physical'])

    def test_split_uses_combined_mana_value_and_both_costs(self):
        data = oracle('split')
        a, b = data[FULL]
        a.update(types=['Instant'], manaValue=3)
        b.update(types=['Sorcery'], manaValue=3, faceManaValue=2, manaCost='{1}{U}')
        report = validate(Counter({FULL: 4}), data, Counter({FULL: 4, 'Island': 56}))
        self.assertEqual(report['status'], 'PASS_WITH_LIMITATIONS')
        self.assertEqual(report['mana_curve_nonlands'], {'3': 4})
        self.assertEqual(report['printed_mana_costs'][FULL], '{U} // {1}{U}')
        self.assertEqual(report['card_types_overlapping']['Sorcery'], 4)
        b['colorIdentity'] = ['R']
        report = validate(Counter({FULL: 4}), data, Counter({FULL: 4, 'Island': 56}))
        self.assertEqual(report['status'], 'UNVERIFIED')
        self.assertIsNone(report['lands_physical'])

    def test_commander_front_alias_rechecks_shared_color_identity(self):
        data = oracle()
        a, b = data[FULL]
        a.update(supertypes=['Legendary'], leadershipSkills={'commander': True})
        data['Red Spell'] = [{'name': 'Red Spell', 'colorIdentity': ['R'], 'manaValue': 1,
                              'types': ['Instant'], 'manaCost': '{R}'}]
        pool = Counter({FRONT: 1, 'Red Spell': 1})
        deck = Counter({FULL: 1, 'Island': 99})
        report = validate(pool, data, deck, mode='commander', commander=FRONT)
        self.assertEqual(report['status'], 'PASS_WITH_LIMITATIONS')
        a['leadershipSkills'] = {'commander': False}
        report = validate(pool, data, deck, mode='commander', commander=FRONT)
        self.assertEqual(report['checks']['commander_eligibility'], 'FAIL')
        a['leadershipSkills'] = {'commander': True}
        deck['Island'] -= 1
        deck['Red Spell'] += 1
        report = validate(pool, data, deck, mode='commander', commander=FRONT)
        self.assertEqual(report['checks']['commander_color_identity'], 'FAIL')
        report = validate(pool, data, deck, mode='commander', commander=BACK)
        self.assertEqual(report['checks']['commander_count'], 'FAIL')

    def test_gateway_runs_both_tools_on_same_owned_alias(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            data = oracle()
            data[FULL][1]['text'] = 'Flying'
            oracle_path = base / 'oracle.json'
            oracle_path.write_text(json.dumps(data))
            pin = hashlib.sha256(oracle_path.read_bytes()).hexdigest()
            pool = base / 'pool.csv'
            pool.write_text(f'Name,Quantity\n{FRONT},4\n')
            deck = base / 'deck.txt'
            deck.write_text(f'4 {FRONT}\n56 Island\n')
            gateway = [sys.executable, str(ROOT / 'tools/agent_gateway.py')]
            common = ['--oracle', str(oracle_path), '--oracle-sha256', pin,
                      '--collection', str(pool), '--collection-scope', 'synthetic']
            for action, extra, expected in (
                ('discover', ['--theme', 'Flying'], 'CANDIDATES_NOT_VALIDATED'),
                ('validate', ['--deck', str(deck)], 'VALIDATED_WITH_LIMITATIONS'),
            ):
                proc = subprocess.run(gateway + [action] + common + extra,
                                      capture_output=True, text=True, timeout=15)
                result = json.loads(proc.stdout)
                self.assertEqual((proc.returncode, result['child_exit_code']), (0, 0))
                self.assertEqual(result['status'], expected)
                if action == 'discover':
                    self.assertEqual(result['result']['results'][0]['owned_copies'], 4)
                else:
                    self.assertEqual(result['result']['checks']['ownership'], 'PASS')
                    self.assertEqual(result['result']['mana_curve_nonlands'], {'1': 4})

    def test_quantity_grammar_preserves_x_prefixes(self):
        spellbook_parser = runpy.run_path(
            str(ROOT / 'integrations/commander-spellbook/analyze.py'))['read_deck']
        validator_parser = runpy.run_path(str(VALIDATOR))['parse_deck']
        with tempfile.TemporaryDirectory() as directory:
            deck = Path(directory) / 'deck.txt'
            deck.write_text('4 Lightning Bolt\n4x Lightning Bolt\n4× Lightning Bolt\n'
                            '4×Lightning Bolt\n4 x Lightning Bolt\n'
                            '4 Xenagos, God of Revels\n1 X\n1 X Marks the Spot\n'
                            '1 Xantid Swarm\n1 Xyris, the Writhing Storm\n', encoding='utf-8')
            expected = Counter({'Lightning Bolt': 16, 'x Lightning Bolt': 4,
                                'Xenagos, God of Revels': 4, 'X': 1, 'X Marks the Spot': 1,
                                'Xantid Swarm': 1, 'Xyris, the Writhing Storm': 1})
            self.assertEqual(validator_parser(deck), (expected, []))
            self.assertEqual(spellbook_parser(deck), (expected, Counter()))
            for line in ('0 Shock', '-4 Shock', '4x', '4×', '4', '4.5 Shock'):
                deck.write_text(line, encoding='utf-8')
                self.assertTrue(validator_parser(deck)[1])
                with self.assertRaises(ValueError):
                    spellbook_parser(deck)

    def test_duplicate_oracle_key_fails_standalone_cli(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            (base / 'oracle.json').write_text('{"data":{"Island":[],"Island":[]}}')
            (base / 'pool.csv').write_text('Name,Quantity\n')
            (base / 'deck.txt').write_text('60 Island\n')
            cmd = [sys.executable, str(VALIDATOR), '--oracle', str(base / 'oracle.json'),
                   '--collection', str(base / 'pool.csv'), '--deck', str(base / 'deck.txt')]
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
            self.assertEqual(result.returncode, 2)
            self.assertIn('Duplicate Oracle JSON key', result.stderr)
