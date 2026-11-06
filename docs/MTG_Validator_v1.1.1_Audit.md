# AI Deckbuilding Tool: Independent Technical Audit (October 14, 2026)

## Scope

Reviewed: private repository settings, complete Git tree, six masterprompt backups, Validator v1.1 and new v1.1.1, discoverable regression tests, MTGJSON release, official rules source monitor, GitHub Actions, and documentation.

This is **not a full MTG rules-engine audit**, nor proof that every card interaction or Commander deck-construction exception is supported.

## Findings and corrections

1. The original v1.1 could return `PASS` with missing `types` or insufficient `colorIdentity` data and did not detect contradictory `leadershipSkills` variants. These cases were reproduced with synthetic inputs.
2. The original regression test filename `test_MTG_Deck_Validator_v1.1.py` was skipped by Python's `unittest discover`. Tests are now available under `tests/test_validator_v1_1_original.py`; the undiscoverable duplicate was removed.
3. Validator **v1.1 was originally preserved byte-for-byte** for historical and reproducible use. The separate `validator/MTG_Deck_Validator_v1.1.1.py` handles missing or conflicting Oracle data more conservatively, returning `UNVERIFIED` where appropriate for card types, Commander color identity, leadership skills, and Basic-land copy/ownership exceptions.
4. `actions/checkout@v4` and `actions/setup-python@v5` were upgraded to **v6** for Node.js 24 compatibility; the runner was pinned to `ubuntu-24.04`. Tests are also triggered by changes under `scripts/`.
5. The former MTGJSON guide referred to an obsolete workflow, incorrect schedule, and incorrect Release asset. It was corrected against the actual implementation.
6. All six masterprompt backups were compared again with saved source files. A real inconsistency in the v7.3 backup (internal version v7.2 rather than v7.3) was corrected. At the time of that verification, all **six Git blob SHA-1 hashes matched their saved source files byte-for-byte**, including the final newline.
7. `.gitignore` excludes local collection CSVs, AtomicCards archives, data directories, and common sensitive files. Previously committed history was not rewritten.

## Verification performed

- **41 of 41 tests PASS on Python 3.9, 3.12, and 3.13** in GitHub Actions: run 38612536326 (historical private reference).
  - 18 original validator regression tests.
  - 10 additional v1.1.1 safety tests.
  - 6 MTGJSON updater regression tests.
  - 7 rules source monitor regression tests.
- Additional offline integration test with two example decks using both `AtomicCards.json.gz` and `AtomicCards_slim_v2.json.gz`, version `5.3.0+20261011`: both decks contained 60 cards and 21 physical lands, resolved all Oracle names, and returned `PASS_WITH_LIMITATIONS` with **synthetically sufficient ownership**. This was **not a check against the actual collection CSV**, nor against the later private GitHub Release.
- CLI smoke tests for **v1.1.1** with both available AtomicCards archives: casual Mono-Red v7.3 and a simple single-commander Lathliss, Dragon Queen deck produced exit code 0 and `PASS_WITH_LIMITATIONS`, using a **synthetic test collection**.
- MTGJSON workflow: first successful online download and Release publication; assets included `AtomicCards.json.gz`, `AtomicCards.json.gz.sha256`, and `manifest.json`.
- Official MTG rules monitoring: first online baseline was successful; `rules/manifest.json` recorded checksums for Wizards pages and rules documents.
- The repository was **Private**. The entire current Git tree was examined; no personal collection CSVs or large AtomicCards archives were in the then-current Git tree. This does not establish what is present in every historical commit.

## Not verified by this audit

- The **updated** scheduled MTGJSON and rules-monitoring workflows were not rerun after migrating to `actions/checkout@v6` and `actions/setup-python@v6`. CI for these versions was successful, but the two scheduled workflows still need separate live confirmation.
- No complete deck legality validation against dynamic banlists, card-text construction exceptions, mana production, gameplay, win rates, unusual multi-commander cases, or cross-deck physical allocation.
- No independent Oracle verification of every MTGJSON card in the newer Release beyond the checks performed.
- GitHub Releases and ChatGPT Projects do not synchronize automatically.

## Recommendation

Use **Validator v1.1.1** for new checks with an up-to-date local AtomicCards database, explicitly respecting the `NOT_CHECKED` categories. Keep v1.1 for reproducibility. After workflow changes, manually run each scheduled job once via GitHub Actions. Keep stable Builder v7.3 without unsolicited substantive prompt edits.

## Subsequent changes (separate from this historical audit)

- Later on October 14, 2026, Forge 2.0.15 ran **one actual headless AI-vs-AI game** with both original example decks: run 38623719565 (historical private reference). This does not retrospectively expand the original validator audit or establish a matchup win rate.
- The experimental Commander Spellbook ingredient-screening tool was later added with 14 isolated synthetic tests. No live official bulk-data match has been confirmed.
- **English-language migration:** Six masterprompts received targeted language-instruction changes from Dutch output to English output, as expressly requested by the owner. The prior byte-identical archived copies remain recoverable through Git history, but the current prompt files are **no longer byte-identical** to those copies. Other prompt behavior was intentionally left unchanged. The original validator executables were not rewritten.
