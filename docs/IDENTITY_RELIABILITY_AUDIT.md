# Physical-card identity and execution audit

**Scope** Public test preview. Starting public `main` was `0fd38ab2846a0e4c575e6ecac947b006407f913b`. No open pull requests were found at preflight. The [baseline hosted push run](https://github.com/Dreadpool-87/ai-Deckbuilding-tool/actions/runs/42311552347) passed both Python matrices, workflow syntax and history privacy checks.

## Baseline and ownership boundaries

- Stable Builder v7.4 chooses the deck. Stable Tester v3.4.2 independently analyzes a frozen deck. They are AI prompts, not executable simulators. Neither prompt was changed here.
- Card Search narrows candidates. The active public Validator checks selected structural properties and per-deck ownership. The Gateway pins, stages and invokes the tools and reports bounded subprocess evidence. See the [authoritative source profiles](AGENT_SOURCE_COMPATIBILITY_P4.md) and [result contract](AGENT_RESULT_CONTRACT_V1.md).
- Historical Validator v1.1, frozen beta, and separately managed Project Sources are distinct. The previous public Validator at the start SHA and earlier public beta at `ddcd441` were both hashed from their actual Git blobs. External Project and frozen beta bytes were unavailable in this checkout and remain `NOT_TESTED`. See the [manual migration and rollback](CHATGPT_PROJECT_PRIVATE_BETA_SETUP.md#optional-manual-migration-from-project-v16).
- Commander Spellbook supplies ingredient evidence. Forge is a separate optional gameplay runtime. Neither establishes collection ownership.

## Reproductions and changes

| Finding | Root cause | Fix and evidence |
| --- | --- | --- |
| Delver front name rejected | Validator exact lookup missed the combined AtomicCards key. Comparing both face costs as alternative printings also made the combined record unsafe. | Resolve names before copy checks. Validate both face identities, then project the structural front. Same card passes with synthetic ownership against the official snapshot. |
| Mixed inventory labels could inflate search counts | Discovery added every recognized label, even front plus combined names of unknown overlap. | Quarantine mixed labels in shared coverage. Aggregate deck usage before enforcing physical ownership and copy limits. A back-face discovery match supplies no ownership. See `tests/test_physical_identity.py`. |
| Reversible basic entries shadow ordinary names | The official dataset includes records such as `Island // Island`, which presented a competing name claim for the distinct ordinary Basic. | Ignore the alias claim of corroborated identical-face reversible records. Keep the combined reversible entry unsupported. Tested against the full data and a synthetic regression. |
| Standalone duplicate Oracle keys overwritten | Validator used the default JSON mapping decoder. | Use the shared duplicate-key rejector in both loaders. Direct CLI exits 2. |
| Source pin for new dependency | Executing only the pinned top-level script would leave its helper outside the trust boundary. | Pin, stage and recheck the helper for discovery and default validation. Tests exercise launch, source mutation, missing Python, bounds, timeout, malformed and duplicate-key child JSON, bad hashes, symlinks, and input snapshots. |
| Ambiguous spaced ASCII marker | Both parsers already treat `4 x Lightning Bolt` as the literal name `x Lightning Bolt`. | Preserve existing grammar and X-prefixed names. Cross-parser regression covers attached ASCII and multiplication-sign markers, malformed counts, and literal names. |
| Hosted Forge summary echoed raw paths | Summary logged dispatch inputs even when validation failed. | Omit raw inputs from summary and label inputs as intentionally public. Valid hosted runs still publish selected decks and outputs in their short-lived artifacts. |

## Official data smoke

The [AtomicCards model](https://mtgjson.com/data-models/card/card-atomic/) documents a name-to-record-array mapping with explicit face fields. The official [AtomicCards.json.xz](https://mtgjson.com/api/v5/AtomicCards.json.xz) matched its [upstream checksum](https://mtgjson.com/api/v5/AtomicCards.json.xz.sha256). MTGJSON metadata was `5.3.0+20261106`, date `2026-11-06`, 35,479 names. No upstream dataset was added to Git.

| Bytes | SHA-256 |
| --- | --- |
| Downloaded XZ | `b29f7ffce51acefea9da1363484e7c53bfcb6f50a8c9f50eaa6de2ced7888e8a` |
| Decompressed JSON | `879ab16fb4545152a196e6d1828bbdebd937a0e970f766c14e2297cff40010d8` |
| Local `gzip -n -1` of the JSON, for Gateway input size | `95b4ce5482240b2da9ebc2065ccd3fe8165751b6d86973331071ddeecf66b907` |

Reproduce with a synthetic pool containing four Delvers (`Name,Quantity` header, `Delver of Secrets,4`) and a deck of four Delvers plus 56 Islands. Use the current Validator and baseline Validator with `--oracle AtomicCards.json.gz --collection synthetic.csv --deck synthetic.txt --exact-60`. Baseline exited 1 with `FAIL` for the missing short name. The current Validator exited 0 with `PASS_WITH_LIMITATIONS`, ownership `PASS`, 56 physical lands and four nonlands at mana value 1. Card Search found the combined card with four copies. An additional synthetic inventory row for four Ajani's Pridemates exercised punctuation and produced a real Gateway lifegain candidate. The Gateway `discover` and `validate` ran their children with exit 0 and returned `CANDIDATES_NOT_VALIDATED` and `VALIDATED_WITH_LIMITATIONS`. Use synthetic mode and the observed local gzip digest.

Separate direct Validator function calls against the same snapshot with synthetic ownership found these outcomes.

| Name | Layout / status | Structural observation |
| --- | --- | --- |
| Bala Ged Recovery | Modal DFC / `PASS_WITH_LIMITATIONS` | MV 3, reverse land excluded from physical lands |
| Fire // Ice | Split / `PASS_WITH_LIMITATIONS` | Combined MV 4 and separate printed costs |
| Brazen Borrower | Adventure / `PASS_WITH_LIMITATIONS` | MV 3 from the front, Adventure excluded from curve |
| Abigale, Poet Laureate | Prepare / `PASS_WITH_LIMITATIONS` | MV 3, Prepare audit `PASS` |
| Brisela, Voice of Nightmares | Meld / `FAIL` | Ambiguous claims, ownership unverified |
| Artist Alley | Planar/normal collision / `FAIL` | Ambiguous identity, ownership unverified |
| Insectile Aberration | Reverse face / `FAIL` | No legal physical name established by this input |
| X | Ordinary / `PASS_WITH_LIMITATIONS` | Preserved literal name, MV 2 |

The full upstream snapshot exercises synthetic ownership only. Gateway `doctor` exited 0 without an Oracle (local components ready, no child), and exited 3 with the full gzip (frozen slim pin mismatch, no child).

### Exact frozen slim profile

Two separate copies of `AtomicCards_slim_v2.json.gz` matched the Gateway's production pin in the [source record](AGENT_SOURCE_COMPATIBILITY_P4.md). The data is version `5.3.0+20261011`, slim 2.0, with 3,427 canonical names. The same hash was used in all slim tests.

- `doctor --oracle` returned `RUNTIME_COMPONENTS_PRESENT` (exit 0, no child).
- With synthetic ownership of four Brazen Borrowers and four Shocks, direct Card Search found four owned copies under the combined Adventure name. Gateway `discover --theme damage` returned Shock with four copies (`CANDIDATES_NOT_VALIDATED`, gateway/child 0/0).
- Gateway `validate` accepted a deck of four Brazen Borrowers and 56 Islands (`VALIDATED_WITH_LIMITATIONS`, 0/0, `FROZEN_SLIM_PIN`, four MV-3 nonlands). Direct checks against representative slim transform, split, Adventure, and Prepare pairs passed, including the Prepare audit for Bloodline Recollector. The snapshot contains no modal DFC, meld or flip records and does not contain Delver.
- The slim acceptance used synthetic ownership. Current-run user authorization and independently managed Project Validator bytes were outside the test. No slim snapshot was added to Git.

The structural scope follows the [Wizards rules reference](https://magic.wizards.com/en/rules) and [modal DFC rulings](https://magic.wizards.com/en/news/feature/kaldheim-release-notes-2021-01-22). Neither physical-land counts nor printed costs predict the availability or timing of the alternate side.

## Integration and security evidence

- Ran the documented offline suites and the [synthetic smoke](AGENT_QUICKSTART.md#synthetic-smoke-test). Baseline on each of Python 3.12.14 and 3.13.5 was 266 root, 6 Forge, 23 Spellbook. The final branch reached 279 root, 6 Forge, 23 Spellbook, with exit 0 for every suite on both versions.
- Ran `timeout 90s python integrations/commander-spellbook/tests/live_bulk_smoke.py` on the baseline. The [official export](https://json.commanderspellbook.com/variants.json.gz) version 7.3.6, timestamp `2026-11-06T22:11:42.450454+00:00`, archive SHA-256 `0ba813e9fb7f74ef139e0122844f2f8efadf5fb5da22858cd8566be7eb366556`, parsed 121,296 variants and matched the expected synthetic ingredient pair (exit 0). The final branch repeated the same live smoke on a subsequent 7.3.6 export, timestamp `2026-11-07T00:11:39.094648+00:00`, archive SHA-256 `fbafd28387f7bbb46fadeb97b1d3f2b269df73d702b582863e1ec5842f54a50d`. It again parsed 121,296 variants and matched the synthetic pair (exit 0). No Forge gameplay was executed.
- All seven workflows were reviewed. Checkout disables persisted credentials. The sole write-permission exception is the private draft backup with separate visibility checks. Custom Forge verifies cache/download size and SHA before extraction and passes dispatch data through quoted environment variables.
- Official upstream Git tags resolved to all five exact pins: checkout v6.1.0, setup-python v6.3.0, setup-java v4.9.1, cache v4.3.0 and upload-artifact v4.6.2. No pin changes. The [Python support policy](https://devguide.python.org/versions/) supports the existing 3.12 and 3.13 matrix.
- `python scripts/check_workflows.py` and `python scripts/audit_public_history.py --repo . --strict` check YAML/policy and reachable Git privacy patterns. Pattern checks are heuristic.

Review and rollback are independent of the experimental prompt comparison. If this code change is later accepted and a regression is found, revert the PR as a unit so the Validator, Card Search, helper, Gateway pins and manifest stay synchronized. GitHub does not change ChatGPT Project Sources.
