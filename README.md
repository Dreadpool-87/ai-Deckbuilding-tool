# AI Deckbuilding Tool

AI Deckbuilding Tool is a free, open-source toolkit for AI-assisted Magic: The Gathering deckbuilding, analysis, and validation. An external AI-capable host follows the Builder and Tester prompts. Local Python tools handle card search and deterministic checks such as deck size, owned quantities, and copy limits. The repository contains no built-in AI model or autonomous deckbuilder.

**Status** `PUBLIC_TEST_PREVIEW`. The primary workflow is Casual 60+ card deckbuilding. The Agent Gateway, Forge and Commander Spellbook integrations are experimental. See [project status](PROJECT_STATUS.md), [public testing](PUBLIC_TESTING.md), and the [publication checklist](docs/PUBLIC_RELEASE_CHECKLIST.md).

## Current AI host support

**Capability-based public test preview.** Any AI host with a local checkout, Python 3.12/3.13 and permitted network access (or a verified local cache) can use the CLI. ChatGPT was the primary evaluated chat host; this is not certification that every chat platform can execute Python. Never claim deck validation without actual tool results.

## Start with an AI (recommended)

Give an AI assistant this repository URL or the dedicated [chat-first starter](START_HERE.md). The AI should read the onboarding instructions and **ask for your current card collection CSV** (`Name,Quantity`) if it has not already been provided. The AI builds and reasons about the deck; Python tools support verification.

**For AI agents:** A message containing only this repository URL is a request to begin the onboarding in `START_HERE.md`. Ask the user directly for the missing collection; do not stop at a repository summary or request a separate implementation task.

The link alone does not give an AI access to Python, source files or the verified Oracle dataset. If those cannot actually be loaded, the assistant must say so rather than inventing validation results. This is a public test preview, not a hosted one-click deckbuilding service.

## MTGJSON data freshness (no redistribution)

[Weekly AtomicCards verification](.github/workflows/mtgjson-atomic-update.yml) runs every **Sunday at 07:17 UTC**. It verifies the complete official MTGJSON download in temporary runner storage, and proposes a reviewed PR containing only [the official URL, version and SHA-256 pointer](data/README.md) when the version or digest changes. **No MTGJSON card archive is stored in Git history, GitHub Releases or Actions artifacts.** The official download URL is mutable; verify every downloaded archive against the current upstream checksum. This pointer does not yet activate full-AtomicCards support in the existing real-collection Gateway.
## One-command validation for Python-capable AI hosts (experimental)

After the AI has authored a deck, it should **attempt the real Validator before presenting a validated result**, instead of stopping at a manual card-count check. The new standard-library CLI automatically runs Gateway preflight and then delegates to the pinned Gateway. In a local checkout:

```sh
python -m ai_deckbuilding_tool setup
python -m ai_deckbuilding_tool discover --collection /private/CURRENT_COLLECTION.csv --collection-confirmed --theme aggro
python -m ai_deckbuilding_tool validate --collection /private/CURRENT_COLLECTION.csv --collection-confirmed --deck /private/ai_candidate.txt
```

Setup automatically verifies and caches official full MTGJSON AtomicCards. Discovery and validation invoke setup when Oracle arguments are omitted. Users do not manually prepare files or hashes. Actual execution permissions and current-run collection confirmation remain required. Invalid decks must be revised by the AI and revalidated. See [the quickstart](docs/AGENT_QUICKSTART.md#automatic-preflight-and-validation-entry-point).

## Get started

Use Python 3.12 or 3.13 from a local checkout. Run the [synthetic smoke test](docs/AGENT_QUICKSTART.md#synthetic-smoke-test) to check your setup. The core tools use the standard library. To validate a deck, supply a local MTGJSON AtomicCards JSON or gzip file, a current collection CSV with `Name,Quantity` columns, and a UTF-8 decklist with entries like `4 Lightning Bolt`. Download and verify Oracle data separately using the [MTGJSON verification guide](docs/MTGJSON_Automated_Backup.md). Keep collection CSVs, private decks, and generated reports local.

1. Start with the [agent entry point](AGENTS.md) and [quickstart](docs/AGENT_QUICKSTART.md). Confirm the actual runtime and the collection for the current run.
2. Find candidates with [Card Search](docs/CARD_SEARCH.md) and use [Casual Builder v7.4](prompts/casual/builder/stable/MTG_Deck_Builder_v7.4_full.md) in the host to construct a deck. Discovery roles and pair suggestions are heuristics.
3. Validate the finished deck. Review the actual exit code and JSON, including any failures or uncertainties. The experimental Gateway offers `doctor`, `discover`, and `validate` under its [pinned source policy](docs/AGENT_SOURCE_COMPATIBILITY_P4.md).
4. Use [Casual Tester v3.4.2](prompts/casual/tester/MTG_Deck_Tester_v3.4.2_full.md) for optional analytical review of the validated deck.

For direct Validator use, replace the example paths with your local files.

```sh
python validator/MTG_Deck_Validator_v1.1.1.py \
  --collection collection.csv --oracle AtomicCards.json.gz \
  --deck candidate.txt --mode casual --exact-60 --output report.json
```

Omit `--exact-60` for decks larger than 60 cards. A result of `PASS_WITH_LIMITATIONS` means the implemented structural checks passed. Full rules legality, format banlists, castability, strategic strength, and win rates are outside those checks. The project does not edit decks or apply swaps automatically. [Forge](integrations/forge/README.md) supports separate experimental gameplay, while [Commander Spellbook](integrations/commander-spellbook/README.md) screens for combo ingredients.

Use the [card naming and import guide](docs/MTG_Validator_Guide.md#physical-card-names-and-import) for aliases, disputed inventory labels and spaced `x` markers. Full AtomicCards and the Gateway-pinned slim dataset were tested with synthetic ownership. The Gateway accepts verified full snapshots with their local setup receipts; the frozen slim profile remains for reproducibility. AI prompt equivalence across models and the external Project Source migration are `NOT_VERIFIED`.

An optional [experimental AI-led workflow controller](docs/AGENT_WORKFLOW_MVP.md) gates completion on actual Gateway evidence. The AI selects the deck and authors its strategic review.

## Run the offline tests

```sh
sha256sum -c SHA256SUMS.txt
python -m unittest discover -s tests -p "test_*.py" -v
python -m unittest discover -s integrations/forge/tests -p "test_*.py" -v
python -m unittest discover -s integrations/commander-spellbook/tests -p "test_*.py" -v
```

The suites use synthetic inputs. See [CI maintenance](docs/CI_MAINTENANCE.md) for the Python matrix and workflow checks. See the [verification record](docs/PUBLIC_PREVIEW_AUDIT.md) for the scope, dated results, and historical private-beta evidence. ChatGPT Project Sources have separate pins and require manual synchronization. See the [Project setup](docs/CHATGPT_PROJECT_PRIVATE_BETA_SETUP.md).

## License and credits

The project-authored material is available under the [MIT license](LICENSE). [MTGJSON](https://mtgjson.com) provides the core card data format and upstream database. Forge, Commander Spellbook, MTGJSON, and Wizards of the Coast retain their respective rights. See the [third-party notices](THIRD_PARTY_NOTICES.md) for attribution and distribution boundaries.

> This project is unofficial and is not affiliated with, sponsored by, or endorsed by Wizards of the Coast. Magic: The Gathering is a trademark of Wizards of the Coast and identifies the compatible game.
