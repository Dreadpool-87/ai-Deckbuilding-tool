#!/usr/bin/env python3
"""Record a verified MTGJSON AtomicCards pointer without re-hosting any card data.

Input MUST be the manifest emitted by update_mtgjson_atomic.py after it has
downloaded and checksum-verified the complete upstream archive. The output
contains only upstream URLs, version, SHA-256, counts, and a verification time.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re

SOURCE_URL = "https://mtgjson.com/api/v5/AtomicCards.json.gz"
CHECKSUM_URL = SOURCE_URL + ".sha256"
META_URL = "https://mtgjson.com/api/v5/Meta.json"
POINTER_RELATIVE_PATH = "data/mtgjson_atomic_latest.json"
HASH_LINE = re.compile(r"^([0-9a-f]{64})  (\S+)$")


def utc_timestamp(value: str | None) -> str:
    if value is None:
        return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", value):
        raise ValueError("INVALID_VERIFICATION_TIME")
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise ValueError("INVALID_VERIFICATION_TIME") from None
    return value


def validated_manifest(value: object) -> dict:
    if not isinstance(value, dict) or value.get("source") != SOURCE_URL:
        raise ValueError("INVALID_VERIFIED_SOURCE")
    version = value.get("version")
    if not isinstance(version, str) or not re.fullmatch(r"[A-Za-z0-9_.+-]{1,100}", version):
        raise ValueError("INVALID_VERIFIED_VERSION")
    sha256 = value.get("sha256")
    if not isinstance(sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", sha256):
        raise ValueError("INVALID_VERIFIED_SHA256")
    size = value.get("compressed_bytes")
    count = value.get("card_names")
    if (type(size) is not int or not 1024 * 1024 <= size <= 120 * 1024 * 1024
            or type(count) is not int or count < 20000):
        raise ValueError("INVALID_VERIFIED_COVERAGE")
    if value.get("license") != "https://mtgjson.com/license/":
        raise ValueError("INVALID_VERIFIED_LICENSE")
    return dict(version=version, sha256=sha256, compressed_bytes=size, card_names=count)


def read_hashes(path: Path) -> dict[str, str]:
    if path.is_symlink() or not path.is_file():
        raise ValueError("HASH_MANIFEST_UNAVAILABLE")
    result = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        match = HASH_LINE.fullmatch(line)
        if not match or match[2] in result:
            raise ValueError("HASH_MANIFEST_INVALID")
        result[match[2]] = match[1]
    return result


def record(manifest_path: Path, pointer_path: Path, hashes_path: Path,
           recorded_at: str | None = None) -> bool:
    # The publication workflow passes only its verified, small upstream manifest.
    # Never accept or publish the downloaded archive as an output.
    if manifest_path.is_symlink() or not manifest_path.is_file() or manifest_path.stat().st_size > 8192:
        raise ValueError("VERIFIED_MANIFEST_UNAVAILABLE")
    manifest = validated_manifest(json.loads(manifest_path.read_text(encoding="utf-8")))
    timestamp = utc_timestamp(recorded_at)
    old = None
    if pointer_path.exists() or pointer_path.is_symlink():
        if pointer_path.is_symlink() or not pointer_path.is_file() or pointer_path.stat().st_size > 8192:
            raise ValueError("POINTER_UNSAFE_OR_TOO_LARGE")
        old = json.loads(pointer_path.read_text(encoding="utf-8"))
        if (not isinstance(old, dict) or old.get("schema_version") != 1
                or old.get("source") != "MTGJSON"
                or old.get("download_url") != SOURCE_URL
                or old.get("checksum_url") != CHECKSUM_URL):
            raise ValueError("EXISTING_POINTER_UNTRUSTED")
    keys = ("version", "sha256", "compressed_bytes", "card_names")
    changed = old is None or any(old.get(key) != manifest[key] for key in keys)
    pointer = {
        "schema_version": 1,
        "source": "MTGJSON",
        "dataset": "AtomicCards.json.gz",
        "version": manifest["version"],
        "download_url": SOURCE_URL,
        "checksum_url": CHECKSUM_URL,
        "metadata_url": META_URL,
        "sha256": manifest["sha256"],
        "compressed_bytes": manifest["compressed_bytes"],
        "card_names": manifest["card_names"],
        "verified_at_utc": timestamp if changed else old["verified_at_utc"],
        "download_url_is_mutable": True,
        "notice": "Hash identifies a verified snapshot, not the future bytes at the mutable URL.",
    }
    content = json.dumps(pointer, indent=2, sort_keys=True) + "\n"
    checksums = read_hashes(hashes_path)
    checksums[POINTER_RELATIVE_PATH] = hashlib.sha256(content.encode("utf-8")).hexdigest()
    updated_hashes = "".join(f"{checksums[name]}  {name}\n" for name in sorted(checksums))
    if changed:
        pointer_path.parent.mkdir(parents=True, exist_ok=True)
        pointer_path.write_text(content, encoding="utf-8")
    if hashes_path.read_text(encoding="utf-8") != updated_hashes:
        hashes_path.write_text(updated_hashes, encoding="utf-8")
    return changed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verified-manifest", type=Path, required=True)
    parser.add_argument("--pointer", type=Path, default=Path(POINTER_RELATIVE_PATH))
    parser.add_argument("--hash-manifest", type=Path, default=Path("SHA256SUMS.txt"))
    parser.add_argument("--verified-at", help="UTC timestamp, YYYY-MM-DDTHH:MM:SSZ")
    args = parser.parse_args()
    changed = record(args.verified_manifest, args.pointer, args.hash_manifest, args.verified_at)
    print(json.dumps({"status": "POINTER_UPDATED" if changed else "UNCHANGED",
                      "dataset_republished": False}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
