#!/usr/bin/env python3
"""Fetch and verify official MTGJSON AtomicCards for a GitHub Release."""
import argparse
import gzip
import hashlib
import json
import re
from pathlib import Path
from urllib.request import Request, urlopen

BASE = "https://mtgjson.com/api/v5/"
ARCHIVE = "AtomicCards.json.gz"
MAX_BYTES = 120 * 1024 * 1024

def fetch(name, limit=131072):
    with urlopen(Request(BASE + name, headers={"User-Agent": "MTG-Deck-Tools/1.0"}), timeout=90) as response:
        data = response.read(limit + 1)
    if len(data) > limit:
        raise ValueError("Unexpectedly large metadata: " + name)
    return data

def parse_checksum(raw):
    text = raw.decode("ascii").strip()
    match = re.fullmatch(r"([0-9a-fA-F]{64})(?:\s+\*?AtomicCards\.json\.gz)?", text)
    if not match:
        raise ValueError("Unexpected MTGJSON checksum format")
    return match.group(1).lower()

def validate_data(payload, version):
    if not isinstance(payload, dict) or not isinstance(payload.get("data"), dict):
        raise ValueError("Invalid AtomicCards root")
    if len(payload["data"]) < 20000:
        raise ValueError("Unexpectedly few card names")
    for name in ("Mountain", "Shock", "Chandra's Spitfire"):
        cards = payload["data"].get(name)
        if not isinstance(cards, list) or not cards:
            raise ValueError("Missing card: " + name)
        if not all(isinstance(c, dict) and c.get("name") == name and
                   isinstance(c.get("types"), list) and
                   isinstance(c.get("manaValue"), (int, float)) for c in cards):
            raise ValueError("Unexpected card schema: " + name)
    if payload.get("meta", {}).get("version") != version:
        raise ValueError("Archive and Meta.json versions differ")
    return len(payload["data"])

def prepare(out):
    out.mkdir(parents=True, exist_ok=True)
    meta = json.loads(fetch("Meta.json"))
    version = meta["data"]["version"]
    if not isinstance(version, str) or not re.fullmatch(r"[a-zA-Z0-9_.+-]{1,100}", version):
        raise ValueError("Unexpected version")
    checksum = parse_checksum(fetch(ARCHIVE + ".sha256"))
    path = out / ARCHIVE
    digest = hashlib.sha256()
    size = 0
    try:
        with urlopen(Request(BASE + ARCHIVE, headers={"User-Agent": "MTG-Deck-Tools/1.0"}), timeout=180) as response:
            with path.open("wb") as dest:
                while block := response.read(1024 * 1024):
                    size += len(block)
                    if size > MAX_BYTES:
                        raise ValueError("Compressed file too large")
                    digest.update(block)
                    dest.write(block)
        if size < 1024 * 1024 or digest.hexdigest() != checksum:
            raise ValueError("Download size/checksum verification failed")
        with gzip.open(path, "rt", encoding="utf-8") as stream:
            count = validate_data(json.load(stream), version)
    except Exception:
        path.unlink(missing_ok=True)
        raise
    (out / (ARCHIVE + ".sha256")).write_text(checksum + "\n", encoding="ascii")
    manifest = {"version": version, "tag": "mtgjson-atomic-" + version,
                "source": BASE + ARCHIVE, "sha256": checksum,
                "compressed_bytes": size, "card_names": count,
                "license": "https://mtgjson.com/license/"}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest))
    return manifest

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=Path("mtgjson-build"))
    args = parser.parse_args()
    prepare(args.output_dir)
