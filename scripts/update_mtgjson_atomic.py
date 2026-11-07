#!/usr/bin/env python3
"""Verify official full AtomicCards temporarily; publish metadata only."""
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

def official_response(name, timeout=90):
    result = urlopen(Request(BASE + name, headers={"User-Agent": "AI-Deckbuilding-Tool/1.0", "Cache-Control": "no-cache"}), timeout=timeout)
    if result.geturl() != BASE + name:
        result.close()
        raise ValueError("Unexpected upstream redirect")
    return result


def fetch(name, limit=131072):
    with official_response(name) as response:
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

def ensure_upstream_snapshot_unchanged(version, checksum):
    """Never record a moving 'latest' URL if MTGJSON changed mid-download."""
    latest = json.loads(fetch("Meta.json"))
    latest_version = latest.get("data", {}).get("version") if isinstance(latest, dict) else None
    latest_checksum = parse_checksum(fetch(ARCHIVE + ".sha256"))
    if latest_version != version or latest_checksum != checksum:
        raise ValueError("MTGJSON upstream changed during verification; retry on next run")


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
        with official_response(ARCHIVE, timeout=180) as response:
            with path.open("wb") as dest:
                while block := response.read(1024 * 1024):
                    size += len(block)
                    if size > MAX_BYTES:
                        raise ValueError("Compressed file too large")
                    digest.update(block)
                    dest.write(block)
        if size < 1024 * 1024 or digest.hexdigest() != checksum:
            raise ValueError("Download size/checksum verification failed")
        # Reuse the runtime's bounded, strict full-record integrity check.
        helper = Path(__file__).resolve().parents[1] / 'tools/atomic_runtime.py'
        support = {'__name__': 'weekly_atomic_integrity'}
        exec(compile(helper.read_bytes(), str(helper), 'exec'), support)
        coverage = support['inspect_archive'](path, checksum, version)
        count = coverage['card_names']
        ensure_upstream_snapshot_unchanged(version, checksum)
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
