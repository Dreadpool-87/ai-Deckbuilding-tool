# Agent Gateway Result Contract v1 (experimental)

**Status:** Experimental output contract, exercised in independent synthetic acceptance. Python standard library only. Consumers should use the observed execution result as evidence.

## Consumer rule: one authoritative gateway status

The JSON returned by `python tools/agent_gateway.py doctor|discover|validate` emits the fields below. The three new execution and source fields are optional in the schema so consumers can still validate earlier v1 reports.

| Field | Meaning |
| --- | --- |
| `schema_version: 1` | Version of this common output contract, independent of tool/Validator versions |
| `gateway_version` | Versioned implementation that emitted this report |
| `action`, `status` | Requested supported action and **one authoritative gateway result** |
| `executed` | **True only if the downstream process was launched**; local `doctor` checks are not child execution |
| `tool_execution` | `NOT_EXECUTED`, `EXECUTED`, or `FAILED_AFTER_START` |
| `child_exit_code` | Observed child process exit code, including its termination code when known; null for doctor or failed launch |
| `validator_version`, `card_search_sha256` | Verified source identity fields when applicable, otherwise null |
| `sources` | Observed file hashes (when available), explicitly selected Validator profile, collection declaration and authentication boundary |
| `evidence.facts` | Narrow facts such as local SHA-256 bytes matching a supplied expectation, **not card-rule correctness** |
| `evidence.derivations` | Executed, bounded mechanical/structural deductions, with a named scope |
| `evidence.hypotheses` | Heuristic card-theme/role ideas, **never rules/strategic proof** |
| `reason_codes` | Machine-readable failure or abstention cause codes |
| `uncertainties`, `limitations` | Explicit unknowns and unsupported claims |
| `automatic_swap_authorized: false` | No automatic deck changes |
| `strategic_improvement_verified: false` | No superior-deck claim |

The full machine-readable schema is [`schemas/agent_gateway_result_v1.schema.json`](../schemas/agent_gateway_result_v1.schema.json). It uses JSON Schema Draft 2020-12; runtime schema validation is not an installed dependency. Existing P2 `checks`, `result`, `reason` and selected provenance keys remain for compatibility. **Do not treat `result.status` as a second gateway verdict.** It is the original underlying tool's status (for example, the Validator's `PASS_WITH_LIMITATIONS`). The top-level `status` is the gateway authority.

## Outcomes and exit codes

| Action | Gateway status | Meaning | Exit |
| --- | --- | --- | --- |
| doctor | `RUNTIME_COMPONENTS_PRESENT` | Local interpreter path available and pinned scripts readable; **no child process or deck test** | 0 |
| doctor | `UNVERIFIED` | One or more required local components not established | 3 |
| discover | `CANDIDATES_NOT_VALIDATED` | Card Search script executed and emitted candidate data; no deck/strategy proof | 0 |
| validate | `VALIDATED_WITH_LIMITATIONS` | Existing Casual Validator reported structural `PASS_WITH_LIMITATIONS` with matching exit | 0 |
| validate | `BLOCKED_INVALID_DECK` | Existing Validator reported `FAIL`; blocked from positive deck conclusions | 2 |
| validate | `UNVERIFIED` | Existing Validator could not establish full scoped validation | 3 |
| any | `INPUT_ERROR` | Bad/missing/unsafe inputs or failed preconditions; child not started | 2 |
| launch failure | `UNVERIFIED` | `NOT_EXECUTED` with `SUBPROCESS_NOT_STARTED`, for example when Python cannot be launched | 3 |
| downstream failure | `UNVERIFIED` | Child started but timed out or returned unusable/contradictory output; no trusted result | 3 |

`--help` prints ordinary human-readable argparse help. Invalid CLI arguments, however, produce a structured JSON `INPUT_ERROR` with `INVALID_ARGUMENTS`, without echoing user-provided paths.

## Ownership outcomes inside an executed validation

The nested Validator `checks.ownership` is three-valued. Verified sufficient stock gives `PASS`; a proven selected-card shortfall gives `FAIL`; unresolved required inventory gives `UNVERIFIED`. Mixed canonical/front labels with unknown overlap are quarantined. They supply neither added verified copies nor proof of zero stock. A definite shortfall for another selected card still makes the ownership check `FAIL`, while the affected unknown stock remains in nested `uncertainties`.

A Validator `FAIL` due to an independent copy-limit or deck-size violation may coexist with `checks.ownership: UNVERIFIED`. The Gateway returns outer `BLOCKED_INVALID_DECK` for that overall failure and `UNVERIFIED` for an otherwise unverified deck. Both can have `tool_execution: EXECUTED`. Inspect nested failures and uncertainties for the evidence behind each check. Result schema v1 and its exit mappings are preserved.

## P4 compatible source identity extension

The v1 contract now requires `sources.validator_profile`, one of `github-main-v0.2`, `project-prepare-candidate`, `frozen-beta-20261022` or null when not selected. A **profile is only a declared selection**; it is not proof of local execution. The gateway compares the selected local Validator bytes against the corresponding fixed SHA-256 and rejects mismatches. See [P4 compatibility details](AGENT_SOURCE_COMPATIBILITY_P4.md). No alternate-runtime GO is implied.

## Pinned execution and input snapshots

The Gateway pins Card Search code (`doctor.checks.card_search.pin_matches`) and executes SHA-checked, staged code bytes. The underlying tool reads staged snapshots of the declared Oracle and collection, and additionally the deck for validation. `sources.*_sha256` correspond to those captured snapshots, not authenticated ownership. A change of the original files detected after execution still invalidates the result with `UNVERIFIED`. The v1 execution fields are additive. Gateway and child exit codes are independent; for example, an invalid deck uses gateway exit 2 and child exit 1. Python children ignore interpreter startup hooks, and stdout/stderr are bounded during capture. The timeout applies to the pinned standalone tools, which do not launch descendant processes. The gateway rejects missing, malformed, contradictory or oversized output without forwarding child stderr. `SUBPROCESS_REPORTED_INPUT_ERROR` means the child rejected an input. To diagnose the exact line, inspect the direct tool's error locally.

## Sources and evidence

- `sources.oracle_sha256`: observed local bytes matching `--oracle-sha256`. A **synthetic** run may supply its own fixture hash; this does **not** authorize real-user operation. Real collection mode requires the frozen slim Oracle pin.
- `sources.validator_sha256`: the observed local source hash from `doctor`, or the explicitly pinned GitHub-main Validator during validation. This is **not** a claim of general rules-engine completeness.
- `sources.collection_sha256`, `sources.deck_sha256`: observed fingerprints of the inputs staged for the tool. They do not authenticate ownership or establish an atomic multi-file handoff.
- `sources.collection_scope`: `synthetic`, `current-run-confirmed` or null for `doctor`. The flag `--collection-confirmed` is a caller declaration only; `ownership_authentication` remains `NOT_IMPLEMENTED`.
- `evidence` entries contain only `code`, `basis` and `scope`. Their presence does not override `uncertainties`; an AI agent must not promote a role guess to `FACT`.
- No user collection, deck, path, private Oracle dump, or hidden test data may be committed to GitHub. Tool JSON output can include private deck/card data when run locally and **must not be forwarded to an external AI provider without separate authorization**.

## Compact sample (illustrative, not an executed report)

```json
{
  "schema_version": 1,
  "gateway_version": "0.3.0-experimental",
  "action": "discover",
  "status": "CANDIDATES_NOT_VALIDATED",
  "executed": true,
  "tool_execution": "EXECUTED",
  "child_exit_code": 0,
  "validator_version": null,
  "card_search_sha256": null,
  "sources": {
    "oracle_sha256": null,
    "validator_sha256": null,
    "validator_profile": null,
    "collection_sha256": null,
    "deck_sha256": null,
    "collection_scope": "synthetic",
    "ownership_authentication": "NOT_IMPLEMENTED"
  },
  "evidence": {
    "facts": [],
    "derivations": [],
    "hypotheses": [
      {"code": "DISCOVERED_CARD_ROLES", "basis": "CARD_SEARCH_V0_3", "scope": "HEURISTIC_NOT_RULES_VERIFIED"}
    ]
  },
  "reason_codes": [],
  "uncertainties": ["CANDIDATES_NOT_DECK_VALIDATED", "STRATEGIC_IMPROVEMENT_UNVERIFIED"],
  "limitations": ["An illustrative output shape, not a source of card truth."],
  "automatic_swap_authorized": false,
  "strategic_improvement_verified": false
}
```

The above example uses null hashes deliberately; real successful `discover` output has actual hashes derived from read files. The full P2 child `result` is omitted for readability. Do not submit this sample to the system as evidence.

## Hard consumer safeguards

1. Respect `status` and `tool_execution` together. A tool crash or invalid JSON is `UNVERIFIED`, never success, and `FAILED_AFTER_START` means no trusted child result.
2. `VALIDATED_WITH_LIMITATIONS` is **not** verified strategy, complete legality, castability, combo viability or win probability.
3. Card Search results are **candidates only**. They cannot establish ownership beyond the currently declared collection.
4. The output may be shown or archived locally but is not a reusable proof input. Never accept a cached report or AI-written claim as new source data.
5. This output contract covers the Gateway actions. Cross-agent evaluation and any Builder or Swap Advisor integration have separate scopes.

The legacy `collection_owned_copies` integer is the raw CSV row-quantity sum. Its additive `collection_owned_copies_basis` field identifies `RAW_DECLARED_CSV_QUANTITY_SUM_NOT_VERIFIED_PHYSICAL_TOTAL`. Overlapping aliases can contribute to that raw total, which is never verified physical stock. Use `checks.ownership`, `collection_coverage` and per-card uncertainty for ownership evidence.
