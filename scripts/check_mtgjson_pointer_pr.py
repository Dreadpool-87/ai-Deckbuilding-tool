#!/usr/bin/env python3
"""Decide whether a verified AtomicCards metadata PR is still necessary.

The Actions runner may be queued after verification while a separate
maintainer merges the same pointer. Always compare against freshly fetched
main before pushing a branch or proposing a PR. Never move or publish data.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
import re

SOURCE = "MTGJSON"
ARCHIVE = "AtomicCards.json.gz"
URL = "https://mtgjson.com/api/v5/AtomicCards.json.gz"
DIGEST_URL = URL + ".sha256"
MAX_POINTER_BYTES = 8192


def _distinct_object(pairs: list[tuple[str, object]]) -> dict:
    result: dict = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("DUPLICATE_POINTER_KEY")
        result[key] = value
    return result


def _reject_constant(_: str) -> None:
    raise ValueError("INVALID_POINTER_NUMBER")


def load_pointer(path: Path) -> dict:
    """Fail closed on missing, malformed or unexpected snapshot references."""
    if (path.is_symlink() or not path.is_file()
            or path.stat().st_size > MAX_POINTER_BYTES):
        raise ValueError("POINTER_UNAVAILABLE_OR_UNSAFE")
    try:
        data = json.loads(path.read_text(encoding="utf-8"),
                          object_pairs_hook=_distinct_object,
                          parse_constant=_reject_constant)
    except (UnicodeError, json.JSONDecodeError, RecursionError):
        raise ValueError("POINTER_JSON_INVALID") from None
    if (not isinstance(data, dict) or type(data.get("schema_version")) is not int
            or data["schema_version"] != 1
            or data.get("source") != SOURCE
            or data.get("dataset") != ARCHIVE
            or data.get("download_url") != URL
            or data.get("checksum_url") != DIGEST_URL
            or data.get("download_url_is_mutable") is not True):
        raise ValueError("POINTER_PROVENANCE_INVALID")
    sha = data.get("sha256")
    version = data.get("version")
    timestamp = data.get("verified_at_utc")
    if (not isinstance(sha, str) or not re.fullmatch(r"[0-9a-f]{64}", sha)
            or not isinstance(version, str)
            or not re.fullmatch(r"[A-Za-z0-9_.+-]{1,100}", version)
            or not isinstance(timestamp, str)
            or not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", timestamp)):
        raise ValueError("POINTER_IDENTITY_INVALID")
    try:
        datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except ValueError:
        raise ValueError("POINTER_TIMESTAMP_INVALID") from None
    return data


def proposal_decision(proposed: dict, current_main: dict | None) -> str:
    """Use verified snapshot identity, never just a version or branch name."""
    if current_main is None:
        return "PROPOSE"
    if (current_main["version"], current_main["sha256"]) == (
            proposed["version"], proposed["sha256"]):
        return "ALREADY_ON_MAIN"
    if current_main["verified_at_utc"] >= proposed["verified_at_utc"]:
        # A queued older verification must not overwrite newer metadata.
        return "SUPERSEDED_BY_MAIN"
    return "PROPOSE"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--proposed", type=Path, required=True)
    parser.add_argument("--current-main", type=Path,
                        help="Freshly fetched origin/main pointer, if present")
    args = parser.parse_args()
    proposed = load_pointer(args.proposed)
    current = load_pointer(args.current_main) if args.current_main else None
    print(proposal_decision(proposed, current))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
