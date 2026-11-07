# Full AtomicCards runtime acceptance

The CLI is standard-library Python, independent of ChatGPT APIs. Any agent with a runnable checkout and the required file/network permissions can invoke it. Chat-only hosts cannot be certified as executable agents.

## Reproduce

```sh
python -m ai_deckbuilding_tool setup --cache-dir /private/atomic-cache
python scripts/full_atomic_acceptance.py --cache-dir /private/atomic-cache --offline
python -m unittest discover -s tests -p 'test_*.py' -v
python -m unittest discover -s integrations/forge/tests -p 'test_*.py' -v
python -m unittest discover -s integrations/commander-spellbook/tests -p 'test_*.py' -v
python scripts/check_workflows.py
python scripts/audit_public_history.py --repo . --strict
```

Run all three unittest commands under Python 3.12 and 3.13. The opt-in full test requires a genuinely verified official full snapshot; it cannot pass using the slim test Oracle. It generates synthetic ownership privately and emits only small provenance/check receipts, never card data. The test exercises discovery, valid/invalid decks, the confirmed-scope controller and stale-deck invalidation. It does not test strategic superiority.

## Observed official snapshot (2026-11-07)

- Version: `5.3.0+20261106`.
- Official archive SHA-256 and actual downloaded file SHA-256: `5ff3e5001c722a3f62f0decc162f9cfb0ade5bc6c8ac481ce3ef95d4fc8cf9f8`.
- Compressed bytes: 52,106,324; decompressed bytes: 162,855,301.
- Coverage: 35,479 names; 36,430 records.
- Clean online setup: exit 0, `RUNTIME_READY`, `DOWNLOADED_VERIFIED`.
- CLI discovery: exit 0, `CANDIDATES_NOT_VALIDATED`, Card Search child 0.
- Valid 60-card synthetic deck: exit 0, `VALIDATED_WITH_LIMITATIONS`, Validator child 0 / `PASS_WITH_LIMITATIONS`.
- 59 cards, five normal copies, unowned and unknown cards: CLI exit 2, `BLOCKED_INVALID_DECK`, child 1 / `FAIL`.
- Confirmed collection scope was separately exercised using synthetic ownership: exit 0, `VALIDATED_WITH_LIMITATIONS`.

These are dataset/runtime observations, not an accepted weekly pointer. The mutable upstream URL may serve different bytes later; every online setup independently rechecks official checksum/version. Local receipts provide integrity and recorded HTTPS provenance, not authentication against hostile same-user tampering. Offline use explicitly does not establish latest upstream freshness.

## Combined acceptance evidence

`python scripts/full_atomic_acceptance.py --cache-dir /private/atomic-cache --offline` exited 0 with `PASS_WITH_LIMITATIONS`. The controller reached `COMPLETE_WITH_EVIDENCE` through real discovery and validation replay; changing the deck produced `STALE` and removed the certificate. Online repeat setup exited 0 with `REUSED_VERIFIED`.

Python 3.12 and 3.13 each passed 358 core tests, 6 Forge offline integration tests and 23 Spellbook offline tests. Workflow policy checks passed. The reachable-history heuristic scan reported `NO_PATTERN_HITS`, 282 blobs, no skipped oversized objects; this is not a proof about secrets in unreachable objects or external assets. An independent read-only review found and prompted a fix for nonofficial redirects in the weekly updater; its new negative test passes.

Exact-head GitHub CI on integration head `885dcc01053cac795ef5a951550d62206b956879` passed: run `42380170108`, both Python jobs, workflow syntax and historical privacy scan. Its tree was independently compared with the tested local checkout and matched exactly.

## Weekly metadata policy

The workflow runs Sundays at 07:17 UTC and supports manual dispatch. It verifies full temporary upstream data and publishes only version/hash/coverage metadata through a reviewed PR. No archive is a Git object, Release asset or Actions artifact. The small pointer is initialized only by verified evidence; unchanged version/hash causes no new commit.

**Observed repository setting (2026-11-07):** The browser showed **Allow GitHub Actions to create and approve pull requests** unchecked. Default token permissions remain read-only. This is a confirmed blocker to automatic metadata PR creation; no permission setting was changed.

Settings requirement: Repository **Settings → Actions → General → Workflow permissions → Allow GitHub Actions to create and approve pull requests** must be enabled for `GITHUB_TOKEN` PR creation. Workflow job permissions alone cannot override this setting. A denied PR creation is an operational settings blocker, not successful publication. PRs created by `GITHUB_TOKEN` may not trigger other workflows automatically; review and explicitly run required checks before merging metadata updates.

## Retained boundaries

Frozen slim test pins, alternate Validator profiles and synthetic fixtures remain supported. Neither strategy selection nor automatic swaps are implemented in Python. Existing card identity ambiguity and ownership checks remain authoritative. Private exports are never committed; committed import tests contain invented cards/text. Full banlists, mana castability, gameplay and cross-platform AI reasoning equivalence remain unverified.
