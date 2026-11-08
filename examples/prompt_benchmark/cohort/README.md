# Same-host exploratory benchmark cohort

One matched response was generated for each of 14 Builder and four Tester cases on the Work host, 36 responses in total. The [blinded pilot](../pilot/README.md) is included in those totals. The remaining cases ran in separate matched batches with the same inherited model/reasoning setting, baseline checkout `0fd38ab2846a0e4c575e6ecac947b006407f913b`, Python 3.12.14, fixture bytes and local tool access. Batch runs share session context within each arm and are exploratory. No second independent host, exact model build, seed control, comparable elapsed timing or model token telemetry was available. B14 enforced no-use behavior by instruction and no Oracle was present. It did not exercise a separate technically tool-disabled sandbox.

| Observed check | Stable | Candidate |
| --- | ---: | ---: |
| Builder responses | 14 | 14 |
| Tester responses | 4 | 4 |
| Displayed Builder decklists equal to recorded 60-card imports | 15 | 15 |
| Gateway actions observed | 22 | 20 |
| Validated with limitations (exit 0, child 0) | 16 | 16 |
| Discovery only (exit 0, child 0) | 1 | 0 |
| Unverified (exit 3, child 3) | 3 | 3 |
| Blocked invalid deck (exit 2, child 1) | 2 | 1 |

Candidate used direct Card Search in seven Builder runs. Stable used an additional Gateway discovery and an intentionally invalid ambiguity probe. The Gateway totals therefore do not measure general efficiency. Prompt source lengths by `wc -w` were 6,470 → 1,522 Builder and 5,136 → 1,449 Tester. They are source word counts, separate from host token and response costs.

- Both arms kept the explicitly ambiguous B10 inventory row out of their final decks. Both validated exact per-deck counts in B11 and B13, and an independent aggregate arithmetic check confirmed B11 fits the joint stock while B13 has a legitimate shared-card shortage.
- Both arms stopped at the baseline Validator's `UNVERIFIED` transform in B07 and the conflicting Prepare probe in B12. Both approved the bounded positive Prepare structure in B08. Neither B14 response claimed runtime execution or Oracle facts.
- T02 reported the same one-copy shortage in both runs. The stable answer called the audit `PARTIAL QUICK`, while the candidate called it complete with a failed ownership outcome. T03 also differed on whether optional broader castability work affects completion. Resolve completion-label interpretation across modes before promotion. Both T04 reports withheld a certified full mana curve and labeled the analysis partial. The historical runtime's literal ownership ledger reported PASS for T04. The identity-aware runtime withholds that result on the conflicting physical card, and the fixture preflight tests both contracts.
- The two fully blinded pilot pairs tied with zero observed critical violations. The broader cohort has independent deck import/aggregate arithmetic checks and recorded Gateway evidence. It has no full blind strategic rubric review, repeat runs or statistical non-inferiority assessment. No claim of zero new critical violations across the cohort or passing Gate E follows from this evidence.

Each JSONL record contains a complete synthetic answer, fixture/deck digests, and observed Gateway output digests with scoped checks, action and exit codes. Re-materialize inputs using the [benchmark instructions](../README.md). The pinned tool commit is held constant across both prompts for comparison.

- Builder: [stable B01–B07](builder-stable-01.jsonl), [stable B08–B14](builder-stable-02.jsonl), [candidate B01–B07](builder-candidate-01.jsonl), [candidate B08–B14](builder-candidate-02.jsonl).
- Tester: [stable T01–T04](tester-stable.jsonl), [candidate T01–T04](tester-candidate.jsonl).

The [2026-11-07 follow-up](../../../docs/PROMPT_FOLLOWUP_2026-11-07.md) adjudicates T02/T03 against the active specification, records archived response-word costs, and specifies a smaller blind diagnostic repeat. Candidate wording changed after this cohort; none of these archived answers evaluates the revised wording. Historical evidence stays pinned to its original runtime.
