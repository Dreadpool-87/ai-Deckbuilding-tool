# MTG Masterprompts: Versioned Archive

This directory preserves **six established masterprompt versions plus two English-output editions of the mobile Tester prompts** (eight full files total). They are retained for version control, comparison and manual reuse in ChatGPT Projects. GitHub files do not automatically synchronize with ChatGPT Projects. There is **no automatic synchronization** between this repository and ChatGPT Projects.

## Casual 60-card Constructed

| Prompt | File | Status |
|---|---|---|
| Builder v7.3 | [MTG_Deck_Builder_v7.3_full.md](casual/builder/backup/MTG_Deck_Builder_v7.3_full.md) | **Rollback backup; unchanged** |
| Builder v7.4 | [MTG_Deck_Builder_v7.4_full.md](casual/builder/stable/MTG_Deck_Builder_v7.4_full.md) | **Stable working version (promoted October 16, 2026)** |
| Builder v7.4.1 | [MTG_Deck_Builder_v7.4.1_full.md](casual/builder/experimental/MTG_Deck_Builder_v7.4.1_full.md) | Experimental; not promoted |
| Tester v3.2 | [MTG_Deck_Tester_v3.2_full.md](casual/tester/MTG_Deck_Tester_v3.2_full.md) | Preserved English GitHub baseline |
| Tester v3.3 | [MTG_Deck_Tester_v3.3_full.md](casual/tester/MTG_Deck_Tester_v3.3_full.md) | English-output edition of the archived mobile upload |
| **Tester v3.4.2** | [MTG_Deck_Tester_v3.4.2_full.md](casual/tester/MTG_Deck_Tester_v3.4.2_full.md) | **Latest Tester; English-output edition** |

## Experimental compact comparison

The [compact Builder](casual/builder/experimental/MTG_Deck_Builder_compact_candidate.md) and [compact Tester](casual/tester/experimental/MTG_Deck_Tester_compact_candidate.md) are comparison candidates only. The [fixed synthetic benchmark](../examples/prompt_benchmark/README.md) and [traceability matrix](../docs/PROMPT_CANDIDATE_TRACEABILITY.md) document what is covered and what remains **NOT_VERIFIED**. Active Builder v7.4 and Tester v3.4.2 are unchanged.

## Alpha handoff: Python mana-curve facts for Casual Builder + Tester

The [shared Validator handoff](casual/SHARED_PYTHON_VALIDATOR_HANDOFF.md) contains a short, copyable ChatGPT Project instruction and the existing Validator CLI invocation. It **does not** edit the Tester v3.4.2 prompt or silently enable execution in ChatGPT. The user must apply the Project instruction manually; each run must verify file access and actual execution.

## Commander

| Prompt | File | Status |
|---|---|---|
| Builder v4.2 | [MTG_Commander_Builder_v4.2_full.md](commander/builder/MTG_Commander_Builder_v4.2_full.md) | Latest recovered complete version |
| Tester v4.2 | [MTG_Commander_Tester_v4.2_full.md](commander/tester/MTG_Commander_Tester_v4.2_full.md) | Latest recovered complete version |

## Preservation and language migration

- **The original six archives were verified byte-for-byte against their source files on October 14, 2026.** This was a historical verification, not an assertion that every prompt has been fully audited.
- **Language-only change on October 14, 2026:** at the owner's request, instructions requiring Dutch output were changed to require **English**. These six current working copies therefore **no longer match** the verified original source bytes. The previous exact versions remain recoverable in Git history.
- The October 14 language-only change did not itself approve other edits or promote an experimental version. The separate October 16 promotion of v7.4 is limited to switching its stable status; prompt contents are unchanged.
- Stable Builder v7.4 is the approved working version as of October 16, 2026, not a scientifically proven optimal builder. The unchanged v7.3 backup remains available for rollback.
- v7.4.1 remains experimental for comparison and does **not** automatically replace stable v7.4.
- Casual Tester v3.2 now has a correct **v3.2** heading and active-version declaration; historical v2.5/v3.1 references inside the archived specification remain historical only. The correction is version metadata, not a functional redesign.
- The two mobile Tester editions retain their analytical instructions and use English output. The private project preserves the exact uploaded originals.
- v3.4.2 prioritizes practical STANDARD analysis; the mandatory D2 mana-curve and D3 printings-aware ownership aggregation gates are retained.
- The repository contains eight complete prompt backups, not necessarily every historical version.
- Private collection files, full MTGJSON data, credentials, and personal API tokens are intentionally excluded.

**Language convention:** All eight prompts, project documentation and agent outputs use English.
