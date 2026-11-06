# MTG Rules Sources and Source Precedence

This project **links to authoritative Magic: The Gathering rules** and records changes to source documents. It does not automatically copy the entire copyrighted Comprehensive Rules into GitHub.

## Primary sources

| Topic | Official source | Purpose |
|---|---|---|
| Comprehensive Rules (PDF and DOCX) | https://magic.wizards.com/en/rules | Rules and card interactions |
| Commander format | https://magic.wizards.com/en/formats/commander | Deck construction and format information |
| Banned & Restricted | https://magic.wizards.com/en/banned-restricted-list | Current format-specific legality |
| MTGJSON AtomicCards | https://mtgjson.com/api/v5/AtomicCards.json.gz | Oracle-related card facts, **not** a rules engine |

**Precedence:** Current official Wizards rules and format/banlist information first; MTGJSON for card data second; project-specific rules only within an explicitly agreed casual scope third. If sources conflict, report `UNVERIFIED`; never silently guess.

## Automated source monitoring

The workflow `.github/workflows/mtg-rules-check.yml` checks source pages every two months and also supports manual execution. It compares SHA-256 fingerprints of discoverable official documents and source pages with the tracked baseline. **Only raw HTML changes at the same recognized official page URLs** result in a green workflow with a prominent `HTML_ONLY_REVIEW_REQUIRED` warning in the Actions summary; this is **not** an automatic approval of current banlists or format rules, and the baseline remains unchanged until a separate reviewed PR. A changed/missing/new PDF/DOCX, changed source URL, missing verified baseline, corrupted source or failed official retrieval remains a **red blocking failure**. All detected differences are shown in the Actions summary. The workflow has read-only GitHub permissions and never commits or pushes. After checking whether changed fingerprints reflect actual rules or banlist changes, update `rules/manifest.json` and `rules/CHANGELOG.md` through a separately reviewed PR.

**Important:** A fingerprint change means **only** that the source content changed. It does not prove that a specific gameplay rule or banlist entry changed. The workflow does not automatically interpret changes, validate deck legality, or implement a rules engine. Consult the current official source.

## Commander and casual scope

See [Commander references](commander.md) and [House rules](house-rules.md). The house-rules document is a **template**, not a collection of approved custom rules.

## Legal and practical limits

Consult the official Comprehensive Rules on Wizards' website. The repository stores references, metadata, and project notes, not unauthorized full copies. Automated source retrieval may fail if upstream websites change their page structure or access policies; inspect the GitHub Actions logs.
