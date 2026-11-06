# Public Release Readiness Checklist

**Status: PUBLIC_TEST_PREVIEW (source-only).** This is a historical/original-repository rights checklist, not a legal certification or stable-product acceptance. The original private repository, its Git history, binaries, card data and Actions records remain private. This new public source-only export excludes those assets. Credits and upstream license texts are recorded in [Third-Party Notices](../THIRD_PARTY_NOTICES.md).

## Project source and identity

- [x] Choose the [MIT license](../LICENSE) for independently authored AI Deckbuilding Tool material (Copyright (c) 2026 Dreadpool-87). Review any externally sourced material and historic contributions separately before publication; upstream GPL/MIT notices do not license those parts as our own.
- [ ] Keep the Wizards of the Coast unofficial Fan Content notice visible. Check the [Fan Content Policy](https://company.wizards.com/en/legal/fancontentpolicy), trademarks/logos, noncommercial conditions, and other third-party IP rights.
- [x] Execute the automated **reachable Git history** scanner with a full-depth checkout: run 38638287867 inspected **635 reachable objects and 147 blobs**, with zero recognised secret/path patterns and zero oversized skipped blobs.
- [ ] Conduct a **manual** review of historical content and all GitHub Releases, Actions logs and artifacts for private collections, secrets, credentials or restricted uploads. A heuristic scan is not a privacy guarantee; `.gitignore` never removes older commits.
- [ ] Review workflows, permissions, repository secrets and existing GitHub **Releases**, not just source files.

## Forge GPL binary

- [ ] Remove or explicitly resolve the **existing** `forge-runtime-2.0.15` Release; the new workflows download from the official Forge release and no longer create mirrored binaries. The old executable may become public if the repository's visibility changes.
- [ ] Retain the original Forge contributors' notices and the upstream [GNU GPLv3 license](https://github.com/Card-Forge/forge/blob/forge-2.0.15/LICENSE) and its [local preserved copy](../third_party_licenses/Forge-GPL-3.0.txt).
- [ ] Before redistributing the Forge binary publicly, verify access to the **Corresponding Source** for that exact published build (including applicable build scripts and dependencies). Provide source-acquisition directions **beside the binary** using a method compliant with [GPLv3 section 6](https://www.gnu.org/licenses/gpl.en.html#section6), and maintain that access as required.
- [ ] Pin the correct upstream tag and source: [forge-2.0.15](https://github.com/Card-Forge/forge/tree/forge-2.0.15). A version tag alone is not proof that every Corresponding Source requirement is met.
- [ ] If those obligations remain unresolved, **do not publicly redistribute this copied binary**. Consider having users download the original upstream release instead while keeping the Python integration separate.

## MTGJSON data in existing Releases

- [ ] Remove or explicitly resolve every **existing** `mtgjson-atomic-*` Release; the new workflow verifies directly from MTGJSON and no longer creates mirrored datasets. Older archived data may become publicly downloadable if repository visibility changes.
- [ ] Accompany publicly distributed covered MTGJSON materials with the upstream MIT copyright and permission notice, [Copyright © 2018 – Present, Zach Halpern](https://mtgjson.com/license/) and the [local MIT notice](../third_party_licenses/MTGJSON-MIT.txt). A license link in the source repository alone may be insufficient for a stand-alone downloaded archive.
- [ ] Check separately whether the distributed dataset contains material subject to Wizards or third-party rights; MIT licensing of the MTGJSON project does not establish every other permission.

## Commander Spellbook / other upstream projects

- [ ] Retain Commander Spellbook contributors' credit, and the backend MIT notice if third-party code is ever copied.
- [ ] Do not publish or mirror `variants.json.gz` without checking data-specific redistribution rights. Current code expects a local user download and does not re-host the snapshot.
- [ ] Do not present researched but unused tools as included dependencies or claimed authors of the local Python scripts.

## Final verification

- [ ] Run `python -m unittest discover -s tests -p "test_*.py" -v` and inspect GitHub Actions results. Preserve the original 41 regression tests and the six language-migration tests.
- [x] Current Forge and read-only MTGJSON verification workflows fetch directly from upstream. A separate workflow can create private, unpublished MTGJSON draft archives.
- [x] Run all 59 general regression tests and 14 separate Spellbook tests across Python 3.9/3.12/3.13, plus YAML workflow validation and full-history pattern scan (GitHub Actions run 38638287867).
- [ ] Review upstream licenses again whenever Forge versions, exported datasets or other dependencies change.
- [ ] Decide explicitly whether to make the repository public **only after** the binary, data and content redistribution checks above pass.

Attribution is respectful and necessary, but it is not a substitute for satisfying copyright and software-distribution conditions.

## Public source package requirements

- [ ] Confirm that the final archive provides the complete distributable project free of charge under MIT where the project has licensing authority. Include independently developed tools, prompts, instructions, tests, configuration, workflows and documentation.
- [ ] Confirm English public-facing content, reproducible setup and official upstream links. Retain the upstream notices and keep external inputs under their respective terms.
- [ ] Verify the archive manifest and exclude proprietary card databases, protected artwork, personal collections and decks, private evidence, historical Git metadata and unauthorized third-party binaries.

## Historical publication gates and future release reviews

- [x] Record the [project owner declaration](PROJECT_PROVENANCE.md) for independently developed contributions and retain separate upstream notices.
- [ ] Confirm the legal basis for the intended public project name, descriptive trademark references, disclaimer and retained functional card-language fixtures. Obtain written permission where required.
- [ ] Resolve any contribution-specific rights exception discovered during review.
- [ ] Obtain separate owner approval of the exact candidate before publication.

The historical mirrors, commit history and Actions records belong to the private source repository. They are outside this source-only export and must remain private.
