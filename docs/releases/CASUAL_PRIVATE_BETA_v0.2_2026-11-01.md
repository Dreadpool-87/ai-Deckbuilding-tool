# Casual Private Beta v0.2 — Release Definition and Acceptance Gate

**Date:** 2026-11-01  
**Release channel:** `PRIVATE_BETA_V0_2` (APPROVED for scoped private Casual constructed; not public/stable)  
**Lifecycle:** `ACTIVE_PRIVATE_BETA` / `PASS_WITH_LIMITATIONS` — candidate and merge-source CI gates completed; dated release ref is created after documentation finalization  
**Promotion authority:** Owner requested a more complete private beta on 2026-11-01. This record is scoped to Casual only.  
**Previous frozen checkpoint:** `release/casual-private-beta-2026-10-22` — **unchanged, rollback reference**.

## Supported beta workflow

1. **Builder v7.4** designs a 60+ card Casual Constructed deck using only a specifically confirmed collection accessible in the **current conversation**. Independent decks can reuse the pool; shared inventory requires an explicitly simultaneous-build request.
2. **Validator v1.1.1 Prepare Color Integrity** executes on the **exact** final deck with a readable current-chat collection CSV and local MTGJSON AtomicCards Oracle data; `--mode casual --output` and `--exact-60` only when exact 60 is required. Process exit, `status`, `checks`, `failures`, `uncertainties`, `mana_curve_integrity`, and `prepare_layout_audit` MUST be inspected. If required metadata is missing or contradictory, keep `UNVERIFIED` and never grant `ORACLE_ARITHMETIC_PASS`. Critical failures, nonzero exit, `FAIL`, `INPUT_ERROR`, and blocking `UNVERIFIED` prevent downstream Tester execution.
3. **Tester v3.4.2**, when separately requested after a valid gate, independently checks D2 mana-curve integrity and D3 aggregated ownership on the frozen decklist. It is a prompt-based analytical tester, **not** an executed gameplay engine. It must distinguish executed calculations, approximations and judgment; no fabricated game simulations or win rates.
4. All project content and agent outputs use **English** in this source candidate.

### Active file identities

| Component | GitHub path / context | Identity |
|---|---|---|
| Builder (stable) | `prompts/casual/builder/stable/MTG_Deck_Builder_v7.4_full.md` | v7.4, unchanged |
| Tester (baseline) | `prompts/casual/tester/MTG_Deck_Tester_v3.4.2_full.md` | v3.4.2, unchanged |
| Validator on GitHub `main` | `validator/MTG_Deck_Validator_v1.1.1.py` | SHA-256 `f8e915a95e73e20edf59267dfe39e45f82d62bb5eb49fd4eb180194189d995ef`; identical behavior to Prepare candidate, one corrected docstring usage line |
| Previous active Project Source | `MTG_Deck_Validator_v1.1.1_PREPARE_COLOR_INTEGRITY_CANDIDATE.py` | SHA-256 `c422295676d0bad04aa1449725b07a7c11bf58b7990a34aff209e10ba742ac8d`; **still selected by existing Project Instructions v1.6 until independently updated** |
| Frozen private beta | `validator/MTG_Deck_Validator_v1.1.1.py` on `release/casual-private-beta-2026-10-22` | SHA-256 `8749b50d0aeaa52124a99271a0ab40bcc979350c6e8b5e9074c4f28d63a3d1ac`; rollback only |
| Historical Project rollback | Project-only `MTG_Deck_Validator_v1.1.1.py` | SHA-256 `0d296f69a465bdaf5d967d2155460bbe69bb3d653f58952468d45713d2f9db8e`; rollback only |

Do not infer matching code from matching filenames or versions. GitHub and ChatGPT Projects do **not** synchronize.

## Acceptance evidence

- The pre-change Prepare candidate SHA-256 `c4222956…` passed a private 7,075-check experimental/regression review **as recorded in existing Project status**; those private artifacts are not on GitHub and this is not a claim they were rerun for this release.
- On 2026-11-01, the corrected one-line CLI-usage candidate SHA-256 `f8e915…` passed **10/10** synthetic Prepare integrity regression tests locally, including missing/contradictory faces and illegal five copies.
- The same corrected candidate was **actually executed** locally against four previously confirmed independent 60-card Casual decks, using a local current-chat collection and readable MTGJSON Oracle data. **4/4** returned exit 0, `PASS_WITH_LIMITATIONS`, `prepare_layout_audit: PASS`, `mana_curve_integrity: ORACLE_ARITHMETIC_PASS`, and `ownership: PASS`. The private decklists, collection and execution JSONs are not distributed through GitHub.
- New GitHub `tests/test_validator_cli_usage_contract.py` checks that the updated docstring references the correct entrypoint and that `--help` executes. The existing 10 Prepare regression tests remain unchanged.
- **Release gate:** the full GitHub Python and integration regression CI MUST succeed on the candidate commit and on the eventual `main` merge commit. Do not claim CI success until verified at those exact commits. If it fails, mark release `NOT_READY`.
- **Release gate:** verify the corrected GitHub blob matches the SHA-pinned local source, and the frozen beta branch commit is unchanged.
- **Release gate:** create a distinct release ref only after a successful merge and CI; do not advance the original frozen beta branch.

## Verified beta activation evidence (2026-11-01)

- PR #29: GitHub regression workflow 41315644860 (historical private reference) **SUCCESS** on exact candidate head the historical private revision.
- GitHub `main` code merge: workflow 41315700456 (historical private reference) **SUCCESS** on exact merge commit the historical private revision.
- The corrected source blob SHA is the historical private revision (matching the locally verified source SHA-256 `f8e915a95e73e20edf59267dfe39e45f82d62bb5eb49fd4eb180194189d995ef`).
- The original frozen checkpoint still has branch tip the historical private revision.
- **Versioned recovery ref:** `release/casual-private-beta-v0.2-2026-11-01`, pinned to the accepted documentation-final `main` commit after documentation CI. Verify the ref explicitly before claiming the release archive is frozen.
- The current ChatGPT Project Source and v1.6 selection have **not** automatically migrated to v0.2. Do not claim cross-environment byte identity until the new Project Source has been installed and SHA-verified.

## What this beta does NOT certify

- Actual physical gameplay, Forge gameplay, game win rates, or strategic optimality.
- Full colored-mana castability, all Oracle timing/corner-case rules, format-specific bans, or every card-layout exception.
- AIO orchestrator, independent Forge/Commander integrations, Power Level analysis, or every experimental tool in this repository.
- Automatic update of ChatGPT Project Sources, current-chat collection ownership, public redistribution rights, or a completed end-to-end rollback rehearsal.
- Broad/public/stable readiness. The private repository remains private; historic Forge/MTGJSON Release redistribution concerns still block public publication.

## Exit criteria for a future stable/public release

Require broader representative-deck tests and systematic negative cases; strong independent D2/D3 checks; actual user-facing error/recovery testing; a full rollback rehearsal; verification of license/privacy and historic Release assets; updated Project Source selection and user setup; and separately authorized release/publication. `PASS_WITH_LIMITATIONS` is **not** `PASS` for every MTG rules question.

## Governance

This release authorizes the **scoped private Casual beta** after all acceptance gates, not a public release or a global rename of every experimental module. Preserve the 2026-10-22 frozen branch, both Project rollbacks, stable Builder and Tester files, and their Git histories. No personal collection/decks/test reports/Oracle bulk data may enter this repository.
