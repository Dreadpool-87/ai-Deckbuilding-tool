#!/usr/bin/env python3
"""Bounded, collection-only strategic card-pair discovery, v0.4.

Complement to card_search.py and Commander Spellbook, not a rules engine.
No unowned cards, internet access, winrate, or automatic deck construction.
"""
from __future__ import annotations

import argparse
from collections import Counter
import importlib.util
import json
from pathlib import Path
import re
import sys


VERSION = "0.4.0"
MAX_PAIRS = 500
ALIASES = {
    "aristocrats": "sacrifice", "sac": "sacrifice",
    "token": "tokens", "blink/etb": "blink", "etb": "blink",
    "artifact": "artifacts", "spells": "spellslinger",
    "landfall": "landfall", "counter": "counters",
}

# Exact bounded evidence patterns; no claims of complete Oracle coverage.
# A source supplies a useful event or ingredient, a payoff can benefit from it.
PROFILES = {
    "sacrifice": {
        "event": "SACRIFICE_OWN_CREATURE_CAN_TRIGGER_DEATH_PAYOFF",
        "source": (
            r"\bsacrifice (?:a|an|another|one or more|two|three|x)"
            r"\s+(?:\w+\s+){0,5}creatures?\b",
        ),
        "payoff": (
            r"\bwhenever\b[^\n.!?]{0,130}\b(?:dies?|is sacrificed)\b",
            r"\bwhenever you sacrifice\b[^\n.!?]{0,130}",
        ),
    },
    "tokens": {
        "event": "TOKEN_CREATION_CAN_TRIGGER_TOKEN_OR_ETB_PAYOFF",
        "source": (r"\bcreate\b[^\n.!?]{0,160}\btokens?\b",),
        "payoff": (
            r"\bwhenever\b[^\n.!?]{0,130}\btokens?\b[^\n.!?]{0,90}\b(?:enters?|dies?|leaves?)\b",
            r"\bwhenever\b[^\n.!?]{0,110}\bcreatures?\b[^\n.!?]{0,80}\benters?\b",
        ),
    },
    "proliferate": {
        "event": "PROLIFERATE_CAN_ADD_COUNTERS_ALREADY_PRESENT",
        "source": (r"\bproliferate\b",),
        "payoff": (
            r"\bput\b[^\n.!?]{0,100}(?:\+1/\+1|charge|loyalty|poison)\s+counters?\b",
            r"\benters?\b[^\n.!?]{0,80}(?:\+1/\+1|charge|loyalty)\s+counters?\b",
        ),
    },
    "blink": {
        "event": "BLINK_REENTRY_CAN_TRIGGER_ETB",
        "source": (
            r"\bexile (?:target|up to one target|another target|this|that) "
            r"(?:\w+\s+){0,5}(?:creature|permanent)\b[^\n]{0,175}"
            r"\breturn (?:it|that card|them)\b[^\n]{0,90}\bbattlefield\b",
        ),
        "payoff": (
            r"\bwhen(?:ever)?\b[^\n.!?]{0,110}\benters?\b",
        ),
    },
    "artifacts": {
        "event": "ARTIFACT_TOKEN_CREATION_CAN_TRIGGER_ARTIFACT_PAYOFF",
        "source": (
            r"\bcreate\b[^\n.!?]{0,160}\b(?:Treasure|Food|Clue|Map|artifact)\b[^\n.!?]{0,70}\btokens?\b",
        ),
        "payoff": (
            r"\bwhenever\b[^\n.!?]{0,130}\bartifacts?\b[^\n.!?]{0,100}\b(?:enters?|dies?|leaves?|sacrificed)\b",
            r"\bfor each artifact you control\b",
        ),
    },
    "spellslinger": {
        "event": "CASTING_INSTANT_OR_SORCERY_CAN_TRIGGER_SPELL_PAYOFF",
        "source_type": ("Instant", "Sorcery"),
        "payoff": (
            r"\bwhenever you cast\b[^\n.!?]{0,100}\b(?:instant|sorcery|noncreature|spell)\b",
        ),
    },
    "landfall": {
        "event": "ADDITIONAL_LAND_ENTRY_CAN_TRIGGER_LANDFALL",
        "source": (
            r"\b(?:play (?:an?|one|two|three|four|\d+) additional lands?|"
            r"play up to [^\n.!?]{0,60}additional lands?)\b",
            r"\bput\b[^\n.!?]{0,130}\bland\b[^\n.!?]{0,100}\bonto the battlefield\b",
        ),
        "payoff": (
            r"\blandfall\b[^\n]*",
            r"\bwhenever\b[^\n.!?]{0,90}\bland\b[^\n.!?]{0,80}\benters?\b",
        ),
    },
    "counters": {
        "event": "PUT_PLUS_COUNTERS_TO_ENABLE_COUNTER_PAYOFF",
        "source": (
            r"\bput (?:a|an|one|two|three|x|\d+) \+1/\+1 counters?\b",
        ),
        "payoff": (
            r"\bwhenever\b[^\n.!?]{0,120}\bcounters?\b[^\n.!?]{0,100}\b(?:put|placed|removed)\b",
            r"\bif one or more \+1/\+1 counters? would be put\b",
            r"\bfor each \+1/\+1 counter\b",
        ),
    },
}


def load_card_search():
    """Load the one canonical MTGJSON and ownership reader, never copy it."""
    path = Path(__file__).with_name("card_search.py")
    if not path.is_file():
        raise ValueError("card_search.py must be next to synergy_engine.py")
    spec = importlib.util.spec_from_file_location("mtg_shared_card_search", path)
    if spec is None or spec.loader is None:
        raise ValueError("Cannot load card_search.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def evidence(text: str, expressions: tuple[str, ...]) -> str | None:
    for pattern in expressions:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            start = text.rfind("\n", 0, match.start()) + 1
            stop = text.find("\n", match.end())
            return text[start:stop if stop != -1 else len(text)].strip()[:450]
    return None


def classify(card: dict, profile: dict, shared) -> tuple[str | None, str | None]:
    """Return source/payoff evidence; no rules-legal inference."""
    text = card.get("text")
    if not isinstance(text, str):
        return None, None
    # Remove reminder text through the existing canonical function.
    text = shared.remove_reminder_text(text)
    types = card.get("types") if isinstance(card.get("types"), list) else []
    if "source_type" in profile and set(types).intersection(profile["source_type"]):
        source = "Card type: " + ", ".join(sorted(set(types) & set(profile["source_type"])))
    else:
        source = evidence(text, profile.get("source", ()))
    payoff = evidence(text, profile["payoff"])
    if profile["event"].startswith("SACRIFICE") and source:
        if re.search(r"(?i)\b(?:whenever|when|if)\b[^\n.!?]{0,60}\byou sacrifice\b", source):
            source = None
    # Replacement effects need an independent source. A card that doubles
    # token creation is not a token maker by itself (same for artifact tokens).
    if profile["event"].startswith(("TOKEN_CREATION", "ARTIFACT_TOKEN")) and source:
        if re.search(r"(?i)\b(?:if|when|whenever)\b[^\n.!?]{0,110}"
                     r"\bwould create\b|\binstead create\b", source):
            source = None
    # A land self-ETB trigger cannot be enabled by creature-target-only blink.
    # Permanents-other-than-creatures can be reconsidered with a typed target
    # compatibility model; v0.4 conservatively excludes them as blink payoffs.
    if profile["event"].startswith("BLINK") and payoff and "Creature" not in types:
        if re.search(r"(?i)\bwhen(?:ever)? (?:this|that)\s+"
                     r"(?:land|artifact|enchantment|permanent)\s+enters?\b", payoff):
            payoff = None
    # Responding to proliferate is not the act of proliferating.
    if profile["event"].startswith("PROLIFERATE") and source:
        if re.search(r"(?i)\b(?:whenever|when|if)\s+you proliferate\b", source):
            source = None
    return source, payoff


def analyze(cards: dict, owned: Counter, *, theme: str, color_identity: str = "ANY",
            limit: int = 100) -> dict:
    """Offline, collection-only, bounded pair suggestions, not proven combos."""
    normalized = ALIASES.get(theme.strip().casefold(), theme.strip().casefold())
    if normalized not in PROFILES:
        raise ValueError("Unsupported pair profile; use card_search.py for generic theme discovery")
    if not 1 <= limit <= MAX_PAIRS:
        raise ValueError("limit must be between 1 and 500")
    if owned is None:
        raise ValueError("Current collection is mandatory")
    shared = load_card_search()
    identity = None if color_identity.strip().upper() == "ANY" else shared.color_set(color_identity)
    profile = PROFILES[normalized]
    sources, payoffs, uncertainties = [], [], Counter()
    known = {n.casefold() for n in cards if isinstance(n, str)}
    normalized_owned = Counter()
    for name, count in owned.items():
        if not isinstance(name, str) or type(count) is not int or count < 0:
            raise ValueError("Invalid owned quantity")
        normalized_owned[name.casefold()] += count

    for name, variants in cards.items():
        if not isinstance(name, str) or normalized_owned[name.casefold()] < 1:
            continue
        if not isinstance(variants, list) or not variants or not all(isinstance(v, dict) for v in variants):
            uncertainties["malformed_oracle_records"] += 1
            continue
        if identity is not None:
            outcomes = [
                shared.evaluate_variant(
                    v, name=None, abilities=[], keywords=[], oracle_text=[],
                    card_type=None, subtype=None, identity=identity,
                    min_mv=None, max_mv=None
                ) for v in variants
            ]
            if outcomes != [True] * len(variants):
                uncertainties["outside_or_uncertain_color_identity"] += 1
                continue
        matched = [classify(v, profile, shared) for v in variants]
        for kind, index, output in (("source", 0, sources), ("payoff", 1, payoffs)):
            evidence_lines = [match[index] for match in matched]
            if any(evidence_lines) and not all(evidence_lines):
                uncertainties["conflicting_oracle_variants"] += 1
                continue
            if all(evidence_lines):
                first = variants[0]
                types = first.get("types")
                types = types if isinstance(types, list) else []
                value = first.get("manaValue")
                mv = value if type(value) in (int, float) else None
                text = first.get("text") if isinstance(first.get("text"), str) else ""
                repeatable = bool(re.search(r"(?i)\b(?:whenever|at the beginning|each time)\b|:", text))
                output.append({
                    "name": name, "owned_copies": normalized_owned[name.casefold()],
                    "evidence": evidence_lines[0], "types": types,
                    "mana_value": mv, "repeatable_hint": repeatable,
                })
    def order(item: dict) -> tuple:
        types = set(item["types"])
        permanent = bool(types.intersection({"Creature", "Artifact", "Enchantment", "Planeswalker"}))
        return (
            not (permanent and item["repeatable_hint"]),
            not permanent,
            "Land" in types,
            item["mana_value"] if item["mana_value"] is not None else 999,
            item["name"].casefold(),
        )
    sources.sort(key=order)
    payoffs.sort(key=order)
    common = len({s["name"] for s in sources} & {p["name"] for p in payoffs})
    possible_pairs = len(sources) * len(payoffs) - common
    pairs = []
    if payoffs:
        # Round-robin across distinct owned sources. Avoid filling the result
        # with one source and many payoffs simply due to lexical ordering.
        for offset in range(len(payoffs)):
            for i, source in enumerate(sources):
                payoff = payoffs[(i + offset) % len(payoffs)]
                if source["name"] == payoff["name"]:
                    continue
                pairs.append({
                    "source": source["name"],
                    "payoff": payoff["name"],
                    "source_owned_copies": source["owned_copies"],
                    "payoff_owned_copies": payoff["owned_copies"],
                    "source_evidence": source["evidence"],
                    "payoff_evidence": payoff["evidence"],
                    "relation": profile["event"],
                    "confidence": "HEURISTIC",
                    "conditional": True,
                    "status": "POSSIBLE_SYNERGY_NOT_RULES_VERIFIED",
                })
                if len(pairs) == limit:
                    break
            if len(pairs) == limit:
                break

    return {
        "tool_version": VERSION,
        "status": "BOUNDED_OWNED_SYNERGIES_NOT_COMBOS",
        "theme": normalized,
        "requested_theme": theme,
        "color_identity_subset_of": color_identity,
        "source_count": len(sources),
        "payoff_count": len(payoffs),
        "possible_pairs": possible_pairs,
        "returned_pairs": len(pairs),
        "truncated": possible_pairs > len(pairs),
        "pair_limit": limit,
        "collection_coverage": {
            "distinct_owned_names_absent_from_oracle": sum(
                count > 0 and name not in known for name, count in normalized_owned.items()
            ),
        },
        "uncertainties": dict(uncertainties),
        "pairs": pairs,
        "limitations": [
            "Heuristics discover possible card relationships, not executable combos.",
            "No validation of mana, zones, timing, targeting, deck legality or win rate.",
            "Pairs require separate cards and at least one owned copy of each.",
            "False positives/negatives are possible; Oracle excerpts provide evidence, not proof.",
            "The active CSV is the only source of ownership; missing Oracle names are UNKNOWN.",
            "Pair cap is applied after source/payoff detection; totals remain untruncated.",
        ],
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--oracle", type=Path, required=True)
    parser.add_argument("--collection", type=Path, required=True)
    parser.add_argument("--theme", required=True)
    parser.add_argument("--identity", default="ANY")
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        shared = load_card_search()
        cards, metadata = shared.read_atomic(args.oracle)
        owned = shared.read_collection(args.collection)
        report = analyze(cards, owned, theme=args.theme,
                         color_identity=args.identity, limit=args.limit)
        report["oracle_version"] = metadata.get("version")
        rendered = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(rendered, encoding="utf-8")
        else:
            print(rendered, end="")
        return 0
    except (ValueError, OSError, UnicodeError, EOFError, json.JSONDecodeError) as exc:
        print(f"NOT_EXECUTED: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
