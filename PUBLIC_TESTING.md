# Public testing guide

**Project:** AI Deckbuilding Tool  
**Compatible game:** Magic: The Gathering  
**Status:** Experimental public source preview. Not a finished one-click application.

You can run the offline tests and explore the Agent Gateway without uploading any personal card collection. The project is independently developed and is not affiliated with, sponsored by, or endorsed by Wizards of the Coast.

## Requirements

- Python 3.12 is recommended.
- A local checkout of this repository.
- Optional: `PyYAML==6.0.3` for the workflow syntax/policy check.
- Optional for real card checks: the MTGJSON AtomicCards data you download independently from [MTGJSON](https://mtgjson.com/downloads/all-files/). The database is not included.

## Start with no personal data

```bash
python -m unittest discover -s tests -p 'test_*.py' -v
python -m unittest discover -s integrations/forge/tests -p 'test_*.py' -v
python -m unittest discover -s integrations/commander-spellbook/tests -p 'test_*.py' -v
python tools/agent_gateway.py doctor
python tools/agent_gateway.py discover --help
python tools/agent_gateway.py validate --help
```

These tests use synthetic fixtures. `doctor` may report that optional Oracle data is missing; this is expected without a local dataset.

For details on local Oracle/collection inputs and actual validation, see [Agent Quickstart](docs/AGENT_QUICKSTART.md) and [README](README.md). Review the SHA-256 requirements for any specifically pinned inputs.

## What to evaluate

1. Check whether the documented commands execute on your system and include Python version and exact command in a report.
2. Verify valid and invalid 60-card test decks are classified correctly by the Validator.
3. Evaluate explanations, mana source assumptions, card identity uncertainty and unsupported abilities.
4. Treat Builder/Tester recommendations as unverified advice until independently reviewed. These are AI prompts, not a complete automated deckbuilding application.

## Report an issue

Use [GitHub Issues](https://github.com/Dreadpool-87/ai-Deckbuilding-tool/issues). Include reproduction steps, expected/actual behavior, Python version, and sanitized examples. **Never upload your personal collection, actual private decks, API credentials, MTGJSON database, or unredacted logs.**

## Scope and licensing

Independently developed project materials are MIT-licensed where the owner has authority to grant that license. Forge, MTGJSON, Commander Spellbook and Wizards of the Coast retain all their respective rights. Download optional third-party inputs from official upstream sources. No game artwork, proprietary Oracle dump or third-party binary is bundled here.
