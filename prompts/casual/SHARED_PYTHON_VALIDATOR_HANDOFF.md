# Casual Builder + Tester: shared Python Validator handoff (historical snippet; see active v1.6 Project Instructions)

**Scope:** historical additive handoff, not a new Builder or Tester masterprompt. **Do not paste this legacy handoff on top of active ChatGPT Project Instructions v1.6.** The currently active Project Validator is the SHA-pinned `MTG_Deck_Validator_v1.1.1_PREPARE_COLOR_INTEGRITY_CANDIDATE.py`; GitHub `main` now contains identical code under `validator/MTG_Deck_Validator_v1.1.1.py` after PR #27. The frozen beta branch keeps its older version at the same path. Builder v7.4 and Tester v3.4.2 remain unchanged.

## Historical copyable snippet (do not replace active Project Instructions v1.6)

> For Casual Builder v7.4 and Casual Tester v3.4.2, use the **active SHA-verified** Prepare Integrity Validator (`c422295676d0bad04aa1449725b07a7c11bf58b7990a34aff209e10ba742ac8d`) only after checking code execution, current-chat collection ownership, and readable local Oracle data. Validate **each exact decklist** using `--mode casual --output` (and `--exact-60` only when required). Inspect process exit code, `status`, `checks`, `failures`, `uncertainties`, `mana_curve_integrity`, and **`prepare_layout_audit`**. `prepare_layout_audit` missing, contradictory or `UNVERIFIED` blocks `ORACLE_ARITHMETIC_PASS`. `FAIL`, `INPUT_ERROR`, blocking `UNVERIFIED`, critical ownership/copy/size/Oracle failures, or nonzero exit **block independent Tester execution**, reported as `TESTER_NOT_EXECUTED_INVALID_DECK` where appropriate. Only an exit-0 `PASS_WITH_LIMITATIONS` with relevant checks may proceed to independent Tester v3.4.2, which must perform its own D2 curve integrity and D3 ownership aggregation; it never modifies a frozen deck. Never infer castability, synergy, gameplay, win rate, or ownership from the Validator alone. Preserve Builder/Tester source and both rollback versions, and never upload private decks, collections or reports to GitHub.

## GitHub `main` CLI illustration (Project Source filename is different)

With the Validator script, collection CSV, Oracle dataset, and decklist **actually accessible in the same Python session**, run (adjust filenames to the user's uploaded files):

```bash
python validator/MTG_Deck_Validator_v1.1.1.py \
  --collection ACTIVE_COLLECTION.csv \
  --oracle AtomicCards_slim_v2.json.gz \
  --deck EXACT_DECK.txt \
  --mode casual --exact-60 \
  --output validator_report.json
```

`--exact-60` applies only when the requested Casual deck has exactly 60 cards; omit it for a permitted 60+ card deck. Use one fresh execution **per deck**. Capture the actual program's exit code, JSON status, `checks`, `failures`, and `uncertainties`. `PASS_WITH_LIMITATIONS` is *not* a playability verdict. Treat `mana_curve_integrity.status == ORACLE_ARITHMETIC_PASS` as verified *printed Oracle arithmetic only*, not a complete rules check. The Tester still checks each unusual card's mana value, the physical-land policy and the independent D2/D3 gates.

**Project setup matters:** GitHub and ChatGPT Projects do not synchronize. Adding these instructions to GitHub or uploading a `.py` file as a Project Source does *not* cause ChatGPT to execute Python. **For an already configured v1.6 Casual Project, do not paste the historical block again.** In a separately configured Project, explicitly select the correct current version with its full SHA-256 and provide the needed runnable files in a code-capable chat. Do not pretend they were loaded or executed when they were not.

**Out of the active Casual Validator/Tester handoff scope:** Forge, Power Level, automatic full-game simulation, a new orchestrator/framework, and changes to Commander masterprompts.
