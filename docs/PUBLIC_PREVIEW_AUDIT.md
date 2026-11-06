# Public preview verification record

## Public checkout tested on 2026-11-07

Baseline `ddcd4412c81db80b6c4caceb749220b932793b19` and the audit candidate were exercised locally on Linux with Python 3.12.14 and 3.13.5. The same results were observed on both interpreters. Commands ran from the repository root.

| Command | Baseline count / exit | Candidate count / exit |
| --- | ---: | ---: |
| `python -m unittest discover -s tests -p "test_*.py" -v` | 243 / 0 | 266 / 0 |
| `python -m unittest discover -s integrations/forge/tests -p "test_*.py" -v` | 6 / 0 | 6 / 0 |
| `python -m unittest discover -s integrations/commander-spellbook/tests -p "test_*.py" -v` | 23 / 0 | 23 / 0 |

These are suite totals. The root suite combines several kinds of coverage:

- **Behavioral units:** Search role and mechanic checks, subtype matching, face-name ambiguity, exact quantities, Validator rules checks and synthetic Oracle cases.
- **Integration:** Active Validator CLI in Casual and single-Commander mode, both deck parsers, and actual Gateway subprocess runs for discovery and structural validation. The Forge suite covers deck conversion. The Spellbook suite covers ingredient screening and salt reporting.
- **Security:** Missing runtime, nonzero child exit, timeout, output bounds, duplicate or invalid JSON, source changes and mismatches, symlinks, malformed collection input, and private workflow policy.
- **Integrity and documentation:** Exact source and example identities, repository links, Python syntax and English prompt directives. `sha256sum -c SHA256SUMS.txt` verifies the public checkout manifest. The local [CI checker](CI_MAINTENANCE.md) parses workflow YAML and checks Bash syntax, immutable Action pins, permissions, and Forge default deck digests.

Scope is synthetic. The offline runs do not cover the production Oracle, separate Project/frozen Validator binaries, live Forge gameplay, or the upstream Spellbook export. Hosted GitHub Actions evidence is tracked separately on the audit pull request.

## Historical private-source evidence

The following evidence was recorded in the original private repository and is retained for provenance. The run numbers are private references. They do not report results for the public preview branch.

| Coverage recorded at the time | Private Actions run |
| --- | --- |
| 41 root tests on Python 3.9, 3.12, and 3.13 (18 original Validator, 10 v1.1.1 safety, 6 MTGJSON updater, 7 rules monitor) | 38612536326 |
| 47 root tests on the same matrix, adding six repository-integrity checks for prompt language, example hashes, paths, links, and syntax | 38631408916 |
| 59 root tests and 14 Spellbook tests, workflow YAML validation, and a historical pattern scan (635 reachable objects, 147 blobs, no oversized skips or recognized matches) | 38638287867 |
| Private beta Prepare Validator merge before the CLI docstring correction | 41311187060 |
| Private beta v0.2 candidate and post-merge CI | 41315644860 and 41315700456 |

The historical October 15, 2026 Spellbook smoke used the upstream bulk export and reported detecting the Sanguine Bond and Exquisite Blood ingredients in a synthetic deck. This was an ingredient lookup. The historical Forge gameplay run predates the example directory rename. See the [private beta release record](releases/CASUAL_PRIVATE_BETA_v0.2_2026-11-01.md), [Validator audit](MTG_Validator_v1.1.1_Audit.md) and [publication checklist](PUBLIC_RELEASE_CHECKLIST.md) for historical scope and rollback context.
