# M6 runner-result intake

Date: 17 November 2026.

M6 adds a validation contract for result records supplied by a future authorized runner. It does not run that runner, replay its commands, authenticate the external run or accept the suite.

## Boundary

- The current clean direct-upstream package remains `blocked_not_runnable`; no real result file exists for it.
- Fixture results in tests only exercise the intake schema. They are not execution evidence and are not stored as project results.
- A result row must match the manifest hash, runner identity, task revision, task hash, verifier hash and planned trial index.
- A complete result set must cover every planned task/trial exactly once.
- Base-side infrastructure errors are rejected: the base verifier must end as an ordinary pytest failure with exit code 1, and the fixed verifier must pass with exit code 0.
- Model access, benchmark data, secrets, artifact uploads and automatic retries violate the result policy.
- A blocked manifest cannot accept results.

## Future flow

1. Build and validate a `ready_not_executed` M4 manifest after repository rights, owner task acceptance and execution authority exist.
2. Let the separately authorized runner produce `m6-run-result-v0` JSONL records.
3. Recompute and validate the M4 manifest from suite, source, execution and review evidence.
4. Run `validate-run-results <manifest> <results>` to check result identity, completeness and policy boundaries.

A valid result summary means only that the supplied records match the contract. It does not prove the runner ran, does not authenticate its logs and does not change task acceptance.
