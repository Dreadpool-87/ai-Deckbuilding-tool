# AI Deckbuilding Tool

AI Deckbuilding Tool is an independent, free, open-source project for AI-assisted deckbuilding, deck analysis, and validation for Magic: The Gathering.

**Public repository:** `Dreadpool-87/ai-Deckbuilding-tool`. **Status:** `PUBLIC_TEST_PREVIEW` (experimental source release; no strategic acceptance or automatic swaps).

> **Experimental Agent Gateway:** Start with [AGENTS.md](AGENTS.md), the [Python quickstart](docs/AGENT_QUICKSTART.md), and the [integration roadmap](docs/AGENT_INTEGRATION_ROADMAP.md). These guides do **not** change the stable Builder/Validator/Tester, establish a new runtime, or authorize Swap Advisor integration.

> **Current project status (1 November 2026):** [PROJECT_STATUS.md](PROJECT_STATUS.md) describes the scoped **[Casual Private Beta v0.2](docs/releases/CASUAL_PRIVATE_BETA_v0.2_2026-11-01.md)**, the supported Builder/Validator/Tester workflow, previous frozen beta checkpoint (historical private reference), sanitized test history (historical private reference), and AI roadmap (historical private reference). **The original beta was private; the source is now public for experimental testing, not stable release. No automatic Project sync.**

> **Active Casual status:** `ACTIVE_PRIVATE_BETA` / `PASS_WITH_LIMITATIONS`; **Historical private beta v0.2** covered stable Builder v7.4, the SHA-pinned Prepare Validator in the historical private `main` (`validator/MTG_Deck_Validator_v1.1.1.py`, SHA-256 `f8e915a95e73e20edf59267dfe39e45f82d62bb5eb49fd4eb180194189d995ef`), and unchanged Tester v3.4.2. The Validator changed from `c422295676d0bad04aa1449725b07a7c11bf58b7990a34aff209e10ba742ac8d` **only in the docstring's outdated CLI usage example**. **ChatGPT Project Instructions v1.6 still select the separately managed earlier Prepare Source** (`MTG_Deck_Validator_v1.1.1_PREPARE_COLOR_INTEGRITY_CANDIDATE.py`, SHA-256 `c422295676d0bad04aa1449725b07a7c11bf58b7990a34aff209e10ba742ac8d`) until explicitly updated. Previous beta rollback `release/casual-private-beta-2026-10-22` retains SHA-256 `8749b50d0aeaa52124a99271a0ab40bcc979350c6e8b5e9074c4f28d63a3d1ac`; historical Project rollback retains SHA-256 `0d296f69a465bdaf5d967d2155460bbe69bb3d653f58952468d45713d2f9db8e`. **Verify full hashes; matching filenames alone prove nothing.**

**[Powered by MTGJSON](https://mtgjson.com)**

AI Deckbuilding Tool uses [MTGJSON](https://mtgjson.com) as a core source of Magic: The Gathering card data. We gratefully credit the MTGJSON maintainers and contributors. This independent project is **not affiliated with or endorsed by MTGJSON**. See [third-party notices](THIRD_PARTY_NOTICES.md) and the [official brand assets](https://mtgjson.com/brand-assets/).

Open-source collection of tools for **Magic: The Gathering** deckbuilding, validation, research, and experimental rules-aware gameplay. **The historically accepted private beta v0.2 was Casual-only**, documented in [its release record](docs/releases/CASUAL_PRIVATE_BETA_v0.2_2026-11-01.md). The original private repository `main` used Prepare Color Integrity Validator v1.1.1, SHA-256 `f8e915a95e73e20edf59267dfe39e45f82d62bb5eb49fd4eb180194189d995ef`; the earlier `c422295676d0bad04aa1449725b07a7c11bf58b7990a34aff209e10ba742ac8d` Prepare source remains selected in ChatGPT Project Instructions v1.6 pending separate Project update. The frozen beta branch and original v1.1 remain historical. This is not proof of full rules-engine support, actual win rate, or stable quality.

**Language policy:** All project content and agent outputs use **English**. Official card names and technical identifiers are preserved.

## Credits, licenses and potential public release

**Public source status: PUBLIC_TEST_PREVIEW.** The original Casual v0.2 private-beta acceptance remains historical and is not a public product-stability endorsement. The experimental Gateway provides `doctor`, `discover` and `validate`, with synthetic acceptance on `04124cd7`. Forge gameplay and Forge Lite remain experimental. Swap Advisor is separate and on hold. Historical Release assets and repository history require review before changing visibility.

This is an independent project. **Forge** (Card-Forge contributors), **MTGJSON** (Zach Halpern and contributors), **Commander Spellbook** (its contributors) and **Wizards of the Coast** retain their respective rights. Attribution does not imply endorsement.

> This project is unofficial and is not affiliated with, sponsored by, or endorsed by Wizards of the Coast. Magic: The Gathering is a trademark of Wizards of the Coast and identifies the compatible game.

Read [**Third-Party Credits, Licenses and Provenance**](THIRD_PARTY_NOTICES.md) and the [**Public Release Readiness Checklist**](docs/PUBLIC_RELEASE_CHECKLIST.md) **before publishing this source. Historical releases in the original private repository contain Forge binaries and MTGJSON data. Those assets are outside this candidate and have separate redistribution requirements.

**License for independently authored AI Deckbuilding Tool material:** [MIT](LICENSE), Copyright (c) 2026 Dreadpool-87. This permission applies only to material the project owner has rights to license. It does **not** relicense Forge, MTGJSON, Commander Spellbook code/data, Wizards of the Coast material or other third-party contributions. See [Third-Party Notices](THIRD_PARTY_NOTICES.md) and the [project owner declaration](docs/PROJECT_PROVENANCE.md).

## Open-source distribution

The public source preview is free of charge and includes the complete distributable project source. It includes the independently developed Python tools, Agent Gateway, Builder and Tester prompts and instructions, Validators, tests, configuration, workflows, and English documentation. The MIT license applies to those materials where the project has the right to grant it. Free access to this distribution adds no restriction to the rights granted by MIT.

Forge, MTGJSON, Commander Spellbook, and other external dependencies retain their own licenses. Wizards of the Coast retains its rights in Magic: The Gathering materials. The source archive excludes proprietary card databases, protected artwork, personal collections and decks, private evidence, and third-party binaries. Obtain optional external inputs from the official upstream projects below and keep personal inputs local.

## Repository layout

| Path | Purpose |
|---|---|
| `validator/MTG_Deck_Validator_v1.1.1.py` | **Active GitHub `main` Casual Private Beta v0.2 Validator** (SHA-256 `f8e915a95e73e20edf59267dfe39e45f82d62bb5eb49fd4eb180194189d995ef`); the old beta branch has different code and hash. |
| `validator/MTG_Deck_Validator_v1.1.py` | Original unchanged validator, retained for reproducibility |
| `tests/test_validator_v1_1_original.py` | 18 original discoverable regression tests |
| `tests/test_validator_v1_1_1.py` | 10 additional tests for incomplete or contradictory Oracle data |
| [`tests/test_card_search_roles_v0_2.py`](tests/test_card_search_roles_v0_2.py) | Regression coverage for theme role classification and pagination |
| [`docs/MTG_Validator_Guide.md`](docs/MTG_Validator_Guide.md) | User guide for the original v1.1 validator |
| [`docs/MTG_Validator_v1.1.1_Audit.md`](docs/MTG_Validator_v1.1.1_Audit.md) | Technical audit and recorded execution evidence |
| [`docs/MTGJSON_Automated_Backup.md`](docs/MTGJSON_Automated_Backup.md) | Verified MTGJSON release workflow and maintenance guide |
| [`examples/`](examples/) | Two original Mono-Red example decklists; no personal collection data |
| `.github/workflows/python-tests.yml` | GitHub Actions tests across Python 3.9, 3.12, and 3.13 |
| [`prompts/`](prompts/) | Versioned Casual and Commander masterprompts; stable/backup/experimental separation |
| `scripts/update_mtgjson_atomic.py` | Official MTGJSON AtomicCards download and verification |
| `.github/workflows/mtgjson-atomic-update.yml` | Monthly upstream verification only (no republishing) |
| [`rules/`](rules/) | Official rules source references, Commander checklist, house-rule template, manifest, and change log |
| [`integrations/forge/`](integrations/forge/) | Isolated experimental Forge gameplay integration; current workflows fetch upstream |
| [`integrations/commander-spellbook/`](integrations/commander-spellbook/) | Optional offline Commander combo ingredient screening with 14 separate tests |
| [`tools/card_search.py`](tools/card_search.py) | Card Search v0.3: role-aware Oracle/owned discovery plus Lifegain pairs |
| [`tools/synergy_engine.py`](tools/synergy_engine.py) | Synergy Engine v0.4: eight bounded strategy pair profiles |
| [`tools/combo_synergy_report.py`](tools/combo_synergy_report.py) | KISS v0.5: thin report wrapper, no changes to existing engines |
| `scripts/check_mtg_rules.py` | Official rules and banlist source fingerprint monitoring |
| `.github/workflows/mtg-rules-check.yml` | Bimonthly source monitoring and change history |
| [`LICENSE`](LICENSE) | MIT license for independently authored AI Deckbuilding Tool material |
| [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md) | Upstream creator credits, licensing boundaries and unofficial Wizards disclaimer |
| [`third_party_licenses/`](third_party_licenses/) | Preserved GPLv3/MIT notices for Forge, MTGJSON and Commander Spellbook |
| [`docs/PUBLIC_RELEASE_CHECKLIST.md`](docs/PUBLIC_RELEASE_CHECKLIST.md) | Review of existing binary/data Releases and source obligations before going public |
| `.gitignore` | Python exclusions and protection against committing personal collection exports or large data archives |

## Card discovery v0.3: owned thematic candidate search

[Card Search v0.3](tools/card_search.py) reuses your attached MTGJSON AtomicCards file and the **current collection CSV you supply manually for each ChatGPT Project chat**. It identifies **CORE**, **ENABLER**, **PAYOFF** and **SYNERGY** suggestions around a named mechanic/theme and shows card-level Oracle-text evidence and owned quantities. A card may have several roles; conditional or heuristic synergies remain explicitly unverified.

The tool preserves the earlier `--ability`, `--keyword`, `--text`, name/type/subtype, mana-value and color-identity filters. `--theme` enables role discovery; `--role` narrows suggested roles; `--limit` plus `--offset` pages through larger results. The only source of ownership is the *active manually supplied CSV*, never MTGJSON or older chat memory.

~~~bash
python tools/card_search.py --oracle AtomicCards_slim_v2.json.gz \
  --collection my_current_collection.csv --owned-only \
  --theme Deathtouch --identity BG --limit 500 --format json
~~~

The role suggestions are **not a complete ontology of every MTG mechanic**, a decklist or proven rules interactions. [Read the complete guide](docs/CARD_SEARCH.md), including instructions for integrating the helper script with a **ChatGPT Project**. Adding a Python file to Project Sources does not, by itself, guarantee the script can be executed or accessed as a runtime file; verify execution when using it.

The [Casual Builder v7.4](prompts/casual/builder/stable/MTG_Deck_Builder_v7.4_full.md) is the stable working version. The unchanged [v7.3 backup](prompts/casual/builder/backup/MTG_Deck_Builder_v7.3_full.md) remains available for rollback; v7.4.1 remains experimental. v7.4 preserves ownership and mana safeguards while adding qualitative synergy-package tradeoffs. The latest uploaded [Casual Tester v3.4.2](prompts/casual/tester/MTG_Deck_Tester_v3.4.2_full.md) is included alongside v3.3 and v3.2. The public copies of v3.3 and v3.4.2 specify English output. The original files remain in the private project.



## Public testing

This repository is a **public experimental source preview**, not a finished one-click desktop or web app. To test it without sharing personal cards, follow [PUBLIC_TESTING.md](PUBLIC_TESTING.md). The Builder and Tester are AI-agent prompts, while the Validator and Agent Gateway are executable Python tools. **Do not assume strategic improvements, rules completeness, or automatic swaps.**


## Quick start

Use Python 3.12 and run these commands from the extracted source root. The offline regressions use the bundled fixtures and Python standard library.

```bash
sha256sum -c SHA256SUMS.txt
python -m unittest discover -s tests -p "test_*.py" -v
python -m unittest discover -s integrations/forge/tests -p "test_*.py" -v
python -m unittest discover -s integrations/commander-spellbook/tests -p "test_*.py" -v
```

The optional workflow syntax check uses the same PyYAML version as CI. Install it in an isolated environment.

```bash
python -m venv .venv
.venv/bin/python -m pip install "PyYAML==6.0.3"
.venv/bin/python scripts/check_workflows.py
```

For a real deck validation, provide **your own local** collection CSV with `Name,Quantity` columns and an MTGJSON AtomicCards `.json` or `.json.gz` database. These personal and large data files are **not stored** in this repository.

```bash
python validator/MTG_Deck_Validator_v1.1.1.py \
  --collection "my_collection.csv" \
  --oracle "AtomicCards_slim_v2.json.gz" \
  --deck "examples/Synthetic_Red_A.txt" \
  --mode casual --exact-60 --output "report.json"
```

Replace all sample paths with your actual files. This invokes the **exported Prepare Integrity Validator**, now with the corrected docstring command `python validator/MTG_Deck_Validator_v1.1.1.py --help` (SHA-256 `f8e915a95e73e20edf59267dfe39e45f82d62bb5eb49fd4eb180194189d995ef`). Check `prepare_layout_audit`, `mana_curve_integrity`, every mandatory validation check and process exit. Use the active Project Source and its **different pinned hash** when operating inside an unchanged ChatGPT Project v1.6. The v1.1 source is historical. See [Project setup](docs/CHATGPT_PROJECT_PRIVATE_BETA_SETUP.md).

## Interpreting validation results

- `PASS_WITH_LIMITATIONS`: The implemented hard checks passed; documented limitations still apply.
- `FAIL`: An established violation was found.
- `UNVERIFIED`: Required card information is missing, ambiguous, or contradictory.
- `NOT_CHECKED`: That property has not been verified.

The Python validator does **not** implement a full rules engine, actual gameplay or win-rate simulation, comprehensive banlist checks, or strategic synergy proofs. The separate Forge integration performs experimental gameplay but does not change the validator's scope.

## Official MTGJSON verification (monthly)

The scheduled [MTGJSON verification workflow](.github/workflows/mtgjson-atomic-update.yml) fetches **the official upstream AtomicCards data**, checks its published SHA-256, gzip/JSON structure, card coverage and version metadata, and reports a small summary. It **does not republish or mirror the database** and has read-only GitHub permissions. Run it manually or on the first day of every month.

Use [MTGJSON API v5](https://mtgjson.com/api/v5/AtomicCards.json.gz) to download a local database. Verify the download against the [official SHA-256](https://mtgjson.com/api/v5/AtomicCards.json.gz.sha256) and record the data version and digest to reproduce a run. The upstream download and the slim snapshot mentioned in examples are different inputs. For Gateway profiles, follow the [source and hash requirements](docs/AGENT_QUICKSTART.md). The source candidate ships no MTGJSON database. See the [updated guide](docs/MTGJSON_Automated_Backup.md).

## Forge gameplay integration (separate, manual)

The [Forge integration](integrations/forge/README.md) uses **official Forge 2.0.15 directly from Card-Forge** with an exact SHA-256 and byte-size check, instead of downloading from or publishing to a release in this repository. The [manual Forge verification workflow](.github/workflows/forge-runtime-download.yml) tests the upstream archive without storing another public copy. The [manual one-game smoke workflow](.github/workflows/forge-smoke.yml) independently downloads that same upstream archive and retains gameplay logs temporarily as Actions evidence.

**Forge smoke inputs:** The bundled decks are synthetic technical fixtures.

This source candidate ships no Forge binaries. The Python Validator contains no Forge Java code.

## Commander Spellbook (experimental, no scheduled Actions jobs)

The independent [Commander Spellbook analyzer](integrations/commander-spellbook/README.md) can process the official bulk combo export **when explicitly downloaded by the user**. It screens a local decklist for **named card ingredient candidates** and variants missing **exactly one copy**. The result does **not** demonstrate that the combo is legally executable. Template-dependent variants are skipped; the tool does not verify the complete Oracle prerequisites.

**Verified:** the official Spellbook bulk export was read successfully and the known Sanguine Bond + Exquisite Blood ingredient pair was detected in a synthetic 60-card deck using real data (October 15, 2026). The original Spellbook analyzer has 23 offline regression tests; no real gameplay simulation or real personal collection audit is claimed. The bulk export is never committed or fetched in routine CI.

For a **combined, read-only report** that preserves deck validation, current collection ownership and separate synergy/combo statuses, see [Combo & Synergy Report v0.5](docs/COMBO_SYNERGY_V0_5.md). It does not replace the existing tools or the ChatGPT Project's Builder instructions.

## Official rules and banlists

See [rules/README.md](rules/README.md) for current official Comprehensive Rules, Commander format references, banned-list sources, and our still-unapproved house-rule template.

A separate read-only GitHub Actions workflow checks source fingerprints every two months against the [manifest](rules/manifest.json) and [change log](rules/CHANGELOG.md). Changes are shown in the Actions summary and require a manually reviewed PR; the workflow never pushes to `main`. **A source change is not automatically interpreted as a changed game rule or ban**, and no rule or ban is silently applied by the validator. The first online source baseline was successful on October 14, 2026; updated workflow versions require their own subsequent live verification.

## CI and verification coverage

The original offline regression suite contains **41 synthetic tests**: 18 original validator tests, 10 v1.1.1 safety tests, 6 MTGJSON updater tests, and 7 rules monitor tests. The suite was successfully executed on **Python 3.9, 3.12, and 3.13** in GitHub Actions run 38612536326 (historical private reference), using Node.js 24-compatible `actions/checkout@v6` and `actions/setup-python@v6` on Ubuntu 24.04.

**English migration verification:** Six additional offline repository-integrity checks were added without changing the original 41 tests. The resulting **47 of 47 tests passed on Python 3.9, 3.12, and 3.13** in GitHub Actions run 38631408916 (historical private reference). The new tests check exact original decklist hashes, English prompt output directives, renamed file paths, internal Markdown links, and Python syntax. The 14 standalone Commander Spellbook tests are separate.

**Third-party attribution safeguards:** The attribution tests remain part of the suite, updated to prohibit new Forge/MTGJSON mirrors. The original 41 tests and six English migration tests were not modified.

**Casual Private Beta v0.2 accepted GitHub CI:** PR #29 candidate run 41315644860 (historical private reference) and merged main run 41315700456 (historical private reference) both succeeded. Release snapshot ref: `release/casual-private-beta-v0.2-2026-11-01` after final documentation CI. The ChatGPT Project v1.6 still has the older Prepare hash; see [Project setup](docs/CHATGPT_PROJECT_PRIVATE_BETA_SETUP.md).

**Historical PR #27 Prepare Validator CI (before the one-line usage correction):** GitHub Actions run 41311187060 (historical private reference) succeeded on the actual 2026-11-01 `main` merge commit the historical private revision. The older metrics below are retained as historical evidence.

**Historical integration and security gates:** GitHub Actions run 38638287867 (historical private reference) passed **59 root Python tests plus 14 standalone Commander Spellbook tests** on Python 3.9, 3.12 and 3.13, an independent YAML workflow parser check, and the historical Git pattern scanner. The new test run found no recognised secret/collection patterns in **635 reachable Git objects**, scanning **147 blobs** with no files skipped for size. This is a heuristic privacy check, not proof of absence of every possible secret or sensitive historical attachment.

Those tests demonstrate only their actual coverage, not complete support for MTG rules, every card mechanic, or all formats. The full Forge gameplay workflow has **not yet been rerun after the examples-directory rename**; its last verified game predates that rename.

## Prompt language migration and historical integrity

The earlier language migration was performed in the private source project. This candidate requires English output in all eight included prompts. Builder v7.4 remains the stable working version; v7.4.1 remains experimental.

The language updates do not change the Validator implementations. The examples in this export are synthetic technical fixtures.

## Privacy and usage

Keep personal inputs private. Do not commit personal collection CSVs, full MTGJSON or Spellbook bulk exports, login credentials, or API keys. Only the two example decklists are tracked, by card name and quantity. Unit tests use synthetic fixtures with no access to your actual collection.

The validator may be uploaded as a ChatGPT Project file, but there is **no automatic GitHub ↔ ChatGPT Projects synchronization**. GitHub remains the versioned source archive and a location for controlled tests.
