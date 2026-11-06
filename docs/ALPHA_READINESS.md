# Casual AI Deckbuilding Tool: small alpha release gate

> **HISTORICAL RECORD — superseded on 2026-10-22.** This document preserves the private-alpha readiness review as it was understood on 2026-10-16; its pending gates and references to issues #11 and #14 are **not** the current project state. Those two issues were closed on 2026-10-16. For the current controlled private-beta status, verified versions, limitations, test index and roadmap, see [PROJECT_STATUS.md](../PROJECT_STATUS.md), the frozen beta checkpoint (historical private reference), and the sanitized private beta test-results index (historical private reference). Nothing in this historical document authorizes stable/public promotion.

**Target:** first private Casual alpha by the weekend of October 17–18, 2026. This is a checklist, **not** a claim that the alpha is already released.

**Readiness review (October 16, 2026):** the reported rehearsals support a **guided private Casual alpha** with the limitations below. This is not a public release or a claim of general deck quality. Keep Builder v7.4, Tester v3.4.2 and Validator v1.1.1 unchanged. Complete the remaining release gates below before publishing an alpha tag.

## Rehearsal evidence supplied by the user

The following results were shared by the user in the handoff conversation. They were **not rerun by the agent preparing this readiness update**, and the original private inputs/reports were not inspected in this review. Their exact Git commit was not established; do not present them as tests of the eventual release commit.

| Check | User-reported result |
|---|---|
| Two unchanged decklists, Validator v1.1.1 | Both `PASS_WITH_LIMITATIONS` |
| Independent Tester v3.4.2 | Both `COMPLETE STANDARD`; D2 and D3 `PASS` |
| Deliberately invalid 60-card deck | Overall `FAIL`; ownership `FAIL`; copy limit `FAIL`; exit code `1` |
| Windows regression run | Python 3.13.7, pytest 8.4.2: `174 passed` |
| File integrity and working copy | Original decks reported unchanged using SHA-256; CRLF-related byte differences explained/restored; clean local Git status reported |

This records a small, two-deck workflow sample, not broad card coverage or gameplay evidence. No personal collection, deck contents, private report, or local file path is included here. Each future chat still needs its own confirmed current collection.

## Repository verification and remaining release gates

- Reviewed `main` at the historical private revision. The shared handoff already exists. At review time there were no open PRs; open issues were #11 and #14. Existing releases/tags cover MTGJSON data and the historical Forge runtime, not a Casual alpha.
- Existing CI run 38859675977 (historical private reference) succeeded on that exact main commit: Python 3.9/3.12/3.13 regression jobs, workflow syntax and historical privacy scan. This is inspected GitHub evidence, separate from the user's Windows run.
- The agent independently ran the existing offline suites on the reviewed checkout using Windows Python 3.12.14: **145 root tests + 23 Spellbook tests + 6 existing Forge offline converter tests = 174 passed**. No Forge gameplay was run. Initial attempts hit sandbox temporary-directory permissions; rerunning with a writable workspace temporary directory passed. Local pytest and PyYAML were unavailable, so neither a local pytest run nor a local workflow-parser success is claimed.
- Rollback reference `backup/pre-python-metrics-20261016` resolves to the historical private revision, an ancestor of reviewed main; its Validator source is readable. This verifies recoverable Git history, not a performed deployment rollback. The byte-preserved Builder v7.3 backup also remains available.
- **Project setup gate:** confirm that the existing shared handoff is pasted into the actual target Casual Project Instructions and that the required files execute in that chat. GitHub cannot establish this setup; the supplied results do not independently confirm installation of that instruction block.
- **Release gate:** review this documentation PR and require green CI on its final head. After any merge, verify CI on the exact intended release commit. Do not transfer a green result from another commit.
- **Optional release proposal:** once those gates pass, create a private prerelease named `Casual guided private alpha 0.1` with proposed tag `casual-private-alpha-v0.1.0` at that verified commit. Reuse this evidence and limitations as release notes; attach no personal data. No alpha tag or release is created by this documentation update. Repository visibility remains private; public release has its own [checklist](PUBLIC_RELEASE_CHECKLIST.md).

## Minimum alpha scope

- Stable **Builder v7.4** can produce a coherent deck from a *confirmed current-chat collection*, respecting copies, color/mana requirements and real Oracle text. It may use existing Card Search, Synergy Engine, and optional Spellbook data when available; no tool execution may be invented.
- **Validator v1.1.1** actually executes on the final deck when its files are available; passes hard construction/ownership checks and emits `mana_curve_integrity` with honest status.
- Preserved **Tester v3.4.2** analyzes that **unchanged** list independently. Its D2 mana-curve audit and D3 ownership checks remain mandatory when applicable; strategy, mana color, card interactions, and weaknesses are assessed separately from the Python arithmetic.
- The [shared handoff](../prompts/casual/SHARED_PYTHON_VALIDATOR_HANDOFF.md) is installed into the actual ChatGPT Casual Project Instructions **manually**. Merely changing GitHub does not affect Project instructions.
- At least one actual workflow rehearsal in the target Project with an active current-chat collection and valid 60-card deck; include a deliberately invalid deck to confirm rejection. Avoid uploading collections to GitHub.
- CI green on the exact release commit and rollback via the existing backup branch / Git history verified.

## Known alpha limitations (must be disclosed, not hidden)

- `combo_synergy_report.py` does not yet pass a chosen Casual color restriction into its component search/pair filters (Issue #14 (historical private reference)). Builder must separately check actual colors and mana before accepting suggestions.
- Commander Spellbook real bulk snapshot is optional. Without it, combo output remains `NOT_EXECUTED`/`PARTIAL`; do not infer that no combos exist.
- Most synergy detection is heuristic, and no full rules-accurate gameplay or win-rate simulation is promised.
- Validator `PASS_WITH_LIMITATIONS` does not verify comprehensive banlists, castability or colored-source timing. Builder and Tester must separately review practical mana and relevant Oracle interactions.
- Card-specific exceptions to the ordinary four-copy limit are not implemented (Issue #11 (historical private reference)); cards such as Hare Apparent can receive a false copy-limit failure. Review such exceptions manually without bypassing ownership or weakening ordinary copy limits.
- The Parser/Validator expects a `Name,Quantity` CSV and exact `Quantity Card Name` deck text. Builder/Tester may need to normalize supported exports *before* running it; never silently lose or duplicate inventory rows.

## Not a blocker for a private alpha

Forge, Power Level, broad refactors, GUI development, and exhaustive synergy discovery. Alpha success means a **usable, honestly checked workflow**, not perfect Magic automation.
