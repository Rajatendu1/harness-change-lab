# M5 review-gate reconciliation

Date: 17 November 2026.

This milestone makes the acceptance gates machine-readable without turning a review into approval. It is documentation and validator work only: no runner, model, benchmark dataset, network execution or new upstream batch was used.

## Reconciled gates

- Independent engineering review is no longer stale bookkeeping. `proposals/m3-m4-independent-review.evidence.jsonl` records the review coverage for all five direct-upstream candidates and points to the review record. The validator verifies the review's suite identity, task coverage and `acceptance_decision: none`.
- The review does not accept tasks. Every candidate still needs an owner task-acceptance decision under source-grounded authority.
- The current direct-upstream package does not need benchmark-data rights. Its task cards explicitly use direct upstream issue, pull-request, pinned repository and license metadata only, with no benchmark dataset metadata. The generic rights blocker is therefore narrowed to repository-rights acceptance for this package.
- Historical SWE-bench Lite-derived selection metadata remains factual provenance. It is not benchmark-data use and does not make the package SWE-bench-compatible. A future optional Lite-compatible evaluation would reopen the separate dataset-terms gate documented in `docs/m4-intended-use-research.md`.

## M7 owner acceptance update

On 17 November 2026, the owner accepted the five direct-upstream test cases under their pinned MIT, BSD and Apache repository license terms and approved one bounded 15-trial verification batch on free public GitHub runners. The private approval record is retained by Instinct and is not republished here.

That approval resolves repository-rights acceptance and owner task acceptance for this direct-upstream package only. It does not approve AI evaluation, coding-agent runs, benchmark-data use, paid services or any later batch. The M4 manifest can now be `ready_not_executed` for the approved M7 runner configuration.

The review evidence row was re-bound from the candidate-suite hash to the accepted-suite hash `f6ad2081931c4ea4945d74b960596b91786a911a74d913a4c8d3d641b2e5084f`. That re-binding records only the owner status and rights bookkeeping change; it is not a new engineering review and does not turn review into acceptance.

Remaining boundary: obtain separate authority before any coding-agent, model or benchmark-data run.

Privacy guard: public review records must use generic private-channel references, never private message IDs or phone numbers. The test suite scans public files for those identifier shapes so this does not recur.
