#!/usr/bin/env python3
"""Conservative offline ingredient matcher for Commander Spellbook bulk variants.

NOT the upstream combo engine or an MTG rules/legality checker.
"""
from __future__ import annotations
import argparse
from collections import Counter
import importlib.util
import gzip
import hashlib
import json
from pathlib import Path
import re
import sys

SOURCE_URL = 'https://json.commanderspellbook.com/variants.json.gz'
# An ASCII x marker must attach to the quantity and be followed by whitespace.
# Keep the grammar identical in the standalone Validator and Spellbook analyzer.
ENTRY = re.compile(r'^([0-9]+)(?:[xX]\s+|×\s*|\s+)(\S.*)$')
SECTIONS = {
    'deck': 'main', 'main': 'main', 'mainboard': 'main', 'main deck': 'main',
    'commander': 'commander', 'commanders': 'commander',
    'sideboard': 'reject', 'maybeboard': 'reject', 'considering': 'reject',
}
PUBLIC_STATUSES = {'OK', 'E'}
SCOPES = ('commander', 'casual60', 'collection')


def read_deck(path: Path) -> tuple[Counter, Counter]:
    """Reject sideboards and malformed text instead of silently including them."""
    main, commanders = Counter(), Counter()
    section = 'main'
    for lineno, raw in enumerate(path.read_text(encoding='utf-8-sig').splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith(('#', '//')) or line.startswith(chr(96) * 3):
            continue
        name = line.strip('[]').rstrip(':').strip().lower()
        if name in SECTIONS:
            section = SECTIONS[name]
            continue
        if section == 'reject':
            raise ValueError(f'{path}:{lineno}: sideboard/maybeboard not supported')
        match = ENTRY.fullmatch(line)
        if not match:
            raise ValueError(f'{path}:{lineno}: malformed card line: {line!r}')
        count, card = int(match.group(1)), match.group(2).strip()
        if count <= 0:
            raise ValueError(f'{path}:{lineno}: quantity must be positive')
        (commanders if section == 'commander' else main)[card] += count
    return main + commanders, commanders


def load_card_search():
    """Reuse the trusted card_search.py module in GitHub or Project runtime."""
    candidates = [Path(__file__).resolve().parent / 'card_search.py']
    for ancestor in Path(__file__).resolve().parent.parents:
        candidates.append(ancestor / 'tools' / 'card_search.py')
    for file in candidates:
        if file.is_file():
            spec = importlib.util.spec_from_file_location('mtg_card_search_shared', file)
            if spec is None or spec.loader is None:
                continue
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module
    raise ValueError('Cannot find card_search.py; upload or install the original module')


def read_owned_collection(path: Path) -> Counter:
    """Read current CSV using the existing card_search.py ownership parser."""
    return Counter(load_card_search().read_collection(path))


def read_card_salt_csv(path: Path) -> dict:
    """Read voluntarily supplied, source-attributed CARD scores. No scraping."""
    import csv
    scores = {}
    with path.open('r', encoding='utf-8-sig', newline='') as stream:
        reader = csv.DictReader(stream)
        required = {'Name', 'SaltScore', 'Source'}
        if not reader.fieldnames or not required <= set(reader.fieldnames):
            raise ValueError('Card salt CSV requires Name,SaltScore,Source columns')
        for line_number, row in enumerate(reader, 2):
            name = (row.get('Name') or '').strip()
            source = (row.get('Source') or '').strip()
            literal = (row.get('SaltScore') or '').strip()
            if not name or not source:
                raise ValueError(f'Card salt CSV line {line_number}: Name and Source required')
            try:
                score = float(literal)
            except ValueError as exc:
                raise ValueError(f'Card salt CSV line {line_number}: invalid score') from exc
            if not 0 <= score <= 4 or score != score:
                raise ValueError(f'Card salt CSV line {line_number}: score outside 0..4')
            key = name.casefold()
            if key in scores:
                raise ValueError(f'Card salt CSV line {line_number}: duplicate card')
            scores[key] = {'score': score, 'source': source,
                           'as_of': (row.get('AsOf') or '').strip() or None}
    return scores


def combo_salt_metadata(variant: dict) -> dict:
    """Official combo-level community vote, never an individual card score."""
    value = variant.get('salt')
    votes = variant.get('saltVoteCount')
    # Do not coerce strings or booleans into statistical evidence.
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 4:
        value = None
    if isinstance(votes, bool) or not isinstance(votes, int) or votes < 0:
        votes = None
    return {'score': value, 'vote_count': votes,
            'scale': [0, 4], 'source': 'Commander Spellbook combo voting',
            'meaning': 'Community perception of combo annoyance; not win rate or card power'}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def load_snapshot(path: Path) -> dict:
    opener = gzip.open if path.name.lower().endswith('.gz') else open
    with opener(path, 'rt', encoding='utf-8') as f:
        document = json.load(f)
    if not isinstance(document, dict) or not isinstance(document.get('variants'), list):
        raise ValueError('Expected Commander Spellbook export with variants array')
    return document


def require_cards(uses: object) -> tuple[Counter, set[str]]:
    if not isinstance(uses, list) or not uses:
        raise ValueError('Empty or invalid uses')
    required, commanders = Counter(), set()
    for use in uses:
        if not isinstance(use, dict) or not isinstance(use.get('card'), dict):
            raise ValueError('Malformed card ingredient')
        card, count = use['card'].get('name'), use.get('quantity')
        if not isinstance(card, str) or not card.strip() or type(count) is not int or count <= 0:
            raise ValueError('Invalid card name or required quantity')
        required[card.strip()] += count
        if use.get('mustBeCommander') is True:
            commanders.add(card.strip())
    return required, commanders


def analyze(deck: Counter, commanders: Counter, document: dict, *,
            commander: str | None = None, identity: str | None = None,
            limit: int = 30, scope: str = 'commander',
            card_salt_scores: dict | None = None) -> dict:
    if limit < 0 or limit > 1000:
        raise ValueError('limit must be between 0 and 1000')
    if scope not in SCOPES:
        raise ValueError('Invalid analysis scope')
    if scope == 'casual60' and sum(deck.values()) != 60:
        raise ValueError('casual60 requires exactly 60 cards')
    if scope != 'commander' and (commander is not None or sum(commanders.values()) > 0):
        raise ValueError('Casual and collection scopes must not specify a Commander')
    if scope != 'commander' and identity is not None:
        raise ValueError('Commander identity filtering is not a casual 60-card legality rule')
    chosen = commander or (next(iter(commanders)) if len(commanders) == 1 else None)
    normalized_deck = Counter()
    for name, count in deck.items():
        if not isinstance(name, str) or type(count) is not int or count < 0:
            raise ValueError('Deck or collection has invalid name/quantity')
        normalized_deck[name.casefold()] += count

    if chosen and (deck[chosen] != 1 or (commanders and commanders.get(chosen) != 1)):
        raise ValueError('Selected commander must appear exactly once in the deck/Commander section')
    if commander and commanders and commander not in commanders:
        raise ValueError('Explicit commander differs from Commander section')
    normalized_identity = None
    if identity is not None:
        normalized_identity = set(identity.upper().replace('C', ''))
        if not normalized_identity <= set('WUBRG'):
            raise ValueError('Color identity must consist of WUBRG symbols (and optional C)')

    counts, exact, near, seen_ids = Counter(), [], [], set()
    for variant in document['variants']:
        counts['variants_examined'] += 1
        if not isinstance(variant, dict):
            counts['invalid_variants'] += 1
            continue
        vid = variant.get('id')
        if not isinstance(vid, str) or not vid or vid in seen_ids:
            counts['invalid_variants'] += 1
            continue
        seen_ids.add(vid)
        if variant.get('status') not in PUBLIC_STATUSES:
            counts['nonpublic_variants'] += 1
            continue
        if variant.get('spoiler') is True:
            counts['spoiler_variants_skipped'] += 1
            continue
        templates = variant.get('requires')
        if not isinstance(templates, list):
            counts['invalid_variants'] += 1
            continue
        if templates:
            counts['template_variants_unverified'] += 1
            continue
        try:
            ingredients, required_commanders = require_cards(variant.get('uses'))
        except ValueError:
            counts['invalid_variants'] += 1
            continue
        if required_commanders and scope != 'commander':
            counts['requires_commander_excluded'] += 1
            continue
        if required_commanders and not chosen:
            counts['commander_unknown_variants'] += 1
            continue
        if required_commanders - {chosen}:
            counts['wrong_commander_variants'] += 1
            continue
        combo_identity = variant.get('identity')
        if normalized_identity is not None:
            if not isinstance(combo_identity, str) or not set(combo_identity.upper()) <= set('WUBRGC'):
                counts['identity_unknown_variants'] += 1
                continue
            if not (set(combo_identity.upper()) - {'C'}) <= normalized_identity:
                counts['outside_selected_identity'] += 1
                continue
        missing = {card: n - normalized_deck.get(card.casefold(), 0) for card, n in ingredients.items()
                   if n > normalized_deck.get(card.casefold(), 0)}
        missing_total = sum(missing.values())
        if missing_total > 1:
            continue
        produces = []
        if isinstance(variant.get('produces'), list):
            for obj in variant['produces']:
                feature = obj.get('feature') if isinstance(obj, dict) else None
                name = feature.get('name') if isinstance(feature, dict) else None
                if isinstance(name, str) and name:
                    produces.append(name)
        item = {
            'variant_id': vid, 'required_cards': dict(sorted(ingredients.items())),
            'missing_cards': missing, 'produces': produces,
            'bracket_tag': variant.get('bracketTag'),
            'variant_status': variant.get('status'),
            'required_commander_cards': sorted(required_commanders),
            'unverified_conditions': [
                *(['commander_not_provided'] if not chosen else []),
                *(['color_identity_not_provided'] if normalized_identity is None else []),
                'zone_mana_timing_prerequisites_not_verified',
                'gameplay_legality_not_verified',
            ],
            'popularity': variant.get('popularity'),
            'combo_salt': combo_salt_metadata(variant),
            'card_salt': {
                name: card_salt_scores[name.casefold()]
                for name in ingredients
                if card_salt_scores is not None and name.casefold() in card_salt_scores
            },
            'prerequisites': variant.get('notablePrerequisites') if isinstance(
                variant.get('notablePrerequisites'), str) else None,
            'steps': variant.get('description') if isinstance(
                variant.get('description'), str) else None,
        }
        (exact if missing_total == 0 else near).append(item)
    def sort_key(item):
        popularity = item['popularity']
        return (-popularity if isinstance(popularity, int) else 0, item['variant_id'])
    exact.sort(key=sort_key)
    near.sort(key=sort_key)
    return {
        'status': 'INGREDIENT_SCREEN_ONLY', 'snapshot_source': SOURCE_URL,
        'snapshot_timestamp': document.get('timestamp'),
        'snapshot_version': document.get('version'),
        'deck_size': sum(deck.values()), 'commander': chosen,
        'analysis_scope': scope,
        'card_salt_source': ('EXTERNAL_USER_SUPPLIED_CSV' if card_salt_scores is not None
                             else 'NOT_PROVIDED'),
        'combo_salt_source': 'OFFICIAL_SPELLBOOK_SNAPSHOT_IF_PRESENT',
        'identity_user_supplied': identity,
        'total_exact_card_ingredient_candidates': len(exact),
        'total_one_card_missing_candidates': len(near),
        'exact_card_ingredient_candidates': exact[:limit],
        'one_card_missing_candidates': near[:limit],
        'counts': dict(counts),
        'limitations': [
            'Matches mean card-name/quantity presence only, not executable combos or win conditions.',
            'Variants with templates are skipped; results are incomplete by design.',
            'No verification of mana, zones, prerequisites, card legality, commanders, other MTG rules or deck power.',
            'Commander and identity constraints only checked against manually provided or parsed values.',
            'No card-name aliases, double-faced names or Oracle-ID resolution.',
            'Salt scores may be absent; do not substitute zero for unknown.',
            'Combo salt is not card salt. External card scores require a source-attributed user file.',
            'No synergy strength, probability or combo playability inferred from ingredient matching.',
            'Casual60 mode checks deck length only; legality, color mana, max-four and ownership remain with the existing validator.',
            'Completeness is limited to Commander Spellbook public nonspoiler exported variants.',
        ],
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sources = parser.add_mutually_exclusive_group(required=True)
    sources.add_argument('--deck', type=Path, help='Existing decklist, 60 or Commander')
    sources.add_argument('--collection', type=Path, help='Active Name,Quantity inventory CSV')
    parser.add_argument('--mode', choices=SCOPES, default='commander',
                        help='Commander default; casual60 verifies exact 60; collection checks owned inventory')
    parser.add_argument('--card-salt-csv', type=Path,
                        help='Optional separately licensed, source-attributed Name,SaltScore,Source CSV')
    parser.add_argument('--oracle', type=Path,
                        help='Optional MTGJSON AtomicCards for a separate theme/synergy report')
    parser.add_argument('--theme',
                        help='Optional mechanic/strategy search; requires --oracle and card_search.py')
    parser.add_argument('--max-synergy-pairs', type=int, default=100)
    parser.add_argument('--snapshot', type=Path, required=True,
                        help='Offline variants.json.gz from official Commander Spellbook export')
    parser.add_argument('--commander', help='Exact commander card name; optional if deck has Commander section')
    parser.add_argument('--identity', help='Manually provided color identity, e.g. WUBRG, UR, or C')
    parser.add_argument('--limit', type=int, default=30)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args(argv)
    try:
        if args.collection:
            if args.mode != 'collection':
                raise ValueError('--collection requires --mode collection')
            deck, commander_section = read_owned_collection(args.collection), Counter()
            input_path = args.collection
        else:
            if args.mode == 'collection':
                raise ValueError('--mode collection requires --collection')
            deck, commander_section = read_deck(args.deck)
            input_path = args.deck
        document = load_snapshot(args.snapshot)
        card_salt = read_card_salt_csv(args.card_salt_csv) if args.card_salt_csv else None
        result = analyze(deck, commander_section, document, commander=args.commander,
                         identity=args.identity, limit=args.limit, scope=args.mode,
                         card_salt_scores=card_salt)
        result['input_sha256'] = sha256_file(input_path)
        result['deck_sha256'] = sha256_file(input_path) if args.deck else None
        result['snapshot_sha256'] = sha256_file(args.snapshot)
        result['input_type'] = 'collection_csv' if args.collection else 'decklist_txt'
        result['card_salt_sha256'] = sha256_file(args.card_salt_csv) if args.card_salt_csv else None
        if bool(args.theme) != bool(args.oracle):
            raise ValueError('--theme and --oracle must be supplied together')
        if args.theme:
            reader = load_card_search()
            oracle_data, oracle_meta = reader.read_atomic(args.oracle)
            owned = Counter({name.casefold(): quantity for name, quantity in deck.items()})
            pair_mode = args.theme.strip().casefold() == 'lifegain'
            themed = reader.search(
                oracle_data, collection=owned, owned_only=True, theme=args.theme,
                color_identity=None, limit=min(max(args.limit, 1), 500),
                synergy=pair_mode, max_synergy_pairs=args.max_synergy_pairs,
            )
            themed['oracle_version'] = oracle_meta.get('version')
            themed['oracle_sha256'] = sha256_file(args.oracle)
            known_names = {key.casefold() for key in oracle_data}
            themed['inventory_name_coverage'] = {
                'distinct_names_not_in_oracle': sum(
                    1 for name in owned if name not in known_names
                ),
            }
            result['theme_candidates'] = themed
            result['theme_vs_combo_note'] = (
                'Card Search role and pair matches are heuristic suggestions; '
                'Spellbook variant matches indicate ingredients only; '
                'neither guarantees playability.'
            )
        # Filenames and personally revealing local paths are excluded from report.

        output = json.dumps(result, indent=2, ensure_ascii=False) + '\n'
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(output, encoding='utf-8')
        else:
            print(output, end='')
        return 0
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError, EOFError) as exc:
        print(f'NOT_EXECUTED: {type(exc).__name__}: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
