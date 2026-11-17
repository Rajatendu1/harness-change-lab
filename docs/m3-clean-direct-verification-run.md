# M3 clean direct-path source verification run

Run date: 17 November 2026.

The fixed clean-path workflow was executed once as GitHub Actions run [#1](https://github.com/Rajatendu1/harness-change-lab/actions/runs/44082421716). The run completed successfully in 37 seconds. It tested exactly the three candidates whose evidence changed in the clean-path proposal: the Xarray rebase, the Click replacement and the pytest rebase. Flask and Requests were not rerun; their applicable M2 execution evidence remains unchanged.

## Run identity

- Workflow commit: `6ac1091c367f787dc5586a627e41610e7581b986`
- Workflow SHA-256: `28edc29e5ef117430bea29c5e9e3024c32ce213f2999f8771b838ecaa77a11de`
- Executed manifest: `proposals/m1-direct-parent-clean-path.research.jsonl`
- Executed manifest raw-byte SHA-256: `0004c108e34b55adc2ae8a4097e40b7d927e2cb18a9a060c1f6532bfb8ca9559`
- Executed manifest canonical suite identity hash: `8620bb20b3530dfa2d65b7f47de60f569ab436cd7c6dd323b9118ed4300b492a`
- Trigger: one explicit `workflow_dispatch`
- Runner label: `ubuntu-22.04`
- Job timeout: 20 minutes per candidate
- Benchmark data: not downloaded or used
- Secrets, model credentials, cache and artifacts: none
- Automatic retry: none

## Results

| Candidate | Python | Base result | Fixed result | Job |
| --- | --- | --- | --- | --- |
| `m1-xarray-unstack-single-dim` | 3.7.17 | exit 1, 1 failed | exit 0, 1 passed | [134036120241](https://github.com/Rajatendu1/harness-change-lab/actions/runs/44082421716/job/134036120241) |
| `m1-click-hyphenated-help-wrap` | 3.11.18 | exit 1, 3 failed | exit 0, 3 passed | [134036119660](https://github.com/Rajatendu1/harness-change-lab/actions/runs/44082421716/job/134036119660) |
| `m1-pytest-number-docstring` | 3.11.18 | exit 1, 1 failed | exit 0, 1 passed | [134036119928](https://github.com/Rajatendu1/harness-change-lab/actions/runs/44082421716/job/134036119928) |

Each job cloned only its pinned public upstream repository, computed the first-parent fixed-commit test diff for the focused matrix test path, applied only that test patch to the direct-parent base, observed an ordinary pytest failure with exit code 1, reset to the fixed commit and observed the same focused verifier pass with exit code 0. Base exits other than ordinary pytest failure failed closed. Fixed-side failures failed the job. No job was retried.

Machine-readable records are:

- Source evidence: `proposals/m1-direct-parent-clean-path.source-evidence.jsonl`
- Execution evidence: `proposals/m1-direct-parent-clean-path.execution-evidence.jsonl`

Summarize the clean-path package with:

```sh
python -m harnesslab.cli acceptance-status \
  proposals/m1-direct-parent-clean-path.research.jsonl \
  proposals/m1-direct-parent-clean-path.source-evidence.jsonl \
  proposals/m1-direct-parent-clean-path.execution-evidence.jsonl
```

The resulting status is `upstream_source_verified_not_accepted`: 5 tasks, 5 with upstream-source execution evidence, 0 accepted, 5 rights reviews pending, 0 model or agent runs and no benchmark-data use.

## Scope boundary

This run verifies upstream source behavior for the three changed candidates. It is not a coding-agent result, model-quality result, benchmark-dataset run, production gate or suite acceptance. It does not complete the harness project.

Remaining acceptance work:

1. Accept repository rights for the intended evaluation use and resolve the historical SWE-bench Lite selection metadata retained on Flask, Requests, Xarray and pytest.
2. Record independent review against `docs/task-spec.md` for every candidate.
3. Get separate authority before any coding-agent, model or benchmark-data run.
