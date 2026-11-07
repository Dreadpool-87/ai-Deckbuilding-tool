# Start here: use AI Deckbuilding Tool in a chat

**For people:** Share the [repository link](https://github.com/Dreadpool-87/ai-Deckbuilding-tool) or this page with a capable AI assistant. The AI is the deckbuilder; Python tools only retrieve and verify facts and enforce the workflow.

**For AI agents:** Read [AGENTS.md](AGENTS.md), then [the optional workflow guide](docs/AGENT_WORKFLOW_MVP.md) when local Python execution is available. The active Casual specification is [Builder v7.4](prompts/casual/builder/stable/MTG_Deck_Builder_v7.4_full.md); [Tester v3.4.2](prompts/casual/tester/MTG_Deck_Tester_v3.4.2_full.md) is optional and is not a game simulator. Do not substitute archived or draft prompts.

## First reply to the user

Treat a message containing only this page's URL as a request to begin deckbuilding onboarding. Address the user directly; do not merely summarize this document or say what an agent should ask. When the collection is missing, actually ask for it in your first reply. For example:

> Please upload your current card collection CSV with `Name,Quantity` columns. I will choose the cards and strategy, and check which validation tools and verified card data I can actually access. A preferred color or deck style is optional.

If the current collection is not already attached and explicitly confirmed for this run, **ask for their collection CSV** (columns `Name,Quantity`, one card per row). Do not demand an installation, a checksum or a collection re-upload when the needed inputs are already accessible. You may ask for a deck goal or color preference, but the AI can propose those after examining the collection.

Explain in plain language that real validation also requires executable Python tools and verified Oracle/MTGJSON card data. Check what the host can actually access. A GitHub URL or pasted prompt does **not** install the repository, mount files, provide Oracle data or grant code execution. If the required runtime or Oracle is missing, try the available permitted setup options; otherwise state the exact blocker and do not claim the workflow was executed.

## Required operating rules

1. Confirm the **current-run** ownership source: only the CSV explicitly provided or confirmed for this run authorizes ownership claims. Never use prior chats, other repositories, card datasets or test fixtures as the user's collection. Keep personal collections and generated decklists out of public GitHub.
2. Verify access to the checkout, Python runtime, official MTGJSON/Oracle data and required source hashes before using tools. The real-collection Gateway/controller currently requires the explicitly pinned slim Oracle profile. Do not silently replace it with other data. Report `NOT_EXECUTED` where verification cannot run.
3. Follow the stable Builder's strategy guidance. **The AI** selects colors, strategy, cards, quantities and manabase, and writes the deck. Python Card Search, Gateway, Validator and optional Workflow Controller supply bounded evidence, not autonomous strategic decisions.
4. When available, use the [AI-led Workflow Controller](docs/AGENT_WORKFLOW_MVP.md) to require preflight, source checks, collection, discovery, an AI-authored candidate, validation and review in the proper order. A changed deck or source invalidates previous evidence. If the controller cannot run, distinguish manual steps from controller-certified completion.
5. Inspect actual exit codes, JSON statuses, failures and uncertainties. `PASS_WITH_LIMITATIONS` is structural validation, **not** proof of format legality, strategy, gameplay or win rate. Never invent executed tests or a completion certificate.
6. Return the complete decklist, strategic reasoning, source/validation status, and clearly named limitations. Forge and Commander Spellbook integrations are separate experiments; never claim games were played unless they were executed.

## After the AI creates a candidate deck

**Python-capable agents: validation is the next required attempt, not an optional follow-up to offer the user.** Check that a local checkout and the pinned Oracle are actually available. When they are, save the AI-authored deck to a private local file and run the one-command entry point:

```sh
python -m ai_deckbuilding_tool validate --oracle /private/AtomicCards_slim_v2.json.gz --collection /private/CURRENT_COLLECTION.csv --collection-confirmed --deck /private/candidate.txt
```

This command performs preflight and delegates to the real pinned Gateway/Validator. Read its JSON status, actual execution evidence, failures and uncertainties. If it rejects the deck, **revise the AI-authored list and execute validation again** before describing it as validated. Do not wait for the user to explicitly ask for this step when all inputs and execution permissions are already available. Use `discover` first when card discovery can run.

If the host cannot obtain an executable local checkout or verified pinned Oracle through permitted capabilities, explain the exact blocker, mark the formal check `NOT_EXECUTED`, and present only a clearly labeled unvalidated proposal. A GitHub link cannot force host execution, and this entry point does not automatically download the Oracle or decide the deck strategy. See [the quickstart](docs/AGENT_QUICKSTART.md#automatic-preflight-and-validation-entry-point).

## Copy-paste starter message

> Use https://github.com/Dreadpool-87/ai-Deckbuilding-tool as the reference for building a Casual Magic: The Gathering deck. Read `START_HERE.md` and `AGENTS.md`. You choose the cards and strategy; Python only supports and verifies your work. Ask me for my current collection CSV if I have not provided it yet. Check whether you can actually run the tools and access verified Oracle data. Never claim execution or validation without evidence. Keep my collection private.

**Scope:** Public test preview; the main supported workflow is Casual 60+ cards. The optional controller MVP currently validates exactly 60-card Casual decks. Commander, full banlist legality, automatic swaps and Forge gameplay are not implied by a successful Casual validation.
