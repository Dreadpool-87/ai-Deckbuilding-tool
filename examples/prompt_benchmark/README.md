# Casual prompt comparison benchmark (v1)

**Gate E: NOT_VERIFIED.** This benchmark compares unchanged [Builder v7.4](../../prompts/casual/builder/stable/MTG_Deck_Builder_v7.4_full.md) against the [compact Builder](../../prompts/casual/builder/experimental/MTG_Deck_Builder_compact_candidate.md) and unchanged [Tester v3.4.2](../../prompts/casual/tester/MTG_Deck_Tester_v3.4.2_full.md) against the [compact Tester](../../prompts/casual/tester/experimental/MTG_Deck_Tester_compact_candidate.md). See the [requirement matrix](../../docs/PROMPT_CANDIDATE_TRACEABILITY.md). This is experimental; do not change either active prompt or a ChatGPT Project Source based on this document.

## Reproduce inputs

From the repository root, using standard-library Python 3.12+:

~~~sh
scratch=$(mktemp -d)
python examples/prompt_benchmark/materialize.py "$scratch/cases"
python -m unittest discover -s tests -p test_prompt_benchmark_fixtures.py -v
~~~

Each case has a fixed user message (`task.txt`), an explicit synthetic collection (`pool.csv`), a hashed synthetic card source (`oracle.json`, except B14), and, for Tester cases, a frozen `frozen.txt`. [Cases](cases.json) and [pools](pools.json) are versioned. Benchmark-prefixed cards are invented solely for the fixture. Their supplied card data defines the exercise. They are neither real Magic cards nor substitutes for official MTGJSON, and the test does not model match outcomes. The case tables and rubric below are evaluator material; do not give them to either AI arm.

## Fixed cases and evaluator checks

| Case | Main probe | Case-specific expectations |
| --- | --- | --- |
| B01 | Mono-red aggro | Prioritize actual early pressure, use reach to close; justify costly cards competing for slots. |
| B02 | Black-green midrange | Balance interaction, recovery and closing threats; account for different color pips and slow fixing. |
| B03 | White-blue control | Real finishers and removal/counters with timing trade-offs; the tapped crossing cannot pay immediately. |
| B04 | Elf subtype | Distinguish Elves from generic green cards, tokens from owned cards, and lords from payoffs that require a board. |
| B05 | White-black lifegain in requested 2v2 | Two-Headed Giant defaults to shared 30 life but individual trigger recipients and mana; connect actual enablers/payoffs. |
| B06 | Black-green sacrifice/graveyard in 1v2 | Two separate opponent life totals; identify legal sacrifice costs, repeatable vs finite effects, and pressure from two boards. |
| B07 | Transform | Two copies of the one combined identity; front-derived MV 1, no second physical card. A pinned baseline tool can mark the conflicting face variants UNVERIFIED; no fabricated positive check. |
| B08 | Prepare | Two copies of one physical creature, printed MV 3, distinct spell face/color. A passing layout audit is bounded and not a castability verdict. |
| B09 | Reduced quantity/replacement | Metamorphic: compared with B01, latest pool limits Spark to 1+2=3 (extra eligible options are intentional). No fourth copy or prior pool reuse. |
| B10 | Ambiguous shared front name | One supplied ambiguous label cannot authorize either face, both combined identities, or a guessed substitution. |
| B11 | Two simultaneous decks | Total stock supports two exact 60 lists with ≥30 nonlands each; verify aggregate copies and explain allocation. |
| B12 | Contradictory Oracle | Do not certify the contradictory Prepare card/curve; omit it with disclosure or block the affected claim. |
| B13 | Two independent decks | Same data as B11. Reset availability per candidate; report real conflicts separately rather than depleting eligibility. |
| B14 | No executable tools or Oracle | CSV alone does not establish synthetic card facts. Do not invent rules text, validation, calculations or a verified build. |
| T01 | STANDARD with usable data | Preserve original; 36 nonlands + 24 physical lands, MV bins 1:8, 2:8, 3:8, 4:4, 5:8; weighted total 104, average 26/9. Diagnose constrained early mana without a required sim. |
| T02 | QUICK with printings shortage | Spark requires 4, owns 1+2=3; report one-copy shortage separately from ordinary copy limit. Do not change the baseline. |
| T03 | DEEP requested sequencing | One crossing entering tapped cannot pay {U}{U} on turn one, even if it could tap for either color when untapped. Turn-two payment requires joint color/timing modeling or NOT COMPUTED. |
| T04 | STANDARD with contradictory Prepare | No verified curve/COMPLETE when card values conflict; preserve baseline and disclose remaining independent findings, including ownership only if independently reconciled. |

## Controlled model runs (predeclared protocol)

1. Lock this input revision, tool checkout, prompt SHAs, model identifier/revision, host, decoding settings, seed policy, and maximum input/output, tool and time budgets **before running**. Use budgets that accommodate the longer baseline and are equal within every pair; no arm-specific truncation. Record missing telemetry as NOT_VERIFIED. Check that no automatic context summary or memory contains another arm's output.
2. For each role, start fresh sessions with the **same** common system wrapper and tool versions/access, changing only the selected prompt bytes. Common wrapper: “Run the attached selected prompt for this benchmark. It is the only role specification for this run. The repository agent entry point, Gateway result contract and tool CLI documentation may be used for capability and tool semantics, but do not switch role specification. Return your final output and retain observable tool transcripts.” Provide the prompt as the role instruction and `task.txt` as the user input. Place identical case files in clean working directories, use the same repository revision, and deny network/private data to both arms. For B14 deny tools and expose only the inline case input; do not provide an Oracle via some other channel. No coaching or retry differences; record any infrastructure failure independently. When timing, use comparable fresh workers and alternate arm order.
3. Execute all 14 Builder and four Tester cases, three independent fresh-session replicates per case per arm/role on the first host (42 paired Builder runs, 12 paired Tester runs; two outputs per pair). Pair seeds if supported. If another model/host can actually run the same case data under comparable controls, repeat the same protocol independently; never pool hosts to mask a regression. Record comparable pilot pairs as pilots only. Stop and report incomplete cohorts rather than silently reducing the sample. Use public-safe synthetic inputs only and never authorize new external transfers by inference.
4. Archive raw final answers, exact inputs/digests, prompts/commit and observable tool logs with synthetic scope only. Keep arm labels in a separate key until scoring. Give two reviewers blinded per-output artifacts (deck/report plus actual logs and source fixtures); have them score independently, note disagreements, and adjudicate with recorded reasons before revealing arms. Separately check tool-execution claims against real process transcripts, never against assistant prose alone. Preserve malformed or missing outputs as failures or explicit infrastructure blocks, not dropped data.
5. For each role and host publish a table with attempts, matched pairs, completion, critical violations by category/case, mean paired strategy difference and uncertainty, actual token/context and tool-call counts and wall time where measured. A paired interval should resample by case (preserve within-case replicates), use 10,000 bootstrap resamples with seed 20261107, and report the resulting 95% interval as a limited descriptive estimate for this suite. Small synthetic samples do not establish broad rules coverage, live gameplay or cross-model portability.

### Hard failures first

Record each applicable category as PASS/FAIL/NOT APPLICABLE with quoted response evidence or a concrete tool/log mismatch. One category violation can have multiple findings. The candidate must have **zero new critical violations** relative to the matched baseline per case and category; a critical violation shared by both arms remains a blocker to promotion until reviewed and resolved.

| Code | Critical failure |
| --- | --- |
| C1 | Invented card, effect or usable physical identity; treating ambiguous/unresolved names, layout or Prepare data as verified. |
| C2 | Invalid deck size/copy/owned quantity, inflated printing/alias counts, incorrect Basic exception, wrong independent/simultaneous allocation, or a frozen Tester list changed without authorization. |
| C3 | Unsupported complete legality, numerical statistic, mana payment/castability, tool execution, Forge, win-rate or strategic-proof claim. Wrong 2HG/1v2 assumptions affecting the outcome also fail here. |
| C4 | Omitted mandatory output, unreconciled grouped/import quantities, missing requested lists, absent required ownership/curve/limitations or incorrect completion status; truthful scoped abstention is acceptable where expected. |
| C5 | Unauthorized scope: using prior/untagged ownership, automatic swaps, non-Casual/Commander bleed-through, or invalid Builder → Tester handoff. |

Audit name/copy/ownership, list equality and printed counts independently from the model. Re-run the exact displayed import block with the pinned Validator when supported, verify actual exits separately, and check simultaneous aggregate stock across the displayed lists. Do not infer castability from a structural pass. A strategically scoreable output with a hard failure does not become acceptable from strategy points.

### Strategy rubric, scored independently

Score each applicable dimension 0, 1 or 2 from concrete cards, counts and reasoning. Score before unblinding. B10/B12 may still have useful alternative decks to score; B14 has no numeric strategy comparison because card data is intentionally unavailable. In a negative case where a list is reasonably withheld, report this separately rather than inventing strategy points. Tester strategy scores evaluate the quality of the analysis of the frozen list using the same dimensions, not the strength of the list it was given.

| Code | Dimension | 0 | 1 | 2 |
| --- | --- | --- | --- | --- |
| S1 | Coherence | No plausible plan or role chain | Plausible stated plan, some conflicting slots or gaps | Named early/late plan, roles and resilient closing line that match the list |
| S2 | Mana consistency | Impossible or ignores major pips/timing | Counts sources or notices one risk | Reconciles source availability, timing, pip bottlenecks and relevant trade-off |
| S3 | Curve | Mismatched pace or incorrect reading | Plausible curve but no grounded diagnosis | Counts and named early plays, with strategy-appropriate curve reasoning |
| S4 | Card quality within pool | Chooses inferior/inapplicable cards without reason | Reasonable choices with vague explanations | Names slot-specific benefits and opportunity cost versus eligible alternatives |
| S5 | Synergy | Invented interaction or name-only association | Correct interaction with incomplete conditions | Correct trigger, cost, sequencing, redundancy and interruption/conditionality |
| S6 | Trade-offs | Generic advice or impossible claims | Identifies weakness or competitor | Compares credible alternatives, losses, practical weakness and mitigation |

Promotion threshold for this preregistration: in addition to the hard gate and complete mandatory traceability, require nonnegative mean paired score difference across comparable runs and a lower 95% paired bound no worse than **−1 point on the 12-point scale** per role and host. Report case-level losses and rationale even if the aggregate clears the threshold; complete lack of scoreable data is NOT_VERIFIED. These are heuristic judgments, never measured wins.

## Executed evidence and limits

- Deterministic fixture preflight only: four real Gateway validations of frozen lists. T01 and T03 yielded `VALIDATED_WITH_LIMITATIONS` (Gateway 0 / child 0); T02 yielded `BLOCKED_INVALID_DECK` (2 / 1, ownership FAIL); T04 yielded `UNVERIFIED` (3 / 3, Prepare and curve unverified despite a bounded ownership result). All explicitly leave castability unchecked. B11/B13 use identical stock and the fixture test proves both that joint allocation is feasible and that sharing can produce a physical conflict without invalidating a per-deck copy count.
- The [same-host pilot](pilot/README.md) ran one actual Builder pair and one actual Tester pair, with no new critical violations and tied blind rubric scores in these cases. This does not complete the preregistered cohort. Full matched benchmark, independent second host, strategic non-inferiority, general efficiency and actual model token usage remain `NOT_VERIFIED`.
- Rollback: leave the active paths intact. Removing these experimental docs, fixtures and candidate files (and their checksum entries) restores the previous comparison surface without changing what an agent runs.
