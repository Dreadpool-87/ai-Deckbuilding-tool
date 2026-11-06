#!/usr/bin/env python3
"""Deterministic conversion of the two checked-in Mono-Red examples to Forge .dck."""
import argparse
import hashlib
import json
import re
from pathlib import Path

DECKS = ("Synthetic_Red_A", "Synthetic_Red_B")
LINE = re.compile(r"([1-9][0-9]*)\s+(.+)")


def read_plain_deck(path):
    cards = {}
    for lineno, raw in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        match = LINE.fullmatch(line)
        if not match:
            raise ValueError(f"{path}:{lineno}: invalid deck row")
        qty, name = int(match.group(1)), match.group(2).strip()
        if not name or name in cards:
            raise ValueError(f"{path}:{lineno}: empty or duplicate card name")
        cards[name] = qty
    if sum(cards.values()) != 60:
        raise ValueError(f"{path}: expected exactly 60 cards, got {sum(cards.values())}")
    return cards


def read_forge_deck(path):
    section, cards = None, {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("[") and line.endswith("]"):
            section = line
            continue
        if section != "[Main]" or not line:
            continue
        match = LINE.fullmatch(line)
        if not match:
            raise ValueError(f"Unparseable .dck card row: {line!r}")
        name = match.group(2).strip()
        if name in cards:
            raise ValueError(f"Duplicate Forge card row: {name}")
        cards[name] = int(match.group(1))
    return cards


def convert(repo, destination):
    destination.mkdir(parents=True, exist_ok=True)
    manifest = {"purpose": "technical Forge CLI smoke test with synthetic fixtures",
                "decks": []}
    for stem in DECKS:
        source = repo / "examples" / f"{stem}.txt"
        original = read_plain_deck(source)
        output = destination / f"{stem}.dck"
        content = f"[metadata]\nName={stem}\n[Main]\n"
        content += "".join(f"{n} {name}\n" for name, n in original.items())
        output.write_text(content, encoding="utf-8")
        if read_forge_deck(output) != original:
            raise RuntimeError(f"Conversion mismatch for {stem}")
        manifest["decks"].append({
            "name": stem,
            "source": str(source.relative_to(repo)),
            "forge_file": output.name,
            "cards": sum(original.values()),
            "distinct_card_names": len(original),
            "original_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
            "forge_sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
            "source_to_forge_card_counts_equal": True,
        })
    (destination / "deck-manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path("."))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(convert(args.repo.resolve(), args.output.resolve()), indent=2))
