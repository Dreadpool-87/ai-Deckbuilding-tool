# Agent Gateway integration roadmap

The Agent Gateway is an **experimental entry point** for Python-capable agents working with Casual Deck Tools. The candidate includes the work from PRs #35–39 and the source-hardening follow-up in PR #41. Independent synthetic acceptance covered the gateway workflow and the hardening patch. The stable Casual workflow is described in [PROJECT_STATUS.md](../PROJECT_STATUS.md).

| Action | Supported behavior |
| --- | --- |
| `doctor` | Reports local tool availability and checks the selected source pins. |
| `discover` | Returns candidates from the declared collection using pinned Card Search. |
| `validate` | Runs the selected pinned Validator for structural Casual checks. |

Start with the [quickstart](AGENT_QUICKSTART.md). The [result contract](AGENT_RESULT_CONTRACT_V1.md) explains exit codes, uncertainty and machine-readable evidence. [Source compatibility](AGENT_SOURCE_COMPATIBILITY_P4.md) covers code pins, private input snapshots and confirmation for the current run.

## Evidence and boundaries

- Synthetic acceptance covered invalid decks, mismatched source hashes, missing collection confirmation and conflicting card data. The patch retest also covered code replacement, input replacement and cleanup.
- Real collections, the production Oracle bulk file, alternate Validator binaries and portability across agents remain outside the independent test scope. Collection confirmation is a declaration for the current run.
- The Gateway provides tool execution evidence. Card suggestions remain heuristic and structural validation provides no evidence of strategic deck improvement.
- Swap Advisor work remains separate and on hold. The Gateway exposes no swap action. Any future Swap Advisor integration requires separate acceptance and owner approval.

Keep private collections, decks, Oracle bulk data and private evidence out of GitHub. Installation into ChatGPT Project Sources is a separate action.
