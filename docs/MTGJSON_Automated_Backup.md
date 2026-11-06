# MTGJSON AtomicCards: Official Upstream Verification

## MTGJSON acknowledgement and brand assets

**[Powered by MTGJSON](https://mtgjson.com)**

We appreciate the MTGJSON project and its contributors for providing the card data used by AI Deckbuilding Tool. This is an **independent** project, not affiliated with or endorsed by MTGJSON. Attribution is provided as a text link to MTGJSON. See the licensing and third-party notices below for attribution and redistribution boundaries.

The project verifies the **official MTGJSON AtomicCards v5 database** from MTGJSON's public API. It no longer republishes the data through our GitHub Releases. The existing historical private backup is retained until a separate owner-approved release cleanup is completed.

## Credits and license

MTGJSON is maintained by **Zach Halpern and contributors** and published under the [MIT license](https://mtgjson.com/license/). The original MTGJSON copyright notice is stored at [`third_party_licenses/MTGJSON-MIT.txt`](../third_party_licenses/MTGJSON-MIT.txt). MTGJSON's license does not independently grant the right to redistribute Wizards' third-party materials. See [Third-Party Notices](../THIRD_PARTY_NOTICES.md) and the [Public Release Checklist](PUBLIC_RELEASE_CHECKLIST.md).

## Authoritative upstream sources

- [AtomicCards.json.gz](https://mtgjson.com/api/v5/AtomicCards.json.gz)
- [AtomicCards.json.gz.sha256](https://mtgjson.com/api/v5/AtomicCards.json.gz.sha256)
- [Meta.json](https://mtgjson.com/api/v5/Meta.json)
- [Atomic card data model](https://mtgjson.com/data-models/card/card-atomic/)
- [MTGJSON license](https://mtgjson.com/license/)

## Actual schedule and operation

Workflow: [`.github/workflows/mtgjson-atomic-update.yml`](../.github/workflows/mtgjson-atomic-update.yml), displayed as **Verify upstream MTGJSON AtomicCards (no mirror)**. It runs on the first day of each month at 07:17 UTC, or via manual `workflow_dispatch`.

The workflow downloads `Meta.json`, the official SHA-256 checksum and `AtomicCards.json.gz` to **temporary GitHub Actions runner storage**. It verifies file size, digest, gzip/JSON structure, minimum card coverage and matching version metadata using [`scripts/update_mtgjson_atomic.py`](../scripts/update_mtgjson_atomic.py). The job summary records only the version, checksum and upstream URL.

**No dataset, source file or license file is uploaded as a new Release asset or committed to this repository.** The job token uses `contents: read`. Scheduled jobs may be delayed; inspect Action history for errors. The workflow has not yet been live-executed in its newly revised verification-only form.

## Historical backup (private, not used by the current workflow)

The earlier workflow on October 14, 2026 published Release `mtgjson-atomic-5.3.0+20261013` with `AtomicCards.json.gz`, `AtomicCards.json.gz.sha256` and `manifest.json`. This **existing private asset remains** for now, is not automatically modified, and must not be exposed by making the repository public without a separate rights/distribution review. Its existence does not mean the updated workflow still mirrors the data.

For offline validation, fetch the official database yourself from MTGJSON, or run:

```bash
python scripts/update_mtgjson_atomic.py --output-dir ./mtgjson-build
```

The local output folder is ignored by Git. GitHub does not synchronize MTGJSON with ChatGPT Projects. Do not commit personal collection CSVs or private deck inventory.


## Proposed monthly private DRAFT snapshot (isolated branch until approved)

The separate workflow [`mtgjson-private-draft-bundle.yml`](../.github/workflows/mtgjson-private-draft-bundle.yml)
is designed to run monthly on day 1 at 07:37 UTC, or by manual dispatch **only after this branch is merged**.
It is deliberately separate from the read-only verification workflow above.

It downloads and checks these exact official compressed data/checksum pairs:

| Dataset | Official compressed file | Official SHA-256 |
| --- | --- | --- |
| AtomicCards | [AtomicCards.json.gz](https://mtgjson.com/api/v5/AtomicCards.json.gz) | [AtomicCards.json.gz.sha256](https://mtgjson.com/api/v5/AtomicCards.json.gz.sha256) |
| Cards | [cards.csv.gz](https://mtgjson.com/api/v5/csv/cards.csv.gz) | [cards.csv.gz.sha256](https://mtgjson.com/api/v5/csv/cards.csv.gz.sha256) |
| Identifiers | [cardIdentifiers.csv.gz](https://mtgjson.com/api/v5/csv/cardIdentifiers.csv.gz) | [cardIdentifiers.csv.gz.sha256](https://mtgjson.com/api/v5/csv/cardIdentifiers.csv.gz.sha256) |
| Rulings | [cardRulings.csv.gz](https://mtgjson.com/api/v5/csv/cardRulings.csv.gz) | [cardRulings.csv.gz.sha256](https://mtgjson.com/api/v5/csv/cardRulings.csv.gz.sha256) |

Checks include official SHA-256, archive integrity, CSV headers/row counts and AtomicCards JSON content.
The script checks MTGJSON metadata before and after the download. This is **not** a proof
that all CSV data reflects the exact same instant as the AtomicCards JSON snapshot.

Only when all checks pass, and GitHub confirms the repository is **private**,
a GitHub Release is created as an **unpublished DRAFT** containing the four archives,
four checksum files, manifest and upstream license/third-party notices.

Assets belong together in one draft Release, not in a new Git-tracked folder.
No MTGJSON binaries or bulk CSV data are committed to Git. An existing draft with
matching manifest is left untouched; a different manifest under the same tag fails closed.
Publishing drafts, changing repository visibility, changing historical Releases or
promoting private beta components is not authorized by this mechanism.

**Rights and visibility warning:** MTGJSON MIT provenance does not clear all Wizards
and third-party content rights. Never publish the drafts or make this repository public
without a separate distribution review. The older 2026-10-14 private AtomicCards Release
is historical and is not overwritten or kept current by the new workflow.

### Retention policy (proposed, not yet active)

The draft-bundle workflow keeps the **two newest complete, checksum-verified private DRAFT Releases** created by the new `mtgjson-private-bundle-*` process. It leaves existing Releases with the same tag/checksum untouched and never creates duplicates for the same upstream version.

After the latest draft is uploaded, the workflow downloads its eleven assets again and compares **every byte** with the local verified staging copy. A read-only retention planner fetches all Release metadata, checks all managed Releases have complete assets, and protects the two newest. Before pruning, the Release list is fetched again and must match the original plan. Only validated, older draft IDs with the exact managed tag prefix may be deleted.

The **historical** `mtgjson-atomic-5.3.0+20261013` back-up and all other Releases are excluded; there may therefore be **two current bundles plus this protected historical archive**. A failed verification, missing asset, non-draft managed release, changed inventory, missing private-repo status or other ambiguity stops cleanup. No forced replacements, no deletion of branches or commits, and no public publishing. Automatic deletion is an irreversible GitHub Release removal, so the new workflow must pass offline and CI tests before activation.

The cleanup feature is proposed in draft PR #25, and does not run while unmerged.
