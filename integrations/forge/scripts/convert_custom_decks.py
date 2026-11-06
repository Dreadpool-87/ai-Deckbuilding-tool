#!/usr/bin/env python3
"""Generic, strict, deterministic 60-card plaintext -> Forge .dck conversion."""
import argparse
import hashlib
import json
import re
from pathlib import Path

LINE = re.compile(r"([1-9][0-9]*)\s+(.+)")
BASICS = {"Plains", "Island", "Swamp", "Mountain", "Forest"}
SAFE_STEM = re.compile(r"[A-Za-z][A-Za-z0-9_-]{0,79}\Z")


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_source(path):
    cards = {}
    for number, raw in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        match = LINE.fullmatch(line)
        if not match:
            raise ValueError(f"{path}:{number}: invalid deck row")
        count, name = int(match.group(1)), match.group(2).strip()
        if not name or name in cards or any(c in name for c in "\r\n[]"):
            raise ValueError(f"{path}:{number}: invalid or duplicate card name")
        if count > 4 and name not in BASICS:
            raise ValueError(f"{path}:{number}: more than four copies of {name}")
        cards[name] = count
    if sum(cards.values()) != 60:
        raise ValueError(f"{path}: expected 60 cards, got {sum(cards.values())}")
    return cards


def parse_dck(path):
    cards, section = {}, None
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("[") and line.endswith("]"):
            section = line
            continue
        if section == "[Main]" and line:
            match = LINE.fullmatch(line)
            if not match or match.group(2) in cards:
                raise ValueError(f"Invalid .dck main row: {line}")
            cards[match.group(2)] = int(match.group(1))
    return cards


def safe_source(repo, raw):
    if not raw or raw.startswith("/") or "\\" in raw:
        raise ValueError("Only repository-relative POSIX source paths are allowed")
    root = repo.resolve()
    if any(part in (".", "..") or part.startswith(".") for part in Path(raw).parts):
        raise ValueError("Traversal and hidden source paths are not accepted")
    try:
        source = (root / raw).resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise ValueError("Deck source does not exist or cannot be resolved") from exc
    if not source.is_relative_to(root) or not source.is_file() or source.suffix != ".txt":
        raise ValueError("Deck source must be an existing .txt inside the repository")
    if any(part.startswith(".") for part in Path(raw).parts):
        raise ValueError("Hidden paths are not accepted")
    return source


def convert(repo, destination, a, b, names, expected):
    repo, destination = repo.resolve(), destination.resolve()
    if destination.is_relative_to(repo) and (destination == repo or
        any(destination == (repo / p).resolve() for p in (a, b))):
        raise ValueError("Output must not overwrite a source deck")
    destination.mkdir(parents=True, exist_ok=True)
    manifest = {"schema": 1, "purpose": "custom one-game Forge constructed smoke test",
                "decks": []}
    for i, (raw, name, wanted) in enumerate(zip((a, b), names, expected), 1):
        if not SAFE_STEM.fullmatch(name):
            raise ValueError(f"Unsafe deck label: {name}")
        source = safe_source(repo, raw)
        actual_hash = sha256(source)
        if not re.fullmatch(r"[0-9a-f]{64}", wanted) or actual_hash != wanted:
            raise ValueError(f"Deck {i}: source SHA-256 mismatch: {actual_hash}")
        cards = parse_source(source)
        output = destination / f"{name}.dck"
        content = f"[metadata]\nName={name}\n[Main]\n"
        content += "".join(f"{count} {card}\n" for card, count in cards.items())
        output.write_text(content, encoding="utf-8")
        if parse_dck(output) != cards:
            raise RuntimeError(f"Deck {i}: source-to-.dck mismatch")
        manifest["decks"].append({
            "name": name, "source": str(source.relative_to(repo)),
            "forge_file": output.name, "cards": 60,
            "distinct_card_names": len(cards),
            "original_sha256": actual_hash, "forge_sha256": sha256(output),
            "source_to_forge_card_counts_equal": True,
            "card_names": list(cards),
        })
    (destination / "deck-manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return manifest


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--repo", type=Path, default=Path("."))
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--deck-a", required=True)
    p.add_argument("--deck-b", required=True)
    p.add_argument("--name-a", default="Deck_A")
    p.add_argument("--name-b", default="Deck_B")
    p.add_argument("--sha-a", required=True)
    p.add_argument("--sha-b", required=True)
    a = p.parse_args()
    if a.name_a == a.name_b or a.deck_a == a.deck_b:
        p.error("Two distinct deck labels and sources required")
    print(json.dumps(convert(a.repo, a.output, a.deck_a, a.deck_b,
                             (a.name_a, a.name_b), (a.sha_a, a.sha_b)), indent=2))


if __name__ == "__main__":
    main()
