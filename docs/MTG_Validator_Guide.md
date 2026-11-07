# MTG Deck Validator v1.1: User Guide (Historical Version)

> **Historical v1.1 guide.** For current public testing, run `python validator/MTG_Deck_Validator_v1.1.1.py --help` and see the [quickstart](AGENT_QUICKSTART.md) and [source pins](AGENT_SOURCE_COMPATIBILITY_P4.md). The [private beta release record](releases/CASUAL_PRIVATE_BETA_v0.2_2026-11-01.md) preserves the historical hash and rollback context.

The active Validator reads `4 Lightning Bolt`, `4x Lightning Bolt`, `4× Lightning Bolt`, and `4×Lightning Bolt`. Put a space after an attached ASCII `x` or `X`. With a space after the quantity, the following text is the card name, so `4 Xenagos, God of Revels` preserves the initial X. Write `4x Lightning Bolt` when importing a list with a separated ASCII marker such as `4 x Lightning Bolt`.

**Executable:** `validator/MTG_Deck_Validator_v1.1.1.py` in this repository.

This is an independent **offline** utility for checking hard constraints in a Magic: The Gathering decklist. It is tested on Python 3.12 and 3.13 and requires only the standard library. Keep the checkout layout or place the matching `card_identity.py` beside the public Validator. No GitHub account, external API, or API key is necessary.

## Required files

1. `validator/MTG_Deck_Validator_v1.1.1.py` and its matching `tools/card_identity.py`.
2. Your **active** collection as a CSV containing at least `Name` and `Quantity` (for example, `current_collection.csv`). The validator never silently merges multiple collections.
3. A local MTGJSON `AtomicCards` database, `.json` or `.json.gz` (for example, `AtomicCards_slim_v2.json.gz`). MTGJSON supplies **card facts**, not evidence of ownership.
4. Your final decklist as a **UTF-8 `.txt` file**, one quantity/name entry per line, such as `4 Shock`, `2 Banefire`, `21 Mountain`. Headings such as `Creatures (26)` are ignored. Unrecognized lines or sideboard sections cause `FAIL`; they are not silently accepted.

## Physical-card names and import

Use exact Oracle names for ordinary deck entries. For a supported multiface record, use the combined AtomicCards name or a corroborated front alias such as `Delver of Secrets`. A reverse or alternate face alone is discovery input only. Front and combined deck entries aggregate for ownership, deck totals and copy limits. The same rules apply to the single Commander name, with additional eligibility and color-identity checks. Malformed metadata, ambiguous names, and unsupported layouts including meld and reversible cards block verification.

CSV inventory labels are case-insensitive. Repeated rows with the same label can represent different owned printings. Mixed front and combined inventory labels are quarantined because the inventory cannot establish whether they list the same copies. Those rows remain quarantined even if only one or two copies are requested. No overlap lower bound is inferred. Reconcile and confirm the inventory before retrying. The Validator reports non-exact identity findings and unresolved collection coverage. Its selected-deck checks can still pass when an unrelated collection row is unresolved, or verified stock alone supplies the required copies.

Transform, modal DFC, Adventure and flip use the front record for printed costs and physical land counts. Split/aftermath use combined printed mana value and display the two costs. Prepare retains its separate two-face integrity audit. Incomplete slim multiface data can require a full dataset. The pinned Gateway real-collection profile still uses its separately managed slim dataset.

Both Validator and Spellbook accept `4 Lightning Bolt`, `4x Lightning Bolt`, `4× Lightning Bolt` and `4×Lightning Bolt`. With a separated ASCII marker, `4 x Lightning Bolt` means quantity 4 and the literal name `x Lightning Bolt`. If your exporter emits a separated marker, configure it to output a supported form or inspect and edit the line explicitly. The parsers preserve names including `X` and `Xenagos, God of Revels`.

### Ownership evidence and result status

`checks.ownership` is `PASS` when verified quantities supply every selected nonbasic card, `FAIL` when at least one relevant shortfall is proven, and `UNVERIFIED` when required stock cannot be established. A quarantined alias label is mapped to its possible canonical cards for uncertainty reporting. No quantity from that row is added. Unrelated unknown rows do not authorize a selected card or conceal a proven shortage.

`failures` contains demonstrable violations. `uncertainties` identifies missing evidence, including unknown stock for an affected selected card. Both arrays may be nonempty when one card has a proven shortage and another has uncertain stock. A separate deck-size or copy-limit violation keeps the final `status: FAIL` even when `checks.ownership: UNVERIFIED`. `identity_findings` describes non-exact deck-entry resolution; `collection_coverage` describes inventory resolution. A known deck identity does not resolve ambiguous inventory quantities.

For a mixed Delver inventory (two front labels and two combined labels), requesting four copies yields `UNVERIFIED`, direct exit 3. A lone front-label row with two copies and four requested yields a proven shortage, `FAIL`, direct exit 1. The Gateway preserves those child statuses with outer `UNVERIFIED` (exit 3, child 3) or `BLOCKED_INVALID_DECK` (exit 2, child 1). Both responses describe executed processes. See the [v1 contract](AGENT_RESULT_CONTRACT_V1.md).

## Casual 60-card Constructed

Put your files in an accessible local directory, open a terminal, and run:

```bash
python validator/MTG_Deck_Validator_v1.1.1.py \
  --collection "current_collection.csv" \
  --oracle "AtomicCards_slim_v2.json.gz" \
  --deck "examples/Synthetic_Red_A.txt" \
  --mode casual --exact-60 \
  --output "report.json"
```

In **Windows PowerShell**, put the command on one line without the Bash backslash line continuations. Replace the example paths with your actual file paths.

Omit `--exact-60` if you want to permit casual Constructed decks with **at least** 60 cards. The validator defaults to a minimum of 60; our casual 60-card Builder typically uses `--exact-60`.

## Commander (simple single-commander decks)

```bash
python validator/MTG_Deck_Validator_v1.1.1.py \
  --collection "my_collection.csv" \
  --oracle "AtomicCards_slim_v2.json.gz" \
  --deck "my_commander_deck.txt" \
  --mode commander --commander "Exact Commander Name" \
  --output "commander_report.json"
```

The commander must appear **exactly once among the 100 deck cards** in the TXT decklist. Single-commander construction, recognized card names, ownership, basic color identity, and singleton rules are checked. **Partner, Friends forever, Background, Doctor's companion, other multi-commander exceptions, and special commander construction rules are NOT supported.** The validator does not certify complete Commander legality.

## Interpreting results

- `PASS_WITH_LIMITATIONS`: All implemented hard checks passed; limitations documented in the JSON report still apply.
- `FAIL`: At least one demonstrable problem, such as deck size, ownership, card-name resolution, or copy limits.
- `UNVERIFIED`: Card identity, inventory quantity or other required evidence remains unresolved. An unknown quantity does not prove a shortage.
- `NOT_CHECKED` under `checks`: The program cannot establish that property. This is **not** a PASS.

The report includes deck totals, overlapping and mutually exclusive card type counts, mana curve, **printed mana values per card**, physical land count, exact hypergeometric probability of 2–5 lands in a seven-card opening hand, and explicitly qualified checks.

### Shared mana curve arithmetic for Builder and Tester (v1.1.1)

The current Validator v1.1.1 JSON includes `mana_curve_integrity` alongside the existing
`mana_curve_nonlands` field. When its status is `ORACLE_ARITHMETIC_PASS`, it provides:

- exact nonland copy counts in bins `0` through `6` and `7+`, with `7+` retaining the actual mana values for the weighted calculation;
- a per-card ledger (`name`, `quantity`, `mana_value`, `weighted_mana_value`), weighted total, exact average as a fraction, and rounded average;
- a cross-check against the deck's physical-land and nonland counts.

Builder v7.4 and Tester v3.4.2 can **reuse the same executed numbers** rather than
recalculate them independently. Tester still decides whether a full D2 mana-curve
check is complete, including manual Oracle/rules review for unusual split, modal,
transforming or alternative-cost cards. A `UNVERIFIED` arithmetic status must not
be reported as a verified average or curve. The original Validator output fields,
copy/ownership safety checks, and limitations remain unchanged.

No separate tool or runtime dependency has been introduced; this is a small
extension of the existing Validator. It does **not** calculate colored-mana
castability, mulligans, gameplay, or win rates.

**Classifying a planeswalker, creature, or other spell as removal is intentionally outside the program's scope.** Correct role classification requires card text, targets, timing, and board-state interpretation. Actual mana production, turn-by-turn land-drop probabilities, gameplay, win rates, and synergy quality are likewise **not tested**.

### Important limitations

- Only recognized standard Basic land names are exempt from ownership and copy limits, subject to Oracle confirmation of the `Basic Land` type.
- Card-text-specific construction exceptions such as "a deck can have any number of" are **not** implemented. Special cases require manual review.
- Format-specific construction rules and banned lists are not checked. MTGJSON is a snapshot, not a real-time legality authority.
- `card_types_overlapping` may count a card in multiple types. `card_types_primary_exclusive` assigns one primary type per card so that its total reconciles to the deck size.
- Opening-hand land probability uses **exact combinatorics** for seven cards without mulligans. It is not a simulation or on-curve probability.
- One deck per execution: ownership is checked against the original active collection each time. Simultaneously assembling two decks from limited physical copies is outside scope.
- Conflicting relevant fields across Oracle variants are reported as `UNVERIFIED` in v1.1.1. See the audit for differences from v1.1.

## ChatGPT Projects

Stage the public Validator and matching `card_identity.py` side by side in the executable runtime alongside the current collection CSV and MTGJSON data. For a new build, upload or paste the exact final TXT decklist and request:

> Actually execute `MTG_Deck_Validator_v1.1.1.py` with Python using my active collection CSV, MTGJSON, and this decklist. For casual 60-card decks, use `--exact-60`. Return the actual output/JSON report, errors, and `NOT_CHECKED` categories. If code execution is unavailable, report `NOT EXECUTED` rather than inventing a PASS.

**Important:** Uploading a file alone does not execute Python. ChatGPT must have code execution available and actually run the program. The validator is independent of any Builder prompt and can also be used in a fresh chat.

## Tests

Run the regression suite from the repository root:

```bash
python -m unittest discover -s tests -p "test_*.py" -v
```

The tests and example decklists use synthetic fixtures. Use a confirmed local collection when validating a real deck.

**Privacy:** The repository contains the validator, tests, and synthetic example decks, but not your complete collection or the full MTGJSON database. The validator does not access the network.

The legacy `collection_owned_copies` integer is the raw CSV row-quantity sum. Its additive `collection_owned_copies_basis` field identifies `RAW_DECLARED_CSV_QUANTITY_SUM_NOT_VERIFIED_PHYSICAL_TOTAL`. Overlapping aliases can contribute to that raw total, which is never verified physical stock. Use `checks.ownership`, `collection_coverage` and per-card uncertainty for ownership evidence.
