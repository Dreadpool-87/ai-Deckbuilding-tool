#!/usr/bin/env python3
"""KISS v0.5: run existing Card Search, Synergy Engine and optional Spellbook.

No new card parser, combo rules, ranking algorithm, network calls or deckbuilder.
Always supply the active current-chat collection. Outputs remain provisional.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

VERSION = "0.5.0"
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent


def load_module(name: str, candidates: list[Path]):
    """Load an existing repo module, or its alongside-the-script Project copy."""
    path = next((p for p in candidates if p.is_file()), None)
    if path is None:
        raise ValueError(f"Required existing module {name} not found")
    spec = importlib.util.spec_from_file_location("mtg_v05_" + name, path)
    if spec is None or spec.loader is None:
        raise ValueError(f"Cannot load existing module {name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def commander_identity(cards: dict, name: str) -> str | None:
    """Use the Oracle identity only when all variants agree."""
    variants = cards.get(name)
    if not isinstance(variants, list) or not variants:
        return None
    identities = []
    for variant in variants:
        if not isinstance(variant, dict) or not isinstance(variant.get("colorIdentity"), list):
            return None
        colors = variant["colorIdentity"]
        if any(type(c) is not str or c not in "WUBRG" for c in colors):
            return None
        identities.append(set(colors))
    if any(x != identities[0] for x in identities[1:]):
        return None
    return "".join(c for c in "WUBRG" if c in identities[0]) or "C"


def virtual_basics(cards: dict, basics: frozenset) -> list[str]:
    """Names available without ownership limits; do not edit the active CSV."""
    result = []
    for name in sorted(basics):
        variants = cards.get(name)
        if isinstance(variants, list) and variants and all(
            isinstance(v, dict) and
            isinstance(v.get("types"), list) and "Land" in v["types"] and
            isinstance(v.get("supertypes"), list) and "Basic" in v["supertypes"]
            for v in variants
        ):
            result.append(name)
    return result


def screen_spellbook_colors(document: dict, cards: dict, selected: set[str],
                            spellbook) -> tuple[dict, dict]:
    """Conservatively screen optional casual combo ingredients against MTGJSON.

    Unknown/missing Oracle identities are excluded from color suggestions, not
    guessed as legal or castable. Spellbook itself remains unchanged.
    """
    index = {name.casefold(): variants for name, variants in cards.items()
             if isinstance(name, str)}
    kept = []
    counts = Counter()
    for item in document["variants"]:
        if not isinstance(item, dict):
            kept.append(item)
            continue
        try:
            ingredients, _ = spellbook.require_cards(item.get("uses"))
        except ValueError:
            kept.append(item)  # Existing Spellbook validation owns malformed data.
            continue
        states = []
        for name in ingredients:
            variants = index.get(name.casefold())
            if (not isinstance(variants, list) or not variants or
                    not all(isinstance(v, dict) for v in variants)):
                states.append(None)
                continue
            identities = [v.get("colorIdentity") for v in variants]
            if any(not isinstance(x, list) or
                   any(type(color) is not str or color not in "WUBRG" for color in x)
                   for x in identities):
                states.append(None)
            elif all(set(x) <= selected for x in identities):
                states.append(True)
            else:
                states.append(False)
        if False in states:
            counts["excluded_off_color_variants"] += 1
        elif None in states:
            counts["unverified_or_missing_oracle_variants"] += 1
        else:
            kept.append(item)
    return ({**document, "variants": kept}, dict(counts))


def build_report(*, oracle: Path, collection: Path, theme: str,
                 mode: str = "collection", deck: Path | None = None,
                 commander: str | None = None, snapshot: Path | None = None,
                 limit: int = 30, colors: str | None = None) -> dict:
    if not isinstance(theme, str) or not theme.strip():
        raise ValueError("Nonempty --theme required")
    if mode not in ("collection", "casual", "commander"):
        raise ValueError("Mode must be collection, casual or commander")
    if not 1 <= limit <= 100:
        raise ValueError("Limit must be between 1 and 100")
    if (mode == "collection") != (deck is None):
        raise ValueError("Collection mode has no --deck; casual/commander requires --deck")
    if mode == "commander" and not commander:
        raise ValueError("Commander mode requires --commander")
    if mode != "commander" and commander:
        raise ValueError("--commander only applies to commander mode")
    if mode == "commander" and colors is not None:
        raise ValueError("--colors is a Casual deck-building preference, not Commander identity")

    card_search = load_module("card_search", [
        HERE / "card_search.py", ROOT / "tools" / "card_search.py"])
    synergy = load_module("synergy_engine", [
        HERE / "synergy_engine.py", ROOT / "tools" / "synergy_engine.py"])
    cards, meta = card_search.read_atomic(oracle)
    owned = card_search.read_collection(collection)
    selected_colors = None
    if colors is not None and colors.strip().upper() != "ANY":
        selected_colors = card_search.color_set(colors)
    if colors is not None and colors.strip().upper() == "ANY":
        selected_colors = None
    active = owned
    deck_counts = None
    validation = {"status": "NOT_APPLICABLE_TO_COLLECTION"}
    identity = None

    if deck is not None:
        validator = load_module("validator", [
            HERE / "MTG_Deck_Validator_v1.1.1.py",
            ROOT / "validator/MTG_Deck_Validator_v1.1.1.py"])
        deck_counts, issues = validator.parse_deck(deck)
        validation = validator.validate(
            validator.read_collection(collection), cards, deck_counts,
            mode="commander" if mode == "commander" else "casual",
            commander=commander, exact_60=False, parse_errors=issues,
        )
        if validation["status"] == "FAIL":
            return {
                "version": VERSION, "status": "BLOCKED_INVALID_DECK",
                "mode": mode, "theme": theme, "validation": validation,
                "card_search": {"status": "NOT_EXECUTED"},
                "synergies": {"status": "NOT_EXECUTED"},
                "combos": {"status": "NOT_EXECUTED"},
                "note": "Fix existing deck validation failures before analysis.",
            }
        active = Counter({n.casefold(): q for n, q in deck_counts.items()})
        if mode == "commander":
            identity = commander_identity(cards, commander)

    normalized_theme = theme.strip().casefold()
    is_lifegain = normalized_theme == "lifegain"
    search = card_search.search(
        cards, theme=theme, collection=active, owned_only=True,
        color_identity=(identity if mode == "commander" else colors),
        synergy=is_lifegain, limit=limit, max_synergy_pairs=limit,
    )
    if is_lifegain:
        pair_report = search.pop("synergy_analysis")
    elif synergy.ALIASES.get(normalized_theme, normalized_theme) in synergy.PROFILES:
        pair_report = synergy.analyze(
            cards, active, theme=theme,
            color_identity=(identity if mode == "commander" and identity else
                            colors if mode != "commander" and colors is not None else "ANY"),
            limit=limit,
        )
    else:
        pair_report = {
            "status": "UNSUPPORTED_PAIR_PROFILE",
            "reason": "Card Search can still find theme mentions; no pair inference available.",
            "theme": theme,
        }

    combo_report = {"status": "NOT_EXECUTED", "reason": "No Spellbook snapshot supplied"}
    basic_policy = []
    combo_color_screen = None
    if snapshot is not None:
        spellbook = load_module("spellbook", [
            HERE / "analyze.py", ROOT / "integrations/commander-spellbook/analyze.py"])
        scope = ("collection" if mode == "collection"
                 else "commander" if mode == "commander" else "casual60")
        if mode == "casual" and sum(deck_counts.values()) != 60:
            combo_report = {
                "status": "NOT_EXECUTED",
                "reason": "Existing Spellbook casual60 matcher supports exactly 60 cards; "
                          "validator permits casual decks of 60 or more.",
            }
        else:
            combo_counts = Counter(deck_counts) if deck_counts is not None else Counter(owned)
            if mode == "collection":
                basic_policy = virtual_basics(cards, card_search.BASICS)
                # Sentinel only for this optional ingredient screen, NOT physical
                # ownership, deck contents or a change to the collection.
                combo_counts.update({name: 10000 for name in basic_policy})
            document = spellbook.load_snapshot(snapshot)
            if selected_colors is not None:
                document, combo_color_screen = screen_spellbook_colors(
                    document, cards, selected_colors, spellbook
                )
            combo_report = spellbook.analyze(
                combo_counts,
                Counter({commander: 1}) if mode == "commander" else Counter(),
                document,
                commander=commander,
                identity=identity if mode == "commander" else None,
                scope=scope, limit=limit,
            )
            combo_report["snapshot_sha256"] = sha256_file(snapshot)
            if combo_color_screen is not None:
                combo_report["casual_color_screen"] = combo_color_screen
            if mode == "collection":
                # The underlying matcher calls every input a "deck"; here it is
                # NOT a deck, and virtual Basics must never inflate ownership.
                combo_report["deck_size"] = None
                combo_report["collection_owned_copies"] = sum(owned.values())
                combo_report["availability_basis"] = (
                    "ACTIVE_COLLECTION_PLUS_UNLIMITED_BASIC_POLICY")

    partial = (
        validation.get("status") == "UNVERIFIED" or
        pair_report.get("status") == "UNSUPPORTED_PAIR_PROFILE" or
        combo_report.get("status") == "NOT_EXECUTED" or
        (mode == "commander" and identity is None) or
        (combo_color_screen is not None and
         combo_color_screen.get("unverified_or_missing_oracle_variants", 0) > 0)
    )
    return {
        "version": VERSION,
        "status": "PARTIAL" if partial else "COMPLETED_WITH_LIMITATIONS",
        "mode": mode,
        "selection_scope": "ACTIVE_COLLECTION" if deck is None else "SUBMITTED_DECK",
        "theme": theme,
        "oracle_version": meta.get("version"),
        "source_sha256": {
            "oracle": sha256_file(oracle),
            "collection": sha256_file(collection),
            "deck": sha256_file(deck) if deck is not None else None,
        },
        "validation": {
            "status": validation["status"],
            "checks": validation.get("checks"),
            "failures": validation.get("failures"),
            "uncertainties": validation.get("uncertainties"),
        },
        "commander_identity_from_oracle": identity,
        "selected_casual_colors": colors if mode != "commander" else None,
        "collection_basic_policy": (
            {"virtual_basic_names": basic_policy, "representation": "matching-only sentinel"}
            if mode == "collection" and snapshot is not None else None
        ),
        "card_search": search,
        "synergies": pair_report,
        "combos": combo_report,
        "limitations": [
            "Heuristic synergies are NOT known combos or gameplay verification.",
            "Spellbook finds named card ingredients, NOT a rules-executable combo.",
            "Power level, playability, turn speed and win rate are NOT assessed.",
            "Commander/casual format banlists and card-specific exceptions may need separate review.",
            "No collection, deck or MTGJSON contents are saved outside the chosen report.",
            "This is a bounded thematic report, not exhaustive deck optimization.",
            "Optional Casual color filtering uses conservative Oracle color identity; "
            "it is not Commander legality, spell castability or a complete color-cost audit.",
        ],
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--oracle", required=True, type=Path)
    parser.add_argument("--collection", required=True, type=Path)
    parser.add_argument("--theme", required=True)
    parser.add_argument("--mode", choices=("collection", "casual", "commander"),
                        default="collection")
    parser.add_argument("--deck", type=Path)
    parser.add_argument("--commander")
    parser.add_argument("--colors", help="Optional Casual color preference, e.g. UG; not Commander identity")
    parser.add_argument("--snapshot", type=Path, help="Optional local Spellbook variants.json.gz")
    parser.add_argument("--limit", type=int, default=30)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        result = build_report(
            oracle=args.oracle, collection=args.collection, theme=args.theme,
            mode=args.mode, deck=args.deck, commander=args.commander,
            snapshot=args.snapshot, limit=args.limit, colors=args.colors,
        )
        rendered = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(rendered, encoding="utf-8")
        else:
            print(rendered, end="")
        return 2 if result["status"] == "BLOCKED_INVALID_DECK" else 0
    except (OSError, ValueError, TypeError, json.JSONDecodeError, EOFError) as exc:
        print(f"NOT_EXECUTED: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
