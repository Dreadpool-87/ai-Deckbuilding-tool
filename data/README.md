# MTGJSON data: weekly pointer and public slim snapshot

AI Deckbuilding Tool keeps the **full AtomicCards** database hosted by MTGJSON
and never stores it in Git history, GitHub Releases or Actions artifacts. The
frozen **slim** AllPrintings SQLite snapshot, however, is now distributed
publicly as a GitHub Release asset by explicit owner decision (see below).

Every Sunday at 07:17 UTC, the repository's
[official upstream verification workflow](../.github/workflows/mtgjson-atomic-update.yml)
downloads the full gzip archive temporarily, checks its official SHA-256 and JSON
structure, and checks that upstream metadata and the official checksum have not
changed during verification. The downloaded archive is deleted with the
temporary GitHub Actions runner and is **never committed or published**.

When the upstream version or compressed-file SHA-256 changes, the workflow
proposes a reviewable pull request containing only:

- `data/mtgjson_atomic_latest.json`, a tiny pointer with the official download
  URL, official checksum URL, version, SHA-256, verification time, and record counts
- The updated digest for that pointer in `SHA256SUMS.txt`

The first verified pointer was merged through PR #10. An unchanged Sunday
check produces no new commit or PR. The workflow also refreshes `origin/main`
before preparing a branch and again before proposing its PR. If another
maintainer has already merged the same version and hash, a delayed job exits
successfully without trying to create a duplicate PR. A verification superseded
by newer accepted metadata on `main` is likewise not published.
The verification timestamp comes from the verification job, not a delayed
publication job.

**Important:** `https://mtgjson.com/api/v5/AtomicCards.json.gz` is a mutable
`latest` URL, not an immutable version-specific download. A pointer records
what was verified at a specific time. If upstream changes afterward, the
previous pointer SHA-256 will no longer match the new download. A runtime
must verify the actual bytes it downloads and never silently accept a
mismatch. For newly downloaded latest data, check MTGJSON's official
`.sha256` file as well; the weekly pointer is an audit record, not a
replacement for live checksum verification.

## Public slim AllPrintings SQLite snapshot (policy change, 2026-11-13)

On 2026-11-13 the project owner changed the previous no-redistribution policy
for the frozen slim test database: the exact compressed snapshot
`AllPrintings_slim_07Nov.sqlite.xz` is published as a **GitHub Release asset**
of [release `allprintings-slim-20261107`](https://github.com/Dreadpool-87/ai-Deckbuilding-tool/releases/tag/allprintings-slim-20261107).

Download and verify:

```sh
gh release download allprintings-slim-20261107 --repo Dreadpool-87/ai-Deckbuilding-tool --pattern "AllPrintings_slim_07Nov.sqlite.xz*"
sha256sum -c AllPrintings_slim_07Nov.sqlite.xz.sha256
```

Expected SHA-256 of the compressed archive:

```text
9bc865c411a142801812e3df0d0ad1aed5cc792c055205592851b4b66c968af1
```

Facts and limits of this snapshot:

- Derived from MTGJSON AllPrintings **5.3.0+20261107** (2026-11-07); slim schema
  with `cards.printedName` and `facePrintedName` retained
- **Frozen**: it does not track upstream MTGJSON updates; the weekly pointer
  workflow above remains the freshness mechanism for AtomicCards
- The ~218 MB extracted SQLite file is intentionally **never committed to Git
  history**; the archive exists only as the Release asset
- The release carries the MTGJSON MIT license notice as an asset
  (`MTGJSON-MIT.txt`), satisfying the attribution condition of the
  [MTGJSON license](https://mtgjson.com/license/)

The Gateway retains this frozen **slim** test profile, while production
runtime setup separately supports the verified official **full AtomicCards**
database. The weekly pointer does not replace live upstream checksums.

**Permission prerequisite:** GitHub may require enabling
Settings → Actions → General → **Allow GitHub Actions to create and approve
pull requests**. Without it, the Sunday verification still runs but opening
the metadata PR may fail. The workflow never automatically merges it.

[MTGJSON upstream](https://mtgjson.com/api/v5/) ·
[MTGJSON license](https://mtgjson.com/license/)
