# Workflow controller MVP evidence — 2026-11-07

Starting public main was `a53e64a88c82fbdb0a1876ed95f4ba9f17b00b6b`, containing merged PR #2. PR #3 remained open/draft at `a0e31f132b42aa4c82c7c42509a589d80b04a935`. An isolated feature checkout was used. The maintained Gateway, Validator, Search, identity helper and stable prompts were not edited.

## Scope and design

The [API guide](AGENT_WORKFLOW_MVP.md) defines the stage contract and local trust boundary. One optional standard-library module controls executable prerequisites. The AI authors both candidate bytes and its review. Runtime code contains no card selection, ranking, archetype choice, automatic deck write or swap operation.

Finalization replays pinned Gateway doctor, discovery and validation under the same source/input hashes. A source change marks all dependent stages stale. A deck-only edit invalidates candidate validation/review/completion and permits resubmission. Restart restores configuration only and requires new executable evidence and review; real confirmation resets for the new run.

The certificate includes code/data/deck digests, run ID, profile, authored goal/review digests and receipt output digests, with a checksum over the canonical report. This is local tamper evidence with no hostile same-user authentication guarantee. Candidate discovery is bounded local output; final receipts and certificate omit card names, decklists, paths and rationale contents.

## Executed verification

Baseline on Python 3.12.14 and 3.13.5 passed 292 root, 6 Forge offline and 23 Spellbook offline tests, every suite exit 0. The new controller tests run real Gateway processes for positive and invalid flows. Isolated mocks exercise boundary faults only.

Tests cover early completion, missing/contradictory confirmation, source readiness, 59 cards, five copies, Delver aliases, overlapping inventory, true shortage, independent failures, changed deck/Oracle/collection/source, receipt injection, resume, no optional PASS, output privacy/limits, missing child, timeout, malformed output and contradictory exits. Source replacement tests use temporary code copies.

`python examples/workflow_smoke.py` executed the authored synthetic 56-land/four-spell fixture and returned COMPLETE_WITH_EVIDENCE, process exit 0. The deliberately extreme list isolates structural gates. Both `--skip-discovery` and `--skip-validation` returned BLOCKED, process exit 2, no certificate. Missing stages were respectively all seven prerequisites and VALIDATION/REVIEW. Final successful receipts were doctor 0/null/NOT_EXECUTED, discovery 0/0/EXECUTED and validation 0/0/EXECUTED. Sources and exact deck digests matched.

A separate Python-capable Work agent read only the short API guide, inspected its real returned synthetic discovery candidate and Oracle text, chose/wrote a synthetic 60-card deck and authored a strategy limitation note. It completed the flow and confirmed both skip refusals. During development its first run became STALE when the controller source changed. A fresh run against the stable source completed, confirming the source invalidation rather than reusing earlier evidence. This is single-host usability evidence; strategic strength, broad portability and model-token efficiency remain NOT_VERIFIED.

## Independent review

A separate same-host reviewer found and repro-tested four issues during development: missing candidate visibility/repeated discovery, wrong-shaped Gateway JSON, stale success receipts on failed retries, and unsafe checkpoint/confirmation restoration. The implementation now exposes bounded candidates, checks containers and nested positive validation results, clears superseded receipts, reads only bounded regular checkpoint files, and resets real confirmation. The reviewer independently reran positive completion, stale-deck, malformed-row, FIFO, resumed-confirmation and controller-suite checks, with no remaining blocker. No second independent model/host is claimed.

## Acceptance and limits

Gates A–E pass for the covered API/runtime checks; F has one-host usability evidence; G requires the final exact-head CI recorded in the PR; H requires the open experimental PR. No active prompts are replaced. Hosts without local Python/files must report NOT_EXECUTED.

Rollback removes the optional module, demonstration, tests, guide, evidence and README link together with their manifest entries. Existing direct Gateway workflows need no migration. Project v1.6 sources, PR #3, release tags and other repositories are outside this change.

The next smallest milestone is a controlled fresh-agent trial with a strategically realistic synthetic pool using the stable Builder, scoring whether the host inspects findings and reports limits correctly. The extreme fixture and API tests alone do not establish deck quality or a replacement prompt.

Final local suites on Python 3.12.14 and 3.13.5 passed 326 root tests (including 34 controller methods), 6 Forge offline and 23 Spellbook offline tests, each exit 0. The three nested receipt subcases additionally reject missing child status, absent checks and a success-shaped ownership failure. Manifest and workflow policy checks exited 0. Final hosted CI is recorded for the exact PR head.
