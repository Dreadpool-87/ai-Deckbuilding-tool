# Reusable Forge custom-deck integration (experimental)

This is an opt-in, manually dispatched one-game smoke test, not a deck optimizer or statistical tester.

## Sources and privacy

On the public preview, use checked-in synthetic 60-card plaintext decklists as UTF-8 `<quantity> <exact card name>` rows. GitHub Actions logs and uploaded evidence can expose both decklists. Keep personal decklists and collections out of the public repository and its workflow inputs. Example:
`integrations/forge/decks/Synthetic_Green.txt` vs `examples/Synthetic_Red_B.txt`.

Future Project decklists need only a new `.txt` source file and its SHA-256: **no Python or workflow edits**. The collection CSV and MTGJSON reference stay outside GitHub. Source ownership validation is the responsibility of the ChatGPT Builder/Tester before the list is confirmed. Forge validates gameplay, not collection ownership.

## How to run (requires separate authorization)

1. Confirm both complete source lists and calculate SHA-256 from exact source bytes.
2. Select **Actions > Forge custom 60-card AI-vs-AI smoke > Run workflow** on a branch containing the workflow. Note: GitHub may require the workflow to exist on the default branch before manual dispatch is available.
3. Enter repository-relative paths, both exact SHA-256 values and seed. Exactly **one** constructed game is run. No large batch.
4. Review uploaded `forge-custom-output` evidence, including source and .dck hashes, `result.json`, `stdout.log`, `stderr.log` and pinned Forge metadata.
5. Treat `BLOCKED`, `INCOMPLETE`, `CRASH` and `TIMEOUT` as **zero** valid completed games.

The original `forge-smoke.yml`, `convert_decks.py`, Mono-Red examples and their behavior are retained. Forge 2.0.15 comes from Card-Forge upstream. The custom workflow caches the release archive and verifies its size and SHA-256 on every run before extracting a fresh runtime. Forge binaries stay out of the uploaded evidence artifacts.

## Verification boundaries

The converter proves source-to-.dck equality, not Forge card support. The Forge CLI's actual deck loading and stdout/stderr are required for gameplay evidence. The runner rejects recognized missing-card/deck-load errors, exceptions and timeouts. A successful process exit alone does not prove game completion. This version does **not** independently verify every card's rules implementation; unknown card errors that Forge does not expose may remain undetected. Starting player and turn count are recorded as null unless future verified parsing is added. Seed is recorded, but deterministic replay is not guaranteed.

## Offline tests

`python3 -m unittest discover -s integrations/forge/tests -v`

Tests require no Forge binary, do not start gameplay and do not modify source decks.
