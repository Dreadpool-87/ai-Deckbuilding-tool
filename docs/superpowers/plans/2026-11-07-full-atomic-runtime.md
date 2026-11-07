# Verified AtomicCards Runtime Implementation Plan

Goal: Any Python-capable agent can prepare official AtomicCards and validate its own deck without manual dataset or checksum preparation.

Architecture: Retain the pinned Gateway and Workflow controller. Add a standard-library AtomicCards integrity helper, private content-addressed cache and collection normalizer. Extend the existing runner rather than adding strategic selection.

Constraints: Python 3.12/3.13; no redistribution; synthetic ownership only in committed tests; frozen slim remains supported; source pins stay mandatory.

- [ ] Test and implement bounded official download, strict gzip/JSON verification, upstream drift detection, private atomic cache and offline verified reuse.
- [ ] Test and implement CSV/TSV normalization retaining the original digest; reject ambiguous quantities.
- [ ] Extend Gateway with an explicit official snapshot receipt, verified against exact bytes; stage and pin helper code in runner/controller. Preserve synthetic/slim profiles.
- [ ] Add automatic setup to runner and support full snapshot configuration in controller. Record provenance and actual child evidence.
- [ ] Run negative tests, real full-data discovery/validation, complete 3.12/3.13 suites, workflows and history scan.
- [ ] Publish focused PR and merge dependency PRs only after reviewed evidence is green; report any live workflow/settings blocker honestly.

Review focus: mutable upstream; partial download; symlink/cache corruption; contradictory collection quantities; changed deck invalidating earlier evidence. Local receipts are integrity records, not signatures against same-user tampering.
