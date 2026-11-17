# M3/M4 independent review record

Review date: 17 November 2026.

Scope: read-only review of the clean direct-parent five-task package, M3 execution record and M4 runner-manifest contract at `15b1b4976b3aa4dfd56989a77b2e27e4e639c277`. The reviewer did not execute a runner, model, benchmark dataset or new upstream batch, and did not change acceptance, rights or suite state.

## Findings

- Test isolation: supported for the applied-test delta on all five candidates. Every clean-package base is the fixed commit's first parent, so the recorded base plus applied test patch and the fixed commit differ by the upstream fix under test. This is not a claim that the tests prove every possible behavior or every unapplied upstream test-file change.
- M3 execution facts: independently corroborated through GitHub. Run `44082421716` was one `workflow_dispatch`, attempt 1, at head `6ac1091c367f787dc5586a627e41610e7581b986`, succeeded in 37 seconds, ran exactly the three changed-candidate jobs on `ubuntu-22.04`, and uploaded zero artifacts. The workflow hash matches the recorded `28edc29e5ef117430bea29c5e9e3024c32ce213f2999f8771b838ecaa77a11de`.
- Provenance and licenses: the package documents pinned issues, pull requests, commits, test files, licenses and license hashes. Click correctly has no benchmark record. Flask, Requests, Xarray and pytest preserve the factual history that the original five-case selection was SWE-bench Lite-derived. That disclosure records provenance; it is not a dataset-rights acceptance and no benchmark data was downloaded or used.
- M4 gates: the contract is prepare-only, has no silent acceptance path, recomputes task/evidence/runner/trial identity during validation, and keeps model access, network execution, benchmark data and retries outside the manifest's authority.

## Authority anchor

The M3 dispatch authority was reconciled against the original WhatsApp exchange: the proposal message `wamid.HBgMOTE5OTAzMDczNzkwFQIAERgSOUUyREE1REQ4MzhFMUREMUY0AA==` offered one free three-candidate batch with 20-minute per-candidate caps, no AI-model calls, no private data, no paid services and no automatic retries; the user replied `Yes` in `wamid.HBgMOTE5OTAzMDczNzkwFQIAEhggQUM5MkQ4QTY1QTNEMTMzNTUxOEEzM0M5Qzc2NjU1RTkA`. The reviewer confirmed that anchor. No unauthorized-run concern remains on that evidence.

## Record repair

The reviewer found that `8620bb20b3530dfa2d65b7f47de60f569ab436cd7c6dd323b9118ed4300b492a` was recorded as if it were the executed manifest file's raw-byte hash. It is the canonical suite identity hash returned by `validate-suite`. The executed manifest file's raw-byte SHA-256 is `0004c108e34b55adc2ae8a4097e40b7d927e2cb18a9a060c1f6532bfb8ca9559`. The M3 run record and clean-path research record now label both values explicitly.

## Unresolved owner decisions

These remain open and are not accepted by this review:

1. Repository rights for the intended evaluation use.
2. Treatment of the historical SWE-bench Lite-derived selection metadata for the four retained/rebased candidates.
3. Any future coding-agent, model, network or benchmark-data execution.

Ordinary engineering work that remains is recording review outcomes, maintaining the clean package and building only non-executing contracts until those decisions and separate execution authority exist.
