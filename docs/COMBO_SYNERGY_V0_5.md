# Combo & Synergy Report v0.5 (KISS)

**One script, existing engines unchanged.** `tools/combo_synergy_report.py` combines existing Card Search v0.3, Synergy Engine v0.4 and optional Commander Spellbook v0.2. For submitted decks it calls the existing Deck Validator v1.1.1 first. No new parser, rules engine, ranking algorithm, inference system or automatic downloader was added.

## Inputs

Provide the **current confirmed collection CSV** (`Name,Quantity`) and a local MTGJSON AtomicCards file. A decklist and a locally supplied official Spellbook snapshot are optional for the appropriate modes. No collection or full dataset is stored in Git.

The report uses a **single requested theme** and is bounded to 1–100 displayed results per analysis. Other themes require a separate run; it does not silently enumerate the entire card pool across all strategies.

### 1. Explore a current collection

```bash
python tools/combo_synergy_report.py \
  --oracle AtomicCards_slim_v2.json.gz --collection CURRENT_COLLECTION.csv \
  --theme sacrifice --limit 30 --output collection_report.json
```

The `combos` section says `NOT_EXECUTED` without `--snapshot`, but Card Search and supported synergy detection still run.

### 2. Add the official Spellbook snapshot, if available

```bash
python tools/combo_synergy_report.py \
  --oracle AtomicCards_slim_v2.json.gz --collection CURRENT_COLLECTION.csv \
  --theme sacrifice \
  --snapshot variants.json.gz --output combined_report.json
```

Official bulk data may be fetched **explicitly, separately** using the existing `integrations/commander-spellbook/download_snapshot.py`. No automated bulk fetch, API crawl, dataset replication, or EDHREC salt-score scraping.

In **collection mode** only, known Basic lands with a verified `Basic` supertype in the supplied Oracle data are treated as available without an ownership limit **for ingredient screening**. This does not add them to the CSV or a deck. The report does not invent a deck size from its internal quantity sentinel.

### 3. Analyze an existing casual deck

```bash
python tools/combo_synergy_report.py \
  --oracle AtomicCards_slim_v2.json.gz --collection CURRENT_COLLECTION.csv \
  --mode casual --deck my_deck.txt --theme tokens \
  --snapshot variants.json.gz --output casual_report.json
```

The existing Validator enforces 60 **or more** cards and ownership. The existing Spellbook casual matcher accepts **exactly 60**: for valid larger casual decks, Spellbook is explicitly `NOT_EXECUTED` rather than pretending the deck is invalid. Synergy and Card Search continue.

### 4. Analyze a Commander deck

```bash
python tools/combo_synergy_report.py \
  --oracle AtomicCards_slim_v2.json.gz --collection CURRENT_COLLECTION.csv \
  --mode commander --deck my_commander.txt --commander "Commander Name" \
  --theme artifacts --snapshot variants.json.gz \
  --output commander_report.json
```

Requires an explicit single commander in the 100-card decklist. The commander identity filter is derived from matching Oracle variants if their color identity agrees. The existing Validator checks deck count, owned cards, copy limits and basic Commander identity rules. Partner, background, special text-based deck exceptions and bans are **not** fully supported, and no result claims otherwise.

## Output and error behavior

- **`BLOCKED_INVALID_DECK`**: existing Validator reported a demonstrable failure. No synergy or combo claims are calculated.
- **`PARTIAL`**: missing optional Spellbook data, unsupported heuristic pair profile, a deck validation uncertainty, or unresolved Commander identity. Other safe sections remain visible.
- **`COMPLETED_WITH_LIMITATIONS`**: available steps finished, but no gameplay or format legality guarantee is made.
- The separate `card_search`, `synergies` and `combos` sections preserve their upstream classifications; known curated Spellbook ingredient candidates are **not** described as a gameplay-verified combo. Lifegain continues using Card Search's v0.3 pair engine. Other supported pairs come from Synergy Engine v0.4.
- Missing Spellbook salt scores stay null/`UNKNOWN`. Individual card salt is **not** inferred from combo salt.
- All stored input stays local; the report carries source SHA-256 fingerprints, not absolute paths.

**Important:** the combined report does not replace the independent Validator, the Builder's critical Oracle review, the Deck Tester, or an MTG rules engine. Some combinations are conditional or unsupported by the data. Do not claim win probability, Power Level, legal executable infinite loops or deck performance.

## ChatGPT Projects

GitHub does **not** automatically synchronize with your Builder Project. To execute outside the repository in a Python-enabled Project session, provide the source files `combo_synergy_report.py`, `card_search.py`, `synergy_engine.py`, `analyze.py` (Spellbook), and `MTG_Deck_Validator_v1.1.1.py` in the same runtime directory, plus the MTGJSON snapshot and current-chat collection. The project must actually be able to run Python and access these files. Merely attaching scripts as Project Sources does not execute them.

No existing stable Builder, Tester or Validator prompt is changed by v0.5. Power Level and Forge work are deferred.

## Verification

```bash
python -m unittest discover -s tests -p 'test_*.py' -v
python -m unittest discover -s integrations/commander-spellbook/tests -p 'test_*.py' -v
```

`tests/test_combo_synergy_report_v0_5.py` covers collection, optional and invalid snapshot, unlimited Basic lands without fabricated ownership, casual 60/61, Commander 100, invalid deck ownership blocking, Lifegain, unsupported themes, optional-module absence, and CLI privacy.

**Real-data end-to-end audit (2026-10-15):** GitHub Actions run 38773527429 (historical private reference), Python 3.12, downloaded official full MTGJSON AtomicCards (51,998,108 bytes; SHA-256 `66405a24a75123eee60426e51f297126d5fe8d60d7093f6862ad323f9dc55b87`) and official Commander Spellbook bulk variants (29,326,456 bytes; SHA-256 `55550264c1f388a79483f87808618d86250988e34ab078e8a2212cee3e3ff277`). Two **synthetic decks made from real public cards** passed the integrated Validator, Lifegain pair detection and known `Sanguine Bond + Exquisite Blood` combo-ingredient screen: **casual 60-card** (58 Swamp plus the pair) and **Commander 100-card** (Ayara, First of Locthwain; 97 Swamp plus the pair). Both showed `COMPLETED_WITH_LIMITATIONS`, the proper Spellbook scope and an actual `PASS_WITH_LIMITATIONS` validator result. These were public fixture lists, **not a user collection or real gameplay simulation**. All routine CI remains offline; the one-time dataset-fetch step was removed after the audit.

This check establishes compatibility with that official snapshot for those representative decks, **not** exhaustive card mechanic interpretation, real owner collection coverage, completed combo execution or gameplay success.
