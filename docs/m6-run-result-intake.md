# M6 runner-result intake

Date: 17 November 2026.

M6 adds a validation contract for result records supplied by a future authorized runner. It does not run that runner, replay its commands, authenticate the external run or accept the suite.

## Boundary

- After the M7 owner acceptance, the clean direct-upstream package can produce a `ready_not_executed` manifest for the approved M7 runner configuration. No real result file exists yet.
- Fixture results in tests only exercise the intake schema. They are not execution evidence and are not stored as project results.
- A result row must match the manifest hash, runner identity, task revision, task hash, verifier hash and planned trial index.
- A complete result set must cover every planned task/trial exactly once.
- Base-side infrastructure errors are rejected: the base verifier must end as an ordinary pytest failure with exit code 1, and the fixed verifier must pass with exit code 0.
- Model access, benchmark data, secrets, artifact uploads and automatic retries violate the result policy.
- A blocked manifest cannot accept results.

## M7 flow

1. Build and validate the `ready_not_executed` M4 manifest from the accepted suite, source evidence, execution evidence and review evidence.
2. Dispatch the approved M7 workflow once: five tasks, three trials each, 15 jobs, `ubuntu-22.04`, 20 minutes per job, at most five concurrent jobs, no automatic retries, models, benchmark data, secrets or artifact uploads.
3. Extract the `M6_RESULT_JSON=` lines from that run's logs into a result JSONL file.
4. Recompute and validate the M4 manifest from suite, source, execution and review evidence.
5. Run `validate-run-results <manifest> <results>` to check result identity, completeness and policy boundaries.

A valid result summary means only that the supplied records match the contract. It does not prove the runner ran, does not authenticate its logs and does not change task acceptance.
