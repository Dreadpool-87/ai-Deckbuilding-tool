# MTGJSON data: weekly pointer and public slim snapshot

AI Deckbuilding Tool keeps the **full AtomicCards** database hosted by MTGJSON
and never stores it in Git history, GitHub Releases or Actions artifacts. The frozen slim AllPrintings SQLite snapshot is also **not currently publicly distributed** by this repository; the earlier public Release was removed pending a third-party rights review.

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

## Frozen slim AllPrintings SQLite snapshot (distribution pending rights review)

The previous public Release `allprintings-slim-20261107` was removed. **Do not rely on its former URL or use `gh release download` against it.** No public download of the frozen slim snapshot is currently provided by this repository. Publishing the archive again requires a separate review of rights in Wizards of the Coast card text; the MTGJSON MIT notice alone is not proof of those rights.

Recorded identification for the **unpublished** archive:

- Filename: `AllPrintings_slim_07Nov.sqlite.xz`
- Source: MTGJSON AllPrintings 5.3.0+20261107, frozen slim schema (including `cards.printedName` and `facePrintedName`)
- Expected compressed size: **45,020,048 bytes**
- Expected compressed SHA-256: `9bc865c411a142801812e3df0d0ad1aed5cc792c055205592851b4b66c968af1`
- Extracted SQLite: approximately 218 MiB; never commit it to Git history

These recorded values identify the historical archive; they are **not a verification of a currently downloadable public asset**. If an authorized user already has the archive locally, they can verify it using `sha256sum AllPrintings_slim_07Nov.sqlite.xz` and compare the output to the expected digest above. Do not substitute a different MTGJSON version and assume the same checksum.

For a publicly accessible upstream data source, use the official [MTGJSON API](https://mtgjson.com/api/v5/) and verify each downloaded archive against its matching official checksum. The weekly AtomicCards pointer is an audit record, not a stable archived download. The Gateway's frozen slim test profile is distinct from the verified official full AtomicCards setup.

**Permission prerequisite:** GitHub may require enabling
Settings → Actions → General → **Allow GitHub Actions to create and approve
pull requests**. Without it, the Sunday verification still runs but opening
the metadata PR may fail. The workflow never automatically merges it.

[MTGJSON upstream](https://mtgjson.com/api/v5/) ·
[MTGJSON license](https://mtgjson.com/license/)
