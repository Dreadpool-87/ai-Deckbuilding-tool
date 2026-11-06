#!/usr/bin/env python3
"""Stage checksum-verified MTGJSON data for a PRIVATE, DRAFT GitHub Release.

Never commits source datasets and never publishes a public Release.
"""
import argparse
import csv
import gzip
import hashlib
import json
import re
from pathlib import Path
from urllib.request import Request, urlopen

from update_mtgjson_atomic import prepare as prepare_atomic, fetch as fetch_atomic

BASE = "https://mtgjson.com/api/v5/csv/"
TABLES = {
    "cards": (105 * 1024 * 1024, 10000),
    "cardIdentifiers": (65 * 1024 * 1024, 10000),
    "cardRulings": (65 * 1024 * 1024, 1000),
}
MIN_ARCHIVE_BYTES = 100_000


def parse_sha256(raw, filename):
    parts = raw.decode("ascii").strip().split()
    if not parts or not re.fullmatch(r"[0-9a-fA-F]{64}", parts[0]):
        raise ValueError("Invalid official SHA-256 format: " + filename)
    if len(parts) > 2 or (len(parts) == 2 and
                          parts[1].lstrip("*") != filename):
        raise ValueError("Unexpected SHA-256 filename: " + filename)
    return parts[0].lower()


def validate_csv(path, minimum_records):
    count = 0
    csv.field_size_limit(10_000_000)
    with gzip.open(path, "rt", encoding="utf-8-sig", newline="") as stream:
        reader = csv.reader(stream)
        header = next(reader, None)
        if not header or len(header) < 2 or "uuid" not in header or len(set(header)) != len(header):
            raise ValueError("Missing/invalid CSV headers: " + path.name)
        for record in reader:
            if len(record) != len(header):
                raise ValueError("Inconsistent CSV column count: " + path.name)
            count += 1
    if count < minimum_records:
        raise ValueError("Insufficient CSV records: " + path.name)
    return count


def fetch_verified_csv(table, folder):
    max_bytes, min_rows = TABLES[table]
    filename = table + ".csv.gz"
    checksum_url = BASE + filename + ".sha256"
    with urlopen(Request(checksum_url, headers={"User-Agent": "MTG-Deck-Tools/1.0"}),
                 timeout=90) as response:
        checksum_bytes = response.read(4096)
    expected = parse_sha256(checksum_bytes, filename)
    target = folder / filename
    digest = hashlib.sha256()
    size = 0
    try:
        with urlopen(Request(BASE + filename,
                             headers={"User-Agent": "MTG-Deck-Tools/1.0"}), timeout=180) as response:
            with target.open("wb") as dest:
                while block := response.read(1024 * 1024):
                    size += len(block)
                    if size > max_bytes:
                        raise ValueError("CSV exceeds configured safety limit: " + filename)
                    digest.update(block)
                    dest.write(block)
        if size < MIN_ARCHIVE_BYTES or digest.hexdigest() != expected:
            raise ValueError("Official SHA-256/size verification failed: " + filename)
        rows = validate_csv(target, min_rows)
    except Exception:
        target.unlink(missing_ok=True)
        raise
    (folder / (filename + ".sha256")).write_text(expected + "\n", encoding="ascii")
    return {"source": BASE + filename, "sha256": expected,
            "compressed_bytes": size, "records": rows}


def upstream_version():
    payload = json.loads(fetch_atomic("Meta.json"))
    version = payload["data"]["version"]
    if not isinstance(version, str) or not re.fullmatch(r"[A-Za-z0-9_.+-]{1,100}", version):
        raise ValueError("Invalid official MTGJSON version")
    return version


def prepare(folder):
    folder.mkdir(parents=True, exist_ok=True)
    before = upstream_version()
    atomic = prepare_atomic(folder)
    if atomic["version"] != before:
        raise ValueError("MTGJSON version changed during AtomicCards download")
    csv_data = {}
    for table in TABLES:
        csv_data[table] = fetch_verified_csv(table, folder)
    if upstream_version() != before:
        raise ValueError("MTGJSON version changed during multi-dataset download")
    manifest = {
        "version": before,
        "tag": "mtgjson-private-bundle-" + before,
        "source": "https://mtgjson.com/api/v5/",
        "visibility": "private-draft-only",
        "assets": {
            "AtomicCards.json.gz": {
                "source": atomic["source"], "sha256": atomic["sha256"],
                "compressed_bytes": atomic["compressed_bytes"],
                "card_names": atomic["card_names"]
            },
            **{table + ".csv.gz": data for table, data in csv_data.items()}
        },
        "limitations": [
            "CSV files do not embed the full source JSON metadata: upstream cross-file snapshot consistency cannot be conclusively established.",
            "MTGJSON MIT licensing does not independently clear Wizards/third-party rights; never publish the draft without separate review."
        ]
    }
    (folder / "manifest.json").write_text(
        json.dumps(manifest, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(args.output_dir), sort_keys=True))
