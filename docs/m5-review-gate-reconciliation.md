# M5 review-gate reconciliation

Date: 17 November 2026.

This milestone makes the acceptance gates machine-readable without turning a review into approval. It is documentation and validator work only: no runner, model, benchmark dataset, network execution or new upstream batch was used.

## Reconciled gates

- Independent engineering review is no longer stale bookkeeping. `proposals/m3-m4-independent-review.evidence.jsonl` records the review coverage for all five direct-upstream candidates and points to the review record. The validator verifies the review's suite identity, task coverage and `acceptance_decision: none`.
- The review does not accept tasks. Every candidate still needs an owner task-acceptance decision under source-grounded authority.
- The current direct-upstream package does not need benchmark-data rights. Its task cards explicitly use direct upstream issue, pull-request, pinned repository and license metadata only, with no benchmark dataset metadata. The generic rights blocker is therefore narrowed to repository-rights acceptance for this package.
- Historical SWE-bench Lite-derived selection metadata remains factual provenance. It is not benchmark-data use and does not make the package SWE-bench-compatible. A future optional Lite-compatible evaluation would reopen the separate dataset-terms gate documented in `docs/m4-intended-use-research.md`.

## Remaining legitimate blockers

1. Accept repository rights for the intended direct-upstream evaluation use.
2. Record owner task-acceptance decisions for each candidate.
3. Obtain separate authority before any coding-agent, model, network or benchmark-data execution.

The M4 manifest remains prepare-only and blocked until those gates are resolved.

Privacy guard: public review records must use generic private-channel references, never private message IDs or phone numbers. The test suite scans public files for those identifier shapes so this does not recur.
