#!/usr/bin/env python3
"""Offline MTG deck validator v1.1 (Python 3.9+, only the standard library).

Checks the *submitted decklist* against a collection CSV and a local MTGJSON
AtomicCards JSON/JSON.GZ database. No network access, no MTG gameplay engine.

Verified: deck size, Oracle names, per-deck ownership, copy caps, card types,
printed mana values, commander count/identity (single commander only), and exact
physical-land opening-hand probability.

Not verified: synergy, playability, actual mana production, Oracle interpretation,
conditional card roles/removal, format banlists, unusual deckbuilding exceptions,
partners/backgrounds, cross-deck physical allocation, actual games or win rates.

Usage: python MTG_Deck_Validator_v1.1.py --help
"""

import argparse
import csv
import gzip
import json
import math
import re
import sys
from collections import Counter
from fractions import Fraction
from pathlib import Path

STANDARD_BASICS = frozenset({
    'Plains', 'Island', 'Swamp', 'Mountain', 'Forest', 'Wastes',
    'Snow-Covered Plains', 'Snow-Covered Island', 'Snow-Covered Swamp',
    'Snow-Covered Mountain', 'Snow-Covered Forest',
})
TYPES = ('Land', 'Creature', 'Instant', 'Sorcery', 'Planeswalker', 'Artifact',
         'Enchantment', 'Battle', 'Kindred')
PRIMARY_TYPES = TYPES + ('Other',)
ENTRY = re.compile(r'^\s*(\d+)\s*(?:[x×]\s*)?(.+?)\s*$', re.I)
HEADER = re.compile(r'^\s*(?:Deck|Mainboard|Main Deck|Commander|Companion|'
                    r'Creatures?|Instants?|Sorceries?|Lands?|Planeswalkers?|'
                    r'Artifacts?|Enchantments?|Battles|Other Spells|Spells)'
                    r'\s*(?:\(\d+\))?\s*:?\s*$', re.I)
SIDE_HEADER = re.compile(r'^\s*(?:Sideboard|Maybeboard|Considering)\b', re.I)


def read_collection(path):
    """Read exactly ONE active inventory. Duplicate names sum; no merging with other files."""
    owned = Counter()
    with open(path, encoding='utf-8-sig', newline='') as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames or not {'Name', 'Quantity'} <= set(reader.fieldnames):
            raise ValueError('Collection CSV needs columns Name and Quantity')
        for line, row in enumerate(reader, 2):
            name = (row.get('Name') or '').strip()
            value = (row.get('Quantity') or '').strip()
            if not name and not value:
                continue
            if not name:
                raise ValueError('Collection CSV line %d: missing Name' % line)
            if not re.fullmatch(r'\d+', value):
                raise ValueError('Collection CSV line %d (%s): invalid Quantity %r' %
                                 (line, name, value))
            owned[name] += int(value)
    return owned


def read_oracle(path):
    opener = gzip.open if str(path).lower().endswith('.gz') else open
    with opener(path, 'rt', encoding='utf-8') as handle:
        raw = json.load(handle)
    if not isinstance(raw, dict):
        raise ValueError('MTGJSON root must be an object')
    data = raw.get('data', raw)
    if not isinstance(data, dict):
        raise ValueError('Expected AtomicCards name -> card-variants mapping')
    return data, (raw.get('meta', {}) if isinstance(raw.get('meta', {}), dict) else {})


def parse_deck(path):
    """Only accepts explicit '4 Name' lines and harmless section labels.

    Sideboard sections are rejected, rather than secretly counted in the main deck.
    """
    cards = Counter()
    problems = []
    side = False
    with open(path, encoding='utf-8-sig') as handle:
        for line_no, line in enumerate(handle, 1):
            text = line.strip()
            if not text or text.startswith(('```', '#', '//')) or (text.startswith('[') and text.endswith(']')):
                continue
            if SIDE_HEADER.match(text):
                side = True
                problems.append('Line %d: sideboard/maybeboard input is not supported' % line_no)
                continue
            if HEADER.match(text):
                if side:
                    # Do not let a later section turn rejected sideboard into main-deck entries.
                    problems.append('Line %d: section after sideboard; check deck file' % line_no)
                continue
            match = ENTRY.fullmatch(text)
            if side:
                continue
            if not match:
                problems.append('Line %d: cannot parse %r' % (line_no, text))
                continue
            quantity, name = int(match.group(1)), match.group(2).strip()
            if quantity <= 0 or not name:
                problems.append('Line %d: invalid quantity or name' % line_no)
            else:
                cards[name] += quantity
    return cards, problems


def exact_land_probability(deck_size, physical_lands, draws=7, low=2, high=5):
    """Exact hypergeometric calculation with integer combinations."""
    if not (0 <= physical_lands <= deck_size and 0 <= draws <= deck_size and
            0 <= low <= high <= draws):
        raise ValueError('Invalid hypergeometric parameters')
    numerator = sum(math.comb(physical_lands, k) *
                    math.comb(deck_size - physical_lands, draws - k)
                    for k in range(low, high + 1)
                    if k <= physical_lands and draws-k <= deck_size-physical_lands)
    return Fraction(numerator, math.comb(deck_size, draws))


def field_signature(entry):
    """Facts required by structural audit, independent of printing."""
    return (entry.get('manaValue'), tuple(sorted(entry.get('types') or [])),
            tuple(sorted(entry.get('supertypes') or [])),
            tuple(sorted(entry.get('colorIdentity') or [])),
            entry.get('manaCost'))


def validate(owned, database, deck, mode='casual', commander=None,
             exact_60=False, parse_errors=None):
    """Return a JSON-serializable audit. FAIL only for demonstrable violations.

    An ambiguous Oracle variant is UNVERIFIED, never a silently chosen PASS.
    """
    if mode not in ('casual', 'commander'):
        raise ValueError('Mode must be casual or commander')
    failures = list(parse_errors or [])
    uncertainties = []
    warnings = []
    checks = {}
    count = sum(deck.values())
    checks['deck_parsing'] = 'FAIL' if parse_errors else 'PASS'

    if mode == 'casual':
        size_ok = count == 60 if exact_60 else count >= 60
        if not size_ok:
            failures.append('Deck size %d: %s' %
                            (count, 'exactly 60 required' if exact_60 else 'minimum 60 required'))
        checks['deck_size'] = 'PASS' if size_ok else 'FAIL'
        if count > 60 and not exact_60:
            warnings.append('Casual Constructed permits 60+; 60 exactly is often preferable')
        if commander:
            failures.append('--commander only applies to --mode commander')
    else:
        size_ok = count == 100
        checks['deck_size'] = 'PASS' if size_ok else 'FAIL'
        if not size_ok:
            failures.append('Commander needs exactly 100 cards INCLUDING commander, found %d' % count)
        if not commander:
            failures.append('Commander mode requires --commander NAME')
            checks['commander_count'] = 'FAIL'
        else:
            ok = deck.get(commander, 0) == 1
            checks['commander_count'] = 'PASS' if ok else 'FAIL'
            if not ok:
                failures.append('Commander %r must appear exactly once IN the decklist' % commander)

    overlap = Counter()
    primary = Counter()
    curve = Counter()
    land_count = 0
    unresolved = []
    ambiguous = []
    insufficient = []
    over_limit = []
    cost_by_name = {}
    cards_resolved = {}

    for name, quantity in sorted(deck.items()):
        raw = database.get(name)
        if raw is None:
            unresolved.append(name)
            if quantity > owned.get(name, 0):
                insufficient.append({'card': name, 'needed': quantity, 'owned': owned.get(name, 0)})
            continue
        variants = raw if isinstance(raw, list) else [raw]
        if not variants or not all(isinstance(v, dict) for v in variants):
            unresolved.append(name)
            continue
        card = variants[0]
        if any(field_signature(other) != field_signature(card) for other in variants[1:]):
            ambiguous.append(name)
        cards_resolved[name] = card
        types = set(card.get('types') or [])
        supertypes = set(card.get('supertypes') or [])
        basic_unlimited = name in STANDARD_BASICS and 'Basic' in supertypes and 'Land' in types
        if not basic_unlimited and quantity > owned.get(name, 0):
            insufficient.append({'card': name, 'needed': quantity, 'owned': owned.get(name, 0)})
        limit = 1 if mode == 'commander' else 4
        if not basic_unlimited and quantity > limit:
            over_limit.append({'card': name, 'used': quantity, 'max_without_exception': limit})
        for typ in TYPES:
            if typ in types:
                overlap[typ] += quantity
        main_type = next((typ for typ in TYPES if typ in types), 'Other')
        primary[main_type] += quantity
        if 'Land' in types:
            land_count += quantity
        else:
            value = card.get('manaValue')
            if not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0 or int(value) != value:
                uncertainties.append('Missing/non-integral manaValue for %s: %r' % (name, value))
            else:
                curve[int(value)] += quantity
        cost_by_name[name] = card.get('manaCost')

    if unresolved:
        failures.append('Names missing/invalid in Oracle database: %s' % ', '.join(unresolved))
    checks['oracle_lookup'] = 'PASS' if not unresolved else 'FAIL'
    if ambiguous:
        uncertainties.append('Conflicting MTGJSON variants for: %s' % ', '.join(ambiguous))
    if insufficient:
        failures.append('Not enough owned copies: %s' % json.dumps(insufficient, ensure_ascii=False))
    checks['ownership'] = 'PASS' if not insufficient and not unresolved else ('FAIL' if insufficient else 'UNVERIFIED')
    if over_limit:
        failures.append('Copy-limit violations: %s' % json.dumps(over_limit, ensure_ascii=False))
    checks['copy_limit'] = 'PASS' if not over_limit and not unresolved else ('FAIL' if over_limit else 'UNVERIFIED')
    checks['card_types'] = 'PASS' if not unresolved and not ambiguous else 'UNVERIFIED'
    checks['mana_curve'] = 'PASS' if not unresolved and not ambiguous and not any('manaValue' in x for x in uncertainties) else 'UNVERIFIED'

    if mode == 'commander':
        if not commander or commander not in cards_resolved:
            checks['commander_color_identity'] = 'UNVERIFIED'
            checks['commander_eligibility'] = 'UNVERIFIED'
        else:
            lead = cards_resolved[commander]
            skills = lead.get('leadershipSkills') or {}
            is_legendary_creature = 'Legendary' in (lead.get('supertypes') or []) and 'Creature' in (lead.get('types') or [])
            if skills.get('commander') is True or is_legendary_creature:
                checks['commander_eligibility'] = 'PASS_BASIC_RULE'
            elif skills.get('commander') is False:
                failures.append('%s is not eligible as a single Commander according to loaded data' % commander)
                checks['commander_eligibility'] = 'FAIL'
            else:
                uncertainties.append('Commander eligibility cannot be established for %s' % commander)
                checks['commander_eligibility'] = 'UNVERIFIED'
            allowed = set(lead.get('colorIdentity') or [])
            wrong = [name for name, card in cards_resolved.items()
                     if not set(card.get('colorIdentity') or []) <= allowed]
            if wrong:
                failures.append('Outside commander color identity: %s' % ', '.join(sorted(wrong)))
                checks['commander_color_identity'] = 'FAIL'
            else:
                checks['commander_color_identity'] = 'PASS' if not unresolved and not ambiguous else 'UNVERIFIED'
    else:
        checks['commander_color_identity'] = 'NOT_APPLICABLE'
        checks['commander_eligibility'] = 'NOT_APPLICABLE'
        checks['commander_count'] = 'NOT_APPLICABLE'

    probability = None
    if not unresolved and not ambiguous and count >= 7:
        probability = exact_land_probability(count, land_count)
    checks['land_probability'] = 'PASS_EXACT' if probability is not None else 'UNVERIFIED'
    if ambiguous:
        uncertainties.append('Counts may depend on different Oracle variants; inspect before relying on totals')
    checks['format_banlist'] = 'NOT_CHECKED'
    checks['special_deckbuilding_exceptions'] = 'NOT_CHECKED'
    checks['mana_production_and_castability'] = 'NOT_CHECKED'
    checks['synergy_and_gameplay'] = 'NOT_CHECKED'
    checks['cross_deck_physical_assembly'] = 'NOT_CHECKED'
    if mode == 'commander':
        checks['multiple_commanders_partner_backgrounds'] = 'NOT_SUPPORTED'

    return {
        'status': 'FAIL' if failures else ('UNVERIFIED' if uncertainties else 'PASS_WITH_LIMITATIONS'),
        'mode': mode, 'deck_cards': count, 'unique_card_names': len(deck),
        'lands_physical': land_count if not unresolved else None,
        'nonlands': count - land_count if not unresolved else None,
        'card_types_primary_exclusive': {typ: primary[typ] for typ in PRIMARY_TYPES if primary[typ]},
        'card_types_overlapping': {typ: overlap[typ] for typ in TYPES if overlap[typ]},
        'mana_curve_nonlands': {str(k): curve[k] for k in sorted(curve)},
        'printed_mana_costs': cost_by_name,
        'opening_7_exactly_2_to_5_physical_lands': {
            'fraction': str(probability) if probability is not None else None,
            'percentage': round(float(probability)*100, 6) if probability is not None else None,
            'assumptions': 'uniform random 7-card hand, no mulligan, physical lands only',
        },
        'checks': checks, 'failures': failures, 'uncertainties': uncertainties,
        'warnings': warnings,
        'limitations': ['No gameplay/winrate/synergy verification',
                        'No format banlist or special card-text deck-size/copy exceptions',
                        'No mana availability/castability verification',
                        'No multi-commander rules or cross-deck allocation audit'],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('--collection', required=True, help='CSV with Name,Quantity (one active inventory)')
    parser.add_argument('--oracle', required=True, help='Local MTGJSON AtomicCards .json or .json.gz')
    parser.add_argument('--deck', required=True, help='UTF-8 TXT decklist: one "4 Shock" per line')
    parser.add_argument('--mode', choices=['casual', 'commander'], default='casual')
    parser.add_argument('--commander', help='Exact Commander card name, included in the 100-card deck')
    parser.add_argument('--exact-60', action='store_true', help='Require EXACTLY 60 cards for casual mode')
    parser.add_argument('--output', help='Write JSON report to this file as well as stdout')
    args = parser.parse_args(argv)
    try:
        owned = read_collection(args.collection)
        oracle, metadata = read_oracle(args.oracle)
        cards, parse_problems = parse_deck(args.deck)
        report = validate(owned, oracle, cards, args.mode, args.commander, args.exact_60, parse_problems)
        report['source_collection'] = Path(args.collection).name
        report['source_oracle'] = Path(args.oracle).name
        report['source_deck'] = Path(args.deck).name
        report['oracle_version'] = metadata.get('version', 'unknown')
        report['collection_unique_names'] = len(owned)
        report['collection_owned_copies'] = sum(owned.values())
        rendered = json.dumps(report, ensure_ascii=False, indent=2) + '\n'
        print(rendered, end='')
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as handle:
                handle.write(rendered)
        return {'PASS_WITH_LIMITATIONS': 0, 'FAIL': 1, 'UNVERIFIED': 3}[report['status']]
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        print('INPUT ERROR: %s' % exc, file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
