#!/usr/bin/env python3
"""Opt-in smoke checks using a caller-provided, SHA-256-verified local AtomicCards file."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import card_search  # noqa: E402
import synergy_engine  # noqa: E402

MAX_COMPRESSED = 192 * 1024 * 1024
CASES = {
    "sacrifice": ("Ravenous Harpy", "Poison-Tip Archer"),
    "tokens": ("Sai, Master Thopterist", "Ajani's Welcome"),
    "proliferate": ("Evolution Sage", "Ajani's Pridemate"),
    "blink": ("Ephemerate", "Ravenous Chupacabra"),
    "artifacts": ("Sai, Master Thopterist", "Reckless Fireweaver"),
    "spellslinger": ("Shock", "Guttersnipe"),
    "landfall": ("Explore", "Tireless Tracker"),
    "counters": ("Ajani's Pridemate", "Conclave Mentor"),
}

NEGATIVES = {
    "tokens": ("Anointed Procession",),
    "artifacts": ("Academy Manufactor",),
    "blink": ("Bloodfell Caves",),
}


def verify_local_snapshot(source: Path, destination: Path, expected_sha256: str) -> int:
    """Hash the captured bytes and load only that private snapshot."""
    digest = hashlib.sha256()
    size = 0
    with source.open("rb") as stream, destination.open("xb") as dest:
        while block := stream.read(1 << 20):
            size += len(block)
            if size > MAX_COMPRESSED:
                raise ValueError("AtomicCards file exceeds size bound")
            digest.update(block)
            dest.write(block)
    if not size or digest.hexdigest() != expected_sha256.lower():
        raise ValueError("AtomicCards SHA-256 mismatch or empty file")
    return size


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--oracle", type=Path, required=True)
    parser.add_argument("--oracle-sha256", required=True, help="Expected hash of the chosen local snapshot")
    args = parser.parse_args()
    if len(args.oracle_sha256) != 64 or any(c not in "0123456789abcdefABCDEF" for c in args.oracle_sha256):
        parser.error("--oracle-sha256 must be 64 hexadecimal digits")
    with tempfile.TemporaryDirectory(prefix="synergy-real-oracle-") as work:
        suffix = ".json.gz" if args.oracle.suffix.lower() == ".gz" else ".json"
        path = Path(work) / ("AtomicCards" + suffix)
        size = verify_local_snapshot(args.oracle, path, args.oracle_sha256)
        cards, meta = card_search.read_atomic(path)
        if len(cards) < 20000:
            raise AssertionError("Expected full MTGJSON snapshot, not incomplete selection")
        results = {}
        for theme, (source, payoff) in CASES.items():
            names = {source, payoff, *NEGATIVES.get(theme, ())}
            missing = names.difference(cards)
            if missing:
                raise AssertionError(f"{theme}: real Oracle names missing: {sorted(missing)}")
            # Fictional counts for PUBLIC card names, NOT a user-owned collection.
            owned = Counter({name.casefold(): 1 for name in names})
            subset = {name: cards[name] for name in names}
            result = synergy_engine.analyze(subset, owned, theme=theme, limit=20)
            expected = (source, payoff)
            pairs = {(p["source"], p["payoff"]) for p in result["pairs"]}
            if expected not in pairs:
                raise AssertionError(
                    f"{theme}: missing known public source/payoff relation, "
                    f"sources={result['source_count']}, payoffs={result['payoff_count']}, "
                    f"possible={result['possible_pairs']}"
                )
            for negative in NEGATIVES.get(theme, ()):
                if any(p["source"] == negative for p in result["pairs"]):
                    raise AssertionError(f"{theme}: invalid stand-alone source {negative}")
                if theme == "blink" and any(p["payoff"] == negative for p in result["pairs"]):
                    raise AssertionError(f"{theme}: invalid creature-blink payoff {negative}")
            for p in result["pairs"]:
                if p["status"] != "POSSIBLE_SYNERGY_NOT_RULES_VERIFIED":
                    raise AssertionError("Missing conservative inference label")
                if p["source_owned_copies"] != 1 or p["payoff_owned_copies"] != 1:
                    raise AssertionError("Unexpected non-owned ingredient")
            results[theme] = {
                "sources": result["source_count"], "payoffs": result["payoff_count"],
                "pairs": result["returned_pairs"], "known_relation_pass": True,
                "negative_case_pass": True,
            }
        lifegain_expected = {
            "Lightning Helix": {"core", "interaction"},
            "Regal Bloodlord": {"payoff"},
            "Indulging Patrician": {"core", "payoff"},
        }
        for name, expected_roles in lifegain_expected.items():
            if name not in cards:
                raise AssertionError(f"Missing real Oracle name: {name}")
            for variant in cards[name]:
                roles = set(card_search.classify_lifegain_variant(variant))
                roles.update(card_search.classify_interaction_variant(variant))
                if not expected_roles <= roles or (name == "Regal Bloodlord" and "core" in roles):
                    raise AssertionError(f"Unexpected real Oracle lifegain roles for {name}: {sorted(roles)}")
        owned = Counter({name.casefold(): 1 for name in lifegain_expected})
        life_result = card_search.search(
            {name: cards[name] for name in lifegain_expected}, theme="lifegain",
            collection=owned, owned_only=True, synergy=True,
        )
        if not any(pair["source"] == "Lightning Helix"
                   and pair["payoff"] == "Indulging Patrician"
                   and pair["requires_threshold_check"]
                   for pair in life_result["synergy_analysis"]["pairs"]):
            raise AssertionError("Missing real Oracle threshold-dependent pair")
        print(json.dumps({
            "source": "VERIFIED_LOCAL_ATOMICCARDS", "date": meta.get("date"),
            "version": meta.get("version"),
            "sha256": args.oracle_sha256.lower(), "bytes": size,
            "oracle_distinct_cards": len(cards), "result": "PASS",
            "strategy_checks": results,
            "lifegain_checks": sorted(lifegain_expected),
            "note": "Public real Oracle fixture names only; NOT an audit of personal collection coverage",
        }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
