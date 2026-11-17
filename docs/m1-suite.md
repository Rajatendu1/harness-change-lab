# M1 repair suite: candidate registry

`suites/m1-repair-v0.candidates.jsonl` is a five-task candidate registry for the first repair suite. It is deliberately **not** an accepted benchmark suite yet.

Current state:

- 5 structural candidates.
- 5 upstream source pairs with M2 base-fail/fixed-pass evidence; see `docs/m2-verification-run.md`.
- 0 accepted tasks.
- 5 rights reviews still pending; the current license findings are in `docs/m1-rights-review.md`.
- 0 independent task-spec reviews.
- 0 agent or real-model runs.
- 0 benchmark results.

The candidates are derived from public Python repair instances in [princeton-nlp/SWE-bench_Lite](https://huggingface.co/datasets/princeton-nlp/SWE-bench_Lite). The registry keeps the source repository, pinned base commit, source benchmark instance ID, environment setup commit and fail-to-pass tests with every task. The candidate digest is computed from the full manifest; each task also has a separate `task_revision` and `verifier_sha256` for comparison and audit.

## Candidate selection

The initial registry chooses one candidate from each of five upstream projects:

- Flask
- Requests
- Xarray
- Pylint
- pytest

The setup commands are provisional candidate setup notes. They are not model or benchmark evidence. A task can move from `candidate` to `accepted` only after:

1. The upstream repository license and benchmark-data terms are reviewed.
2. The base revision is checked out in the approved isolated runner.
3. The base verifier fails on the recorded source with the regression tests applied.
4. The known fixed revision or reference patch passes the same verifier.
5. Runtime, dependency and network behavior are recorded in the run manifest.
6. The task gets an independent review against the task-spec rules.

The M2 run completed checks 2 through 5 for the five upstream source pairs. Checks 1 and 6 remain open, so every task stays a candidate and no result is an M1 benchmark result.

## Validation command

Structural validation is local and does not execute task code:

```sh
python -m harnesslab.cli validate-suite suites/m1-repair-v0.candidates.jsonl
```

The validator checks duplicate task IDs, source pinning to a full commit SHA, public GitHub clone URLs, deterministic verifier commands, timeout bounds, provenance fields, fail-to-pass identity, status consistency and rights-review consistency. It prints deterministic task and suite hashes. A separate accepted-suite gate can require accepted tasks:

```sh
python -m harnesslab.cli validate-suite suites/m1-repair-v0.accepted.jsonl --min-accepted 5
```

No such accepted suite exists yet.

## Original-source evidence and M2 result

`suites/m1-repair-v0.source-evidence.jsonl` records the original GitHub issue,
fix pull request, pinned base commit, fixed merge commit, changed test files and
pinned license evidence for every candidate. It is metadata, not execution
evidence.

The completed M2 execution evidence is recorded in
`suites/m1-repair-v0.execution-evidence.jsonl` and `docs/m2-verification-run.md`.
Check the acceptance state without rerunning upstream code:

```sh
python -m harnesslab.cli acceptance-status \
  suites/m1-repair-v0.candidates.jsonl \
  suites/m1-repair-v0.source-evidence.jsonl \
  suites/m1-repair-v0.execution-evidence.jsonl
```

The status is `upstream_source_verified_not_accepted` because rights review and
independent task-spec review remain open. See `docs/m2-verification-proposal.md`
for the original bounded execution scope.
