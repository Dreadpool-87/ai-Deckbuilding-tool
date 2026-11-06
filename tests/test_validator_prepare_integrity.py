"""Synthetic, offline regression tests for the prepare-integrity Validator.

No personal collections, decklists or MTGJSON datasets are embedded here.
"""
import importlib.util
import unittest
from collections import Counter
from copy import deepcopy
from pathlib import Path

VALIDATOR = Path(__file__).resolve().parents[1] / 'validator' / 'MTG_Deck_Validator_v1.1.1.py'
spec = importlib.util.spec_from_file_location('prepare_validator', VALIDATOR)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

NAME = 'Fixture Sentinel // Fixture Insight'


def fixture():
    common = {'name': NAME, 'layout': 'prepare', 'supertypes': [],
              'colorIdentity': ['W', 'G'], 'manaValue': 3}
    front = dict(common, side='a', faceName='Fixture Sentinel', types=['Creature'],
                 manaCost='{2}{W}', text='When this creature enters, gain 1 life.',
                 colors=['W'])
    back = dict(common, side='b', faceName='Fixture Insight', types=['Sorcery'],
                manaCost='{1}{G}', text='Draw a card.', colors=['G'])
    plains = {'name': 'Plains', 'types': ['Land'], 'supertypes': ['Basic'],
              'manaValue': 0, 'colorIdentity': ['W'], 'text': '({T}: Add {W}.)'}
    vanilla = {'name': 'Fixture Bear', 'types': ['Creature'], 'supertypes': [],
               'manaValue': 2, 'manaCost': '{1}{G}', 'colorIdentity': ['G'],
               'text': 'Vanilla creature.'}
    oracle = {NAME: [front, back], 'Plains': [plains], 'Fixture Bear': [vanilla]}
    return oracle


def validate(oracle=None, deck=None, owned=None):
    return module.validate(
        Counter({NAME: 4} if owned is None else owned),
        fixture() if oracle is None else oracle,
        Counter({'Plains': 56, NAME: 4} if deck is None else deck),
        mode='casual', exact_60=True,
    )


class PrepareLayoutUpgradeTests(unittest.TestCase):
    def test_valid_distinct_face_colors_are_supported(self):
        result = validate()
        self.assertEqual(result['status'], 'PASS_WITH_LIMITATIONS')
        self.assertEqual(result['prepare_layout_audit']['status'], 'PASS')
        self.assertEqual(result['mana_curve_integrity']['status'], 'ORACLE_ARITHMETIC_PASS')
        self.assertEqual(result['mana_curve_nonlands'], {'3': 4})
        self.assertEqual(result['lands_physical'], 56)
        self.assertEqual(result['nonlands'], 4)
        self.assertEqual(result['checks']['ownership'], 'PASS')

    def test_missing_spell_face_rejected(self):
        oracle = fixture()
        oracle[NAME].pop()
        self.assert_rejected(oracle)

    def test_invalid_color_list_rejected(self):
        oracle = fixture()
        oracle[NAME][1]['colors'] = ['G', 'G']
        self.assert_rejected(oracle)

    def test_missing_color_identity_rejected(self):
        oracle = fixture()
        del oracle[NAME][1]['colorIdentity']
        self.assert_rejected(oracle)

    def test_wrong_spell_face_types_rejected(self):
        oracle = fixture()
        oracle[NAME][1]['types'] = ['Land']
        self.assert_rejected(oracle)

    def test_cross_face_mana_value_conflict_rejected(self):
        oracle = fixture()
        oracle[NAME][1]['manaValue'] = 2
        self.assert_rejected(oracle)

    def test_conflicting_prepare_printings_rejected(self):
        oracle = fixture()
        other = deepcopy(oracle[NAME][0]); other['text'] += ' Draw a card.'
        oracle[NAME].append(other)
        self.assert_rejected(oracle)

    def test_mixed_layouts_rejected(self):
        oracle = fixture()
        oracle[NAME][1]['layout'] = 'normal'
        self.assert_rejected(oracle)

    def test_non_prepare_card_unaffected(self):
        result = validate(deck={'Plains': 56, 'Fixture Bear': 4}, owned={'Fixture Bear': 4})
        self.assertEqual(result['status'], 'PASS_WITH_LIMITATIONS')
        self.assertEqual(result['prepare_layout_audit']['status'], 'NOT_APPLICABLE')
        self.assertEqual(result['mana_curve_integrity']['status'], 'ORACLE_ARITHMETIC_PASS')

    def test_illegal_five_copies_still_fail(self):
        result = validate(deck={'Plains': 55, NAME: 5}, owned={NAME: 5})
        self.assertEqual(result['status'], 'FAIL')
        self.assertEqual(result['checks']['copy_limit'], 'FAIL')

    def assert_rejected(self, oracle):
        result = validate(oracle=oracle)
        self.assertEqual(result['status'], 'UNVERIFIED')
        self.assertEqual(result['prepare_layout_audit']['status'], 'UNVERIFIED')
        self.assertNotEqual(result['mana_curve_integrity']['status'], 'ORACLE_ARITHMETIC_PASS')


if __name__ == '__main__':
    unittest.main()
