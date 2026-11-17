# M2 upstream source verification run

Run date: 17 November 2026.

The corrected M2 workflow was executed once as GitHub Actions run [#2](https://github.com/Rajatendu1/harness-change-lab/actions/runs/44074746698). The run completed successfully in 39 seconds and uploaded no artifacts.

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

Each job cloned only the pinned public upstream repository, applied only the fixed merge commit's first-parent test-file patch to the recorded base, verified that the patched base failed with ordinary pytest exit code 1, reset to the fixed merge commit, and verified that the same tests passed with exit code 0.

Machine-readable execution evidence is `suites/m1-repair-v0.execution-evidence.jsonl`. Summarize it with:

```sh
python -m harnesslab.cli acceptance-status \
  suites/m1-repair-v0.candidates.jsonl \
  suites/m1-repair-v0.source-evidence.jsonl \
  suites/m1-repair-v0.execution-evidence.jsonl
```

The current acceptance status is `upstream_source_verified_not_accepted`.

## Runner-summary caveat

The original run's generated job summaries hardcoded the Runner row as `ubuntu-24.04`. That text was wrong. The workflow used `runs-on: ubuntu-22.04`, and GitHub's job labels for all five jobs report `ubuntu-22.04`. The workflow summary label was corrected after the run; this record preserves the caveat for the original run.

## Acceptance boundary

This is base-fail/fixed-pass source evidence for five upstream repair cases. It is not a model result, coding-agent benchmark, production gate or accepted five-task suite.

Remaining acceptance work:

1. Accept repository and benchmark-data rights for the intended evaluation use, including the undeclared SWE-bench Lite dataset metadata and the GPL-licensed Pylint source decision.
2. Record independent review against `docs/task-spec.md` for every candidate.
3. Get separate authority before any coding-agent, model or benchmark-data run.
