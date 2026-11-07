# Compact prompt follow-up — 2026-11-07

**DRAFT / NO_GO_FOR_ACTIVATION.** Reviewed from PR #3 head `0046bb51eb0e4479b9550bc0482b824e7f7f5e52`; PR #2 is still open. Stable Builder v7.4 and Tester v3.4.2 remain active. This is focused text/evidence review, not a new model cohort or proof of prompt equivalence.

## Completion findings

Read both complete baseline/candidate prompts, the requirement matrix, preregistered rubric, all pilot answers/reports and all 36 JSONL responses. Existing raw evidence and historical hashes remain unchanged.

| Case | Recorded disagreement | Adjudication against the task and active baseline |
| --- | --- | --- |
| T02 | Stable `PARTIAL QUICK`; candidate `COMPLETE FOR QUICK`; both find 1+2=3 Spark owned, 4 required, short 1 | Stable D3.5–6 separates analysis completion from ownership FAIL; its explicit STANDARD wording plus mode-scoped historical §10 supports the same distinction for QUICK. A finished shortage audit is not blocked aggregation. Candidate's completion interpretation is supported, conditional on all other QUICK duties passing; Gateway remains BLOCKED_INVALID_DECK (2), child FAIL (1). This does not authorize a blocked Builder handoff. |
| T03 | Stable `PARTIAL DEEP` for broader castability; candidate `COMPLETE FOR DEEP` | The task asks if Deny is payable on T2 and whether one entering-tapped Crossing pays UU on T1. Both answers report tested bounded payment and the counterexample; both omit full spell legality. Unrequested full castability does not itself justify PARTIAL. A request for unsupported full castability would. This is interpretation of archived answers; exact enumerator transcripts beyond recorded summaries are not newly verified. |
| T04 | Both PARTIAL, full curve unverified; historical child ownership PASS is qualified | Correct to withhold completion and identity-certified ownership. PR #2 identity-aware outputs must be labeled separately; a literal historical label match cannot establish the disputed physical identity. |

Candidate-only changes make separate analysis, ownership and actual execution fields explicit, retain FAIL/UNVERIFIED/NOT VERIFIED/NOT_EXECUTED distinctions, clarify ambiguous alias stock, restore explicit QUICK weak-slot count/cutting cost, and preserve Builder's field-absence discipline. No active original, selector, Python tool, stored response or rubric threshold was changed. The [traceability addendum](PROMPT_CANDIDATE_TRACEABILITY.md#2026-11-07-follow-up-mandatory-detail-and-execution-boundaries) identifies exact source obligations and remaining execution gaps.

## Observed efficiency, not inferred savings

| Measure | Stable | Historical candidate | Interpretation |
| --- | ---: | ---: | --- |
| Builder source words, original pilot `wc -w` | 6,470 | 1,522 | Source length only; updated candidate is longer |
| Tester source words, original pilot `wc -w` | 5,136 | 1,449 | Source length only; updated candidate is longer |
| Archived Builder answer words (`len(response.split())`, 14 outputs) | 7,750 | 8,578 | Candidate answers were longer in this cohort |
| Archived Tester answer words (same method, 4 outputs) | 2,212 | 2,506 | Candidate answers were longer in this cohort |
| Recorded Gateway actions, all responses | 22 | 20 | Scope differs: stable includes discovery and an invalid ambiguity probe |
| Builder runs reported using direct Card Search | Not fully enumerated | 7 | Gateway-only accounting omits these interactions; counts per run are unavailable |
| Actual model input/output/tool tokens, comparable wall time, all tool interactions | NOT_VERIFIED | NOT_VERIFIED | No net efficiency or runtime conclusion |
| Broad successful task outcomes / strategic non-inferiority | NOT_VERIFIED | NOT_VERIFIED | Two blind pilot ties and list arithmetic do not establish cohort-wide acceptance |

The shorter source cannot establish fewer actual tokens, faster completion or better outcomes. Candidate answer words total 11,084 vs 9,962, and direct discovery has additional costs. The available data cannot determine whether these cancel input savings. Within-arm batch context and unavailable exact model revision/decoding controls confound general comparisons; no second model/host result exists.

## Smallest useful next blind repeat — specified, NOT_EXECUTED

Run a diagnostic subset before funding the preregistered full acceptance cohort: B04 (Elf package opportunity cost), B06 (finite sacrifice/drain under 1v2), B11/B13 (same stock, simultaneous vs independent), T02 (verified printing shortage), T03 (bounded payment), T04 (contradictory Prepare), and one new frozen mixed front/combined-label ownership case. For the new case preregister realistic face metadata, quantities 2+2, demand 4, expected ownership UNVERIFIED absent independent evidence, and separate copy-limit outcome; publish fixture/task hashes **before** any model run. It is a targeted diagnostic, not a replacement promotion threshold or a holdout after its expected answer is disclosed here.

Use two fresh-session repeats per arm per case: **16 matched pairs / 32 outputs** on one host. One case only per session; no inherited other-case or other-arm answers, memory, coaching or summaries. Randomize/alternate arm order. Lock identical collection/Oracle bytes, common system wrapper, full tool/helper/Validator checkout hashes, capabilities, Python/environment, requested scope, rubric and equal output/tool/time budgets. Log the exact prompt digests (new candidate vs unchanged stable), model/build/settings if available, all observed direct and Gateway calls, actual process exits, and token/time telemetry or NOT_VERIFIED. If host isolation or equal tools cannot be enforced, stop and report the blocked control instead of starting another batched cohort.

Randomize artifact IDs and keep the arm key separate. Two reviewers independently score C1–C5 and S1–S6 from complete outputs plus process evidence, record disagreements, adjudicate before unblinding, and retain incomplete outputs as failures/infrastructure blocks. Independently reparse imports, inventory and curve ledgers. For T02 score analysis completion separately from verified ownership failure; for T03 require bounded payment evidence or truthful PARTIAL for a blocked requested event, never demand unrequested full gameplay. A new critical violation blocks advancement. Publish case-level outcomes and observed cost; this small diagnostic cannot establish statistical non-inferiority or cross-model portability. Cross-model reliability remains NOT_VERIFIED until an actual comparable second host/model runs.

## Deferred identity compatibility

Historical pilot/cohort used tool baseline `0fd38ab2846a0e4c575e6ecac947b006407f913b`, Validator SHA `ffe3f958c342b70804941e6cec6604544d027cb8141aaf502f7749120f76bac0`. They are not outputs from PR #2. Do not pool or compare one old arm against one new arm. After the owner merges PR #2, update PR #3 by an ordinary merge of updated main (preserving published commits, no force push), resolve manifests, rerun compatibility and all applicable checksum checks, then run **both** prompt arms against one common updated runtime. Until then this post-merge step is deferred, not accepted. No ChatGPT Project migration or source synchronization is performed by this work.

## Verification scope

Actual command outcomes are recorded below after execution. Fixture tests exercise Python and stored synthetic data; they do not execute or certify either revised candidate as an AI workflow. No new behavioral benchmark or blind re-score was executed during this follow-up.

- Python 3.12.14: `python -m unittest discover -s tests -p test_prompt_benchmark_fixtures.py -v` — exit 0, 3 tests; includes actual four frozen-deck Gateway invocations on this PR #3 runtime, not PR #2.
- `python -m unittest discover -s tests -p test_english_repository_integrity.py -v` — exit 0, 6 tests (English directives, local links, syntax and synthetic example policy).
- A read-only Python metadata audit parsed all 36 records, matched 114 available fixture digests against freshly materialized case files and checked all eight frozen Tester deck hashes; exit 0. Four historical pilot JSON reports were parsed and inspected; their execution was not repeated by that audit. The first temporary audit invocation incorrectly targeted an existing directory, which materialize correctly rejected (exit 1); using a new child directory passed without source changes.
- Updated source `wc -w`: Builder 6,470 / 1,580 and Tester 5,136 / 1,647 (stable / revised candidate); these revised candidates have no new behavioral run.
- Archived word totals were recomputed with `len(record["response"].split())`; these are words, not tokenizer telemetry. No actual model-token or elapsed-time savings was measured.
- A separate agent independently reviewed the working diff against the task and baseline. It confirmed T02/T03 interpretation and recomputed response-word counts; it identified ambiguous ownership-field wording with a simultaneous proven shortage and unresolved identity. The candidate now preserves per-card FAIL/UNVERIFIED evidence and the actual tool check instead of overwriting them with an analysis-completion label. This was a separate same-model review, not second-model benchmarking.
- Full PR #3 offline core suite: `python -m unittest discover -s tests -p 'test_*.py' -v` — exit 0, 269 tests. Workflow checker — exit 0. `git diff --check` — exit 0. Checksum verification — exit 0. These are runtime/repository checks, not AI prompt-behavior acceptance.
- `python scripts/audit_public_history.py --repo . --strict` — exit 0, NO_PATTERN_HITS for reachable locally fetched history before this follow-up commit (278 objects / 192 blobs); heuristic scope excludes external artifacts and unreachable objects. The publisher must repeat against the final updated commit.

### Verified-stock compatibility clarification

Builder B1 also permits ownership PASS when independently verified stock already covers the requested quantity; an unsupported additional row does not erase that proof. For example, with a verified canonical row of 2 and an unsupported reverse-face row of 4, demand 2 can pass from the verified 2 alone, while demand 4 remains UNVERIFIED if the unresolved row might supply the difference. Never count the unresolved 4 as owned or as zero proven stock, and retain any separately proven shortage as FAIL. A front/combined overlap quarantined by the resolver supplies no verified stock merely because its row labels are recognizable.

This is a source-instruction compatibility correction. PR #2's executed deterministic cases establish its runtime behavior; no new candidate model run establishes that a host follows this wording. Text assertions, fixture execution and behavioral acceptance remain different evidence levels. The historical cohort does not evaluate either follow-up candidate revision.
