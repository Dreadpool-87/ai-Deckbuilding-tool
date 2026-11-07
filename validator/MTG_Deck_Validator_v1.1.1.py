#!/usr/bin/env python3
"""Offline MTG deck validator v1.1.1 (tested on Python 3.12 and 3.13).

Checks the *submitted decklist* against a collection CSV and a local MTGJSON
AtomicCards JSON/JSON.GZ database. No network access, no MTG gameplay engine.

Verified: deck size, Oracle names, per-deck ownership, copy caps, card types,
printed mana values, commander count/identity (single commander only), and exact
physical-land opening-hand probability.

Not verified: synergy, playability, actual mana production, Oracle interpretation,
conditional card roles/removal, format banlists, unusual deckbuilding exceptions,
partners/backgrounds, cross-deck physical allocation, actual games or win rates.

Usage: python validator/MTG_Deck_Validator_v1.1.1.py --help
"""

import argparse
import csv
import gzip
import importlib.util
import json
import math
import re
import sys
from collections import Counter
from fractions import Fraction
from pathlib import Path

# Load only the adjacent or checkout-local helper, including in isolated CLI mode.
_identity_path = Path(__file__).resolve().with_name('card_identity.py')
if not _identity_path.is_file():
    _identity_path = _identity_path.parent.parent / 'tools' / _identity_path.name
_identity_spec = importlib.util.spec_from_file_location('mtg_card_identity', _identity_path)
_identity = importlib.util.module_from_spec(_identity_spec)
_identity_spec.loader.exec_module(_identity)

STANDARD_BASICS = frozenset({
    'Plains', 'Island', 'Swamp', 'Mountain', 'Forest', 'Wastes',
    'Snow-Covered Plains', 'Snow-Covered Island', 'Snow-Covered Swamp',
    'Snow-Covered Mountain', 'Snow-Covered Forest',
})
TYPES = ('Land', 'Creature', 'Instant', 'Sorcery', 'Planeswalker', 'Artifact',
         'Enchantment', 'Battle', 'Kindred')
PRIMARY_TYPES = TYPES + ('Other',)
# An ASCII x marker must attach to the quantity and be followed by whitespace.
# Keep the grammar identical in the standalone Validator and Spellbook analyzer.
ENTRY = re.compile(r'^([0-9]+)(?:[xX]\s+|×\s*|\s+)(\S.*)$')
HEADER = re.compile(r'^\s*(?:Deck|Mainboard|Main Deck|Commander|Companion|'
                    r'Creatures?|Instants?|Sorceries?|Lands?|Planeswalkers?|'
                    r'Artifacts?|Enchantments?|Battles|Other Spells|Spells)'
                    r'\s*(?:\(\d+\))?\s*:?\s*$', re.I)
SIDE_HEADER = re.compile(r'^\s*(?:Sideboard|Maybeboard|Considering)\b', re.I)


def read_collection(path):
    """Read exactly ONE active inventory. Duplicate names sum; no merging with other files."""
    owned = Counter()
    with open(path, encoding='utf-8-sig', newline='') as handle:
        reader = csv.reader(handle, strict=True)
        line = 1
        try:
            header = next(reader, [])
            if (len(set(header)) != len(header)
                    or not {'Name', 'Quantity'} <= set(header)):
                raise ValueError('Collection CSV line 1: needs unique Name and Quantity columns')
            name_index, quantity_index = header.index('Name'), header.index('Quantity')
            while True:
                line = reader.line_num + 1
                row = next(reader, None)
                if row is None:
                    break
                if not row:
                    continue
                if len(row) != len(header):
                    raise ValueError('Collection CSV line %d: wrong number of fields' % line)
                name, value = row[name_index].strip(), row[quantity_index].strip()
                if not name:
                    raise ValueError('Collection CSV line %d: missing Name' % line)
                if not re.fullmatch(r'[0-9]+', value):
                    raise ValueError('Collection CSV line %d: invalid Quantity' % line)
                try:
                    owned[name] += int(value)
                except ValueError:
                    raise ValueError('Collection CSV line %d: Quantity is too large' % line) from None
        except csv.Error as exc:
            raise ValueError('Collection CSV line %d: %s' % (line, exc)) from None

    return owned


def read_oracle(path):
    opener = gzip.open if str(path).lower().endswith('.gz') else open
    with opener(path, 'rt', encoding='utf-8') as handle:
        raw = json.load(handle, object_pairs_hook=_identity.reject_duplicate_oracle_keys)
    if not isinstance(raw, dict):
        raise ValueError('MTGJSON root must be an object')
    data = raw.get('data', raw)
    if not isinstance(data, dict):
        raise ValueError('Expected AtomicCards name -> card-variants mapping')
    return data, (raw.get('meta', {}) if isinstance(raw.get('meta', {}), dict) else {})


def parse_deck(path):
    """Accept explicit quantity/name lines and harmless section labels.

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
            if quantity <= 0:
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
    def normalized(field):
        value = entry.get(field)
        if isinstance(value, list) and all(isinstance(item, str) for item in value):
            return tuple(sorted(value))
        return value

    skills = entry.get('leadershipSkills')
    commander_skill = skills.get('commander') if isinstance(skills, dict) else None
    return (entry.get('manaValue'), normalized('types'), normalized('supertypes'),
            normalized('colorIdentity'), entry.get('manaCost'), commander_skill)


def project_multiface(name, variants):
    """Select the front or combine split faces only when required facts agree."""
    pair = _identity.face_pair(name, variants)
    if pair is None:
        return variants, 'unsupported or incomplete face/layout metadata'
    front, back = pair
    layout = front[0]['layout']

    def valid_mv(value):
        return (type(value) in (int, float) and math.isfinite(value)
                and value >= 0 and int(value) == value)

    def usable(face):
        types = face.get('types')
        supertypes = face.get('supertypes', [])
        skills = face.get('leadershipSkills', {})
        cost = face.get('manaCost')
        return (identity_valid(face) and isinstance(types, list) and bool(types)
                and all(isinstance(t, str) for t in types)
                and isinstance(supertypes, list) and all(isinstance(t, str) for t in supertypes)
                and isinstance(skills, dict)
                and ('commander' not in skills or type(skills['commander']) is bool)
                and valid_mv(face.get('manaValue')) and valid_mv(face.get('faceManaValue'))
                and (cost is None or (isinstance(cost, str) and bool(cost.strip()))))

    if not all(usable(face) for face in variants):
        return variants, 'missing or invalid structural face fields'
    for side in pair:
        if any(field_signature(face) != field_signature(side[0]) or
               face.get('faceManaValue') != side[0].get('faceManaValue') for face in side):
            return variants, 'conflicting structural data for the same side'
    a, b = front[0], back[0]
    if set(a['colorIdentity']) != set(b['colorIdentity']):
        return variants, 'conflicting card color identity across sides'
    if layout != 'modal_dfc' and a['manaValue'] != b['manaValue']:
        return variants, 'conflicting shared mana value across sides'
    if layout not in {'split', 'aftermath'}:
        if a.get('faceManaValue') != a['manaValue']:
            return variants, 'front face and card mana values differ or are missing'
        if a.get('manaCost') is None and 'Land' not in a['types']:
            return variants, 'missing front-face cost'
        return front, None

    face_values = [face.get('faceManaValue') for face in (a, b)]
    combined_types = set(a['types']) | set(b['types'])
    if (sum(face_values) != a['manaValue']
            or not combined_types <= {'Instant', 'Sorcery', 'Kindred'}
            or any(not set(face['types']) & {'Instant', 'Sorcery'} or
                   not face.get('manaCost') for face in (a, b))):
        return variants, 'unsupported split types, mana values, or printed costs'
    return [dict(a, types=sorted(combined_types), supertypes=[],
                 leadershipSkills={'commander': False},
                 manaCost=f"{a['manaCost']} // {b['manaCost']}")], None


def resolve_prepare_variants(name, variants):
    """Fail-closed, read-only structural projection for MTGJSON prepare cards.

    MTGJSON stores the creature (side a) and its inset spell (side b) as
    separate records under ONE combined canonical card name. Rules give the
    physical card the creature's characteristics in all zones; a prepared
    permanent instead creates a castable COPY of the spell in exile.

    Return (creature_records, verified_spell_metadata, error). Other layouts
    retain the original variant-by-variant behavior. Neither the database nor
    the original records are mutated or discarded.
    """
    if not any(v.get('layout') == 'prepare' for v in variants):
        return variants, None, None
    if any(v.get('layout') != 'prepare' for v in variants):
        return variants, None, 'mixed prepare and non-prepare layouts'
    parts = name.split(' // ')
    if len(parts) != 2 or not all(parts):
        return variants, None, 'expected canonical Creature // Spell name'
    front_name, spell_name = parts
    creatures = [v for v in variants if v.get('side') == 'a']
    spells = [v for v in variants if v.get('side') == 'b']
    if not creatures or not spells or len(creatures) + len(spells) != len(variants):
        return variants, None, 'missing, unexpected, or malformed side a / side b record'
    # Hardening: validate allowed type combinations before projecting card facts.
    # Artifact/Enchantment Creature and Kindred Instant/Sorcery are supported
    # combinations; Land on either face or spell types on a creature are not.
    # Keep this strictly scoped to the prepare layout.
    def valid_face_types(face, role):
        values = face.get('types')
        if (not isinstance(values, list) or not values or
                any(not isinstance(x, str) for x in values) or
                len(values) != len(set(values))):
            return False
        found = set(values)
        if role == 'creature':
            return 'Creature' in found and found <= {'Creature', 'Artifact', 'Enchantment'}
        return (len(found & {'Instant', 'Sorcery'}) == 1 and
                found <= {'Instant', 'Sorcery', 'Kindred'})

    if any(not valid_face_types(v, 'creature') for v in creatures):
        return variants, None, 'unsupported or contradictory prepare creature-face card types'
    if any(not valid_face_types(v, 'spell') for v in spells):
        return variants, None, 'unsupported or contradictory prepare spell-face card types'

    # Data completeness policy for this layout: colors may be empty for colorless
    # faces, but the field itself must exist and be a valid WUBRG symbol list.
    def valid_colors(face):
        colors = face.get('colors')
        return (isinstance(colors, list) and
                all(type(c) is str and c in {'W', 'U', 'B', 'R', 'G'} for c in colors) and
                len(colors) == len(set(colors)))

    if any(not valid_colors(v) for v in creatures + spells):
        return variants, None, 'missing or invalid prepare-face colors metadata'

    # Every face must independently have a well-formed shared card identity.
    # [] is legitimate on a colorless card, but missing/invalid data is not.
    # A face can have fewer colors than the union of mana symbols on the card;
    # do not demand identical face colors, only a subset of card identity.
    if any(not identity_valid(v) for v in creatures + spells):
        return variants, None, 'missing or invalid prepare-face colorIdentity metadata'
    if any(not set(v['colors']).issubset(set(v['colorIdentity']))
           for v in creatures + spells):
        return variants, None, 'prepare-face colors outside shared colorIdentity'

    if any(not isinstance(v.get('text'), str) or not v['text'].strip()
           for v in creatures + spells):
        return variants, None, 'missing or blank prepare-face Oracle text'

    if any(v.get('name') != name or v.get('faceName') != front_name or
           'Creature' not in (v.get('types') or []) for v in creatures):
        return variants, None, 'creature side a does not match the card identity'
    if any(v.get('name') != name or v.get('faceName') != spell_name or
           len(set(v.get('types') or []) & {'Instant', 'Sorcery'}) != 1 or
           'Creature' in (v.get('types') or []) for v in spells):
        return variants, None, 'prepare spell side b must be a matching instant or sorcery'
    if any(not isinstance(v.get('manaCost'), str) or not v['manaCost']
           for v in creatures + spells):
        return variants, None, 'missing printed cost on a prepare side'
    # Compare normalized color lists within EACH face across printings.
    # Order is not a semantic difference, unlike different color membership.
    def prepare_printing_signature(v):
        return (field_signature(v), tuple(sorted(v['colors'])), v.get('text'))

    if any(prepare_printing_signature(v) != prepare_printing_signature(creatures[0])
           for v in creatures[1:]):
        return variants, None, 'conflicting creature-side printings'
    if any(prepare_printing_signature(v) != prepare_printing_signature(spells[0])
           for v in spells[1:]):
        return variants, None, 'conflicting prepare-spell printings'
    creature, spell = creatures[0], spells[0]
    # MTGJSON encodes shared card-level identity and base mana value on both
    # face records; do not silently accept a malformed combination.
    if (creature.get('colorIdentity') != spell.get('colorIdentity') or
            creature.get('manaValue') != spell.get('manaValue')):
        return variants, None, 'mismatched shared card identity or base mana value across faces'
    if not isinstance(creature.get('text'), str) or not isinstance(spell.get('text'), str):
        return variants, None, 'missing Oracle text for the creature or prepare spell'
    metadata = {
        'creature_face_name': front_name,
        'creature_mana_cost': creature.get('manaCost'),
        'creature_mana_value': creature.get('manaValue'),
        'creature_types': creature.get('types'),
        'creature_oracle_text': creature.get('text'),
        'spell_name': spell_name,
        'spell_mana_cost': spell.get('manaCost'),
        'spell_types': spell.get('types'),
        'spell_oracle_text': spell.get('text'),
        'original_face_records': len(variants),
        'note': 'Card and mana curve use the creature side. The spell is a copy castable only when prepared, with its own cost and timing; castability not simulated.',
    }
    return creatures, metadata, None


def basic_land_status(name, card):
    """True/False for known standard Basics, or None for incomplete Oracle data."""
    if name not in STANDARD_BASICS:
        return False
    types = card.get('types')
    supertypes = card.get('supertypes')
    if not isinstance(types, list) or not isinstance(supertypes, list):
        return None
    return 'Land' in types and 'Basic' in supertypes


def casual_copy_exception(name, variants):
    """Only trust identical, explicit unlimited-copy Oracle wording across prints.

    Return UNLIMITED, ORDINARY, or UNVERIFIED. This is deliberately not a
    general card-text rules engine or a replacement for collection ownership.
    """
    oracle_line = re.compile(
        r'A deck can have any number of cards named ' + re.escape(name) + r'\.',
        re.IGNORECASE,
    )
    flags = [v.get('hasAlternativeDeckLimit') is True for v in variants]
    texts = [v.get('text') for v in variants]
    supported = [
        isinstance(value, str) and any(oracle_line.fullmatch(line.strip())
                                       for line in value.splitlines())
        for value in texts
    ]
    if all(flags) and all(supported):
        return 'UNLIMITED'
    if any(flags) or any(supported):
        return 'UNVERIFIED'
    return 'ORDINARY'


def identity_valid(card):
    colors = card.get('colorIdentity')
    return (isinstance(colors, list) and
            all(type(c) is str and c in {'W', 'U', 'B', 'R', 'G'} for c in colors) and
            len(colors) == len(set(colors)))


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
    verified, possible = _identity.card_name_index(database)
    canonical_deck = Counter()
    identity_findings = {}
    for name, quantity in deck.items():
        status, canonical = _identity.physical_name(name, database, verified, possible)
        if status != 'EXACT_MATCH':
            identity_findings[name] = {'status': status, 'canonical_name': canonical}
        canonical_deck[canonical or name] += quantity
    deck = canonical_deck
    if commander:
        _, canonical = _identity.physical_name(commander, database, verified, possible)
        commander = canonical or commander
    owned_by_name, ownership_coverage = _identity.resolve_collection(
        owned, database, verified, possible)
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
    curve_ledger = []
    missing_mana_value = []
    land_count = 0
    unresolved = []
    ambiguous = []
    insufficient = []
    over_limit = []
    cost_by_name = {}
    cards_resolved = {}
    missing_types = False
    ownership_uncertain = False
    limit_uncertain = False
    applied_copy_exceptions = []
    uncertain_copy_exceptions = []
    prepare_faces_verified = {}
    prepare_faces_unverified = {}

    for name, quantity in sorted(deck.items()):
        finding = identity_findings.get(name)
        raw = (None if finding and finding['canonical_name'] is None
               else database.get(name))
        if raw is None:
            unresolved.append(name)
            continue
        variants = raw if isinstance(raw, list) else [raw]
        if not variants or not all(isinstance(v, dict) for v in variants):
            unresolved.append(name)
            continue
        # Experimental prepare-layout support. Verify BOTH faces before using
        # only the base creature for structural deck and mana-curve checks.
        variants, prepare_metadata, prepare_error = resolve_prepare_variants(name, variants)
        if prepare_error:
            ambiguous.append(name)
            prepare_faces_unverified[name] = prepare_error
            uncertainties.append('Prepare layout not safely resolved for %s: %s' % (name, prepare_error))
        if prepare_metadata is not None:
            prepare_faces_verified[name] = prepare_metadata
        if not prepare_error and prepare_metadata is None and '//' in name:
            variants, face_error = project_multiface(name, variants)
            if face_error:
                ambiguous.append(name)
                uncertainties.append('Multiface layout not safely resolved for %s: %s' % (name, face_error))
                continue
        card = variants[0]
        if any(v.get('name') != name for v in variants):
            unresolved.append(name)
            continue
        if any(field_signature(other) != field_signature(card) for other in variants[1:]):
            ambiguous.append(name)
        cards_resolved[name] = card
        raw_types = card.get('types')
        if not isinstance(raw_types, list) or not raw_types or not all(isinstance(t, str) for t in raw_types):
            missing_types = True
            uncertainties.append('Missing/invalid types for %s' % name)
        types = {typ for typ in raw_types if isinstance(typ, str)} if isinstance(raw_types, list) else set()
        basic_states = [basic_land_status(name, variant) for variant in variants]
        basic_unlimited = all(state is True for state in basic_states)
        basic_ruled_out = all(state is False for state in basic_states)
        if name in ambiguous:
            ownership_uncertain = limit_uncertain = True
        if name not in ambiguous and not basic_unlimited and quantity > owned_by_name.get(name, 0):
            if basic_ruled_out:
                insufficient.append({'card': name, 'needed': quantity, 'owned': owned_by_name.get(name, 0)})
            else:
                ownership_uncertain = True
                uncertainties.append('Basic-land ownership exemption uncertain for %s' % name)
        limit = 1 if mode == 'commander' else 4
        if name not in ambiguous and not basic_unlimited and quantity > limit:
            if basic_ruled_out:
                exception = (casual_copy_exception(name, variants)
                             if mode == 'casual' else 'ORDINARY')
                if exception == 'UNLIMITED':
                    applied_copy_exceptions.append(name)
                elif exception == 'UNVERIFIED':
                    limit_uncertain = True
                    uncertain_copy_exceptions.append(name)
                    uncertainties.append('Unverified card-specific copy exception for %s' % name)
                else:
                    over_limit.append({'card': name, 'used': quantity, 'max_without_exception': limit})
            else:
                limit_uncertain = True
                uncertainties.append('Basic-land copy exemption uncertain for %s' % name)
        for typ in TYPES:
            if typ in types:
                overlap[typ] += quantity
        main_type = next((typ for typ in TYPES if typ in types), 'Other')
        primary[main_type] += quantity
        if 'Land' in types:
            land_count += quantity
        else:
            value = card.get('manaValue')
            if (isinstance(value, bool) or not isinstance(value, (int, float)) or
                    not math.isfinite(value) or value < 0 or int(value) != value):
                uncertainties.append('Missing/non-integral manaValue for %s: %r' % (name, value))
                missing_mana_value.append(name)
            else:
                mana_value = int(value)
                curve[mana_value] += quantity
                curve_ledger.append({
                    'name': name, 'quantity': quantity, 'mana_value': mana_value,
                    'weighted_mana_value': quantity * mana_value,
                })
        cost_by_name[name] = card.get('manaCost')

    if unresolved:
        failures.append('Names missing/invalid in Oracle database: %s' % ', '.join(unresolved))
    checks['oracle_lookup'] = 'PASS' if not unresolved else 'FAIL'
    if ambiguous:
        uncertainties.append('Conflicting MTGJSON variants for: %s' % ', '.join(ambiguous))
    if insufficient:
        failures.append('Not enough owned copies: %s' % json.dumps(insufficient, ensure_ascii=False))
    checks['ownership'] = 'FAIL' if insufficient else ('UNVERIFIED' if unresolved or ambiguous or ownership_uncertain else 'PASS')
    if over_limit:
        failures.append('Copy-limit violations: %s' % json.dumps(over_limit, ensure_ascii=False))
    checks['copy_limit'] = 'FAIL' if over_limit else ('UNVERIFIED' if unresolved or ambiguous or limit_uncertain else 'PASS')
    checks['card_types'] = 'PASS' if not unresolved and not ambiguous and not missing_types else 'UNVERIFIED'
    checks['mana_curve'] = 'PASS' if not unresolved and not ambiguous and not missing_types and not missing_mana_value else 'UNVERIFIED'
    # Reusable arithmetic for Builder and Tester. No rules, casting, or gameplay claim.
    # Keep the original curve output unchanged for existing consumers.
    curve_bins = {str(k): curve[k] for k in range(7)}
    curve_bins['7+'] = sum(q for mv, q in curve.items() if mv >= 7)
    weighted_total = sum(entry['weighted_mana_value'] for entry in curve_ledger)
    counted_nonlands = sum(entry['quantity'] for entry in curve_ledger)
    curve_consistent = (
        checks['mana_curve'] == 'PASS' and
        counted_nonlands == count - land_count and
        sum(curve_bins.values()) == counted_nonlands and
        sum(mv * q for mv, q in curve.items()) == weighted_total
    )
    if checks['mana_curve'] == 'PASS' and not curve_consistent:
        checks['mana_curve'] = 'UNVERIFIED'
        uncertainties.append('Mana curve arithmetic did not reconcile')
    curve_integrity = {
        'status': 'ORACLE_ARITHMETIC_PASS' if curve_consistent else 'UNVERIFIED',
        'bins': curve_bins if curve_consistent else None,
        'nonland_copies': counted_nonlands if curve_consistent else None,
        'weighted_mana_value_total': weighted_total if curve_consistent else None,
        'average_mana_value_fraction': (
            str(Fraction(weighted_total, counted_nonlands))
            if curve_consistent and counted_nonlands else None
        ),
        'average_mana_value_rounded': (
            round(weighted_total / counted_nonlands, 3)
            if curve_consistent and counted_nonlands else None
        ),
        'ledger': curve_ledger if curve_consistent else None,
        'unresolved_mana_values': sorted(missing_mana_value),
        'scope': 'MTGJSON printed manaValue, nonlands only; unusual layouts require separate rules review',
    }

    if mode == 'commander':
        if not commander or commander not in cards_resolved:
            checks['commander_color_identity'] = 'UNVERIFIED'
            checks['commander_eligibility'] = 'UNVERIFIED'
        else:
            lead = cards_resolved[commander]
            skills = lead.get('leadershipSkills', {})
            lead_types = lead.get('types')
            lead_supertypes = lead.get('supertypes', [])
            if (commander in ambiguous or not isinstance(lead_types, list)
                    or not isinstance(lead_supertypes, list)
                    or not all(isinstance(t, str) for t in lead_supertypes + lead_types)
                    or not isinstance(skills, dict)
                    or ('commander' in skills and type(skills['commander']) is not bool)):
                uncertainties.append('Commander eligibility has incomplete/conflicting data for %s' % commander)
                checks['commander_eligibility'] = 'UNVERIFIED'
            elif skills.get('commander') is False:
                failures.append('%s is not eligible as a single Commander according to loaded data' % commander)
                checks['commander_eligibility'] = 'FAIL'
            elif skills.get('commander') is True or ('Legendary' in lead_supertypes and 'Creature' in lead_types):
                checks['commander_eligibility'] = 'PASS_BASIC_RULE'
            else:
                uncertainties.append('Commander eligibility cannot be established for %s' % commander)
                checks['commander_eligibility'] = 'UNVERIFIED'
            bad_identity = sorted(name for name, card in cards_resolved.items()
                                  if not identity_valid(card))
            if bad_identity:
                uncertainties.append('Missing/invalid commander colorIdentity for: %s' % ', '.join(bad_identity))
            allowed = set(lead['colorIdentity']) if identity_valid(lead) else None
            wrong = sorted(name for name, card in cards_resolved.items()
                           if allowed is not None and identity_valid(card) and
                           not set(card['colorIdentity']) <= allowed)
            if wrong:
                failures.append('Outside commander color identity: %s' % ', '.join(wrong))
                checks['commander_color_identity'] = 'FAIL'
            else:
                checks['commander_color_identity'] = ('PASS' if not unresolved and not ambiguous
                                                       and not bad_identity else 'UNVERIFIED')
    else:
        checks['commander_color_identity'] = 'NOT_APPLICABLE'
        checks['commander_eligibility'] = 'NOT_APPLICABLE'
        checks['commander_count'] = 'NOT_APPLICABLE'

    probability = None
    if not unresolved and not ambiguous and not missing_types and count >= 7:
        probability = exact_land_probability(count, land_count)
    checks['land_probability'] = 'PASS_EXACT' if probability is not None else 'UNVERIFIED'
    if ambiguous:
        uncertainties.append('Counts may depend on different Oracle variants; inspect before relying on totals')
    checks['format_banlist'] = 'NOT_CHECKED'
    checks['special_deckbuilding_exceptions'] = (
        'UNVERIFIED' if uncertain_copy_exceptions else
        'PASS_EXPLICIT_UNLIMITED_COPY' if applied_copy_exceptions else 'NOT_CHECKED'
    )
    checks['mana_production_and_castability'] = 'NOT_CHECKED'
    checks['synergy_and_gameplay'] = 'NOT_CHECKED'
    checks['cross_deck_physical_assembly'] = 'NOT_CHECKED'
    if mode == 'commander':
        checks['multiple_commanders_partner_backgrounds'] = 'NOT_SUPPORTED'

    return {
        'status': 'FAIL' if failures else ('UNVERIFIED' if uncertainties else 'PASS_WITH_LIMITATIONS'),
        'mode': mode, 'deck_cards': count, 'unique_card_names': len(deck),
        'lands_physical': land_count if not unresolved and not ambiguous and not missing_types else None,
        'nonlands': count - land_count if not unresolved and not ambiguous and not missing_types else None,
        'card_types_primary_exclusive': {typ: primary[typ] for typ in PRIMARY_TYPES if primary[typ]},
        'card_types_overlapping': {typ: overlap[typ] for typ in TYPES if overlap[typ]},
        'mana_curve_nonlands': {str(k): curve[k] for k in sorted(curve)},
        'mana_curve_integrity': curve_integrity,
        'printed_mana_costs': cost_by_name,
        'prepare_layout_audit': {
            'status': ('UNVERIFIED' if prepare_faces_unverified else
                       'PASS' if prepare_faces_verified else 'NOT_APPLICABLE'),
            'verified_cards': prepare_faces_verified,
            'unverified_cards': prepare_faces_unverified,
            'scope': 'Oracle face classification only; never asserts that a prepare spell was cast or its cost can be paid',
        },
        'opening_7_exactly_2_to_5_physical_lands': {
            'fraction': str(probability) if probability is not None else None,
            'percentage': round(float(probability)*100, 6) if probability is not None else None,
            'assumptions': 'uniform random 7-card hand, no mulligan, physical lands only',
        },
        'identity_findings': identity_findings,
        'collection_coverage': ownership_coverage,
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
