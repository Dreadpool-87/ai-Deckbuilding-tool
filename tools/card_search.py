#!/usr/bin/env python3
"""MTG Card Search v0.3: offline, auditable candidate discovery (Python 3.9+).

Consumes MTGJSON AtomicCards and an optional active collection CSV. Separates
DIRECT printed ability searches from general THEME role suggestions. Heuristic
synergy suggestions are never presented as verified complete rules interactions.

No database download, upload, ownership inference, format legality claim, or deck
construction occurs. The existing v0.1 public search API and CLI remain usable.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
import gzip
import json
from pathlib import Path
import re
import sys
from typing import Any

VERSION = "0.3.0"
BASICS = frozenset({
    "Plains", "Island", "Swamp", "Mountain", "Forest", "Wastes",
    "Snow-Covered Plains", "Snow-Covered Island", "Snow-Covered Swamp",
    "Snow-Covered Mountain", "Snow-Covered Forest",
})
COLOR_ORDER = "WUBRG"
MAX_LIMIT = 500
ROLE_ORDER = ("core", "enabler", "payoff", "synergy", "interaction")
ROLE_SET = frozenset(ROLE_ORDER)
FACE_ALIAS_LAYOUTS = frozenset({"adventure", "flip", "modal_dfc", "prepare", "split", "transform"})

# Heuristics are intentionally *small and explicit*; they are not MTG rules.
# A new mechanic need not be registered to work as an exact Oracle-text theme.
ALIASES = {
    "aristocrats": "sacrifice",
    "treasures": "treasure",
    "tokens": "token",
    "+1/+1 counters": "+1/+1 counter",
    "counters": "+1/+1 counter",
}


def reject_duplicate_oracle_keys(pairs: list[tuple[str, Any]]) -> dict:
    record = {}
    for key, value in pairs:
        if key in record:
            raise ValueError(f"Duplicate Oracle JSON key: {key!r}")
        record[key] = value
    return record


def read_atomic(path: Path) -> tuple[dict, dict]:
    """Load MTGJSON AtomicCards.json(.gz), not AllPrintings or an arbitrary JSON."""
    opener = gzip.open if str(path).lower().endswith(".gz") else open
    with opener(path, "rt", encoding="utf-8") as handle:
        raw = json.load(handle, object_pairs_hook=reject_duplicate_oracle_keys)
    if not isinstance(raw, dict):
        raise ValueError("MTGJSON root must be a JSON object")
    cards = raw.get("data", raw)
    if not isinstance(cards, dict):
        raise ValueError("Expected MTGJSON AtomicCards name-to-variants object")
    meta = raw.get("meta", {})
    return cards, meta if isinstance(meta, dict) else {}


def read_collection(path: Path) -> Counter:
    """Parse a user-supplied Name,Quantity CSV, never assume a saved inventory."""
    owned: Counter = Counter()
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle, strict=True)
        line = 1
        try:
            headers = next(reader, [])
            if len(headers) != len(set(headers)):
                raise ValueError("Invalid collection CSV at line 1: duplicate column names")
            if not {"Name", "Quantity"} <= set(headers):
                raise ValueError("Collection CSV at line 1 requires exact columns Name and Quantity")
            name_index, count_index = headers.index("Name"), headers.index("Quantity")
            while True:
                line = reader.line_num + 1
                row = next(reader, None)
                if row is None:
                    break
                if not row:
                    continue
                if len(row) != len(headers):
                    raise ValueError(f"Invalid collection entry at line {line}: expected "
                                     f"{len(headers)} fields, found {len(row)}")
                name, count = row[name_index].strip(), row[count_index].strip()
                if not name:
                    raise ValueError(f"Invalid collection entry at line {line}: Name is empty")
                if not re.fullmatch(r"[0-9]+", count):
                    raise ValueError(f"Invalid collection entry at line {line}: "
                                     "Quantity must be a nonnegative integer")
                try:
                    quantity = int(count)
                except ValueError as exc:
                    raise ValueError(f"Invalid collection entry at line {line}: "
                                     "Quantity exceeds the supported integer size") from exc
                owned[name.casefold()] += quantity
        except csv.Error as exc:
            raise ValueError(f"Invalid collection CSV at line {line}: {exc}") from exc
    return owned


def color_set(identity: str) -> set[str]:
    cleaned = identity.strip().upper()
    if cleaned == "ANY":
        return set(COLOR_ORDER)
    if not cleaned or any(ch not in "WUBRGC" for ch in cleaned):
        raise ValueError("Color identity must use W/U/B/R/G/C symbols")
    return set(cleaned.replace("C", ""))


def printed_ability_line(rules: str, ability: str) -> bool:
    """Conservative v0.1-compatible standalone printed ability detector."""
    token = re.escape(ability.strip())
    pattern = re.compile(r"(?:^|,)\s*" + token + r"\s*(?=,|$|\()", re.IGNORECASE)
    return any(pattern.search(line.strip()) for line in rules.splitlines())


def remove_reminder_text(text: str) -> str:
    """Remove parenthetical reminder text without dropping adjacent rules text."""
    parts, depth = [], 0
    for char in text:
        if char == "(":
            depth += 1
        elif char == ")" and depth:
            depth -= 1
        elif depth == 0:
            parts.append(char)
    return "".join(parts)


def matching_line(text: str, pattern: str, flags: int = re.IGNORECASE) -> str | None:
    match = re.search(pattern, text, flags)
    if not match:
        return None
    for line in text.splitlines():
        if re.search(pattern, line, flags):
            return line.strip()[:450]
    return match.group(0)[:450]


def _add(found: dict, role: str, *, reason: str, evidence: str,
         confidence: str = "HIGH", conditional: bool = False,
         basis: str = "HEURISTIC_STRATEGY") -> None:
    """One evidence item per role; multiple roles per card are allowed."""
    if role not in found:
        found[role] = {
            "role": role, "reason": reason, "evidence": evidence[:450],
            "confidence": confidence, "conditional": conditional, "basis": basis,
        }


def _keyword_core(topic: str, original: str) -> bool:
    if printed_ability_line(original, topic):
        return True
    # Named ability-word lines (e.g. Landfall — ...) are not always keywords.
    return bool(re.search(r"(?im)^" + re.escape(topic) + r"\s*[—–-]\s*", original))


def creature_subtype_match(card: dict, subtype: str) -> bool:
    return (isinstance(card.get("types"), list) and "Creature" in card["types"]
            and isinstance(card.get("subtypes"), list)
            and any(isinstance(value, str) and value.casefold() == subtype
                    for value in card["subtypes"]))


def theme_patterns(theme: str) -> tuple[str, str | None, str]:
    normalized = theme.strip().casefold()
    subtype = normalized.removesuffix(" tribal").strip() if normalized.endswith(" tribal") else None
    topic = subtype if subtype is not None else ALIASES.get(normalized, normalized)
    term = re.escape(topic)
    if subtype:
        plural = {"elf": "elves", "dwarf": "dwarves", "faerie": "faeries"}.get(subtype)
        term = rf"(?:{term}|{plural})" if plural else rf"{term}(?:es|s)?"
    return topic, subtype, rf"(?<!\w){term}(?!\w)"


def classify_variant(card: dict, theme: str) -> dict:
    """Return conservative role evidence from one card variant.

    This is a thematic discovery heuristic, NOT an executable Oracle parser.
    """
    if not isinstance(card, dict):
        return {}
    topic, tribal_subtype, topic_pattern = theme_patterns(theme)
    if not topic:
        return {}
    if topic == "lifegain":
        return classify_lifegain_variant(card)
    original = card.get("text")
    original = original if isinstance(original, str) else ""
    text = remove_reminder_text(original)
    found = {}
    escaped = re.escape(topic)
    has_topic = bool(re.search(topic_pattern, text, re.IGNORECASE))
    if tribal_subtype and creature_subtype_match(card, tribal_subtype):
        _add(found, "core", reason="MTGJSON creature subtype matches the requested theme",
             evidence=next(value for value in card["subtypes"]
                           if isinstance(value, str) and value.casefold() == tribal_subtype),
             confidence="HEURISTIC", basis="CREATURE_SUBTYPE")
    keyword_values = card.get("keywords")
    has_metadata = (isinstance(keyword_values, list) and
                    topic in {k.casefold() for k in keyword_values if isinstance(k, str)})

    if _keyword_core(topic, original):
        _add(found, "core", reason="Printed standalone ability / named mechanic",
             evidence=matching_line(original, r"(?im)^\s*" + escaped) or original[:300],
             basis="ORACLE_TEXT")
    elif has_metadata and re.search(r"(?im)^\s*" + escaped + r"\b", original):
        _add(found, "core", reason="Printed mechanic corroborated by keyword metadata",
             evidence=matching_line(original, r"(?im)^\s*" + escaped) or original[:300],
             basis="ORACLE_TEXT")

    # A self-activation creates a conditional core ability, not an unconditional one.
    if not "core" in found and has_topic and re.search(
        r"(?i)(?:this creature|this permanent|it) gains?\s+" + topic_pattern, text
    ):
        _add(found, "core", reason="Can gain its own ability conditionally",
             evidence=matching_line(text, r"(?i)(?:this creature|this permanent|it) gains?\s+" + topic_pattern) or text[:300],
             confidence="HEURISTIC", conditional=True, basis="ORACLE_TEXT")

    # Keyword grant or access for other permanents/creatures.
    if has_topic:
        grants = r"(?i)(?:gain|gains|have|has|grant|grants)\s+(?:(?:\w+\s+){0,4})?" + topic_pattern
        grant_line = matching_line(text, grants)
        if grant_line and not re.search(r"(?i)(?:this creature|this permanent|it)\s+gains?\s+" + topic_pattern, grant_line):
            _add(found, "enabler", reason="Provides or grants the requested mechanic",
                 evidence=grant_line, confidence="HEURISTIC", conditional=True, basis="DIRECT_SYNERGY_CANDIDATE")
        # Require the theme IN THE SAME condition/trigger sentence. A card
        # with Deathtouch and an unrelated death trigger is not a theme payoff.
        trigger = r"(?i)\b(?:whenever|when|if|for each|as long as)\b[^\n.!?]{0,180}" + topic_pattern
        line = matching_line(text, trigger)
        if line:
            _add(found, "payoff", reason="Trigger or condition specifically references the requested theme",
                 evidence=line, confidence="HEURISTIC", conditional=True, basis="DIRECT_SYNERGY_CANDIDATE")

        if not found:
            _add(found, "synergy", reason="Mentions requested theme; relationship needs Oracle review",
                 evidence=matching_line(text, topic_pattern) or text[:300],
                 confidence="HEURISTIC", conditional=True, basis="ORACLE_TEXT")

    if topic == "deathtouch":
        # Damage to a creature counts as synergy only when card's own creature
        # does the damage. Removal spells like Lightning Bolt are NOT included.
        pattern = (r"(?i)(?:target|that|a) creature you control\s+deals?\s+"
                   r"(?:damage|an? amount of damage).*?"
                   r"(?:to target creature|to (?:another|a) creature|target creature)")
        line = matching_line(text, pattern)
        if not line and re.search(r"(?i)target creature you control", text):
            line = matching_line(text, r"(?i)(?:that creature|it) deals? damage equal to its power to target creature")
        if line:
            _add(found, "synergy", reason="Own creature deals damage to another creature; Deathtouch may matter",
                 evidence=line, confidence="HEURISTIC", conditional=True, basis="DIRECT_SYNERGY_CANDIDATE")
        # Actual 'fight' action also makes deathtouch relevant to dealt damage.
        line = matching_line(text, r"(?i)(?:target creature you control|creature you control).*?fights?\s+(?:target|another|a) creature")
        if line:
            _add(found, "synergy", reason="Fight effect can combine with Deathtouch",
                 evidence=line, confidence="HEURISTIC", conditional=True, basis="DIRECT_SYNERGY_CANDIDATE")
    elif topic == "lifelink":
        line = matching_line(text, r"(?i)(?:whenever|if)\s+(?:you|a player)\s+gain(?:s)?\s+life")
        if line:
            _add(found, "payoff", reason="Triggers or benefits when life is gained",
                 evidence=line, confidence="HEURISTIC", conditional=True)
    elif topic == "landfall":
        line = matching_line(text, r"(?i)(?:you may play an additional land|play up to .*additional lands?|put .*land card.*onto the battlefield)")
        if line:
            _add(found, "enabler", reason="Helps lands enter the battlefield",
                 evidence=line, confidence="HEURISTIC", conditional=True)
    elif topic == "proliferate":
        line = matching_line(text, r"(?i)(?:put (?:an?|\w+) (?:\+1/\+1|loyalty|poison) counter|with .*counters?)")
        if line and not has_topic:
            _add(found, "synergy", reason="Counter interaction may work with Proliferate",
                 evidence=line, confidence="HEURISTIC", conditional=True)
    elif topic in {"sacrifice", "token", "treasure", "+1/+1 counter"}:
        indirect = {
            "sacrifice": r"(?i)(?:whenever (?:a|another|one or more) creatures? (?:you control )?dies?|whenever .* (?:dies|is put into a graveyard))",
            "token": r"(?i)(?:whenever (?:a|one or more) tokens? (?:you control )?(?:enters?|dies?|leaves?)|for each token)",
            "treasure": r"(?i)(?:whenever you sacrifice an artifact|for each artifact you control|whenever .*artifact.*(?:enters?|dies?))",
            "+1/+1 counter": r"(?i)(?:whenever .*counter.*(?:is|are) put|whenever .*with .*counter.*(?:attacks?|dies?|deals?))",
        }
        line = matching_line(text, indirect[topic])
        if line:
            _add(found, "payoff", reason="Indirect condition may benefit from the requested strategy",
                 evidence=line, confidence="HEURISTIC", conditional=True)

    return found



def classify_lifegain_variant(card: dict) -> dict:
    """Bounded Oracle-text heuristics for life sources, grants and payoffs.

    'Lifegain' is a strategy, not a printed keyword. An opponent gaining life
    is NOT evidence that this card creates life for its controller.
    """
    original = card.get("text")
    if not isinstance(original, str):
        return {}
    text = remove_reminder_text(original)
    found = {}

    # Replacement effects modify future life gain; they do not create an
    # independent event (e.g. "If you would gain life, ... instead").
    modifier = matching_line(
        text, r"(?i)\bif you would gain life\b[^\n.!?]{0,180}\binstead\b"
    )
    if modifier:
        _add(found, "enabler", reason="Modifies a life-gain event supplied by another effect",
             evidence=modifier, confidence="HEURISTIC", conditional=True)

    # The source explicitly gains life for its controller, or has lifelink.
    own_gain = r"(?i)\byou gain\s+(?:(?:\d+|x|that much)\s+)?life\b"
    # "Whenever you gain life" is a CONDITION, never itself a life source.
    source = None
    for occurrence in re.finditer(own_gain, text):
        preceding = text[max(0, occurrence.start() - 30):occurrence.start()]
        if re.search(r"(?i)\b(?:whenever|when|if|as long as)\s+$", preceding):
            continue
        start = text.rfind("\n", 0, occurrence.start()) + 1
        end = text.find("\n", occurrence.end())
        entire_line = text[start:end if end >= 0 else len(text)].strip()[:450]
        if modifier and entire_line == modifier:
            continue
        source = entire_line
        if source:
            break
    if source:
        _add(found, "core", reason="Oracle text explicitly gains life for its controller",
             evidence=source, confidence="HIGH", conditional=bool(
                 re.search(r"(?i)\b(?:when|whenever|if|at the beginning|whenever a)\b", source)))
        _add(found, "enabler", reason="Creates a life-gain event for a separate payoff",
             evidence=source, confidence="HEURISTIC", conditional=True)

    imperative = matching_line(text, r"(?im)^\s*gain\s+(?:\d+|x|that much)\s+life\b")
    if imperative:
        _add(found, "core", reason="Imperative Oracle text gains life for the controller",
             evidence=imperative, confidence="HIGH", conditional=False)
        _add(found, "enabler", reason="Creates a life-gain event for a separate payoff",
             evidence=imperative, confidence="HEURISTIC", conditional=True)

    self_lifelink = matching_line(text, r"(?i)\b(?:this creature|this permanent)\s+(?:has|gains?)\s+lifelink\b")
    if self_lifelink:
        _add(found, "core", reason="This card has its own Lifelink conditionally",
             evidence=self_lifelink, confidence="HEURISTIC", conditional=True)
        _add(found, "enabler", reason="Own conditional Lifelink can create life-gain events",
             evidence=self_lifelink, confidence="HEURISTIC", conditional=True)

    if printed_ability_line(original, "Lifelink"):
        line = matching_line(original, r"(?im)^\s*lifelink\b") or "Lifelink"
        _add(found, "core", reason="Printed lifelink can create life-gain events through damage",
             evidence=line, confidence="HIGH", conditional=True)
        _add(found, "enabler", reason="Lifelink damage can trigger a life-gain payoff",
             evidence=line, confidence="HEURISTIC", conditional=True)

    # This deliberately excludes 'creatures your opponents control gain lifelink'.
    grant = (r"(?i)\b(?:creatures? you control|other creatures? you control|"
             r"target creature|equipped creature|enchanted creature)\b"
             r"[^\n.!?]{0,120}\b(?:gain|gains|have|has)\s+"
             r"(?:your choice of [^\n.!?]{0,60}?\bor\s+)?lifelink\b")
    granted = matching_line(text, grant)
    if granted:
        _add(found, "enabler", reason="Grants lifelink; target and activation must be verified",
             evidence=granted, confidence="HEURISTIC", conditional=True)

    created_lifelink = matching_line(
        text, r"(?i)\bcreate\b[^\n.!?]{0,160}\bcreature tokens?\b[^\n.!?]{0,100}\bwith lifelink\b"
    )
    if created_lifelink:
        _add(found, "enabler", reason="Creates Lifelink creatures; dealing damage remains conditional",
             evidence=created_lifelink, confidence="HEURISTIC", conditional=True)

    payoff = (r"(?i)\b(?:whenever|when|if|as long as)\s+"
              r"(?:you|a player)\s+gain(?:s)?\s+life\b")
    beneficiary = matching_line(text, payoff)
    if not beneficiary:
        beneficiary = matching_line(
            text, r"(?i)\bif you gained\s+(?:(?:\d+|x) or more\s+)?life\b"
        )
    if beneficiary:
        _add(found, "payoff", reason="Oracle condition explicitly rewards or responds to gaining life",
             evidence=beneficiary, confidence="HEURISTIC", conditional=True)

    return found


def classify_interaction_variant(card: dict) -> dict:
    """Recognize bounded, targeted opponent interaction, not generic 'value'."""
    rules = card.get("text")
    if not isinstance(rules, str):
        return {}
    text = remove_reminder_text(rules)
    patterns = (
        r"(?i)\b(?:destroy|exile)\s+(?:up to\s+)?target\s+(?:\w+\s+){0,3}"
        r"(?:creature|permanent|artifact|enchantment|planeswalker)\b",
        r"(?i)\bcounter target (?:spell|activated ability|triggered ability)\b",
        r"(?i)\btarget creature (?:gets|gains)\s+-(?:\d+|x)/-(?:\d+|x)\b",
        r"(?i)\btarget (?:opponent|player)\s+(?:discards?|sacrifices?)\b",
        r"(?i)\bdeals?\s+\d+\s+damage\s+to\s+(?:any target|target creature|target player)\b",
        r"(?i)\breturn target\s+(?:\w+\s+){0,3}"
        r"(?:creature|permanent)\s+to\s+its owner's hand\b",
    )
    for pattern in patterns:
        line = matching_line(text, pattern)
        if line:
            found = {}
            _add(found, "interaction", reason="Potential targeted removal, disruption or damage",
                 evidence=line, confidence="HEURISTIC", conditional=True)
            return found
    return {}


def build_lifegain_synergy_pairs(matches: list[dict], max_pairs: int) -> dict:
    """Suggest bounded owned-card source->payoff pairs, never proven combos."""
    sources = [m for m in matches if "core" in m["roles"] or "enabler" in m["roles"]]
    # Exclude life-gain replacement modifiers as stand-alone two-card sources:
    # they need an independent third effect to make any player gain life.
    sources = [m for m in sources if "core" in m["roles"] or
               m["role_evidence"].get("enabler", {}).get("reason") !=
               "Modifies a life-gain event supplied by another effect"]
    # Prefer repeatable nonland engines over one-shot spells and life-gain lands.
    # This is a deterministic display heuristic, NOT a deck power rating.
    def priority(source: dict) -> tuple:
        types = set(source.get("types") or [])
        oracle = source.get("oracle_text") or ""
        is_land = "Land" in types
        repeatable = bool(re.search(r"(?i)\b(?:whenever|at the beginning|lifelink)\b", oracle))
        is_permanent = bool(types.intersection({"Creature", "Artifact", "Enchantment", "Planeswalker"}))
        return (int(is_land), 0 if is_permanent and repeatable else 1 if is_permanent else 2,
                source["mana_value"] if source["mana_value"] is not None else 999,
                source["name"].casefold())
    sources.sort(key=priority)
    payoffs = [m for m in matches if "payoff" in m["roles"]]
    possible = len(sources) * len(payoffs) - sum(
        1 for m in sources if "payoff" in m["roles"]
    )
    pairs = []
    for source in sources:
        evidence = source["role_evidence"].get("enabler") or source["role_evidence"].get("core")
        for payoff in payoffs:
            if source["name"] == payoff["name"]:
                continue
            pairs.append({
                "source": source["name"], "payoff": payoff["name"],
                "source_owned_copies": source["owned_copies"],
                "payoff_owned_copies": payoff["owned_copies"],
                "source_evidence": evidence["evidence"],
                "payoff_evidence": payoff["role_evidence"]["payoff"]["evidence"],
                "relationship": "LIFE_GAIN_EVENT_TO_PAYOFF",
                "confidence": "HEURISTIC",
                "conditional": True,
                "status": "CANDIDATE_NOT_RULES_VERIFIED",
                "requires_threshold_check": bool(re.search(
                    r"(?i)\bif you gained\s+\d+ or more life\b",
                    payoff.get("oracle_text") or "")),
            })
            if len(pairs) >= max_pairs:
                break
        if len(pairs) >= max_pairs:
            break
    return {
        "status": "BOUNDED_SYNERGY_CANDIDATES_NOT_VERIFIED_COMBOS",
        "max_pairs": max_pairs,
        "possible_pairs": possible,
        "returned_pairs": len(pairs),
        "truncated": len(pairs) < possible,
        "pairs": pairs,
        "limitations": [
            "Only life-source and life-gain-payoff relationships are screened.",
            "Timing, targeting, mana, zones and trigger resolution were not simulated.",
            "A suggested pair does not guarantee a legal or useful game interaction.",
            "Pairs are ordered with repeatable nonland sources first; mana and colors are not checked.",
            "Threshold payoffs may require more life gained than the suggested source provides.",
        ],
    }


def identity_key(name: str) -> str:
    return "//".join(part.strip().casefold() for part in name.split("//"))


def card_name_index(cards: dict) -> tuple[dict, dict]:
    """Index exact canonical names and corroborated face names separately from claims."""
    verified = defaultdict(set)
    possible = defaultdict(set)
    for canonical, variants in cards.items():
        if not isinstance(canonical, str):
            continue
        full = identity_key(canonical)
        possible[full].add(canonical)
        faces = full.split("//") if "//" in full else []
        for face in filter(None, faces):
            possible[face].add(canonical)
        if not isinstance(variants, list) or not variants:
            continue
        names_agree = True
        aliases_agree = len(faces) == 2 and all(faces) and faces[0] != faces[1]
        expected_sides = dict(zip(faces, ("a", "b")))
        layouts = set()
        corroborated_faces = set()
        for variant in variants:
            if not isinstance(variant, dict):
                names_agree = False
                continue
            record_name = variant.get("name")
            record_key = identity_key(record_name) if isinstance(record_name, str) else None
            if record_key:
                possible[record_key].add(canonical)
            if record_name is not None and record_key != full:
                names_agree = False

            layout = variant.get("layout")
            if isinstance(layout, str) and layout in FACE_ALIAS_LAYOUTS:
                layouts.add(layout)
            elif layout is not None:
                aliases_agree = False

            side = variant.get("side")
            if side not in (None, "a", "b"):
                aliases_agree = False
            face_name = variant.get("faceName")
            if face_name is None:
                continue
            if not isinstance(face_name, str) or not face_name.strip():
                aliases_agree = False
                continue
            face = identity_key(face_name)
            possible[face].add(canonical)
            if face not in expected_sides or side not in (None, expected_sides[face]):
                aliases_agree = False
            elif record_key == full:
                corroborated_faces.add(face)
        if names_agree:
            verified[full].add(canonical)
            if aliases_agree and len(layouts) <= 1:
                for face in corroborated_faces:
                    verified[face].add(canonical)
    return verified, possible


def resolve_collection(collection: Counter, verified: dict, possible: dict) -> tuple[Counter, dict]:
    owned = Counter()
    absent, unverified = [], []
    for name, quantity in collection.items():
        key = identity_key(name)
        claims = possible.get(key, set())
        if not claims:
            absent.append(name)
        elif len(claims) != 1 or claims != verified.get(key):
            unverified.append(name)
        else:
            owned[next(iter(claims))] += quantity
    return owned, {
        "distinct_nonzero_owned_names": sum(quantity > 0 for quantity in collection.values()),
        "owned_names_absent_from_oracle": sorted(absent),
        "unverified_owned_names": sorted(unverified),
        "unresolved_name_count": len(absent) + len(unverified),
        "identity_status": "UNVERIFIED" if absent or unverified else "MATCHED",
    }


def evaluate_variant(card: dict, *, name: str | None, abilities: list[str],
                     keywords: list[str], oracle_text: list[str],
                     card_type: str | None, subtype: str | None,
                     identity: set[str] | None, min_mv: float | None,
                     max_mv: float | None) -> bool | None:
    """Preserve v0.1 filter semantics: True/False/None (unknown)."""
    if name is not None:
        if not isinstance(card.get("name"), str):
            return None
        if name.casefold() not in card["name"].casefold():
            return False

    rules = card.get("text")
    if abilities or oracle_text:
        if not isinstance(rules, str):
            return None
        if any(not printed_ability_line(rules, ability) for ability in abilities):
            return False
        if any(term.casefold() not in rules.casefold() for term in oracle_text):
            return False

    if keywords:
        actual = card.get("keywords")
        if not isinstance(actual, list) or not all(isinstance(x, str) for x in actual):
            return None
        found = {item.casefold() for item in actual}
        if any(keyword.casefold() not in found for keyword in keywords):
            return False

    for field, value in (("types", card_type), ("subtypes", subtype)):
        if value:
            actual = card.get(field)
            if not isinstance(actual, list) or not all(isinstance(x, str) for x in actual):
                return None
            if value.casefold() not in {x.casefold() for x in actual}:
                return False

    if identity is not None:
        actual = card.get("colorIdentity")
        if (not isinstance(actual, list) or
                not all(type(x) is str and x in set(COLOR_ORDER) for x in actual)):
            return None
        if not set(actual) <= identity:
            return False

    if min_mv is not None or max_mv is not None:
        value = card.get("manaValue")
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return None
        if (min_mv is not None and value < min_mv) or (max_mv is not None and value > max_mv):
            return False
    return True


def search(cards: dict, *, name: str | None = None,
           abilities: list[str] | None = None, keywords: list[str] | None = None,
           oracle_text: list[str] | None = None,
           card_type: str | None = None, subtype: str | None = None,
           color_identity: str | None = None,
           min_mv: float | None = None, max_mv: float | None = None,
           collection: Counter | None = None, owned_only: bool = False,
           limit: int = 50, theme: str | None = None,
           roles: list[str] | None = None, offset: int = 0,
           synergy: bool = False, max_synergy_pairs: int = 100) -> dict:
    """Find candidate cards; theme is discovery and roles are optional OR-filters."""
    abilities, keywords, oracle_text = abilities or [], keywords or [], oracle_text or []
    roles = [r.casefold() for r in (roles or [])]
    if not any((name, abilities, keywords, oracle_text, card_type, subtype,
                color_identity, min_mv is not None, max_mv is not None, theme)):
        raise ValueError("Provide at least one card search filter")
    if any(not isinstance(v, str) or not v.strip() for v in
           [*abilities, *keywords, *oracle_text]):
        raise ValueError("Search terms cannot be empty")
    if theme is not None and (not isinstance(theme, str) or not theme.strip()):
        raise ValueError("Theme must be a nonempty mechanic or strategy")
    if roles and theme is None:
        raise ValueError("--role requires --theme")
    if any(role not in ROLE_SET for role in roles):
        raise ValueError("Role must be core, enabler, payoff, synergy or interaction")
    if limit < 1 or limit > MAX_LIMIT:
        raise ValueError(f"Limit must be between 1 and {MAX_LIMIT}")
    if offset < 0:
        raise ValueError("Offset must be nonnegative")
    if owned_only and collection is None:
        raise ValueError("--owned-only requires --collection")
    if min_mv is not None and max_mv is not None and min_mv > max_mv:
        raise ValueError("Minimum mana value exceeds maximum")
    if min_mv is not None and min_mv < 0 or max_mv is not None and max_mv < 0:
        raise ValueError("Mana value cannot be negative")
    if synergy and (theme is None or theme.strip().casefold() != "lifegain"):
        raise ValueError("--synergy currently supports --theme lifegain only")
    if synergy and (not owned_only or collection is None):
        raise ValueError("--synergy requires --collection and --owned-only")
    if max_synergy_pairs < 1 or max_synergy_pairs > 500:
        raise ValueError("max_synergy_pairs must be between 1 and 500")
    identity = (None if color_identity is not None and color_identity.strip().upper() == "ANY"
                else color_set(color_identity) if color_identity is not None else None)
    owned, collection_coverage = None, None
    name_targets, name_identity = None, None
    if collection is not None or name is not None:
        verified, possible = card_name_index(cards)
        if collection is not None:
            owned, collection_coverage = resolve_collection(collection, verified, possible)
        if name is not None:
            key = identity_key(name)
            claims = possible.get(key)
            if claims and (len(claims) != 1 or claims != verified.get(key)):
                name_targets = set()
                name_identity = {"status": "UNVERIFIED", "candidate_names": sorted(claims)}
            elif claims and any("//" in canonical for canonical in claims):
                name_targets = claims
                name_identity = {"status": "MATCHED", "candidate_names": sorted(claims)}

    if theme is not None:
        _, tribal_subtype, topic_pattern = theme_patterns(theme)
    totals = Counter()
    matches = []
    role_totals = Counter()
    for canonical_name, variants in cards.items():
        totals["cards_scanned"] += 1
        if (not isinstance(canonical_name, str) or not isinstance(variants, list)
                or not variants or not all(isinstance(v, dict) for v in variants)):
            totals["malformed_card_records"] += 1
            continue
        is_basic = canonical_name in BASICS and all(
            isinstance(v.get("types"), list) and "Land" in v["types"] and
            isinstance(v.get("supertypes"), list) and "Basic" in v["supertypes"]
            for v in variants
        )
        if name_targets is not None and canonical_name not in name_targets:
            continue
        count = owned.get(canonical_name, 0) if owned is not None else None
        if owned_only and not (is_basic or count > 0):
            continue
        outcomes = [evaluate_variant(
            v, name=name if name_targets is None else None, abilities=abilities, keywords=keywords,
            oracle_text=oracle_text, card_type=card_type, subtype=subtype,
            identity=identity, min_mv=min_mv, max_mv=max_mv,
        ) for v in variants]
        if all(result is False for result in outcomes):
            continue
        if not all(result is True for result in outcomes):
            totals["uncertain_variant_matches"] += 1
            continue

        role_info = {}
        match_basis = []
        if theme is not None:
            if tribal_subtype and all(creature_subtype_match(v, tribal_subtype) for v in variants):
                match_basis.append("CREATURE_SUBTYPE")
            if all(isinstance(v.get("text"), str)
                   and re.search(topic_pattern, remove_reminder_text(v["text"]), re.IGNORECASE) for v in variants):
                match_basis.append("ORACLE_TEXT")
            observed = [classify_variant(v, theme) for v in variants]
            agreed_roles = set.intersection(*(set(d.keys()) for d in observed))
            union_roles = set.union(*(set(d.keys()) for d in observed))
            if tribal_subtype:
                agreed_roles = {
                    role for role in agreed_roles
                    if len({record[role]["basis"] for record in observed}) == 1
                }
            if union_roles != agreed_roles:
                totals["uncertain_role_variants"] += 1
            if not agreed_roles and not ("interaction" in roles):
                continue
            role_info = {role: observed[0][role] for role in ROLE_ORDER if role in agreed_roles}
            # Do not add unrelated interaction results to legacy theme searches.
            if theme.strip().casefold() == "lifegain" or "interaction" in roles:
                interactive = [classify_interaction_variant(v) for v in variants]
                if all("interaction" in d for d in interactive):
                    role_info["interaction"] = interactive[0]["interaction"]
            if roles and not any(role in role_info for role in roles):
                continue

        card = variants[0]
        mvs = {v.get("manaValue") for v in variants
               if type(v.get("manaValue")) in (float, int)}
        mv = next(iter(mvs)) if len(mvs) == 1 else None
        identities = {
            frozenset(v["colorIdentity"]) if isinstance(v.get("colorIdentity"), list)
            and all(isinstance(color, str) and color in set(COLOR_ORDER)
                    for color in v["colorIdentity"]) else None
            for v in variants
        }
        display_identity = ("".join(ch for ch in COLOR_ORDER if ch in next(iter(identities)))
                            if len(identities) == 1 and None not in identities else None)
        rules = card.get("text")
        for role in role_info:
            role_totals[role] += 1
        matches.append({
            "name": canonical_name,
            "mana_value": mv,
            "color_identity": display_identity,
            "types": card.get("types"),
            "subtypes": card.get("subtypes"),
            "keywords": card.get("keywords"),
            "oracle_text": rules if isinstance(rules, str) else None,
            "owned_copies": count,
            "unlimited_basic_by_project_policy": bool(is_basic),
            "printing_variants": len(variants),
            "roles": list(role_info),
            "role_evidence": role_info,
            "theme_match_basis": match_basis,
            "match_status": "FILTER_MATCH_NOT_DECK_VALIDATION",
        })
    matches.sort(key=lambda item: (
        item["mana_value"] if item["mana_value"] is not None else float("inf"),
        item["name"].casefold(),
    ))
    report = {
        "tool_version": VERSION,
        "status": "SEARCH_RESULTS_NOT_A_CONSTRUCTED_DECK",
        "query": {
            "name": name, "printed_abilities": abilities, "keywords": keywords,
            "oracle_text_contains": oracle_text, "card_type": card_type,
            "subtype": subtype, "color_identity_subset_of": color_identity,
            "min_mana_value": min_mv, "max_mana_value": max_mv,
            "owned_only": owned_only, "theme": theme, "roles_any_of": roles,
            "offset": offset, "synergy": synergy,
            "max_synergy_pairs": max_synergy_pairs,
        },
        "total_matches": len(matches), "returned_count": len(matches[offset:offset+limit]),
        "truncated": offset + limit < len(matches), "next_offset": (offset + limit if offset + limit < len(matches) else None),
        "role_counts": dict(role_totals),
        "results": matches[offset:offset+limit], "coverage": dict(totals),
        "limitations": [
            "Candidates only: NOT a complete theme catalog, decklist, gameplay test or legality guarantee.",
            "Core printed abilities are detected by a conservative text heuristic.",
            "Enabler, payoff, interaction and synergy roles are heuristic suggestions requiring Oracle review.",
            "A missing keyword or absence from results does not prove that a card lacks the mechanic.",
            "Some indirect synergies do not mention the theme and are not discoverable by generic text search.",
            "Conflicting MTGJSON printing variants and missing queried data are excluded/flagged, not silently resolved.",
            "Owned counts come only from the current user-supplied CSV; basics follow the project unlimited policy.",
            "A color identity filter is NOT a casual-deck color restriction or format legality verification.",
            "Slim MTGJSON snapshots omit cards outside their original selection; verify collection name coverage.",
            "No banlist, full MTG rules, deck size, copy limits, mana consistency or gameplay validation was run.",
        ],
    }
    if name_identity is not None:
        report["name_identity"] = name_identity
    if collection_coverage is not None:
        report["collection_coverage"] = collection_coverage
    if synergy:
        report["synergy_analysis"] = build_lifegain_synergy_pairs(matches, max_synergy_pairs)
    return report


def human_report(report: dict) -> str:
    lines = [
        "MTG CARD SEARCH (candidates only; NOT a deck)",
        f"Matching cards: {report['total_matches']} | Displayed: {report['returned_count']}",
    ]
    if report["query"].get("theme"):
        lines.append("Theme: " + report["query"]["theme"])
        lines.append("Roles across all matches: " + ", ".join(
            f"{r}={report['role_counts'].get(r, 0)}" for r in ROLE_ORDER))
    for card in report["results"]:
        quantity = ("Basic: unlimited" if card["unlimited_basic_by_project_policy"]
                    else f"Owned: {card['owned_copies']}" if card["owned_copies"] is not None
                    else "Ownership: not checked")
        role_part = ", ".join(card["roles"])
        lines.append(f"- {card['name']} | MV {card['mana_value']} | "
                     f"Identity {card['color_identity']} | {quantity}" +
                     (f" | Roles: {role_part}" if role_part else ""))
        if report["query"].get("theme"):
            for role, note in card["role_evidence"].items():
                lines.append(f"    {role}: {note['evidence']} "
                             f"[{note['basis']}, {note['confidence']}{', CONDITIONAL' if note['conditional'] else ''}]")
    if report.get("name_identity", {}).get("status") == "UNVERIFIED":
        lines.append("NOTE: the exact name has UNVERIFIED Oracle identity.")
    if report.get("collection_coverage", {}).get("identity_status") == "UNVERIFIED":
        lines.append("NOTE: some collection names have UNVERIFIED Oracle identity and supplied no copies.")
    if report["coverage"].get("uncertain_variant_matches", 0):
        lines.append("NOTE: some cards were excluded due to missing/conflicting Oracle fields.")
    if report["coverage"].get("uncertain_role_variants", 0):
        lines.append("NOTE: some thematic roles differ across printing variants.")
    if "synergy_analysis" in report:
        summary = report["synergy_analysis"]
        lines.append(f"Synergy candidates: {summary['returned_pairs']} / {summary['possible_pairs']}"
                     + (" (truncated)" if summary["truncated"] else ""))
        for pair in summary["pairs"]:
            lines.append(f"    {pair['source']} -> {pair['payoff']} [HEURISTIC; NOT RULES-VERIFIED]")
    lines.append("These results must be reviewed before constructing and validating a deck.")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--oracle", type=Path, required=True,
                        help="Local MTGJSON AtomicCards.json or AtomicCards.json.gz")
    parser.add_argument("--collection", type=Path, help="One optional Name,Quantity CSV")
    parser.add_argument("--owned-only", action="store_true")
    parser.add_argument("--ability", action="append", default=[],
                        help="Strict printed keyword ability, e.g. Deathtouch")
    parser.add_argument("--keyword", action="append", default=[],
                        help="Raw MTGJSON keyword metadata")
    parser.add_argument("--text", action="append", default=[],
                        help="Oracle-text literal substring")
    parser.add_argument("--theme", help="Mechanic/strategy name (e.g. Deathtouch, Landfall, Sacrifice)")
    parser.add_argument("--synergy", action="store_true",
                        help="Bounded owned-card life-source to life-payoff pairs (lifegain only)")
    parser.add_argument("--max-synergy-pairs", type=int, default=100)
    parser.add_argument("--role", action="append", choices=ROLE_ORDER,
                        help="Optional OR-filter for theme roles; repeat to select several")
    parser.add_argument("--name")
    parser.add_argument("--type", dest="card_type")
    parser.add_argument("--subtype")
    parser.add_argument("--identity", help="Color identity subset; ANY disables filtering")
    parser.add_argument("--min-mv", type=float)
    parser.add_argument("--max-mv", type=float)
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--offset", type=int, default=0,
                        help="Skip this many sorted matches; paginate large results")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("--output", type=Path, help="Optional output file")
    args = parser.parse_args(argv)
    try:
        data, meta = read_atomic(args.oracle)
        owned = read_collection(args.collection) if args.collection else None
        report = search(
            data, name=args.name, abilities=args.ability, keywords=args.keyword,
            oracle_text=args.text, card_type=args.card_type, subtype=args.subtype,
            color_identity=args.identity, min_mv=args.min_mv, max_mv=args.max_mv,
            collection=owned, owned_only=args.owned_only, limit=args.limit,
            theme=args.theme, roles=args.role, offset=args.offset,
            synergy=args.synergy, max_synergy_pairs=args.max_synergy_pairs,
        )
        report["oracle_version"] = meta.get("version")
        report["oracle_file"] = str(args.oracle)
        report["collection_provided"] = args.collection is not None
        rendered = (json.dumps(report, ensure_ascii=False, indent=2) + "\n"
                    if args.format == "json" else human_report(report))
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
