# AI Deckbuilding Tool — Current Project Status

**Runtime update (2026-11-07):** Official full AtomicCards automatic setup, private cache, export normalization and capability-based CLI are implemented. See [runtime acceptance](docs/FULL_ATOMIC_RUNTIME_ACCEPTANCE.md) for exact evidence and limitations. Strategy remains AI-authored.

## Current public checkout (2026-11-07)

**Scope:** `PUBLIC_TEST_PREVIEW`, primarily Casual 60+ decks. This repository is an **AI support toolkit**, not a standalone Python deckbuilding algorithm. The AI selects cards and strategy.

| Current component | Status and authoritative reference |
| --- | --- |
| AI-first start | [START_HERE.md](START_HERE.md) and [AGENTS.md](AGENTS.md) |
| Stable Casual Builder / Tester | [Builder v7.4](prompts/casual/builder/stable/MTG_Deck_Builder_v7.4_full.md) and [Tester v3.4.2](prompts/casual/tester/MTG_Deck_Tester_v3.4.2_full.md) |
| Public Validator | `validator/MTG_Deck_Validator_v1.1.1.py`, SHA-256 `58b1015c1138b6bb5bfb2b49cd1762d56ea9cc4687d9e87314f2124570a0a5fd` |
| Gateway source profile | [Current source compatibility / pins](docs/AGENT_SOURCE_COMPATIBILITY_P4.md); verify actual local bytes |
| Optional AI-led controller | [Workflow MVP](docs/AGENT_WORKFLOW_MVP.md); merged into public main, still experimental |
| Draft compact prompts | PR #3 is experimental, **not activated**, and not part of `main` |
| Separate ChatGPT Project | Project v1.6 has independently managed sources and hashes; GitHub changes do not update it |

**Important:** The Validator pin above identifies the current public source; older hashes elsewhere in this file describe **historical private-beta or rollback sources**, not alternative values for today's public `main`. A passed structural check does not establish comprehensive MTG legality, strategic superiority or gameplay results.

## Historical project and private-beta record (retained for traceability)

**Public lifecycle:** `PUBLIC_TEST_PREVIEW`. The public repository supports experimental source testing and the Casual Builder/Validator/Tester workflow. See [public testing](PUBLIC_TESTING.md), [verification evidence](docs/PUBLIC_PREVIEW_AUDIT.md), and the [active Gateway source pins](docs/AGENT_SOURCE_COMPATIBILITY_P4.md). The audit remediation targets the public preview. Its tests establish only the coverage recorded in the verification evidence.

**Private history:** Casual Private Beta v0.2 was approved for scoped private use with `PASS_WITH_LIMITATIONS`. The following sections preserve that decision and its rollback context. The [private release record](docs/releases/CASUAL_PRIVATE_BETA_v0.2_2026-11-01.md) applies to the historical private source. [ChatGPT Project v1.6](docs/CHATGPT_PROJECT_PRIVATE_BETA_SETUP.md) is a separate environment.

## Read this first

| Need | Where to go | Relationship to main |
|---|---|---|
| **Verified private-beta checkpoint** | Frozen checkpoint (historical private reference) | Lives on frozen beta branch, not automatically synchronized into `main` |
| **What was tested, and what remains unverified** | Sanitized beta test-results index (historical private reference) | Lives on isolated planning branch |
| **Next development priorities and exit criteria** | AI Deckbuilding Roadmap v0.1 (historical private reference) | Lives on isolated planning branch |
| **Safety / maintenance workflow** | [Repository maintenance policy](docs/REPOSITORY_MAINTENANCE_POLICY.md) | Documentation only; no protection rules are silently enabled |
| **Historical alpha readiness review** | [Archived alpha gate](docs/ALPHA_READINESS.md) | Historical status **superseded** by private-beta checkpoint |
| **Prompt version archive** | [Prompt index](prompts/README.md) | GitHub and ChatGPT Project files do not automatically synchronize |
| **ChatGPT Project setup and copy-paste instruction** | [Active private-beta Project setup](docs/CHATGPT_PROJECT_PRIVATE_BETA_SETUP.md) | Additive override; preserve masterprompts and rollback |

## Historical private-beta code and component selection

The original frozen private-beta branch remains unchanged (2026-10-22 checkpoint). Following approved PR #27, the private GitHub `main` used Prepare Validator v1.1.1 with an additional **one-line docstring usage correction** in the v0.2 candidate; new SHA-256 `f8e915a95e73e20edf59267dfe39e45f82d62bb5eb49fd4eb180194189d995ef`. The corrected source has the same functional code as the earlier Project Prepare candidate `c422295676d0bad04aa1449725b07a7c11bf58b7990a34aff209e10ba742ac8d`. The existing ChatGPT Project v1.6 remains pinned to that earlier candidate until separately updated; GitHub and Project Sources do not synchronize. The frozen beta and both Project rollback versions remain unchanged.

| Role | Pinned version / identity | Notes |
|---|---|---|
| **Frozen beta code baseline (historical; retained on release branch)** | the historical private revision | Source commit exercised for original private-beta CI; `main` additionally includes the 2026-11-01 approved Prepare update in PR #27 |
| **Frozen beta branch tip** | the historical private revision | Documentation-only release checkpoint; do not rewrite |
| Builder | `prompts/casual/builder/stable/MTG_Deck_Builder_v7.4_full.md` | Stable Builder v7.4, not the experimental v7.4.1 |
| Tester | `prompts/casual/tester/MTG_Deck_Tester_v3.4.2_full.md` | Masterprompt; not a standalone Python simulator |
| **Frozen-beta Validator (release branch ONLY)** | `validator/MTG_Deck_Validator_v1.1.1.py` on `release/casual-private-beta-2026-10-22` | SHA-256 `8749b50d0aeaa52124a99271a0ab40bcc979350c6e8b5e9074c4f28d63a3d1ac`; previous Project beta rollback is identical; **not** the `main` implementation |
| **Active ChatGPT Project Validator** | Project Source `MTG_Deck_Validator_v1.1.1_PREPARE_COLOR_INTEGRITY_CANDIDATE.py` | SHA-256 `c422295676d0bad04aa1449725b07a7c11bf58b7990a34aff209e10ba742ac8d`; activation confirmed 2026-10-31; behaviorally equivalent to the private v0.2 Validator at the time, with a distinct hash and separately managed file |
| **Historical private GitHub `main` Validator, Private Beta v0.2** | `validator/MTG_Deck_Validator_v1.1.1.py` | SHA-256 `f8e915a95e73e20edf59267dfe39e45f82d62bb5eb49fd4eb180194189d995ef`; only the historical CLI usage example changed since PR #27. Full PR #29 CI and merge CI `SUCCESS`. Independent Project v1.6 still selects previous Prepare SHA `c4222956…` until explicit Project migration. |
| **Previous ChatGPT Project beta — rollback ONLY** | `MTG_Deck_Validator_v1.1.1_BETA_CANDIDATE.py` | SHA-256 `8749b50d0aeaa52124a99271a0ab40bcc979350c6e8b5e9074c4f28d63a3d1ac`; preserve locally as rollback |
| **Historical Project rollback ONLY** | Separate original Project file `MTG_Deck_Validator_v1.1.1.py` | SHA-256 `0d296f69a465bdaf5d967d2155460bbe69bb3d653f58952468d45713d2f9db8e`; **not** the same as the current GitHub file named v1.1.1 |
| Auxiliary tools | `tools/card_search.py`, `tools/synergy_engine.py`, `tools/combo_synergy_report.py` | Verify current-chat executability; never pretend they ran |

### Prepare Validator activation and GitHub `main` merge (2026-10-31 to 2026-11-01)

- **Selection:** ChatGPT Project Instructions v1.6 select the SHA-pinned `PREPARE_COLOR_INTEGRITY_CANDIDATE` as the active Validator; Builder v7.4 and Tester v3.4.2 remain unchanged. Preserve both rollback files.
- **Regression evidence:** 7,075 / 7,075 checks passed in the private ChatGPT experimental/regression review, covering `prepare` face integrity, conflicting color data and non-prepare behavior. This is **Project-local test evidence, not a GitHub CI claim**; private test artifacts are not uploaded here.
- **Fresh-project activation:** `ACTIVATION_CONFIRMED` after SHA verification, direct validation of an unchanged 60-card positive baseline, `prepare_layout_audit: PASS`, `ORACLE_ARITHMETIC_PASS`, independent Tester D2/D3 checks, byte-identical baseline-file comparison, and a deliberately invalid five-copy fixture rejected with `copy_limit: FAIL` before Tester execution. Overall positive deck status remained `PASS_WITH_LIMITATIONS`.
- **Boundary:** This confirms the specified activation tests, not exhaustive Oracle/layout support, full castability, complete rules simulation or win rates. No decklists, ownership CSVs, or private reports have been added to GitHub. The frozen `release/casual-private-beta-2026-10-22` branch has **not** been promoted or changed. The same Prepare code was merged into GitHub `main` by PR #27 on 2026-11-01; the frozen release checkpoint is unchanged.

A **new chat must confirm the currently active ownership CSV**, readable Oracle data, and actual executable files. A GitHub link is not evidence of current-chat ownership or runtime access. Never upload personal collection files or private deck reports to GitHub. Validator `FAIL` / blocking `UNVERIFIED` / nonzero process exit **blocks** downstream Tester execution. Freeze any valid deck before independent Tester STANDARD (including mandatory D2/D3).

## Casual Private Beta v0.2 acceptance and release controls

The activated [v0.2 release definition](docs/releases/CASUAL_PRIVATE_BETA_v0.2_2026-11-01.md) specifies its scoped supported workflow and explicit promotion gates. This change is an approved, **private Casual beta release update** with completed PR and merge CI, not stable/public approval. A release-ref snapshot is required after final documentation CI. The old frozen branch is not being advanced. GitHub `main` and Project v1.6 may temporarily differ by the one-line docstring correction; do not silently substitute one source hash for another.

## Acceptance evidence and important limitations

- Round A: structural Builder / stable Validator / independent Tester acceptance, scoped `PASS_WITH_LIMITATIONS`.
- Round B: original Validator negative-case tests, 23 regular tests passed; one known false rejection of an explicit Oracle unlimited-copy exception, tracked and corrected in later candidate.
- Round C: candidate regression with 24/24 expected outcomes, Oracle exception supported, selected commit CI passed.
- New-chat Project integration: positive deck validated and independently D2/D3 audited; deliberately invalid deck rejected **before** Tester started. The separate Project-only activation on 2026-10-31 remains valid historical evidence; the later approved GitHub `main` update happened on 2026-11-01 through PR #27, without changing the frozen beta checkpoint.
- Practical tests: Golgari Deathtouch; Mono-Blue Flash Tempo/Control; repeatability using a frozen Mono-Blue deck. All `PASS_WITH_LIMITATIONS`; deterministic comparisons had zero discrepancies.
- **Known limits:** sanctioned-format bans, full colored-mana castability, all unusual special rules, gameplay/win rates, exhaustive coverage, universal ChatGPT environment persistence and a real rollback rehearsal have **not** been proven.
- Private evidence ZIPs and ownership ledgers are **not hosted on GitHub**. The sanitized test-results index records scope and filenames; a new chat must be given any underlying evidence needed for independent replay.

**Verified GitHub CI links:**
- Prepare Validator merged into `main` (2026-11-01) (historical private reference) — post-merge CI SUCCESS on commit the historical private revision.
- PR #27 prepare-upgrade review (historical private reference) — MERGED; frozen beta unmodified.
- Code baseline (historical private reference) — 5/5 jobs successful.
- Frozen beta checkpoint (historical private reference) — 5/5 successful.
- Sanitized test-index commit (historical private reference) — successful.

## Experimental Gateway and publication status

The original Gateway was introduced in the private source at `04124cd7`. Its three CLI actions passed synthetic checks with the then-default Validator. Alternate profiles and cross-agent portability remain outside that evidence. Forge Lite remains experimental. Swap Advisor is separate and on hold.

**Public source preview: PUBLIC_TEST_PREVIEW** (2026-11-06). Source is public for independent testing; original private beta acceptance and standalone strategic gates are unchanged. See [PUBLIC_TESTING.md](PUBLIC_TESTING.md) and the [publication checklist](docs/PUBLIC_RELEASE_CHECKLIST.md).

## Open work, in priority order

1. **P1 AI Swap Advisor:** separate experimental workstream on hold.
2. **P2 Mana Bottleneck Detector:** colored sources, double-pip demands, tapped/fetch development, defined cards-seen probabilities and honest unverified castability.
3. **P3 Cross-mechanic Synergy Discovery:** use existing tools, bounded interaction proposals, verify timing/targets/resources.
4. **P4 Strategic Robustness:** resilience without payoff, role balance, early game and removal coverage.
5. **P5 Casual-only AIO Orchestrator:** after improvements are demonstrated; keep AIO draft PR #22 (historical private reference) unmerged unless separately authorized.

No code changes, merges or promotions are implied by this roadmap. Develop experiments on dedicated branches with synthetic, privacy-safe tests. Compare against frozen beta and require explicit owner approval.

## Repository organization / maintenance

- Main folders are intentional: `prompts/` (versioned), `validator/`, `tools/`, `tests/`, `docs/`, `scripts/`, `rules/`, `integrations/`, `.github/workflows/`.
- **Historic branch count at audit:** 24 before the organization documentation branch; this is a dated snapshot, not the live count. The organization documentation was merged through PR #23 (historical private reference) on 2026-10-22. Many historic feature/fix branches have divergent Git histories, **not** proven to be safe to delete. See the inventory before any branch cleanup.
- **Branch protection:** GitHub reported `protected: false` for `main` and the frozen beta branch. Connected GitHub API reads for protection returned `403`; private-repository rulesets reported an unavailable-plan restriction. No branch protection was enabled. Until that can be resolved, adopt strict manual safeguards in the maintenance policy.
- `docs/ALPHA_READINESS.md` is a preserved historical assessment from October 16. The earlier outstanding issues #11 and #14 have since been closed; do not treat that review as current status.
- Forge gameplay Actions are **manual** (`workflow_dispatch`); upstream MTGJSON and rules monitoring are read-only periodic checks. The general Python regression workflow runs on code/documentation changes.

## Next-chat handoff (copy/paste)

> This is the scoped Casual workflow for AI Deckbuilding Tool. Read `PROJECT_STATUS.md` in this source candidate first. Historical private-beta references describe the private source project.
>
> Controlled private beta, `PASS_WITH_LIMITATIONS`. In **ChatGPT Project Sources**, use Builder v7.4, Tester v3.4.2 and active Validator `MTG_Deck_Validator_v1.1.1_PREPARE_COLOR_INTEGRITY_CANDIDATE.py` with SHA-256 `c422295676d0bad04aa1449725b07a7c11bf58b7990a34aff209e10ba742ac8d`; inspect `prepare_layout_audit`. Retain previous beta and historical rollback versions. **GitHub's frozen beta still uses its original Validator code**. Use the scoped Casual workflow; do not modify frozen beta or `main` without explicit approval. Require a confirmed accessible current-chat collection for ownership. Do not upload collections, decklists or private reports to GitHub; keep Forge/Commander/Power Level out of Casual scope. Use English for project content and agent outputs.
