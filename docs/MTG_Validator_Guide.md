# MTG Deck Validator v1.1: User Guide (Historical Version)

> **Current guidance (2026-11-01):** This is the **historical v1.1 guide**; the original v1.1 commands below remain historical only. For new GitHub Casual Beta v0.2 validations, use [Validator v1.1.1 with Prepare Color Integrity](../validator/MTG_Deck_Validator_v1.1.1.py), SHA-256 `f8e915a95e73e20edf59267dfe39e45f82d62bb5eb49fd4eb180194189d995ef`, with the corrected docstring command `python validator/MTG_Deck_Validator_v1.1.1.py --help`. Its functional behavior is unchanged from Project Prepare SHA-256 `c422295676d0bad04aa1449725b07a7c11bf58b7990a34aff209e10ba742ac8d` but the source files are not byte-identical. The original 2026-10-22 frozen beta Validator stays at SHA-256 `8749b50d0aeaa52124a99271a0ab40bcc979350c6e8b5e9074c4f28d63a3d1ac`. Inspect `prepare_layout_audit` and all gates; see [the Beta v0.2 release definition](releases/CASUAL_PRIVATE_BETA_v0.2_2026-11-01.md).

**One reusable Python file:** `validator/MTG_Deck_Validator_v1.1.py` in this repository.

This is an independent **offline** utility for checking hard constraints in a Magic: The Gathering decklist. It runs on Python 3.9+ and requires only the standard library. No GitHub account, external API, or API key is necessary.

## Required files

1. `validator/MTG_Deck_Validator_v1.1.py` (or the same standalone file in your local project directory).
2. Your **active** collection as a CSV containing at least `Name` and `Quantity` (for example, `MTG_Mastercollection_M19_M20_M21_plus_Sorin_Chandra(2).csv`). The validator never silently merges multiple collections.
3. A local MTGJSON `AtomicCards` database, `.json` or `.json.gz` (for example, `AtomicCards_slim_v2.json.gz`). MTGJSON supplies **card facts**, not evidence of ownership.
4. Your final decklist as a **UTF-8 `.txt` file**, one quantity/name entry per line, such as `4 Shock`, `2 Banefire`, `21 Mountain`. Headings such as `Creatures (26)` are ignored. Unrecognized lines or sideboard sections cause `FAIL`; they are not silently accepted.

## Casual 60-card Constructed

Put your files in an accessible local directory, open a terminal, and run:

```bash
python validator/MTG_Deck_Validator_v1.1.py \
  --collection "MTG_Mastercollection_M19_M20_M21_plus_Sorin_Chandra(2).csv" \
  --oracle "AtomicCards_slim_v2.json.gz" \
  --deck "examples/Synthetic_Red_A.txt" \
  --mode casual --exact-60 \
  --output "report.json"
```

In **Windows PowerShell**, put the command on one line without the Bash backslash line continuations. Replace the example paths with your actual file paths.

Omit `--exact-60` if you want to permit casual Constructed decks with **at least** 60 cards. The validator defaults to a minimum of 60; our casual 60-card Builder typically uses `--exact-60`.

## Commander (simple single-commander decks)

```bash
python validator/MTG_Deck_Validator_v1.1.py \
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
- `UNVERIFIED`: Missing or contradictory card data prevent reliable verification of all required properties.
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

Upload the `.py` validator as a **project file** alongside the current collection CSV and MTGJSON data. For a new build, upload or paste the exact final TXT decklist and request:

> Actually execute `MTG_Deck_Validator_v1.1.py` with Python using my active collection CSV, MTGJSON, and this decklist. For casual 60-card decks, use `--exact-60`. Return the actual output/JSON report, errors, and `NOT_CHECKED` categories. If code execution is unavailable, report `NOT EXECUTED` rather than inventing a PASS.

**Important:** Uploading a file alone does not execute Python. ChatGPT must have code execution available and actually run the program. The validator is independent of any Builder prompt and can also be used in a fresh chat.

## Tests

Run the regression suite from the repository root:

```bash
python -m unittest discover -s tests -p "test_*.py" -v
```

The tests and example decklists use synthetic fixtures. Use a confirmed local collection when validating a real deck.

**Privacy:** The repository contains the validator, tests, and synthetic example decks, but not your complete collection or the full MTGJSON database. The validator does not access the network.
