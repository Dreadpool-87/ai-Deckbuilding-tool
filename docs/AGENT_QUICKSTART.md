# Quickstart for a Python-capable AI agent

**Status:** Public test preview. The primary workflow targets Casual 60+ card decks.
Read the short `AGENTS.md` first. If the runtime or actual collection is unavailable, say so rather than presenting imaginary execution.

## Automatic preflight and validation entry point

From a **local checkout** with Python 3.12+ and the pinned slim Oracle, use the standard-library module to chain Gateway preflight and a real action. AI still decides the strategy and writes the candidate. These are **executable commands**, not proof that any particular chat host ran them:

```sh
python -m ai_deckbuilding_tool doctor --oracle /private/AtomicCards_slim_v2.json.gz
python -m ai_deckbuilding_tool discover --oracle /private/AtomicCards_slim_v2.json.gz --collection /private/CURRENT_COLLECTION.csv --collection-confirmed --theme aggro
python -m ai_deckbuilding_tool validate --oracle /private/AtomicCards_slim_v2.json.gz --collection /private/CURRENT_COLLECTION.csv --collection-confirmed --deck /private/candidate.txt
```

The CLI emits one JSON document containing a `preflight` Gateway receipt, the actual `gateway` receipt when the action ran, `validated` (true **only** for `VALIDATED_WITH_LIMITATIONS`), and `next_action`. Exit code 0 means readiness or a successful requested action; 2 means invalid input/deck; 3 means unverified or blocked readiness. `doctor` without `--oracle` runs a source-only check but returns exit 3 with `PINNED_ORACLE_NOT_SUPPLIED`.

For synthetic offline testing only, add `--synthetic --oracle-sha256 <fixture-sha256>` to `discover` or `validate`, and do **not** pass `--collection-confirmed`. This never authorizes ownership claims for real collections. Real mode requires `--collection-confirmed` and the original pinned slim Oracle; the CLI does not change Gateway pins or silently accept a new MTGJSON dataset. To allow a Casual deck above 60 cards, pass `--allow-over-60` to validation. Otherwise validation requires exactly 60.

**Host boundary:** This module does not clone GitHub, download/normalize card data, install Python, start itself from a URL or turn other AI systems into Python hosts. Agents should attempt execution when their host permits it and report an exact blocker otherwise. Do not send a private CSV to GitHub or a remote service. Failed checks must never be described as verified deck results.

## Experimental Gateway

Use the standard-library dispatch interface when the current agent can execute local Python and all required inputs have actually been mounted. The following commands use the pinned slim Oracle and the public repository Validator.

```sh
python tools/agent_gateway.py doctor --oracle /private/AtomicCards_slim_v2.json.gz
python tools/agent_gateway.py discover --oracle /private/AtomicCards_slim_v2.json.gz --oracle-sha256 eb3c03c9303bbf17d50569320f0ab3a7a1d412511198805a36eec03cffff3468 --collection /private/CURRENT_COLLECTION.csv --collection-scope current-run-confirmed --collection-confirmed --theme lifegain --limit 50
python tools/agent_gateway.py validate --oracle /private/AtomicCards_slim_v2.json.gz --oracle-sha256 eb3c03c9303bbf17d50569320f0ab3a7a1d412511198805a36eec03cffff3468 --collection /private/CURRENT_COLLECTION.csv --collection-scope current-run-confirmed --collection-confirmed --deck /private/candidate.txt --exact-60
```

The confirmation flag is **only a caller declaration**, not cryptographic proof of collection ownership. The gateway checks that the Oracle bytes match the frozen slim SHA-256 for real mode; the main Validator must match its documented GitHub-main SHA-256. Alternate Validator profiles require an explicitly supplied file that matches the selected pin. For tests only, use `--collection-scope synthetic --oracle-sha256 <fixture_sha256>` with an explicitly synthetic file. The tool does not build a deck or recommend swaps. A reported `VALIDATED_WITH_LIMITATIONS` is structural validation only.

## Common JSON result contract

All `doctor`, `discover` and `validate` gateway JSON responses now include `schema_version: 1`, one authoritative top-level `status`, `executed`/`tool_execution`, `child_exit_code` (or `null` if unavailable), `sources`, `evidence.facts`, `evidence.derivations`, `evidence.hypotheses`, `reason_codes`, `uncertainties`, and `limitations`. Positive swap and strategic-improvement flags always remain `false`. The older P2 `result`/`checks` fields are preserved for compatibility.

For full status, exit-code and privacy rules, read [Agent Gateway Result Contract v1](AGENT_RESULT_CONTRACT_V1.md) and the [JSON Schema](../schemas/agent_gateway_result_v1.schema.json). If a child script starts but fails to produce trustworthy JSON, the gateway returns `UNVERIFIED` with `FAILED_AFTER_START`. Do not infer deck quality, real collection authentication or strategic improvement from a successful action.

## Source-profile selection

`doctor` and `validate` accept `--validator-profile`. The default `github-main-v0.2` uses this repository's pinned Validator. Selecting `project-prepare-candidate` or `frozen-beta-20261022` requires an explicit `--validator-file` whose actual SHA-256 matches the chosen profile. No fallback is permitted.

Read [P4 Source Compatibility](AGENT_SOURCE_COMPATIBILITY_P4.md) for the exact hashes, CLI examples and limitations. The alternative Project and frozen-validator binaries have **not** been exercised in the synthetic CI environment. A source hash or Validator pass is never proof of a strategically superior deck or authenticated ownership.

## Pinned execution and input snapshots

The Gateway pins Card Search and its shared card identity helper by SHA-256, and `doctor` now reports `checks.card_search.pin_matches`. `discover` rejects modified Card Search bytes before execution. Both `discover` and `validate` stage SHA-checked code together with private snapshots of the Oracle/collection/deck inputs, run only against those snapshots, and clean them on exit. Rechecking the originals after execution may still yield `UNVERIFIED` if an original changed. No caller can replace the required code pin by a CLI parameter.

**Consent:** `--collection-confirmed` is a caller declaration, not a verified signature or proof of ownership. Only set it after the user expressly confirms that collection **for this execution**. Synthetic test mode must not set it. Never infer consent from prior chats, prior collections or the Oracle. This change does not add authentication, strategy validation, an agent deployment or permission to merge.

## 1. Detect the environment

- Intended repository: `Dreadpool-87/ai-Deckbuilding-tool`, Python 3.12 is recommended. Verify the actual installed runtime.
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

**Source selection:** Check the [active source pins](AGENT_SOURCE_COMPATIBILITY_P4.md) and hash the actual bytes. The public checkout, ChatGPT Project Prepare candidate, and frozen beta use separate pins.

## 4. Optional testing and swap discussion

- Tester v3.4.2 is a versioned **prompt**; follow its selected QUICK/STANDARD/DEEP requirements and clearly label computed versus judged outcomes.
- Swap Advisor work remains separate and on hold. The Gateway does not expose a swap action.
- AI can **suggest** candidate improvements in prose with explicit upsides, downsides and assumptions, but must never label those as certified by v2. No automatic deck edits.

## 5. Minimal outcome contract for today

Report `EXECUTED` vs `NOT_EXECUTED` for each actual tool call, the exact source context, validation status, and which strategic statements are hypotheses. If inputs are missing or invalid, return `INPUT_ERROR` / `UNVERIFIED` when appropriate; never quietly substitute a synthetic collection as real ownership.

**Current boundary:** The Gateway workflow and source hardening passed independent synthetic acceptance. The full AtomicCards and pinned slim datasets were exercised with synthetic ownership. Real collections, alternate Validator binaries and cross-agent portability remain outside that test scope. See the [Oracle smoke evidence](IDENTITY_RELIABILITY_AUDIT.md). Swap Advisor work remains separate and on hold.


## Synthetic smoke test

From a clean checkout with Python 3.12 or 3.13, run the following in a temporary directory created by the shell. Use Bash. These names and quantities are synthetic test inputs.

```bash
scratch=$(mktemp -d)
trap 'rm -rf "$scratch"' EXIT
cat > "$scratch/oracle.json" <<'JSON'
{"data":{"Mountain":[{"name":"Mountain","types":["Land"],"supertypes":["Basic"],"colorIdentity":["R"],"manaValue":0}],"Fixture Bolt":[{"name":"Fixture Bolt","types":["Instant"],"colorIdentity":["R"],"manaCost":"{R}","manaValue":1,"text":"Fixture Bolt deals 2 damage to any target."}]}}
JSON
printf 'Name,Quantity\nFixture Bolt,5\n' > "$scratch/collection.csv"
printf '56 Mountain\n4 Fixture Bolt\n' > "$scratch/deck.txt"
oracle_pin=$(sha256sum "$scratch/oracle.json" | cut -d ' ' -f1)
gateway() {
  python tools/agent_gateway.py "$1" --oracle "$scratch/oracle.json" \
    --oracle-sha256 "$oracle_pin" --collection "$scratch/collection.csv" \
    --collection-scope synthetic "${@:2}"
}

python tools/agent_gateway.py doctor
gateway discover --theme damage
gateway validate --deck "$scratch/deck.txt" --exact-60
printf '55 Mountain\n5 Fixture Bolt\n' > "$scratch/deck.txt"
gateway validate --deck "$scratch/deck.txt" --exact-60
```

Expected results in order are `RUNTIME_COMPONENTS_PRESENT` (exit 0, downstream `NOT_EXECUTED`), `CANDIDATES_NOT_VALIDATED` (exit 0, child 0), `VALIDATED_WITH_LIMITATIONS` (exit 0, child 0), and `BLOCKED_INVALID_DECK` (exit 2, child 1). The last check isolates the copy limit because the synthetic inventory supplies five copies. The full upstream Oracle is allowed in synthetic mode with its exact file hash. A full upstream Oracle supplied to `doctor --oracle` will return `UNVERIFIED` unless its bytes match the frozen slim pin.
