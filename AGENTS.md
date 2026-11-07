# AI Deckbuilding Tool: Agent Entry Point

**Purpose:** Help Python-capable AI agents build and evaluate Casual 60+ card decks using the existing AI Deckbuilding Tool workflow. AI reasoning is required by the intended host product; Python tools constrain factual claims. This file is an **onboarding map**, not a replacement for stable Builder/Tester prompts, the Validator, official rules, or approval gates.

**Current public scope:** `PUBLIC_TEST_PREVIEW` for the Casual workflow. Private beta v0.2 acceptance is historical. Stable Builder v7.4 and Tester v3.4.2 are prompts, **not autonomous Python programs**. Swap Advisor work remains separate and on hold. MTG-AIO is a separate future, non-AI project.

**AI host support:** ChatGPT-first public test preview. Other AI agents have not yet demonstrated supported end-to-end tool execution; instruction-reading and deck-proposal behavior alone are insufficient. This is not a claim that only ChatGPT can read the project, nor that ChatGPT automatically executes Python validation.

**Chat-first entry:** When a user provides only the GitHub link or asks an AI to use this repository, begin with [START_HERE.md](START_HERE.md). Ask for the current collection CSV (`Name,Quantity`) only if it is not already accessible and confirmed for this run. Keep setup details behind an actual capability check; a repository link does not grant local execution. The AI selects all cards and strategy; Python tools verify evidence.

## A new agent must follow this order

1. **Check capabilities.** Confirm Python and actual access to local scripts, card data, active collection, and output folder. An attachment, Project Source, link or GitHub file is not proof of executable runtime access. Label an unrun step `NOT_EXECUTED`.
2. **Establish the correct sources.** Check the actual Oracle and applicable Validator file hashes in the runtime. Record the selected environment/version and full SHA-256. Never assume the same filename means the same bytes. MTGJSON/Oracle establishes card facts, **never ownership**.
3. **Confirm collection for this run.** Only a collection explicitly provided/confirmed for the current execution permits owned-card claims. Never reuse ownership from chat memory, earlier exports or repository examples. No real collection: request authorization or use a visibly **synthetic** example.
4. **Read the active specification.** For Casual deck construction use `prompts/casual/builder/stable/MTG_Deck_Builder_v7.4_full.md`; follow its constraints on requested strategy, colors, card counts, independent vs simultaneously assembled decks, and Basic-land policy. Read `PROJECT_STATUS.md` for the preview boundary.
5. **Discover candidates, not conclusions.** Use `tools/card_search.py`, `tools/synergy_engine.py` or `tools/combo_synergy_report.py` as appropriate. Their recognized roles and synergy pairs are **heuristics**, not complete MTG rules verification or proof of strength.
6. **Build and validate.** AI selects a coherent whole-deck strategy and produces complete lists. Run the applicable pinned Validator on each final Casual deck and inspect exit code, status, failures, uncertainties, mana curve and Prepare/face audits. Failed, ambiguous or unsupported validation blocks any claim of a validated deck.
7. **Interpret limits accurately.** Tester v3.4.2 can analyze a frozen deck if requested, but is a **prompt-based analytical tester**, not an executed game engine. Only report genuinely executed numeric analyses. Forge Lite is optional external evidence, not a source of universal win rates.
8. **Treat swaps as advice.** Do not present an unverified AI idea or a bounded Swap Advisor role witness as a proven `SWAP`. Mention pros, cons, prerequisites and unresolved assumptions; no automatic edits (`automatic_swap_authorized=false`). Swap Advisor integration requires a separate acceptance and integration approval.
9. **Report concisely.** Give the deck(s), source/collection status, validation result, strategic rationale, known limitations and, if supported, proposed changes with trade-offs. Distinguish `FACT`, `DERIVATION` and `HYPOTHESIS`. Never claim to have executed a tool without its real output.

## Runtime map

| Need | Maintained entry | Meaning |
| --- | --- | --- |
| Status and versions | `PROJECT_STATUS.md` | Current public preview and historical workflow records |
| Minimal commands | `docs/AGENT_QUICKSTART.md` | Human- and agent-readable start |
| Stable Casual Builder | `prompts/casual/builder/stable/MTG_Deck_Builder_v7.4_full.md` | AI deck-construction instructions |
| Card shortlist | `tools/card_search.py` | Oracle-backed search and heuristic roles |
| Possible pair synergies | `tools/synergy_engine.py` | Bounded heuristic pairing; requires adjacent `card_search.py` |
| Combined thematic report | `tools/combo_synergy_report.py` | Discovery/optional combo ingredients, not a deckbuilder |
| Casual validation | `validator/MTG_Deck_Validator_v1.1.1.py` | Version-specific Python Validator; verify actual SHA |
| Independent analytical testing | `prompts/casual/tester/MTG_Deck_Tester_v3.4.2_full.md` | Prompt, not a physical game simulation |
| Separate project on hold | `Dreadpool-87/MTG-Swap-Advisor` | Separate repo, not yet authorized for Builder integration |
| Implementation priorities | `docs/AGENT_INTEGRATION_ROADMAP.md` | Scope, statuses and review gates |

## Non-negotiable boundaries

- Reject unknown or contradictory card names, faces, quantities and rules rather than guessing. Prepare and multiface require explicit identity/face handling.
- Do not confuse Oracle text matches with actual synergy, payment feasibility, deck validation or strategic superiority.
- Do not feed private collection/deck data to external AI services without separate user permission. Keep all private inputs, Oracle bulk data, test holdouts, tokens and private reports out of GitHub.
- Do not silently modify the Builder, Tester, Validator, accepted `main`, releases, frozen history, Commander, Forge Lite or MTG-AIO. Work on isolated experimental branches and use review.
- Use English for all project content and agent outputs. Preserve official English card names and technical identifiers.

**Gateway status:** See the [current verification record](docs/IDENTITY_RELIABILITY_AUDIT.md) and [synthetic smoke test](docs/AGENT_QUICKSTART.md#synthetic-smoke-test). Portability across agents remains untested. Adding this file to GitHub does not install it as a ChatGPT Project Source or grant Python or file access.

