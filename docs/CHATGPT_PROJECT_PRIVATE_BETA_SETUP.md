# ChatGPT Project Setup — Active Casual Private Beta

**Updated:** 2026-11-01 (GitHub Casual Private Beta v0.2 release preparation; Project v1.6 remains pinned to the earlier Prepare source)  
**Scope:** Personal PRIVATE Casual 60+ card Constructed only. Not Commander, Brawl, Forge, Power Level or sanctioned-format certification.  
**Authority:** [Project status](../PROJECT_STATUS.md) and frozen beta checkpoint (historical private reference).  
**Lifecycle:** `ACTIVE_PRIVATE_BETA`, accepted for controlled private use with `PASS_WITH_LIMITATIONS`. The previous Casual alpha is `SUPERSEDED`, retained for historical evidence/rollback. **This is not public or stable-release approval.**

## 1. Files in the user's Casual ChatGPT Project

**Keep unchanged, if they already exist and are readable:**
- `MTG_Deck_Builder_v7.4_full.md`, local Project source SHA-256: `ab37cb2f3c67a5d5c078bdb1ab7c13b7e955c14f17484bf385bac70c7bb424a5` (GitHub equivalent differs only by newline normalization; no need to re-upload).
- `MTG_Deck_Tester_v3.4.2_full.md`, local SHA-256: `40871a2a6e143625a177f6730e1dd68a8572b5bc62a129e41db8ab4f158d8a30`.
- `MTG_Deck_Validator_v1.1.1_PREPARE_COLOR_INTEGRITY_CANDIDATE.py`, **currently selected ChatGPT Project v1.6 Validator**, SHA-256 `c422295676d0bad04aa1449725b07a7c11bf58b7990a34aff209e10ba742ac8d`. Project activation: `ACTIVATION_CONFIRMED` on 2026-10-31. GitHub `main` Private Beta v0.2 contains the same functional source with one corrected docstring usage example under `validator/MTG_Deck_Validator_v1.1.1.py`, SHA-256 `f8e915a95e73e20edf59267dfe39e45f82d62bb5eb49fd4eb180194189d995ef`. **Do not claim the Project source has been updated**: source selection and project instructions must be deliberately migrated and verified before saying both environments are byte-identical. The frozen beta branch retains the older implementation.
- `MTG_Deck_Validator_v1.1.1_BETA_CANDIDATE.py`, **previous active beta — rollback ONLY**, SHA-256: `8749b50d0aeaa52124a99271a0ab40bcc979350c6e8b5e9074c4f28d63a3d1ac`. This is byte-identical to GitHub's `validator/MTG_Deck_Validator_v1.1.1.py` in the frozen beta baseline.
- `MTG_Deck_Validator_v1.1.1.py`, **historical Project rollback**, local SHA-256: `0d296f69a465bdaf5d967d2155460bbe69bb3d653f58952468d45713d2f9db8e`. Keep this file; do **not** accidentally select it for beta checks.
- Applicable supporting files `AtomicCards_slim_v2.json.gz`, `card_search.py`, `synergy_engine.py`, `combo_synergy_report.py`, `MTG_Deckbuilding_Rules_Casual_v1.0.txt`, `CARD_SEARCH.md` if used by the workflow. Confirm actual readability and execution before claiming use.

The **old** `PROJECT_SETUP_ADDENDUM.md` described *pre-acceptance beta-candidate testing*. It is historically valid but **superseded by this document**. If the old addendum is used as an active Project Source/instruction, replace its guidance with the block below or remove it from the set of active instruction sources; optionally archive it elsewhere. Do **not** delete rollback code or masterprompts.

**No collection file needs to be re-uploaded merely to apply this setup.** However, each deckbuilding/ownership task needs a specifically confirmed collection accessible in the **current chat**. A historical CSV in GitHub, memory, another chat, or an unconfirmed Project source does **not** establish ownership.

## 2. Active Project Instructions v1.6 (do not append the old override)

The user's Casual ChatGPT **Project Instructions v1.6** still select the 2026-10-31 Prepare Validator. It remains valid for its proven scope but is **not automatically the GitHub Private Beta v0.2 source**; GitHub's SHA differs only due to a corrected CLI usage docstring. **Do not paste the obsolete 2026-10-22 `ACTIVE PROJECT OVERRIDE` block** or append a second competing selection: ChatGPT Project instructions have an 8,000-character limit. The excerpt below is for confirming the existing selection **inside** v1.6, not for replacing the complete Project Instructions.

~~~text
Builder: MTG_Deck_Builder_v7.4_full.md
Tester: MTG_Deck_Tester_v3.4.2_full.md
Active Validator: MTG_Deck_Validator_v1.1.1_PREPARE_COLOR_INTEGRITY_CANDIDATE.py
SHA-256: c422295676d0bad04aa1449725b07a7c11bf58b7990a34aff209e10ba742ac8d
Previous beta — rollback ONLY: MTG_Deck_Validator_v1.1.1_BETA_CANDIDATE.py
SHA-256: 8749b50d0aeaa52124a99271a0ab40bcc979350c6e8b5e9074c4f28d63a3d1ac
Historical rollback ONLY: MTG_Deck_Validator_v1.1.1.py
SHA-256: 0d296f69a465bdaf5d967d2155460bbe69bb3d653f58952468d45713d2f9db8e
~~~

**Execution safeguards retained from v1.6:**
- Before each run, verify the selected **active** file's readable bytes, SHA-256 and Python execution access. Never choose a Validator merely by the shared v1.1.1 version label; do not silently fall back to a rollback.
- For every exact finalized deck, require a confirmed and accessible current-chat collection and readable Oracle data. Run the active Validator with `--mode casual --output`; include `--exact-60` only when exactly 60 cards are required. Inspect process exit code, `status`, `checks`, `failures`, `uncertainties`, `mana_curve_integrity` and **`prepare_layout_audit`**. Contradictory, missing or invalid `prepare` metadata must remain `UNVERIFIED`, with no `ORACLE_ARITHMETIC_PASS`.
- Nonzero exit, `FAIL`, `INPUT_ERROR`, blocking `UNVERIFIED`, or critical ownership/copy/deck-size/Oracle failures **block Tester**. After a valid gate, Tester v3.4.2 performs independent D2 mana-curve and D3 ownership checks on a frozen decklist; no silent baseline edits or invented simulations.
- Keep Builder v7.4 and Tester v3.4.2 masterprompts unchanged and preserve both rollback Validators. GitHub `main` may be updated under the [Private Beta v0.2 release gate](../docs/releases/CASUAL_PRIVATE_BETA_v0.2_2026-11-01.md), but **ChatGPT Project v1.6 selection is still the older Prepare SHA-256 `c422295676d0bad04aa1449725b07a7c11bf58b7990a34aff209e10ba742ac8d`** until manually changed. Do not silently run new GitHub code as if it were the verified Project source. Projects never auto-sync.
- Keep collection CSVs, decklists, test evidence and personal exports out of GitHub.

**Private activation evidence (31 October 2026):** 7,075/7,075 local regression checks passed; a 60-card positive deck and its byte-identical file passed `prepare_layout_audit` and mana-curve verification, while an invalid five-copy fixture was rejected before Tester. Final scoped activation status: `ACTIVATION_CONFIRMED`. These are **ChatGPT Project-local** results, not GitHub CI and not full rules/gameplay certification.

## 3. Project checks after changing instructions

1. Confirm **all three** Project Validator files are preserved. Verify the active `PREPARE_COLOR_INTEGRITY_CANDIDATE` by its exact SHA-256, not the previous beta or historical rollback.
2. Confirm Builder and Tester file identities **without modifying them**.
3. In any actual deck workflow, confirm the collection for **that chat**, Oracle availability, and Python execution status. If absent, report `NOT_EXECUTED`; do not fabricate passing validation.
4. The 2026-10-31 Project-only activation is already `ACTIVATION_CONFIRMED` within its tested scope. No need to repeat expensive suites solely for documentation changes; new/deviating decklists still require fresh validation. The sanitized historical beta test index (historical private reference) is a different, older evidence register.
5. Keep user-specific collections and full acceptance ZIPs private/local. The GitHub test index is **only** a sanitized pointer, not the test evidence itself.

## 4. Development handoff

For current development priorities, see AI Deckbuilding Roadmap v0.1 (historical private reference): P1 AI Swap Advisor, P2 Mana Bottleneck Detector, P3 Cross-mechanic Synergy Discovery, P4 Strategic Robustness, P5 deferred AIO. The beta is the baseline; implementation is experimental until separately approved and tested.
