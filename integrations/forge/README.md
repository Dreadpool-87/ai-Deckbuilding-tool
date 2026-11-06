# Forge Integration (Experimental, Upstream-Only Runtime)

Forge is the independent **Card-Forge** open-source MTG rules engine, distributed under GPLv3. This repository runs its unmodified Java CLI using separate Python scripts, without vendoring the runtime in Git or creating any **new** Forge binary Releases. See [third-party credits](../../THIRD_PARTY_NOTICES.md), [GPLv3 notice](../../third_party_licenses/Forge-GPL-3.0.txt), and [public release checklist](../../docs/PUBLIC_RELEASE_CHECKLIST.md).

## Runtime acquisition

- Upstream release: https://github.com/Card-Forge/forge/releases/tag/forge-2.0.15
- Matching source: https://github.com/Card-Forge/forge/tree/forge-2.0.15
- Release archive: https://github.com/Card-Forge/forge/releases/download/forge-2.0.15/forge-installer-2.0.15.tar.bz2
- Expected SHA-256: `4468f182b60f6ca62d89697baa208981085af744f116781af751c611826db600`
- Expected compressed size: `297081149` bytes
- Metadata: [`forge-version.json`](forge-version.json)
- CLI documentation: https://github.com/Card-Forge/forge/blob/forge-2.0.15/docs/AI.md

The [manual Forge verification workflow](../../.github/workflows/forge-runtime-download.yml) checks the **official archive** directly and does not publish or upload it. The [manual one-game smoke workflow](../../.github/workflows/forge-smoke.yml) also fetches upstream directly, checks size and SHA-256, extracts Forge into temporary runner storage and invokes `sim` with Java 21. Both workflows operate with read-only GitHub permissions.

## Isolated integration files

- `scripts/convert_decks.py`: converts the two unchanged tracked decks under `examples/` into temporary Forge `.dck` files with SHA-256 and card-count verification.
- `scripts/run_poc.py`: runs **one actual headless AI-vs-AI game** and captures stdout, stderr, exit code, duration, game outcome and error signatures. Forge may report a draw after an internal exception or timeout; the parser treats those error conditions separately.
- `forge-version.json`: pinned upstream version, digest and archive size.
- `forge-poc-output/`: temporary output; ignored by Git. GitHub Action artifacts retain logs for seven days.
- No new local binary Releases are created.

## Execution evidence and scope

**Smoke inputs:** The bundled decks are synthetic technical fixtures.

The revised upstream-only smoke workflow has **NOT EXECUTED** a game yet. The original Mono-Red Elemental Burn v7.3.1 from Independent Deck Comparison Test 8.0 is not one of the tracked examples. No full ten-game batch, verified alternating first player, or dependable matchup win rate has been implemented. The runner is a technical proof of concept, not a finished benchmark.

## Publication and existing binary

The old private Release `forge-runtime-2.0.15` still contains the 297 MB upstream executable and is **not used by the current workflows**. Before switching repository visibility to public, that old Release must be deleted or its GPL source/distribution obligations fully addressed. Repository visibility changes can expose pre-existing Release assets. The GPLv3 obligations for a re-hosted Forge binary are separate from the MIT license on our independently authored Python files. Do not publish copied binaries by accident.
