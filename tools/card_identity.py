"""Physical-card names shared by discovery and structural validation."""

from collections import Counter, defaultdict

FACE_LAYOUTS = frozenset({
    "adventure", "aftermath", "flip", "modal_dfc", "prepare", "split", "transform",
})


def reject_duplicate_oracle_keys(pairs) -> dict:
    record = {}
    for key, value in pairs:
        if key in record:
            raise ValueError(f"Duplicate Oracle JSON key: {key!r}")
        record[key] = value
    return record


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
        if isinstance(variants, dict):
            variants = [variants]
        repeated_reversible = (len(faces) == 2 and faces[0] == faces[1]
                               and isinstance(variants, list) and bool(variants)
                               and all(isinstance(v, dict) and v.get("layout") == "reversible_card"
                                       and v.get("name") == canonical
                                       and v.get("faceName") in canonical.split(" // ")
                                       for v in variants))
        if not repeated_reversible:
            for face in filter(None, faces):
                possible[face].add(canonical)
        if not isinstance(variants, list) or not variants:
            continue
        names_agree = True
        for variant in variants:
            if not isinstance(variant, dict):
                names_agree = False
                continue
            record_name = variant.get("name")
            if isinstance(record_name, str):
                possible[identity_key(record_name)].add(canonical)
            if record_name != canonical:
                names_agree = False
            face_name = variant.get("faceName")
            if isinstance(face_name, str) and face_name.strip() and not repeated_reversible:
                possible[identity_key(face_name)].add(canonical)
        if names_agree:
            verified[full].add(canonical)
            if faces and face_pair(canonical, variants) is not None:
                for face in faces:
                    verified[face].add(canonical)
    return verified, possible


def physical_name(name, cards, verified, possible, *, inventory=False):
    """Resolve physical input without accepting a reverse/alternate face as a card."""
    key = identity_key(name)
    claims = possible.get(key)
    if not claims:
        return "NOT_FOUND", None
    if len(claims) != 1 or claims != verified.get(key):
        return "AMBIGUOUS_IDENTITY", None
    canonical = next(iter(claims))
    raw = cards[canonical]
    variants = [raw] if isinstance(raw, dict) else raw
    layouts = [card.get("layout") for card in variants]
    if any(layout is not None and not isinstance(layout, str) for layout in layouts):
        return "AMBIGUOUS_IDENTITY", None
    if any(layout in {"meld", "reversible_card", "planar", "scheme", "vanguard"}
           for layout in layouts):
        status = "AMBIGUOUS_IDENTITY" if len(set(layouts)) > 1 else "UNSUPPORTED_LAYOUT"
        return status, None
    full = identity_key(canonical)
    if "//" not in full:
        if (any(layout in FACE_LAYOUTS for layout in layouts)
                or any(card.get("side") is not None or card.get("faceName") is not None
                       for card in variants)):
            return "AMBIGUOUS_IDENTITY", None
        if key != full or (not inventory and name != canonical):
            return "NOT_FOUND", None
        return "EXACT_MATCH", canonical
    if key == full:
        # Structural checks still inspect exact combined names, including Prepare
        # records with contradictory layout metadata.
        return ("EXACT_MATCH" if name == canonical else "VERIFIED_CANONICAL_ALIAS"), canonical
    if key != full.split("//")[0]:
        return "UNSUPPORTED_LAYOUT", None
    return "VERIFIED_CANONICAL_ALIAS", canonical


def face_pair(canonical, variants):
    """Require a single documented layout and explicit corroboration of both faces."""
    names = canonical.split(" // ")
    if len(names) != 2 or not all(names) or names[0] == names[1]:
        return None
    layout = variants[0].get("layout")
    if not isinstance(layout, str) or layout not in FACE_LAYOUTS:
        return None
    sides = {"a": [], "b": []}
    for variant in variants:
        side = variant.get("side")
        if (variant.get("layout") != layout or variant.get("name") != canonical
                or side not in ("a", "b")
                or variant.get("faceName") != names[0 if side == "a" else 1]):
            return None
        sides[side].append(variant)
    if not sides["a"] or not sides["b"]:
        return None
    return sides["a"], sides["b"]


def resolve_collection(collection, cards, verified, possible):
    """Aggregate printings and quarantine duplicate labels of unknown overlap."""
    labels_by_card = defaultdict(dict)
    absent, unverified = [], []
    for name, quantity in collection.items():
        if quantity == 0:
            continue
        status, canonical = physical_name(name, cards, verified, possible, inventory=True)
        if status == "NOT_FOUND":
            absent.append(name)
        elif canonical is None:
            unverified.append(name)
        else:
            raw = cards[canonical]
            variants = [raw] if isinstance(raw, dict) else raw
            if "//" in canonical and face_pair(canonical, variants) is None:
                unverified.append(name)
            else:
                key = identity_key(name)
                previous, originals = labels_by_card[canonical].get(key, (0, []))
                labels_by_card[canonical][key] = (previous + quantity, originals + [name])
    owned = Counter()
    for canonical, labels in labels_by_card.items():
        if len(labels) == 1:
            owned[canonical] = next(iter(labels.values()))[0]
        else:
            unverified.extend(name for _, names in labels.values() for name in names)
    return owned, {
        "distinct_nonzero_owned_names": sum(quantity > 0 for quantity in collection.values()),
        "owned_names_absent_from_oracle": sorted(absent),
        "unverified_owned_names": sorted(unverified),
        "unresolved_name_count": len(absent) + len(unverified),
        "identity_status": "UNVERIFIED" if absent or unverified else "MATCHED",
    }
