# M2 upstream source verification run

Run date: 17 November 2026.

The corrected M2 workflow was executed once as GitHub Actions run [#2](https://github.com/Rajatendu1/harness-change-lab/actions/runs/44074746698). The run completed successfully in 39 seconds and uploaded no artifacts. A later independent review independently corroborated the run through the GitHub API: one `workflow_dispatch`, run attempt 1, head SHA `bd2019423420ad693cb1901a17286d2ec579378e`, five successful `ubuntu-22.04` jobs and zero artifacts.

## Run identity

- Workflow commit: `bd2019423420ad693cb1901a17286d2ec579378e`
- Workflow SHA-256: `797dd9be0702b641aab58bc20f97ac2ca74d1af5dbcf4685b38b4f5a4c1b6465`
- Trigger: one explicit `workflow_dispatch`
- Runner label: `ubuntu-22.04`
- Job timeout: 20 minutes per candidate
- Benchmark data: not downloaded or used
- Secrets, model credentials, cache and artifacts: none
- Automatic retry: none

## Results

| Candidate | Python | Base result | Fixed result | Job duration |
| --- | --- | --- | --- | --- |
| `m1-flask-dotted-blueprint` | 3.9.25 | exit 1, 2 failed | exit 0, 2 passed | 19s |
| `m1-requests-decode-unicode` | 3.7.17 | exit 1, 1 failed | exit 0, 1 passed | 19s |
| `m1-xarray-unstack-single-dim` | 3.7.17 | exit 1, 1 failed | exit 0, 1 passed | 36s |
| `m1-pylint-punctuation-notes` | 3.10.22 | exit 1, 1 failed | exit 0, 1 passed | 24s |
| `m1-pytest-number-docstring` | 3.11.18 | exit 1, 1 failed | exit 0, 1 passed | 25s |

Each job cloned only the pinned public upstream repository, computed the actual patch locally with `git diff --binary <fixed>^ <fixed> -- <matrix.test_path>`, applied only that one matrix test-path patch to the recorded base, verified that the patched base failed with ordinary pytest exit code 1, reset to the fixed commit, and verified that the same tests passed with exit code 0. The `.diff` URLs below are public review locators for the full fixed-commit diffs, not the exact applied patch identity. The exact applied files and command identities are now recorded in `suites/m1-repair-v0.execution-evidence.jsonl`.

Machine-readable execution evidence is `suites/m1-repair-v0.execution-evidence.jsonl`. Summarize it with:

```sh
python -m harnesslab.cli acceptance-status \
  suites/m1-repair-v0.candidates.jsonl \
  suites/m1-repair-v0.source-evidence.jsonl \
  suites/m1-repair-v0.execution-evidence.jsonl
```

The current acceptance status is `upstream_source_verified_not_accepted`.

## Actual base-to-fixed relation

The original source evidence omitted the fixed commit's actual first parent and the test patch URL. This section records the relation used by the M2 run; `suites/m1-repair-v0.source-evidence.jsonl` now carries the same fields for validation.

| Candidate | Fixed commit kind | Actual fixed first parent | Base relation | Gap |
| --- | --- | --- | --- | --- |
| `m1-flask-dotted-blueprint` | merge | `d8c37f43724cd9fb0870f77877b7c4c7e38a19e0` | direct-parent | 0 |
| `m1-requests-decode-unicode` | single-parent | `36453b95b13079296776d11b09cab2567ea3e703` | direct-parent | 0 |
| `m1-xarray-unstack-single-dim` | single-parent | `03d409ec35034d78a3a625dcaf1744117587b93c` | ancestor | 7 commits |
| `m1-pylint-punctuation-notes` | single-parent | `182cc539b8154c0710fcea7e522267e42eba8899` | direct-parent | 0 |
| `m1-pytest-number-docstring` | merge | `d7dbadbffcccc61876aa084affcee4240e3eb64a` | ancestor | 18 commits |

For Flask, Requests and Pylint, the selected base is the fixed commit's first parent. For Xarray, the selected base is 7 commits behind the fixed commit. For pytest, it is 18 commits behind. The GitHub comparison for both ancestor pairs reports `behind_by: 0`, so each selected base is an ancestor of its fixed commit, not a divergent branch.

The M2 observations still support the narrow execution claim for all five: the fixed-diff test patch fails on the recorded base and the same tests pass at the fixed commit. They do not prove that the 7 or 18 intermediate upstream commits are irrelevant. Keep `m1-xarray-unstack-single-dim` and `m1-pytest-number-docstring` evidence-qualified until the owner explicitly permits ancestor bases and review records why the fixed-diff regression tests isolate the claimed fix. No silent direct-parent acceptance applies to those two.

## Fixed-commit diff URLs and applied scope

These URLs are review locators for the full upstream fixed-commit diffs. The hash-pinned workflow did not download them; it computed a local first-parent diff and filtered it to one matrix `test_path` per task. For Flask, upstream changed both `tests/test_basic.py` and `tests/test_blueprints.py`, and the source evidence records both; the M2 run applied only `tests/test_blueprints.py`, which contains the two fail-to-pass tests.

- Flask: https://github.com/pallets/flask/commit/08e459e823235eecd86c635653f4bd6d6003c2b3.diff
- Requests: https://github.com/psf/requests/commit/92fe51c0afd9239388d2c8bb17dc46babdf7881f.diff
- Xarray: https://github.com/pydata/xarray/commit/329cefb99220042a586c2b5fdbea679fd8a89cd5.diff
- Pylint: https://github.com/pylint-dev/pylint/commit/a1df7685a4e6a05b519ea011f16a2f0d49d08032.diff
- pytest: https://github.com/pytest-dev/pytest/commit/084d756ae6a03bba7a257ebae3c83095b228988f.diff

The workflow filters each fixed-commit diff to the single `test_path` recorded in `suites/m1-repair-v0.execution-evidence.jsonl`; implementation files are recorded separately and are not applied to the base. Source-evidence `test_files` remains the complete list of upstream fixed-commit test-file changes.

## Runner-summary caveat

The original run's generated job summaries hardcoded the Runner row as `ubuntu-24.04`. That text was wrong. The workflow used `runs-on: ubuntu-22.04`, and GitHub's job labels for all five jobs report `ubuntu-22.04`. The workflow summary label was corrected after the run; this record preserves the caveat for the original run. The fixed-version row label was also corrected from `Fixed merge commit` to `Fixed commit` because Requests, Xarray and Pylint use single-parent fixed commits.

## Acceptance boundary

This is base-fail/fixed-pass source evidence for five upstream repair cases. It is not a model result, coding-agent benchmark, production gate or accepted five-task suite.

Remaining acceptance work:

1. Resolve the ancestor-base qualification for Xarray and pytest, either by explicit owner policy plus review or by replacing/re-basing those candidates in a separately authorized run.
2. Accept repository and benchmark-data rights for the intended evaluation use, including the undeclared SWE-bench Lite dataset metadata and the GPL-licensed Pylint source decision.
3. Record reconciled independent review against `docs/task-spec.md` for every candidate.
4. Get separate authority before any coding-agent, model or benchmark-data run.
