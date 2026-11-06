# P4: Explicit Oracle and Validator compatibility profiles

**Status:** Experimental Gateway source profiles. Independent synthetic acceptance covered the default Validator path, Card Search pinning and private input snapshots. Alternate Validator binaries remain untested.

## Purpose

Python-capable AI agents must choose the *actual* Validator file selected for their environment. The gateway validates observed local SHA-256 bytes against the chosen named profile **before executing the Validator**. There is no silent fallback, no "latest available" auto-selection and no assumption that matching filenames imply matching code.

### Supported pinned profiles

| `--validator-profile` | Expected SHA-256 of local Validator bytes | Source and status | P4 execution evidence |
| --- | --- | --- | --- |
| `github-main-v0.2` (default) | `ffe3f958c342b70804941e6cec6604544d027cb8141aaf502f7749120f76bac0` | Public preview checkout, `validator/MTG_Deck_Validator_v1.1.1.py` | [Synthetic verification](PUBLIC_PREVIEW_AUDIT.md) |
| `project-prepare-candidate` | `c422295676d0bad04aa1449725b07a7c11bf58b7990a34aff209e10ba742ac8d` | Separately managed ChatGPT Project Source, *not automatically synchronized* | **NOT_TESTED with this gateway**; the actual Project Source binary was not supplied to CI |
| `frozen-beta-20261022` | `8749b50d0aeaa52124a99271a0ab40bcc979350c6e8b5e9074c4f28d63a3d1ac` | Old frozen GitHub `release/casual-private-beta-2026-10-22`, rollback/reference only | **NOT_TESTED with this gateway**; don't confuse compatible CLI shape with executed behavioral verification |

The default CLI selector keeps its legacy name for existing callers. Its digest tracks the public checkout. The prior public baseline Validator digest `f8e915a95e73e20edf59267dfe39e45f82d62bb5eb49fd4eb180194189d995ef` is historical and can be reproduced from commit `ddcd4412c81db80b6c4caceb749220b932793b19`. The prior Card Search digest at that commit is `024de9aaaa1994ab6bce6944bd62e237f9fa9ea0ab52ed5b8bca8aca93a6851e`. **The gateway hashes the actually supplied local file on every invocation**; this document does not claim that the Project Source or frozen binary was read or executed in the current development runtime. Explicit acceptance would require a separate controlled integration run with those exact bytes.

## MTGJSON Oracle policy

Only `AtomicCards_slim_v2.json.gz` SHA-256 `eb3c03c9303bbf17d50569320f0ab3a7a1d412511198805a36eec03cffff3468` is accepted in `current-run-confirmed` mode.

For `synthetic` tests only, `--oracle-sha256 <exact-synthetic-fixture-digest>` may be used; synthetic collection scope is mandatory. This does not grant real ownership or valid MTG card facts.

A pinned Oracle is a card-fact reference, **not a source of collection ownership**; a Validator pass is structural, not strategic or universal legality.

## CLI: same interface, explicit source identity

In the repository runtime:

```sh
python tools/agent_gateway.py doctor --oracle /private/AtomicCards_slim_v2.json.gz
python tools/agent_gateway.py validate --oracle /private/AtomicCards_slim_v2.json.gz --oracle-sha256 eb3c03c9303bbf17d50569320f0ab3a7a1d412511198805a36eec03cffff3468 --collection /private/CURRENT_COLLECTION.csv --collection-scope current-run-confirmed --collection-confirmed --deck /private/candidate.txt --validator-profile github-main-v0.2 --exact-60
```

When using the separately authorized Project Source, the caller **must** supply its actual local file and matching profile; no default-file fallback:

```sh
python tools/agent_gateway.py doctor --oracle /private/AtomicCards_slim_v2.json.gz --validator-profile project-prepare-candidate --validator-file /private/MTG_Deck_Validator_v1.1.1_PREPARE_COLOR_INTEGRITY_CANDIDATE.py
python tools/agent_gateway.py validate --oracle /private/AtomicCards_slim_v2.json.gz --oracle-sha256 eb3c03c9303bbf17d50569320f0ab3a7a1d412511198805a36eec03cffff3468 --collection /private/CURRENT_COLLECTION.csv --collection-scope current-run-confirmed --collection-confirmed --deck /private/candidate.txt --validator-profile project-prepare-candidate --validator-file /private/MTG_Deck_Validator_v1.1.1_PREPARE_COLOR_INTEGRITY_CANDIDATE.py --exact-60
```

These are **instructions, not proof of executed Project Source tests**. Only use an actual local file whose bytes match the selected pin; never fetch private data into GitHub or select a different Validator automatically because the expected file is missing. Frozen beta uses the same explicit `--validator-profile frozen-beta-20261022 --validator-file ...` format and remains a rollback/reference, not a recommended migration.

## Fail-closed rules and meaning

1. Unknown profile: `INPUT_ERROR / INVALID_ARGUMENTS`. Selecting a nondefault profile without `--validator-file`: `INPUT_ERROR / EXPLICIT_VALIDATOR_FILE_REQUIRED`.
2. Wrong Validator bytes in `validate`: `INPUT_ERROR / VALIDATOR_SHA256_MISMATCH`, child `NOT_EXECUTED`. `doctor` reports `UNVERIFIED` with `pin_matches: false`, no downstream execution.
3. If `doctor --oracle` receives wrong Oracle bytes or an unavailable Oracle, **do not** report ready: `UNVERIFIED`. A successful `doctor` without `--oracle` means **local components only**, not Oracle readiness.
4. Real mode rejects alternate Oracle hashes even when the caller supplies them. Synthetic mode does not authenticate real-user ownership.
5. Input paths, including Validator path, must be regular files without symlink components and within existing size bounds. Filenames and personal collection content are not reflected in generic gateway errors.
6. After a child returns, the gateway rechecks observed Oracle/collection/deck/selected Validator hashes. A detectable change produces `UNVERIFIED / SOURCE_CHANGED_DURING_EXECUTION` and `tool_execution: FAILED_AFTER_START`; never trust the returned child analysis.
7. Both `discover` and `validate` execute staged, SHA-checked code bytes in a private temporary directory. Card Search v0.3 has a **non-overridable mandatory code pin**: `c5ceabbaf98d837e0e72598a15906c085c41eb26da74303a408342ff62d7c4e8`. `doctor` checks that pin; `discover` rejects wrong bytes before launching Card Search. The existing Validator profile pin remains mandatory for `validate`.
8. Before either child runs, the gateway copies Oracle and collection, plus the deck for validation, to private temporary input snapshots and records the hash of the bytes actually staged. The Oracle snapshot must match the requested SHA and (in real mode) the frozen slim pin. The child reads only these snapshots. The private stage is cleaned after success/failure. Original paths are still rechecked after execution: a detectable change of an original during execution returns `UNVERIFIED / SOURCE_CHANGED_DURING_EXECUTION` even if the child read the trusted snapshots. This is intentional fail-closed behavior.
9. A set of separately copied inputs is **not** one atomic multi-file capture. The approach does not authenticate collection ownership, protect against hostile same-user manipulation of a temporary runtime, prove complete source-to-file atomicity, or guarantee universal MTG legality. Use a private trusted filesystem. This is development hardening only.
10. The `--collection-confirmed` flag is an unauthenticated **declaration by the calling agent for this invocation**. The agent may pass it only after the user has explicitly confirmed that specific collection for the current run. Never infer that confirmation from previous chats, manifests or MTGJSON data.
11. Source profiles establish file identity. Rules coverage and cross-agent portability require separate evidence. Swap Advisor work remains separate and on hold.

## Evidence and next acceptance steps

- Developer synthetic tests cover correct default profile, explicit alternate selection requirements, mismatch, symlinked Validator rejection, Oracle mismatch, external copy of the same approved Validator detectable mid-run source mutation, and Validator replacement/restoration around the child launch.
- CI verification must name the *exact head commit*, actual job conclusions and test counts. No user CSV or binary Oracle payload is permitted in GitHub.
- The existing [JSON Result Contract v1](AGENT_RESULT_CONTRACT_V1.md) now includes `sources.validator_profile` (a selected label, **not authentication**).

**No merge approval** is conveyed by this compatibility profile document. The active public Validator pin applies to this checkout. Project Sources and private release pins are separate.

**Source hardening:** PR #41 adds the independently tested Card Search pin and private input snapshots on top of PR #39.
