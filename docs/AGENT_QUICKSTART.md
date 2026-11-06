# Quickstart for a Python-capable AI agent

**Status: agent guidance for the existing Casual private beta, not a new executable API.**
Read the short `AGENTS.md` first. If the runtime or actual collection is unavailable, say so rather than presenting imaginary execution.

## Experimental Gateway

Use the standard-library dispatch interface when the current agent can execute local Python and all required inputs have actually been mounted. The examples below are for the documented **pinned slim Oracle / GitHub-main Validator** environment, not a generic source migration:

```sh
python tools/agent_gateway.py doctor --oracle /private/AtomicCards_slim_v2.json.gz
python tools/agent_gateway.py discover --oracle /private/AtomicCards_slim_v2.json.gz --oracle-sha256 eb3c03c9303bbf17d50569320f0ab3a7a1d412511198805a36eec03cffff3468 --collection /private/CURRENT_COLLECTION.csv --collection-scope current-run-confirmed --collection-confirmed --theme lifegain --limit 50
python tools/agent_gateway.py validate --oracle /private/AtomicCards_slim_v2.json.gz --oracle-sha256 eb3c03c9303bbf17d50569320f0ab3a7a1d412511198805a36eec03cffff3468 --collection /private/CURRENT_COLLECTION.csv --collection-scope current-run-confirmed --collection-confirmed --deck /private/candidate.txt --exact-60
```

The confirmation flag is **only a caller declaration**, not cryptographic proof of collection ownership. The gateway checks that the Oracle bytes match the frozen slim SHA-256 for real mode; the main Validator must match its documented GitHub-main SHA-256. Alternate Validator profiles require an explicitly supplied file that matches the selected pin. For tests only, use `--collection-scope synthetic --oracle-sha256 <fixture_sha256>` with an explicitly synthetic file. The tool does not build a deck or recommend swaps. A reported `VALIDATED_WITH_LIMITATIONS` is structural validation only.

## Common JSON result contract

All `doctor`, `discover` and `validate` gateway JSON responses now include `schema_version: 1`, one authoritative top-level `status`, `executed`/`tool_execution`, `sources`, `evidence.facts`, `evidence.derivations`, `evidence.hypotheses`, `reason_codes`, `uncertainties`, and `limitations`. Positive swap and strategic-improvement flags always remain `false`. The older P2 `result`/`checks` fields are preserved for compatibility.

For full status, exit-code and privacy rules, read [Agent Gateway Result Contract v1](AGENT_RESULT_CONTRACT_V1.md) and the [JSON Schema](../schemas/agent_gateway_result_v1.schema.json). If a child script starts but fails to produce trustworthy JSON, the gateway returns `UNVERIFIED` with `FAILED_AFTER_START`. Do not infer deck quality, real collection authentication or strategic improvement from a successful action.

## Source-profile selection

`doctor` and `validate` accept `--validator-profile`. The default `github-main-v0.2` uses this repository's pinned Validator. Selecting `project-prepare-candidate` or `frozen-beta-20261022` requires an explicit `--validator-file` whose actual SHA-256 matches the chosen profile. No fallback is permitted.

Read [P4 Source Compatibility](AGENT_SOURCE_COMPATIBILITY_P4.md) for the exact hashes, CLI examples and limitations. The alternative Project and frozen-validator binaries have **not** been exercised in the synthetic CI environment. A source hash or Validator pass is never proof of a strategically superior deck or authenticated ownership.

## Pinned execution and input snapshots

The Gateway pins Card Search v0.3 by SHA-256, and `doctor` now reports `checks.card_search.pin_matches`. `discover` rejects modified Card Search bytes before execution. Both `discover` and `validate` stage SHA-checked code together with private snapshots of the Oracle/collection/deck inputs, run only against those snapshots, and clean them on exit. Rechecking the originals after execution may still yield `UNVERIFIED` if an original changed. No caller can replace the required code pin by a CLI parameter.

**Consent:** `--collection-confirmed` is a caller declaration, not a verified signature or proof of ownership. Only set it after the user expressly confirms that collection **for this execution**. Synthetic test mode must not set it. Never infer consent from prior chats, prior collections or the Oracle. This change does not add authentication, strategy validation, an agent deployment or permission to merge.

## 1. Detect the environment

- Intended repository: `Dreadpool-87/ai-Deckbuilding-tool`, Python 3.9+ for the existing search tools; verify the actual installed runtime.
- Intended inputs: readable MTGJSON AtomicCards `.json`/`.json.gz`, an explicitly confirmed current-run `Name,Quantity` collection CSV, optional user goal and an existing or candidate deck.
- The Oracle source, Validator variant, collection and output must be read from the **actual runtime**. Verify their integrity and applicable hashes before making verified claims.
- Never assume that code in GitHub, ChatGPT Project Sources or a prior conversation is mounted in the current runtime.

## 2. Discover only owned cards

Run from the host repository root, substituting confirmed local paths:

```sh
python tools/card_search.py --oracle /private/AtomicCards_slim_v2.json.gz --collection /private/CURRENT_COLLECTION.csv --owned-only --theme lifegain --identity ANY --limit 100 --format json --output /private/card_candidates.json
```

This produces candidate matches/roles, **not a deck** or rules-certified interactions. Check unresolved names, pagination and whether the requested theme is actually covered.

For supported bounded pair profiles (e.g. tokens, counters, sacrifice), use:

```sh
python tools/synergy_engine.py --oracle /private/AtomicCards_slim_v2.json.gz --collection /private/CURRENT_COLLECTION.csv --theme tokens --identity ANY --limit 50 --output /private/pair_candidates.json
```

`synergy_engine.py` requires `card_search.py` beside it. Do **not** present `HEURISTIC` / `POSSIBLE_SYNERGY_NOT_RULES_VERIFIED` as rules-executable combos.

For one combined, optional thematic report:

```sh
python tools/combo_synergy_report.py --oracle /private/AtomicCards_slim_v2.json.gz --collection /private/CURRENT_COLLECTION.csv --theme tokens --limit 30 --output /private/thematic_report.json
```

An omitted optional Spellbook snapshot can produce `PARTIAL` / `NOT_EXECUTED` for the **combo** section. Inspect **each section**, not only the headline status. Combined reports do not replace Validator execution on final decks.

## 3. Construct and validate

Follow the full **stable Builder v7.4 prompt** for candidate selection, strategy, mana, owned copies, Basic lands, and complete decklists. The Builder is an AI workflow, not a Python deck-construction executable. Do not invent a built-in Python `build` command.

For a complete candidate, run the version that is authorized for the **current environment**:

```sh
python validator/MTG_Deck_Validator_v1.1.1.py --collection /private/CURRENT_COLLECTION.csv --oracle /private/AtomicCards_slim_v2.json.gz --deck /private/candidate.txt --mode casual --exact-60 --output /private/validation.json
```

Only add `--exact-60` when exactly 60 was required; Casual itself allows 60 or more cards. Inspect the actual process exit code and reported `status`, `checks`, `failures`, `uncertainties`, `mana_curve_integrity` and `prepare_layout_audit`. A valid deck does not establish optimal strategy or win rate.

**Version trap:** GitHub `main`'s Validator SHA-256 is documented as `f8e915a95e73e20edf59267dfe39e45f82d62bb5eb49fd4eb180194189d995ef`. The separately selected ChatGPT Project Prepare candidate is `c422295676d0bad04aa1449725b07a7c11bf58b7990a34aff209e10ba742ac8d`. The frozen old beta/Swap Advisor pin is `8749b50d0aeaa52124a99271a0ab40bcc979350c6e8b5e9074c4f28d63a3d1ac`. These are **documented expected values, not hashes verified by this quickstart**. Re-read `PROJECT_STATUS.md` and actually hash the selected bytes. Never silently substitute one variant for another.

## 4. Optional testing and swap discussion

- Tester v3.4.2 is a versioned **prompt**; follow its selected QUICK/STANDARD/DEEP requirements and clearly label computed versus judged outcomes.
- Swap Advisor work remains separate and on hold. The Gateway does not expose a swap action.
- AI can **suggest** candidate improvements in prose with explicit upsides, downsides and assumptions, but must never label those as certified by v2. No automatic deck edits.

## 5. Minimal outcome contract for today

Report `EXECUTED` vs `NOT_EXECUTED` for each actual tool call, the exact source context, validation status, and which strategic statements are hypotheses. If inputs are missing or invalid, return `INPUT_ERROR` / `UNVERIFIED` when appropriate; never quietly substitute a synthetic collection as real ownership.

**Current boundary:** The Gateway workflow and source hardening passed independent synthetic acceptance. Real collections, the production Oracle bulk file, alternate Validator binaries and cross-agent portability remain outside that test scope. Swap Advisor work remains separate and on hold.

