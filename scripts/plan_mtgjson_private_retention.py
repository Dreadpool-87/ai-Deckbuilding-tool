#!/usr/bin/env python3
"""Read-only, fail-closed selection of exactly two private MTGJSON draft backups."""
import argparse
import json
import re
from pathlib import Path

TAG = re.compile(r"^mtgjson-private-bundle-[A-Za-z0-9_.+-]+$")
DATASETS = ("AtomicCards.json.gz", "cards.csv.gz",
            "cardIdentifiers.csv.gz", "cardRulings.csv.gz")
REQUIRED = set(DATASETS) | {name + ".sha256" for name in DATASETS} | {
    "manifest.json", "MTGJSON-MIT.txt", "THIRD_PARTY_NOTICES.md"
}


def choose(releases, current):
    if not isinstance(current, str) or not TAG.fullmatch(current):
        raise ValueError("Invalid current tag")
    if not isinstance(releases, list):
        raise ValueError("GitHub Releases response is not a list")
    managed, seen_ids, seen_tags = [], set(), set()
    for item in releases:
        if not isinstance(item, dict):
            raise ValueError("Unexpected Release response object")
        tag = item.get("tag_name", "")
        if not isinstance(tag, str) or not tag.startswith("mtgjson-private-bundle-"):
            continue   # Historical mtgjson-atomic-* and all unrelated Releases untouched.
        if not TAG.fullmatch(tag) or item.get("draft") is not True:
            raise ValueError("Unexpected tag or published managed Release: " + tag)
        ident = item.get("id")
        if not isinstance(ident, int) or isinstance(ident, bool) or ident <= 0:
            raise ValueError("Invalid Release ID: " + tag)
        assets = item.get("assets")
        if not isinstance(assets, list) or len(assets) != len(REQUIRED):
            raise ValueError("Missing/extra archive assets: " + tag)
        names = [a.get("name") for a in assets if isinstance(a, dict)]
        if set(names) != REQUIRED or len(names) != len(REQUIRED):
            raise ValueError("Incomplete or ambiguous archive assets: " + tag)
        if any(not isinstance(a.get("id"), int) or a["id"] <= 0
               or not isinstance(a.get("size"), int) or a["size"] <= 0 for a in assets):
            raise ValueError("Invalid asset metadata: " + tag)
        if tag in seen_tags or ident in seen_ids:
            raise ValueError("Duplicate Release tags or IDs")
        seen_tags.add(tag)
        seen_ids.add(ident)
        managed.append({"tag": tag, "id": ident,
                        "assets": sorted((a["name"], a["id"], a["size"]) for a in assets)})
    managed.sort(key=lambda row: row["id"], reverse=True)
    if current not in [row["tag"] for row in managed[:2]]:
        raise ValueError("Current release not among two newest verified candidates")
    return {"current": current, "keep": managed[:2], "older": managed[2:],
            "total_managed": len(managed)}


def load_release_pages(path):
    pages = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(pages, list):
        raise ValueError("Expected JSON array from gh api --paginate --slurp")
    # Some GH API calls produce a one-page array, others an array of arrays.
    return [item for page in pages for item in page] if pages and all(
        isinstance(page, list) for page in pages) else pages


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--current-tag", required=True)
    p.add_argument("--releases", type=Path, required=True)
    p.add_argument("--output", type=Path)
    p.add_argument("--recheck", type=Path)
    args = p.parse_args()
    result = choose(load_release_pages(args.releases), args.current_tag)
    if args.recheck:
        original = json.loads(args.recheck.read_text(encoding="utf-8"))
        if original != result:
            raise ValueError("Release inventory changed since retention plan; aborting")
        print("Release inventory unchanged.")
    elif args.output:
        args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n",
                               encoding="utf-8")
        print("Keep:", [v["tag"] for v in result["keep"]],
              "Older:", [v["tag"] for v in result["older"]])
    else:
        raise ValueError("--output or --recheck is required")


if __name__ == "__main__":
    main()
