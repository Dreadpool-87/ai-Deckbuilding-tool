# MTG Synergy Engine v0.4 — owned pair suggestions

**Status:** bounded offline heuristic, not a combo database, a gameplay engine, or a deckbuilder. This module extends our AI Deckbuilding Tool search workflow. The original `tools/card_search.py` remains the **only** parser for MTGJSON and active collection CSVs; the independent Commander Spellbook adapter remains the source for documented combo *ingredient candidates*. No code or dataset from Draftsim, EDHREC, or Spellbook has been copied here.

## Scope: eight strategy profiles

| Theme | Source | Payoff / beneficiary | Important uncertainty |
|---|---|---|---|
| `sacrifice` / `aristocrats` | Sacrifice own creature effect/outlet | Death or sacrifice triggers | Needs sacrificeable creature, timing and appropriate control |
| `tokens` | Creates tokens | Token- or creature-entry trigger | Token subtype, entering and timing may matter |
| `proliferate` | Performs Proliferate | Puts relevant counters on permanents | Counters must already be present on valid objects |
| `blink` / `etb` | Exiles and returns permanent to battlefield | ETB trigger | Target, return timing and zone restrictions not checked |
| `artifacts` | Creates artifact tokens | Artifact-entry/death trigger or artifact count | Need appropriate artifacts and trigger timing |
| `spellslinger` | Instant or Sorcery card | Casting instant/sorcery/noncreature spells trigger | Must be cast (copying is not always casting) |
| `landfall` | Additional land play or battlefield placement | Landfall/land-entry payoff | Needs playable land and available land-drop |
| `counters` | Puts +1/+1 counters | Cares about counter placement/count | Requires eligible targets and correct counter types |

**Lifegain remains in `card_search.py --theme lifegain --synergy` (v0.3)** and Deathtouch's per-card rules remain in `card_search.py`. General per-card text search accepts many other strategies, but unknown themes do **not** silently get invented pair matches. Future profiles can be added explicitly after regression tests.

## How to use with a current collection

```bash
python tools/synergy_engine.py \
  --oracle AtomicCards_slim_v2.json.gz \
  --collection CURRENT_COLLECTION.csv \
  --theme sacrifice --identity ANY \
  --limit 100 --output sacrifice_synergies.json

python tools/synergy_engine.py \
  --oracle AtomicCards_slim_v2.json.gz \
  --collection CURRENT_COLLECTION.csv \
  --theme proliferate --limit 100 --output proliferate_synergies.json
```

Upload `card_search.py` and `synergy_engine.py` beside one another when running in a ChatGPT Project Python environment. Upload `CURRENT_COLLECTION.csv` anew in each deckbuilding chat. Simply attaching scripts as Project Sources does **not** automatically execute them. Run both analyses separately when needed:

1. `card_search.py`: candidate card roles and explicit Oracle evidence.
2. `synergy_engine.py`: **bounded** source-to-payoff card-pair suggestions for eight registered themes.
3. `integrations/commander-spellbook/analyze.py`: known curated Spellbook combo *ingredient* checks, with published salt scores when available.

The deck Builder/Validator remains the sole authority for owned quantities, deck sizes, colors and format restrictions; results from this tool cannot waive those requirements.

## Output integrity

The output reports `source_count`, `payoff_count`, exact *possible* pair count under the limited profile, `returned_pairs`, `truncated`, a `pair_limit` (1–500) and `collection_coverage`. The source and payoff are separate **owned names** with existing CSV counts, Oracle or card-type evidence, `confidence=HEURISTIC`, `conditional=true`, and `status=POSSIBLE_SYNERGY_NOT_RULES_VERIFIED`.

Real-card false-positive guards distinguish graveyard self-reanimation (such as Bone Dragon) from actual blink effects, and distinguish +1/+1-counter replacement payoffs (such as Conclave Mentor) from independent counter sources. These are still heuristics, not exhaustive rules validation.

A round-robin ordering helps avoid showing only one source card repeatedly. Sorting considers hints of repeatability and mana value for **presentation only**, not relative deck power or win rates. Each role is retained only if all supplied Oracle variants agree that the role is present. Conflicting variants increment uncertainty counters.

No private collection, Oracle snapshot, Spellbook export, card salt score, or resulting user report is committed to Git. Do not assume this tool discovers all possible synergies; many Oracle interactions require rules-aware analysis or more than two cards. No gameplay simulation, deck construction, format legality, sideboard logic, turn-order analysis, card price or mana consistency is performed.

## Tests

```bash
python -m unittest discover -s tests -p "test_*.py" -v
```

The dedicated synthetic `tests/test_synergy_engine_v0_4.py` verifies all eight profiles, owned quantities, aliases, pair caps, source diversity, color filters, false positives, conflicting Oracle variants and CLI JSON.

### Verified public real-data smoke (2026-10-15)

A one-off GitHub Actions run (historical private reference) downloaded **official MTGJSON AtomicCards v5.3.0+20261015** (SHA-256 `66405a24a75123eee60426e51f297126d5fe8d60d7093f6862ad323f9dc55b87`, 51,998,108 compressed bytes; 35,122 distinct Oracle card names). The actual engine passed a real public-card pair for **every one of its eight registered themes**:

- Sacrifice: Ravenous Harpy → Poison-Tip Archer
- Tokens: Sai, Master Thopterist → Ajani's Welcome
- Proliferate: Evolution Sage → Ajani's Pridemate (requires suitable existing counters)
- Blink: Ephemerate → Ravenous Chupacabra
- Artifacts: Sai, Master Thopterist → Reckless Fireweaver
- Spellslinger: Shock → Guttersnipe
- Landfall: Explore → Tireless Tracker
- Counters: Ajani's Pridemate → Conclave Mentor

The audit also checked **false-positive exclusions** for Anointed Procession (token replacement, not a token source), Academy Manufactor (artifact-token replacement), and Bloodfell Caves (noncreature self-ETB not activated by creature-only blink). The effect of Bone Dragon's graveyard self-reanimation is additionally checked in synthetic Oracle-inspired regression tests. All source/pair outputs remain **heuristics, not game-rule proofs**.

The one-off network download step was removed from normal CI after a successful run. The reusable `tests/live_oracle_synergy_smoke.py` is deliberately excluded from default discovery and requires a caller-provided local AtomicCards snapshot and its expected SHA-256: `python tests/live_oracle_synergy_smoke.py --oracle /path/to/AtomicCards.json.gz --oracle-sha256 <expected-sha256>`. It makes no network request. No bulk MTGJSON files or private inventory were committed.

**Coverage boundary:** this verifies representative public real cards and an official snapshot, **not** exhaustive strategy accuracy, all card mechanics, or a user's entire inventory. Profiles can still miss supported interactions and may suggest conditional/nonfunctional pairs; deckbuilding remains subject to Oracle and deck validator review.

### Deferred milestones

After the v0.4 synergy review: unify the independent Card Search, Spellbook combo ingredients and v0.4 synergies in a clear Builder-facing report; then improve explanation quality, ranking and properly sourced saltiness. **Power Level / Commander bracket scoring is explicitly deferred** until those capabilities are stable and separately approved. EDHREC and Draftsim remain design references only, without copying code or scraping ratings.

## Provenance & external projects

Original Python implementation using our existing MTGJSON-backed card search. Third-party projects are *design references only*. We have not vendored Draftsim software (no reusable license verified), Commander Spellbook source, or data. Commander Spellbook's separate upstream MIT notices are maintained in `THIRD_PARTY_NOTICES.md` for its separately implemented integration.
