# Verified MTGJSON AtomicCards pointer

AI Deckbuilding Tool **does not redistribute MTGJSON card archives**. The full
AtomicCards database remains hosted by MTGJSON.

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

The pointer is created on the **first successful run after activation**, once
the generated pull request is merged. No fictitious digest is supplied before
that happens. An unchanged Sunday check produces no new commit or PR.

**Important:** `https://mtgjson.com/api/v5/AtomicCards.json.gz` is a mutable
`latest` URL, not an immutable version-specific download. A pointer records
what was verified at a specific time. If upstream changes afterward, the
previous pointer SHA-256 will no longer match the new download. A runtime
must verify the actual bytes it downloads and never silently accept a
mismatch. For newly downloaded latest data, check MTGJSON's official
`.sha256` file as well; the weekly pointer is an audit record, not a
replacement for live checksum verification.

The Gateway's existing pinned **slim** test Oracle profile is unchanged by
this metadata-only workflow. Supporting verified **full AtomicCards** in the
real-collection Gateway is a separate runtime integration task.

**Permission prerequisite:** GitHub may require enabling
Settings → Actions → General → **Allow GitHub Actions to create and approve
pull requests**. Without it, the Sunday verification still runs but opening
the metadata PR may fail. The workflow never automatically merges it.

[MTGJSON upstream](https://mtgjson.com/api/v5/) ·
[MTGJSON license](https://mtgjson.com/license/)
