# Quickstart for any Python-capable AI agent

## Automatic preflight and validation entry point

Run from a local checkout with Python 3.12 or 3.13. No ChatGPT API, host path or proprietary SDK is required.

```sh
python -m ai_deckbuilding_tool setup
python -m ai_deckbuilding_tool discover --collection /private/current-export.csv --collection-confirmed --theme damage
# The AI selects strategy/cards/quantities/mana and writes candidate.txt.
python -m ai_deckbuilding_tool validate --collection /private/current-export.csv --collection-confirmed --deck /private/candidate.txt
```

`discover` and `validate` automatically prepare the official full AtomicCards cache when `--oracle` is omitted. Users need not download Oracle files or calculate hashes. Each online invocation checks current official metadata/checksum, verifies bytes and strict full JSON, and detects upstream drift. `setup` checks source pins before downloading. No data or collection is uploaded.

The default private cache is `~/.cache/ai-deckbuilding-tool/atomic`. Use `--cache-dir /private/cache` to select another private directory. Existing directories must be owned by the current user with POSIX permissions 0700. Verified archives are content-addressed; replacement is atomic. Interrupted or failed downloads never become accepted snapshots. Online failures do not silently reuse old data. Explicit `--offline` allows only intact previously verified data and reports that freshness was not checked.

Collections support comma/tab exports, common Name/Card Name and Quantity/Qty/Count columns, integral quantities including `5x`, and separate regular/foil counts. The known `QuantityX` TSV export treats blank/boolean Foil as a finish marker. Its unused descriptive text can contain legacy quotes; ownership fields still reject ambiguous input. Contradictory totals, fractions, missing counts and unknown formats fail closed. Original and normalized SHA-256 values are retained in `collection_import`; the input is never edited.

Set `--collection-confirmed` only after current-run confirmation. This is a caller declaration, not authenticated ownership. For synthetic fixtures use `--synthetic`; never relabel a private collection as synthetic. Basic lands follow the existing Validator policy. Exact 60 is the CLI default; use `--allow-over-60` for Casual 60+.

| CLI exit | Status | Required agent response |
| --- | --- | --- |
| 0 | RUNTIME_READY | Setup only; no deck validated |
| 0 | CANDIDATES_NOT_VALIDATED | AI constructs a complete candidate |
| 0 | VALIDATED_WITH_LIMITATIONS | Inspect `gateway.result.checks`, failures and uncertainties; report structural limits |
| 2 | BLOCKED_INVALID_DECK | AI revises the list and executes validation again |
| 2 | INPUT_ERROR | Correct arguments or current-run declaration |
| 3 | UNVERIFIED | Report exact reason; never claim validation |

Receipts include actual Gateway/child exit evidence, Oracle version/provenance/hash, collection hashes and deck hash. Evidence applies only to those bytes. A revised deck must be validated again. Neither the tools nor local receipts certify strategy, full legality, gameplay, ownership or protection against same-user tampering. Hosts without execution or permitted network/cache access must report `NOT_EXECUTED` and the blocker.

## Existing source profiles and controller

Explicit `--oracle` preserves the frozen slim profile and requires its exact historic pin for real collections. Full snapshots require `--oracle-receipt <setup receipt>` and the exact `--oracle-sha256` emitted by setup. The CLI handles these automatically when `--oracle` is omitted. Synthetic Oracle fixtures retain explicit hash support. The original Validator profiles and pins are unchanged.

The [Workflow Controller](AGENT_WORKFLOW_MVP.md) remains the stateful workflow API. Supply setup's `archive_path`, `sha256`, `receipt_path` as `oracle`, `oracle_sha256`, `oracle_receipt`. Its collection API accepts canonical `Name,Quantity`; use the CLI for export normalization. `prepare`, `submit`, `validate`, `review`, `finalize` require actual evidence and invalidate changed decks/sources. No Python command chooses cards or strategy.

## Synthetic smoke test

```sh
python -m unittest discover -s tests -p 'test_agent_cli.py' -v
python -m unittest discover -s tests -p 'test_runtime_setup.py' -v
```

These are offline synthetic tests, not certification of the live full database. The separate full acceptance command is documented in [runtime acceptance](FULL_ATOMIC_RUNTIME_ACCEPTANCE.md).
