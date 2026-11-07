# AI Deckbuilding Tool

AI Deckbuilding Tool is a free, open-source toolkit for AI-assisted Magic: The Gathering deckbuilding, analysis, and validation. An external AI-capable host follows the Builder and Tester prompts. Local Python tools handle card search and deterministic checks such as deck size, owned quantities, and copy limits. The repository contains no built-in AI model or autonomous deckbuilder.

**Status** `PUBLIC_TEST_PREVIEW`. The primary workflow is Casual 60+ card deckbuilding. The Agent Gateway, Forge and Commander Spellbook integrations are experimental. See [project status](PROJECT_STATUS.md), [public testing](PUBLIC_TESTING.md), and the [publication checklist](docs/PUBLIC_RELEASE_CHECKLIST.md).

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

Use the [card naming and import guide](docs/MTG_Validator_Guide.md#physical-card-names-and-import) for aliases, disputed inventory labels and spaced `x` markers. Full AtomicCards and the Gateway-pinned slim dataset were tested with synthetic ownership. The real-collection Gateway requires the frozen slim dataset. AI prompt equivalence across models and the external Project Source migration are `NOT_VERIFIED`.

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
