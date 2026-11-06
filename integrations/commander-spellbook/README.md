# Commander Spellbook Integration v0.2: Offline Combo Ingredients & Salt Metadata

**Status: verified ingredient screening (not rules-aware).** Independently written Python adapter; not an MTG rules engine, not a second deckbuilder. The existing `tools/card_search.py` remains responsible for strategy and heuristic **synergy**, while this analyzer screens **known, curated combos** from the official Commander Spellbook snapshot. The current Casual Builder, Tester and Validator do not execute this script automatically.

## Upstream, license and ethical use

- Official project: https://commanderspellbook.com/ ; syntax guide: https://commanderspellbook.com/syntax-guide/
- Source: https://github.com/SpaceCowMedia/commander-spellbook-backend ; **MIT software license**, Copyright (c) 2023 Commander-Spellbook.
- Official bulk-data documentation: https://github.com/SpaceCowMedia/commander-spellbook-backend/blob/master/docs/api.md
- Bulk dataset URL: https://json.commanderspellbook.com/variants.json.gz
- Our own code reads the officially published schema. **No upstream software source or bulk data is copied/committed into the repo.** This does not establish a right to republish the entire combo dataset. See `THIRD_PARTY_NOTICES.md`.
- The official docs request that consumers use periodic bulk snapshots instead of paginating the whole HTTP API. Our downloader is *explicitly invoked*, not automatic.
- Card-level salt ratings from EDHREC are **different data** from combo-level votes at Commander Spellbook. The MIT backend license does not license EDHREC rating data. Never scrape/publish EDHREC card-salt data without an authorized source.

## Supported modes

| Mode | Input | Meaning |
|---|---|---|
| `commander` (default) | `--deck` | Old behavior: supplied Commander section and optional identity/commander parameters |
| `casual60` | `--deck` | Requires exactly 60 cards; excludes all variants with `mustBeCommander` ingredients |
| `collection` | `--collection` | Scans current Name,Quantity inventory; no deck legality claim and no commander |

In `casual60` and `collection` modes, `--commander` and `--identity` are rejected. A Commander color identity is **not** a casual 60-card legality rule. For deck color restrictions and nonbasic copy limits, continue to use the existing Builder/Validator; the combo matcher does not repeat their duties. `collection` mode shares the *existing* CSV reader in `card_search.py`; keep both scripts in the same folder when uploading Project Sources.

The matcher accepts public, non-spoiler `OK` or `E` variants without unresolved template ingredients and checks exact card quantities case-insensitively. It reports candidate variants with all named ingredients present and variants missing exactly one **copy**. It conservatively skips candidates requiring a commander in non-Commander modes.

### Combo salt score

Each known combo can expose the official `salt` value (0–4) and `saltVoteCount`. The official scores are community averages updated periodically. A missing value is **null / UNKNOWN**, not zero. The resulting `combo_salt` metadata is explicitly separate from card salt, win rate, strength, and gameplay probability.

### Optional card salt

You may attach your own **appropriately licensed/authorized** CSV:

    Name,SaltScore,Source,AsOf
    Example Card,2.5,Source you are authorized to reuse,2026-10-01

The analyzer validates a 0–4 numeric score, nonempty Source and no duplicate names. Such scores appear under the distinct `card_salt` key. **No EDHREC card-score importer/scraper is provided.** Do not interpret missing scores as 0 or derive card salt from combo salt.

## Run it

First download the official bulk data *once* when you have internet access:

```bash
python integrations/commander-spellbook/download_snapshot.py \
  --output integrations/commander-spellbook/local-data/variants.json.gz
```

The downloader verifies basic gzip/size integrity and SHA-256 but does not guarantee the snapshot's correctness. Keep bulk data and private collections out of Git.

**Casual 60-card existing deck:**

```bash
python integrations/commander-spellbook/analyze.py \
  --mode casual60 --deck current_deck.txt \
  --snapshot integrations/commander-spellbook/local-data/variants.json.gz \
  --limit 30 --output combo_report.json
```

**Private current inventory (owned combo candidates, not a deck):**

```bash
python integrations/commander-spellbook/analyze.py \
  --mode collection --collection current_collection.csv \
  --snapshot integrations/commander-spellbook/local-data/variants.json.gz \
  --limit 30 --output owned_combo_candidates.json
```

**Combined combo + thematic synergy report**: reuse the existing `card_search.py` and your existing MTGJSON dataset instead of inventing a second synergy engine:

```bash
python integrations/commander-spellbook/analyze.py \
  --mode casual60 --deck current_deck.txt \
  --snapshot integrations/commander-spellbook/local-data/variants.json.gz \
  --oracle AtomicCards_slim_v2.json.gz --theme lifegain \
  --max-synergy-pairs 100 --limit 50 --output joint_combo_synergy.json
```

The `theme_candidates` section contains the existing Card Search role evidence for **owned/deck-present cards only**. For Lifegain it also includes bounded heuristic card-pair suggestions; other themes retain v0.3's existing per-card role classification without claiming universal combo discovery. `--oracle` and `--theme` must both be present or both absent. The `card_search.py` source is shared, not duplicated.

**Optional separately attributed card salt scores**: append `--card-salt-csv current_card_salt.csv` to either command. If using ChatGPT Projects, upload `analyze.py` (beside your existing `card_search.py`), and provide the Spellbook snapshot as a Project/Chat file. Python execution and file availability must be verified in the actual Project chat; simply adding a script as a Project Source does **not** execute it.

The output includes input and dataset SHA-256, dataset timestamp/version, candidate counts, `combo_salt` and optional `card_salt`. Local input paths are omitted for privacy. The official syntax guide (`cards<=2`, `is:winning`, `salt<2`, `legal:modern`, etc.) describes **website/API search syntax**, not CLI parameters recognized by this offline tool. We do not claim full query-language support.

## Guarantees and limitations

**INGREDIENT_SCREEN_ONLY**: a matching ingredient set does not establish that a combo can actually be executed. Mana, starting zones, prerequisites, turn order, timing, other cards, Commander identity, deck legality, format banlists and gameplay are **not** verified. `prerequisites` and `steps` are copied only if the snapshot contains the expected string fields, and remain unverified source information.

Conflicting spellings, Oracle/DFC aliases and replacement cards are **not** resolved. Variant templates are skipped deliberately, rather than claiming a complete combo catalog. Output is bounded by `--limit`, while totals are reported separately. Blank or unsupported variant salt values remain unknown. Casual 60-card combo matching is useful as a discovery tool but does not imply Commander-only variants are playable.

## Tests

```bash
python -m unittest discover -s integrations/commander-spellbook/tests -p 'test_*.py' -v
python -m unittest discover -s tests -p 'test_*.py' -v
```

Synthetic tests cover Commander backward compatibility; casual length and commander exclusion; case-insensitive quantity matching; separated salt score provenance; user card-salt CSV parsing; privacy and the CLI. **Real official bulk export verified on 2026-10-15.** An explicitly invoked, one-off GitHub Actions smoke test fetched the official compressed snapshot (29,326,432 bytes, SHA-256 `d8424ddcc1f41e09883844656c0ff8847cc9781216910468dc4ba42a5d6d2043`, exporter version 7.1.11, timestamp 2026-10-15T13:11:32Z). The export contained **114,756 variants**, with **1,236** requiring a commander and **108** exposing a numeric combo salt value. The real-data test confirmed that a **60-card synthetic deck with Sanguine Bond and Exquisite Blood** yields the corresponding two-card ingredient candidate. Results establish **data schema and ingredient-matching compatibility only**, not mana/timing/rules correctness, complete coverage, or a verified deck strength assessment.

The temporary automated bulk-download step was removed after the successful check; normal GitHub CI runs **only offline synthetic tests**. The reusable `tests/live_bulk_smoke.py` may be invoked manually when the official schema changes. No official export or personal collection is committed, published, or bundled.


## Deck entry separators

Use `4 Lightning Bolt`, `4x Lightning Bolt`, `4× Lightning Bolt`, or `4×Lightning Bolt`. An attached ASCII `x` or `X` requires a following space. After whitespace immediately following the quantity, the text is a card name. This preserves names such as `Xenagos, God of Revels`. Convert separated ASCII markers such as `4 x Lightning Bolt` to `4x Lightning Bolt` before import.
