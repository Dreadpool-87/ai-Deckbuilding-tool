# Repository Maintenance Policy — Private Source Project

**Recorded:** 2026-10-22  
**Status:** Organizational guidance; **does not** enable GitHub protection, delete branches, merge PRs, or replace working component versions.  
**Historical scope:** This policy documents the private source project. The separate intended repository for this candidate is `Dreadpool-87/ai-Deckbuilding-tool`.

## Protected by policy (manual until enforced technically)

1. **`main`:** shared working code. Do not force-push, rename, rewrite history, or merge unreviewed experiments.
2. **`release/casual-private-beta-2026-10-22`:** frozen, verified private-beta reference. **Never advance its ref** without a separate explicitly approved versioning decision; when improving software, create a new branch.
3. **`planning/casual-ai-deckbuilding-roadmap-20261022`:** current roadmap and sanitized result index; **not** a code release branch.
4. **`backup/pre-python-metrics-20261016`:** historical rollback reference, not necessarily identical to the separate ChatGPT Project historic Validator backup.
5. **`experiment/aio-handoff-v0-1`:** linked to open Draft PR #22. Remains experimental, not stable, no automatic merge.
6. **`docs/project-hub-organization-20261022`:** **historical documentation branch**; its PR #23 (historical private reference) was merged into `main` on 2026-10-22. The project hub is now [PROJECT_STATUS.md](../PROJECT_STATUS.md) on `main`; the old branch itself is not an active workstream.

The exact tested code commit is the historical private revision; the frozen beta docs checkpoint is the historical private revision. Commit hashes, not mutable branch names, provide the immutable recovery reference.

## Changing code safely

1. Start a **dedicated feature branch** based on an explicitly chosen and hashed reference. Keep experiments separate from `main` and the frozen beta.
2. Confirm source identity and executable runtime. Do not use implicit ChatGPT Project ownership from GitHub or prior conversations; active collection must be confirmed in the current chat.
3. Use **synthetic, non-private fixtures** for GitHub tests. Never commit collection CSVs, private decklists/reports, local evidence ZIPs or the copied Oracle dataset.
4. Run the existing root tests, independent Validator checks, positive and invalid-deck hard-gate tests, and any affected integration tests. Inspect **CI on the actual candidate commit**.
5. Compare against frozen stable Builder v7.4, Tester v3.4.2 and beta Validator SHA `8749b50d0aeaa52124a99271a0ab40bcc979350c6e8b5e9074c4f28d63a3d1ac`. Treat strategy improvement as judgment unless backed by executed defined calculations.
6. Open a **Draft PR** with scope, test evidence, known limitations and rollback instructions. Do not auto-merge; request explicit owner approval for any promotion.
7. Keep the frozen beta unchanged as a fallback. GitHub and ChatGPT Project Sources do **not** synchronize automatically.

## Branch cleanup checklist (NO DELETE WITHOUT REVIEW)

- Check PR history and linked issues (including whether a PR was merged, closed or remains draft).
- Compare diffs and actual file content, not only commit ancestry or branch naming.
- Identify possible exclusive bug fixes, source backups, tests, licensing/provenance records or pinned external downloads.
- Confirm that the changes are present in a protected reference, intentionally rejected, or independently archived.
- Preserve recovery commit SHAs and make a deliberate deletion list.
- **Require explicit user approval before any branch deletion.** No cleanup deletion was performed in this organizational pass.

## Branch protection limitations and safe fallback

GitHub branch list reported `protected: false` for both `main` and the frozen beta branch. A connected request to read branch protection returned `403 Resource not accessible by integration`. The rulesets API returned `403 Upgrade to GitHub Pro or make this repository public to enable this feature`.

**Do not make the private repository public to acquire branch protections.** Repository privacy is a firm constraint. If the user's GitHub plan and UI later support protection/rulesets for this private repo, the owner can independently configure rules on `main` and the frozen beta branch to forbid force-push/deletion and require checks/review where suitable. Recheck via the GitHub UI; a successful configuration has **not** been established by this document.

Until then:
- Never use `git push --force` against `main` or the frozen beta.
- Prefer PR review and green checks even for docs changes.
- Pin recovered code by SHA and retain the existing backup.
- Explicitly verify branch heads before and after any authorized write.
- Do not treat a green CI run on an older commit as proof that a new head passed.

## Maintenance and scope

- The periodic official-rules and MTGJSON verification workflows are intentionally read-only and do not publish source data or push commits automatically.
- Forge gameplay workflows use `workflow_dispatch` (manual triggering) and Forge stays outside the active Casual beta/AI roadmap.
- Existing historical alpha documentation is preserved as evidence; **the private beta supersedes the alpha as the active Casual reference**. The current authority for status is [`PROJECT_STATUS.md`](../PROJECT_STATUS.md), the [active ChatGPT Project setup](CHATGPT_PROJECT_PRIVATE_BETA_SETUP.md) and the frozen beta checkpoint.
- In the historical private repository, the previous beta implementation on `main` was replaced in-place by the Prepare Validator in PR #27. Casual Private Beta v0.2 corrects **only the misleading CLI usage docstring** and changes its SHA-256 to `f8e915a95e73e20edf59267dfe39e45f82d62bb5eb49fd4eb180194189d995ef`; same path `validator/MTG_Deck_Validator_v1.1.1.py`. The frozen 2026-10-22 beta branch stays byte-identical at SHA-256 `8749b50d0aeaa52124a99271a0ab40bcc979350c6e8b5e9074c4f28d63a3d1ac`; the old Project `v1.1.1` historical rollback is SHA-256 `0d296f69a465bdaf5d967d2155460bbe69bb3d653f58952468d45713d2f9db8e`. **Never delete old release refs or silently replace a Project source.**

**Next authorized improvement target:** research/design P1 AI Swap Advisor. No code implementation was authorized by this organization-only action.
