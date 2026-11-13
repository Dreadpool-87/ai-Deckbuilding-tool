# Third-Party Credits, Licenses and Provenance

AI Deckbuilding Tool is an **independent, unofficial** Magic: The Gathering fan project. The following creators retain credit and rights to their respective work. Referencing them does **not** mean that they endorse this project, that their software is owned by AI Deckbuilding Tool, or that our independently written Python modules inherit their licenses.

## Forge: Card-Forge contributors

- **Creators and maintainers:** [Card-Forge/forge](https://github.com/Card-Forge/forge) and the Forge contributors.
- **Used here:** the updated opt-in workflows fetch the **unmodified Forge 2.0.15 desktop binary directly from Card-Forge**, verify its checksum and invoke its headless CLI. No new binary is redistributed as a GitHub Release; an **older private Release** still contains a historical copy and must be removed or reviewed before making the repository public. No Forge Java source is incorporated into the Python validator or adapter.
- **Source and provenance:** [2.0.15 release](https://github.com/Card-Forge/forge/releases/tag/forge-2.0.15), [corresponding source tag](https://github.com/Card-Forge/forge/tree/forge-2.0.15), [upstream license](https://github.com/Card-Forge/forge/blob/forge-2.0.15/LICENSE).
- **License:** GNU General Public License v3 (GPLv3). [Local copy of upstream GPLv3 text](third_party_licenses/Forge-GPL-3.0.txt). Copyright notices in the original upstream package remain with their authors.
- **If publicly distributing the executable:** GPLv3 sections 4 and 6 impose conditions beyond credit. The exact **Corresponding Source**, relevant copyright/license notices and clear source-acquisition directions must be available under a compliant method. A link to an upstream homepage and an unchanged binary are not, by themselves, proof of GPL compliance. Check the corresponding build source and dependencies.

## MTGJSON: Zach Halpern and contributors

- **Creators and maintainers:** [MTGJSON](https://mtgjson.com/) and its contributors.
- **Used here:** official [AtomicCards](https://mtgjson.com/api/v5/AtomicCards.json.gz) data, fetched and verified from upstream on temporary CI runners, via the read-only verification workflow. An older private archived dataset Release still exists and requires cleanup or rights review before publication.
- **Also used here:** the frozen slim AllPrintings SQLite snapshot derived from MTGJSON AllPrintings 5.3.0+20261107. By explicit owner decision (2026-11-13) this exact compressed archive (`AllPrintings_slim_07Nov.sqlite.xz`, SHA-256 `9bc865c411a142801812e3df0d0ad1aed5cc792c055205592851b4b66c968af1`) is publicly redistributed as a Release asset of the public repository, together with its checksum sidecar and a copy of the MTGJSON MIT notice (`MTGJSON-MIT.txt`), satisfying the attribution condition above. The extracted database is never committed to Git history.
- **Official license:** [MTGJSON License](https://mtgjson.com/license/) (MIT); [local copy of the MIT notice](third_party_licenses/MTGJSON-MIT.txt); **Copyright © 2018 – Present, Zach Halpern**.
- **License notice:** The MIT terms require keeping the original copyright and permission notice with copies or substantial portions of covered material. Before publishing or re-hosting AtomicCards data, ensure the applicable notice accompanies the **release asset itself**. Existing Releases need review.
- **Rights distinction:** MTGJSON's MIT license does not grant ownership of Wizards of the Coast trademarks, card artwork or other independently protected material.

## Commander Spellbook: Commander Spellbook contributors

- **Creators and maintainers:** [Commander Spellbook](https://commanderspellbook.com/) and [its backend contributors](https://github.com/SpaceCowMedia/commander-spellbook-backend).
- **Used here:** an independently written **offline ingredient-screening tool** reads a user-downloaded bulk export in the documented format. No Spellbook backend code or bulk export is committed to this repository.
- **Backend license:** [MIT](https://github.com/SpaceCowMedia/commander-spellbook-backend/blob/master/LICENSE); [local copy of the MIT notice](third_party_licenses/Commander-Spellbook-MIT.txt); **Copyright (c) 2023 Commander-Spellbook**.
- **Data distinction:** Do not assume that the backend's software license automatically grants all rights to republish the separate `variants.json.gz` dataset. Check the data terms before any future redistribution.

## License notices attached by updated release workflows

Current Forge workflows and read-only MTGJSON verification fetch upstream directly. A separate workflow can create private MTGJSON draft archives. Earlier private Forge and MTGJSON Releases remain in the repository and are not retroactively changed. Remove them or resolve all distribution obligations **before** making the repository public. Their saved license texts in `third_party_licenses/` are attribution, not proof that publishing the old assets is permissible.

## Wizards of the Coast and Magic: The Gathering

*Magic: The Gathering* and related names, card content, trademarks, artwork and other protected materials belong to their respective rights holders, including **Wizards of the Coast LLC**. This project does not claim their ownership or official approval.

> This project is unofficial and is not affiliated with, sponsored by, or endorsed by Wizards of the Coast. Magic: The Gathering is a trademark of Wizards of the Coast and identifies the compatible game.

Official sources: [Wizards Fan Content Policy](https://company.wizards.com/en/legal/fancontentpolicy), [Magic rules](https://magic.wizards.com/en/rules) and [Wizards Terms](https://company.wizards.com/en/legal/terms). Review these before publishing, especially rules for logos, trademarks, licensed material and commercial use. Crediting a rights holder is not an independent grant of permission.

## Research references, not bundled dependencies

These projects were **researched but not incorporated** into this repository. No source code was copied from them; these are acknowledgements, not claims that they contributed our implementation:

- [svarozhych/card-deck-mtg](https://github.com/svarozhych/card-deck-mtg), an examined deck-management application. No root license file was verified, so we make no claim about reuse permission.
- [MagicTheGathering/mtg-sdk-python](https://github.com/MagicTheGathering/mtg-sdk-python), an examined API client. Its [MIT license](https://github.com/MagicTheGathering/mtg-sdk-python/blob/master/LICENSE.txt) credits **Andrew Backes**.

## Project license and public visibility

See the [project owner declaration](docs/PROJECT_PROVENANCE.md) for the development record and the scope of the owner’s statement.

**Project license:** [MIT](LICENSE), Copyright (c) 2026 Dreadpool-87, applies to independently authored AI Deckbuilding Tool code and documentation only to the extent the owner holds rights to grant that license. Third-party software, data, trademarks, copyright notices and archival material that belongs to others are excluded from this grant and remain governed by their own terms. The GPL for Forge and MIT licenses for other projects are separate; the root MIT license does **not** override them.

See [Public Release Readiness Checklist](docs/PUBLIC_RELEASE_CHECKLIST.md). Public GitHub visibility may expose **existing GitHub Release assets**, so the distribution review must include those assets and not merely the files tracked in Git.

## Controlled private MTGJSON draft snapshots

The isolated `mtgjson-private-draft-bundle.yml` workflow stages four checksum-verified MTGJSON archives with their official SHA-256 files in a single **private, unpublished DRAFT** GitHub Release per upstream version. It refuses to run if the repository is public and includes the original MIT notice and these third-party notices as downloadable assets. This changes the previous *no new dataset mirror* practice only for owner-controlled private draft backups; it does not authorize public distribution. (The 2026-11-13 public redistribution of the frozen slim AllPrintings snapshot is a separate, explicit owner decision documented above and in `data/README.md`; it does not change the private-draft policy for AtomicCards archives.) The existing read-only upstream verification workflow remains unchanged. Do not publish these drafts or change repo visibility without separate rights review.
