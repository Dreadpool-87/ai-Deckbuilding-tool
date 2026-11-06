# MTG Card Search v0.3: Theme, Role and Owned Synergy Discovery


## v0.3: collection-scoped Lifegain + Interaction + Synergy

Version 0.3 extends v0.2: no second database, duplicate builder, extra runtime dependency or hosted service. The bounded Lifegain profile recognizes life gains for the controller, Lifelink, grants of Lifelink, and conditional rewards for gaining life. Text such as "Whenever you gain life" is a **condition**, not a life source. An opponent gaining life does not mean you gain life.

- **CORE:** Controller life gain or printed Lifelink (damage is required).
- **ENABLER:** Supplies a possible life-gain event or grants Lifelink.
- **PAYOFF:** Explicitly responds to life gain.
- **INTERACTION:** Independent, heuristic tag for targeted removal, counterspells, discard/sacrifice disruption, damage and bounce. Not a complete interaction detector.
- **SYNERGY:** v0.2's per-card role remains. Version 0.3 optionally adds bounded **pair-level** suggestions between owned sources and payoffs; this is not a rules-aware combo check.

### Requested command: search before deck construction

    python tools/card_search.py \
      --oracle AtomicCards_slim_v2.json.gz \
      --collection current_collection.csv \
      --owned-only --theme lifegain --identity ANY \
      --role core --role enabler --role payoff --role interaction \
      --synergy --max-synergy-pairs 100 \
      --limit 500 --format json --output lifegain_candidates.json

ANY disables the color filter. It does **not** waive deck construction or mana requirements. Repeated roles mean OR, not AND. Results are paginated with --offset and next_offset. A card may have more than one role.

Synergy candidates are computed from the entire role-filtered, **owned** candidate set before pagination. The analysis is capped at --max-synergy-pairs (1..500) and reports possible_pairs, returned_pairs and truncated. --synergy requires --theme lifegain, --collection and --owned-only. Each pair contains card names, quantities, source/payoff Oracle excerpts, confidence=HEURISTIC, conditional=true and status=CANDIDATE_NOT_RULES_VERIFIED. No timing, mana, targeting, board-state or gameplay simulation is claimed.

Unrecognized collection entries outside a slim MTGJSON snapshot are reported through collection_coverage and are **not** silently treated as nonexistent. The personal CSV is only a local input; it is never committed or uploaded by the script.

### Real-data audit hardening

The classifier recognizes several bounded patterns: self-lifelink limited to the active turn, choices that grant lifelink, tokens with lifelink, and payoffs gated on earlier life gain. It can also tag targeted power-and-toughness reduction as interaction.

Pair suggestions sort **repeatable nonland sources first**, then other nonland cards and finally lands, before applying the cap. This is a display heuristic, not proof of deck strength; different colors may not fit the same mana base. Life-gain replacement modifiers without an independent life-gain source are excluded as stand-alone two-card sources. Threshold payoffs include `requires_threshold_check=true`; a pair can require additional life gained on the turn to function. Pair evidence is not a simulation, and multi-card prerequisites are not automatically solved.

The audit of a *private* collection remains local: no user's inventory, filenames, card lists, generated pairs or execution artifacts should be committed to the repository. New synthetic tests, not the user's collection, are suitable for GitHub CI.

Generic interaction is opt-in for themes other than Lifegain through `--role interaction`. The existing deck validator, Commander Spellbook checker and Forge remain separate.

### Original implementation and licensing

The new code is independently implemented, using existing MTGJSON reference data. The projects eliador90/mtg_collection, nccurry/mtg-mcp and mwisnowski/mtg_python_deckbuilder were reviewed solely as design references. No external source files or dependencies were copied. Any future vendor/import requires a separate pinned-revision license, copyright and transitive-dependency assessment.

### Testing

Run: python -m unittest discover -s tests -p "test_*.py" -v

The tests/test_card_search_lifegain_v0_3.py module covers lifegain classification, opponent-life false positives, interaction, collection-only pairs, color ANY, pagination, Oracle variant disagreement, CLI JSON and old Deathtouch behavior. Unit tests use synthetic fixtures; a separate real-data smoke test is needed before claiming broad MTG card coverage.

**Purpose:** Give the existing **ChatGPT Casual Deck Builder v7.3** a reproducible shortlist of cards matching a requested mechanic or strategy. The user attaches their **current collection CSV separately in every chat**. The searcher only suggests candidates; the Builder chooses an actual deck and the Validator checks deck construction and ownership.

**Requirements:** Python 3.9+ (standard library), the project's `card_search.py`, an MTGJSON **AtomicCards** `.json` or `.json.gz` (the existing `AtomicCards_slim_v2.json.gz` also works), and optionally a current collection CSV with `Name` and `Quantity` headers. No paid service or second card database is required.

Source attribution: [MTGJSON](https://mtgjson.com/), Zach Halpern and contributors, MIT; [MTGJSON API v5](https://mtgjson.com/api/v5/). Magic: The Gathering belongs to Wizards of the Coast. See the repository's `THIRD_PARTY_NOTICES.md` and `LICENSE` for the project's licensing boundaries.

## The two intended ChatGPT Project workflows

### A. Search first, build later

User message:

> This is my current collection CSV. Search all cards I own for Deathtouch. Group them as **CORE**, **ENABLER**, **PAYOFF**, and **SYNERGY**. Show the number of copies I own and the actual Oracle-text evidence. Do not build a deck yet.

If Python is genuinely available and the Project sources are accessible as files, run:

```bash
python card_search.py \
  --oracle AtomicCards_slim_v2.json.gz \
  --collection my_current_collection.csv \
  --owned-only --theme Deathtouch \
  --limit 500 --format json --output deathtouch_candidates.json
```

If the user then says **"Build a Golgari Deathtouch deck from those cards"**, the Builder must *recheck the active collection* and choose a legal, coherent 60-card deck, adding owned mana, removal, card draw and other support as appropriate. Role matching is a **candidate suggestion, never automatic permission** to include an unowned card.

### B. Direct thematic deckbuilding

User message:

> This is my current collection CSV. Build the strongest casual 60-card deck based on Deathtouch. First search my current inventory for cores, enablers, payoffs and synergies; then add other owned support cards where the deck needs them. Check the exact owned quantities and mana curve. Do not use unowned nonbasic cards.

Run the same search before deck construction. If the user specifies **all creatures must have Deathtouch**, that is a separate hard constraint. **"Deathtouch themed" does NOT mean all 60 cards must say "deathtouch"**, because lands, removal and supporting engines may not mention the keyword.

### C. Find a mechanic and optionally narrow it

The `--theme` parameter accepts **any nonempty mechanic or theme text**, not a closed allowlist:

```bash
python card_search.py --oracle AtomicCards_slim_v2.json.gz \
  --collection my_current_collection.csv --owned-only \
  --theme Proliferate --format json

python card_search.py --oracle AtomicCards_slim_v2.json.gz \
  --collection my_current_collection.csv --owned-only \
  --theme Deathtouch --subtype Elf --identity BG --max-mv 3

python card_search.py --oracle AtomicCards_slim_v2.json.gz \
  --collection my_current_collection.csv --owned-only \
  --theme Deathtouch --role enabler --role payoff --format text
```

**Important distinction:** every topic can be searched for *explicit Oracle text mentions*; indirect, wordless synergy requires mechanic-specific patterns or Builder reasoning. The included v0.2 heuristic library covers selected Deathtouch, Lifelink, Landfall, Proliferate, Sacrifice, Treasure, Tokens and +1/+1-counter interactions. It **does not discover every possible interaction** and does not establish that cards can legally perform a combo.

## Creature subtype and Oracle-text evidence

A theme such as `--theme "Elf tribal"` considers a creature with the exact MTGJSON `subtypes` entry `Elf` even when its Oracle text omits the word. A card with Oracle text mentioning Elf or Elves can also match without having that subtype. Each result's `theme_match_basis` separates consistent `CREATURE_SUBTYPE` and `ORACLE_TEXT` matches across records. A subtype match alone gives a heuristic core role and says nothing about strategic strength.

Role evidence may identify a `DIRECT_SYNERGY_CANDIDATE` where a recognized interaction or explicit reference links the role to the requested theme. This still requires rules review. `HEURISTIC_STRATEGY` covers broader role patterns. An Oracle-text mention on its own provides evidence of wording only.

## Names and collection input

Ordinary `--name` queries support case-insensitive substring discovery. A combined AtomicCards name such as `Wear // Tear` can be selected by the full name with optional spacing around `//` or by an exact face name corroborated by `faceName` on a matching canonical record. This applies to split, flip, modal double-faced, transform, Adventure and Prepare layouts with consistent metadata. A slim record can omit layout or side if the canonical name and explicit face name agree. A face query selects the whole card entry. Other filters still use the existing conservative agreement across its records.

The same exact identity lookup applies to collection rows. A spelling resemblance, delimiter component without corroborating metadata, or unsupported meld face supplies no owned copies. Shared face names, competing canonical name claims and contradictory face metadata are reported as `UNVERIFIED`. Inspect `name_identity` for exact name queries and `collection_coverage` for unmatched and unverified CSV names. Duplicate keys anywhere in the Oracle JSON abort loading. A slim snapshot can only check uniqueness within its own records. Use full canonical names and a trusted complete snapshot when a short name could be ambiguous outside that snapshot.

Collection CSVs require unique headers including `Name` and `Quantity`, a consistent number of fields, a nonempty name and a nonnegative integer quantity on every data row. Blank physical lines are allowed. Malformed rows abort discovery with the start line and cause. Repeated resolved rows add their quantities, so list each owned copy only once even if a card has multiple face names.

## Search types and evidence semantics

| Filter | Meaning |
|---|---|
| `--ability Deathtouch` | Conservative **standalone printed** ability search only (v0.1 compatible) |
| `--keyword Deathtouch` | MTGJSON keyword metadata (which may not enumerate grants or conditional uses) |
| `--text "gains deathtouch"` | Literal case-insensitive Oracle-text substring |
| `--theme Deathtouch` | Group candidates by roles using explicit text and bounded synergy patterns |
| `--role core` | Select at least this role; repeat flags for **OR** matching |
| `--name`, `--type`, `--subtype` | Name/primary type/subtype filters |
| `--identity BG` | Filter to color identity subset of BG, including mono-black, mono-green and colorless; **not** a casual format rule |
| `--min-mv`, `--max-mv` | Inclusive printed mana value filters |
| `--collection FILE --owned-only` | Only available nonbasic cards in the current CSV; established project unlimited Basic-land policy |
| `--limit N --offset N` | Sort and paginate results (default 50, maximum **500 per page**); `total_matches` is not truncated |
| `--format json --output FILE` | Machine-readable candidates for the ChatGPT Builder; JSON contains exact text evidence |

Every role evidence object has `role`, `reason`, `evidence`, `confidence` (`HIGH` or `HEURISTIC`), `conditional` and `basis`. A card may have **multiple roles**, and confidence does not certify a comprehensive rules analysis. Uncertain multi-printing or malformed data are conservatively flagged or excluded.

### What the roles mean

- **CORE:** the requested ability, mechanic or creature subtype appears on the card itself. A self-activated ability may be labeled conditional CORE, not unconditional CORE.
- **ENABLER:** a card can grant/enable the mechanic. Conditions such as tribal restrictions or temporary duration must be inspected by the Builder.
- **PAYOFF:** a triggered or conditional effect explicitly benefits from the theme, such as Hooded Blightfang's Deathtouch-dependent attacks. Merely having the ability and an unrelated trigger is **not** a payoff.
- **SYNERGY:** a suggested interaction. A Deathtouch creature plus a Rabid Bite-style effect is one example; Oracle/rules verification is required.

**SUPPORT** (land base, removal, card draw, fixing) is deliberately **selected by the Builder**, not inferred by thematic keyword matches. A candidate list alone is not a deck, nor does it guarantee Commander/casual legality, available copies, mana consistency or gameplay performance.

## ChatGPT Project setup (Android or web)

1. Open your existing **MTG Casual Deck Builder** Project and its **Sources** section.
2. Keep `MTG_Deck_Builder_v7.3_full.md`, your existing casual rules and `AtomicCards_slim_v2.json.gz`.
3. Upload **`card_search.py`** and **`CARD_SEARCH.md`** as additional Project sources. If you want to use the newer Tester, replace the old Tester Project source with **`MTG_Deck_Tester_v3.4.2_full.md`** (English-output edition for this candidate).
4. **Never add your personal collection as a permanent Project source.** Upload the relevant CSV anew when starting a deckbuilding chat, exactly as you prefer. If multiple CSVs appear in one chat, confirm whether a later upload replaces or adds to the current one before combining them.
5. In the Project chat, explicitly ask it to *actually execute* the search with Python, inspect the returned JSON/evidence and only then build. **A `.py` file in Sources is not automatically executed.** If the environment cannot access or run the files, require an honest limitation report, not fabricated search results.

Suggested English-language Project instruction:

> When a current collection CSV is uploaded in this chat, use it as the **only** source of owned nonbasic cards. The MTGJSON Project database is card reference data only. For mechanic/strategy searches, use `card_search.py` (version 0.2) with the active CSV and `--owned-only` when code execution is available; otherwise transparently use a limited, verified manual analysis and do not claim script execution. Classify and report CORE, ENABLER, PAYOFF and SYNERGY with actual Oracle text and uncertainty notes. If the user asks only to search, **do not build a deck**. If the user asks to build, pass the verified candidate list to Casual Builder v7.3, consider additional owned support, enforce all Builder ownership/copy/quantity rules, and then validate the complete deck. Keep Deck Tester v3.4.2 distinct: do not claim full-game simulation without an actual rules-aware engine. Do not assume a collection persists across chats.

## Accuracy and privacy checks

- The optional CSV should have `Name,Quantity` columns. Additional columns like `Sets` and `Quantities by set` are accepted; copies of one card are summed by canonical name (case-insensitive).
- The slim MTGJSON file intentionally contains a **subset** of Magic cards. Verify that every owned card name appears in the available database. Unknown cards are **UNKNOWN**, not nonexistent.
- The old `--ability`, `--keyword`, `--text`, `--identity`, `--limit`, `--format` and `--owned-only` options still work.
- Multiple selected `--role` flags mean **OR**, not AND. All other active filters are combined with **AND**.
- For more than 500 matching cards, use `next_offset` to request subsequent pages. Never imply that the first 50 or 500 records are every match.
- `--theme` heuristics omit indirect synergies they cannot prove; conditional text is labeled, not silently elevated to a guaranteed synergy.
- The user's collection CSV and MTGJSON file are **never uploaded or committed to GitHub** by these scripts. The included sample-result JSON is for the *example collection* supplied in the chat only and must not be published into a public repository.
- Running these scripts does not modify the original Deck Builder v7.3, Validator v1.1.1, archived prompts or gameplay engine.

## Testing

```bash
python -m unittest discover -s tests -p "test_*.py" -v
python -m unittest -v tests/test_card_search_roles_v0_2.py
```

The repository's test workflow runs regressions on Python 3.12 and 3.13. The new classifier needs its own real-data smoketest with the slim MTGJSON and CSV; private sample outputs belong in the user's chat, not the repository.
