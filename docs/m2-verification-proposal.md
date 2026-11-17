# M2 candidate verification proposal

Prepared on 17 November 2026. The corrected bounded workflow was later approved and executed once. This file remains the proposal and scope record; the result is in `docs/m2-verification-run.md`.

## What is now prepared without a new run

`suites/m1-repair-v0.source-evidence.jsonl` records the original public GitHub issue, pull request, pinned base commit, fixed merge commit, changed test files, pinned license file hash and current SWE-bench Lite dataset metadata for each of the five candidates.

`plan-verification` validates that evidence against the candidate registry and emits a deterministic base-fail/fixed-pass plan:

```sh
python -m harnesslab.cli plan-verification \
  suites/m1-repair-v0.candidates.jsonl \
  suites/m1-repair-v0.source-evidence.jsonl
```

The command runs no upstream repository code, installs no dependency, calls no model and executes no sandbox. The current prepared plan hash is `8394a07624bf4d563df65678e72a3786dacc11ba22b82a092069dc7d5b6c2e26` for suite hash `b70c18f9d6be2044e5db385d4988f3762170301eafea6156662cc338143d2834`.

## Source and rights boundary

This M2 proposal is intentionally narrower than a benchmark run:

- The workflow must **not** download SWE-bench data, apply its `patch` or `test_patch` fields, upload benchmark records or redistribute Hugging Face dataset content.
- It verifies only the manually curated public-upstream evidence already recorded in this repository: the named public repository, pinned base and fixed commits, and test command.
- Upstream code execution is governed by the upstream repository licenses recorded in `suites/m1-repair-v0.source-evidence.jsonl`.
- The five candidates were selected with SWE-bench Lite provenance. Both the legacy `princeton-nlp/SWE-bench_Lite` dataset and the current `SWE-bench/SWE-bench_Lite` Hugging Face metadata currently expose no dataset license field/tag. Permission to use or redistribute benchmark metadata and task content remains unresolved.
- Because of that gap, an M2 base-fail/fixed-pass result would verify the five upstream source pairs only. It would not complete benchmark rights review, make this an accepted SWE-bench suite, or authorize benchmark redistribution/use.

## Why fresh approval is needed

The completed manual Docker pilot was a fixed-code isolation smoke. Its one-time scope is consumed. M2 would be a new external run: it would clone upstream repositories, install their dependencies and execute upstream tests. That is not covered by the earlier fixed-code smoke approval.

Model access is **not** required for this M2 verification. It would only become relevant for a later coding-agent baseline/candidate run, after the tasks are accepted.

## Minimal proposed approval scope

If approved, add and manually dispatch one new workflow with this exact scope:

- One explicit `workflow_dispatch` run only.
- Five matrix jobs, one per candidate, on GitHub-hosted `ubuntu-22.04` runners.
- At most 20 minutes per candidate job.
- `permissions: contents: read`; no secrets, model credentials, repository write scope, cache, artifact upload, package publication or paid resource.
- Clone only the public repository named by each candidate.
- Checkout the pinned base commit and run the listed verifier command; expected result: at least one fail-to-pass test fails.
- Checkout the recorded fixed merge commit and run the same verifier command; expected result: all listed tests pass.
- Install only dependencies declared by that upstream repository, using public GitHub/PyPI access.
- Write a job summary with task ID, commit SHAs, command exit codes, duration and dependency versions. Do not commit results automatically.
- Any unexpected pass/fail result keeps the candidate at `candidate`; it does not get edited to match an expected story.

## Free-runner guard

GitHub's current billing documentation says standard GitHub-hosted runners in public repositories remain free independently of included compute usage, while larger runners are billed for public repositories. GitHub's current limits documentation gives a Free account 20 concurrent standard GitHub-hosted jobs; this proposal needs 5. The repository is public, the workflow must use only standard `ubuntu-22.04`, and it must not use larger runners, cache or artifacts.

If GitHub reports that the repository is no longer public, asks for a paid runner, or cannot schedule standard public-repo runners without billing, cancel the run. There is no paid fallback.

## Result interpretation

A successful M2 run is base-fail/fixed-pass execution evidence only. It is still not a model result, coding-agent benchmark, production gate or accepted five-task suite. A candidate moves to `accepted` only after this execution evidence and the rights review are both complete.
