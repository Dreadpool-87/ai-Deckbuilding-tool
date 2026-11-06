#!/usr/bin/env python3
"""One-off official bulk dataset smoke audit, intentionally excluded from routine CI.

This script downloads the official public export only when explicitly invoked.
No user collection or personal deck enters logs, GitHub, or the export.
"""
from __future__ import annotations
from collections import Counter
from pathlib import Path
import json
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from analyze import analyze, load_snapshot  # noqa: E402
from download_snapshot import download  # noqa: E402


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="spellbook-live-") as folder:
        source = Path(folder) / "variants.json.gz"
        meta = download(source)
        document = load_snapshot(source)
        variants = document["variants"]
        if not variants:
            raise AssertionError("The official Spellbook export contains no variants")
        known = {"sanguine bond", "exquisite blood"}
        matches = []
        statuses = Counter()
        salt_present = 0
        commander_required = 0
        for v in variants:
            if not isinstance(v, dict):
                continue
            statuses[str(v.get("status"))] += 1
            if isinstance(v.get("salt"), (int, float)) and not isinstance(v.get("salt"), bool):
                salt_present += 1
            uses = v.get("uses")
            if not isinstance(uses, list):
                continue
            names = {u.get("card", {}).get("name", "").casefold()
                     for u in uses if isinstance(u, dict)
                     and isinstance(u.get("card"), dict)
                     and isinstance(u["card"].get("name"), str)}
            if known <= names:
                matches.append(v)
            if any(isinstance(u, dict) and u.get("mustBeCommander") is True
                   for u in uses):
                commander_required += 1
        if not matches:
            raise AssertionError("Expected a known Sanguine Bond + Exquisite Blood variant")

        # 58 Swamps plus the two verified combo names. No private deck used.
        deck = Counter({"Swamp": 58, "Sanguine Bond": 1, "Exquisite Blood": 1})
        result = analyze(deck, Counter(), document, scope="casual60", limit=15)
        combo_candidates = result["exact_card_ingredient_candidates"]
        matching_candidates = [
            candidate for candidate in combo_candidates
            if known <= {k.casefold() for k in candidate["required_cards"]}
        ]
        if not matching_candidates:
            raise AssertionError(
                "Known two-card combo absent from casual60 ingredient candidates; "
                "inspect unsupported templates, snapshot schema and ranking/pagination"
            )
        if result["counts"].get("requires_commander_excluded", 0) < 0:
            raise AssertionError("Impossible commander-exclusion count")
        report = {
            "source": "official bulk export; NOT mirrored to the repository",
            "timestamp": document.get("timestamp"),
            "version": document.get("version"),
            "archive_sha256": meta["sha256"],
            "archive_size_bytes": meta["size_bytes"],
            "variants": len(variants),
            "status_counts": dict(statuses),
            "variants_with_numeric_salt": salt_present,
            "variants_requiring_commander": commander_required,
            "known_pair_variants": len(matches),
            "synthetic_casual60_exact_candidates": result["total_exact_card_ingredient_candidates"],
            "known_pair_reported": len(matching_candidates),
            "snapshot_parse": "PASS",
            "casual60_ingredient_smoke": "PASS",
        }
        print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
