# Harness change lab

## Latest verified checkpoint

18 November 2026: [Flask narrow-task preparation](docs/flask-preparation.md) now has local unchanged-base/fix/reference controls, hash-bound source transfer and a separate offline verifier input plan. One blueprint-name test fails on the base and passes on both reference fixes. This is trusted-process local evidence, not Docker qualification or an AI repair. The complete 150-file development/test-support snapshot was downloaded from the pinned public revision, hash-checked and tested: 347 local tests passed with no skips. No new provider request or workflow dispatch was made.

Reproducibility correction: the earlier 121-file manifest left out 19 legacy files needed by the full test command. Its earlier full-suite pass used a fuller checkout. The current manifest explicitly lists those test-support prerequisites. This corrects the snapshot boundary, not the separate recorded runtime results.

18 November 2026: the local [supplied runner evidence intake](docs/evidence-intake.md) feeds the paired-comparison CLI. It excludes canned/reference results and transport errors from model-repair metrics, refuses incomplete or changed planned records, and keeps one-task/fixture evidence inconclusive. Its earlier fuller-checkout test count was 318. This remains offline software validation, not a new model attempt or changed-image runtime qualification.

18 November 2026: the [single live Click attempt](https://github.com/Rajatendu1/harness-change-lab/actions/runs/44236654519) was excluded after one failed provider transport attempt. No repair was collected, usage and failure cause are unknown, and there was no retry. The temporary provider key was revoked and repository secret deleted, both verified afterward. [Result and remaining diagnostic gap](docs/click-live-attempt-result.md). The model-free mapping pass below remains valid but is not a model repair.

18 November 2026: the separate [Click model-free task mapping diagnostic passed](https://github.com/Rajatendu1/harness-change-lab/actions/runs/44235253963) on its first dispatch. Unchanged source failed 3/3 focused cases; the upstream reference and actual Aider canned edit passed 3/3 in fresh verifier containers. Cleanup completed. This made zero provider calls and demonstrates zero model repairs. [Result, exact inputs and limits](docs/click-model-free-result.md). Local development checks for this newer archive: 283 passed, no skips; the older 92-file source snapshot below remains distinct.

18 November 2026: the fixed model-free Docker adapter check [passed on GitHub Actions](https://github.com/Rajatendu1/harness-change-lab/actions/runs/44226880573). It exercised separate offline-built agent/verifier images, PID/memory/CPU/disk/timeout checks, one canned-response Aider edit, protected fixture controls and cleanup. [Result, failure history and limits](docs/fixed-runtime-result.md).

This is not a real AI repair result, adversarial-scoring proof or production-ready runner. The run made zero provider calls. The earlier real-agent smoke run remains zero successful source repairs.

Readable runtime sources, fixed input manifests, development tests and required legacy test-support files are in the normal repository tree. The current `source-publication-manifest.json` records the pinned 150-file development snapshot tested above; earlier 92-file and 121-file publications remain historical checkpoints, with the 121-file standalone-test limitation corrected above. Historical documents are not necessarily current. Runtime-only archives remain immutable run inputs, not the primary source-editing interface. No private handoffs, credentials, chats or repository history were added in this publication.

A proposed paired-regression workflow for coding-agent harness changes.

Work-in-progress foundation, not a released agent runner. The earlier working name
"agentfit" was retired because existing projects already use it.

## What works locally

- A standard-library Python CLI compares paired task/trial outcomes.
- Task revisions and verifier hashes must match. Missing pairs, duplicate rows,
  malformed booleans, unscored outcomes and changed verifiers fail closed.
- Percentile bootstrap intervals resample task clusters, keeping repeated trials
  together and weighting tasks equally. A fixed seed makes analysis repeatable.
- The verdict distinguishes regression, no detected regression, and insufficient
  evidence. The default minimum of 20 tasks is an engineering policy, not a power
  calculation. Small and degenerate samples abstain.
- An optional Inspect 0.3.290 integration check writes and reads a real Inspect log
  using fixed mock responses. This is synthetic plumbing evidence, not model
  quality or sandbox evidence.
- A deterministic M4 manifest contract prepares and validates a future external
  runner package without starting it. Candidate, rights-pending or otherwise
  blocked suites produce `blocked_not_runnable` with exact blockers; task,
  verifier, provenance, runner and trial-plan hashes are recomputed during
  validation.

```sh
python -m unittest discover -s tests -v
python -m harnesslab.cli compare baseline.jsonl candidate.jsonl
```

CLI exit codes: `0` no detected regression within the declared margin; `1`
regression; `2` invalid input; `3` insufficient evidence. A zero exit code is not a
claim of equivalence, population-level safety, or production readiness.

Each input line has `task_id`, nonnegative integer `trial`, boolean `passed`,
`task_revision`, `verifier_sha256` and `status` (`scored`). Provider/model identity,
run provenance, evidence class and budget metadata still need a signed-off run
manifest before these results can drive a real CI gate. User-provided JSONL is
not authenticated experimental evidence.

## Build on existing tools

[Inspect](https://inspect.aisi.org.uk/) already provides model adapters, agents,
sandbox interfaces and logs. It is the current runner integration candidate, not
something this project claims to have invented.

[promptfoo](https://www.promptfoo.dev/docs/guides/evaluate-coding-agents/) supports
coding-agent evaluations, repeated runs and CI gates.
[AgentFit](https://github.com/kingkyylian/agentfit) checks agent instruction files,
runs tasks and compares composite reports. Its `compareReports` implementation
at source revision `6800623417bff00aa324e51fa032ad5178843d06` compares aggregate
scores and check lists. That is a scoped observation about that source, not a
claim that other products lack paired statistics.
[SWE-bench](https://github.com/SWE-bench/SWE-bench) provides repair tasks and a
Docker evaluator. Its full reference footprint is not assumed to fit our pilot.

The proposed value is a reproducible small-team workflow with a pinned repair
suite, protected verifiers, paired uncertainty reports and an understandable
regression policy. No novelty, adoption or production claim is made.

## Verified container-route pilot

On 17 November 2026, the manually dispatched fixed-code isolation smoke passed on
GitHub's standard Ubuntu 24.04 runner. The job took 18 seconds (24 seconds total
workflow duration). [Read the run and logs](https://github.com/Rajatendu1/harness-change-lab/actions/runs/44047033684).

The probes confirmed UID 65534, a read-only root, no new privileges, no Linux
capabilities, blocked external network access and no Docker socket. The controller
checked no bind mounts, devices or privileged mode, enforced 256 MiB RAM, 1 CPU
and 64 PIDs, and removed the container. No build artifacts or caches were uploaded.
The manual workflow has a 10-minute timeout and read-only repository permissions.

This is **fixed-code container smoke evidence only**, not an agent benchmark,
model-quality result, completed repair suite or hardened multi-tenant sandbox.
The source code is published under MIT with owner approval.

## M1 candidate registry

A five-candidate structural registry now exists at
`suites/m1-repair-v0.candidates.jsonl` with deterministic task and verifier
hashes, provenance and pending rights reviews. Validate it without executing
external code:

```sh
python -m harnesslab.cli validate-suite suites/m1-repair-v0.candidates.jsonl
```

This is candidate-registry progress only. It has 5 candidates and 0 accepted
tasks. The M2 run now provides base-fail/fixed-pass evidence for all five
upstream source pairs, but rights review and independent task-spec review are
still open.

Original-source metadata for those candidates is recorded in
`suites/m1-repair-v0.source-evidence.jsonl`. The completed M2 execution
evidence is recorded in `suites/m1-repair-v0.execution-evidence.jsonl` and
`docs/m2-verification-run.md`. Summarize verified evidence and remaining
acceptance blockers without running upstream code:

```sh
python -m harnesslab.cli acceptance-status \
  suites/m1-repair-v0.candidates.jsonl \
  suites/m1-repair-v0.source-evidence.jsonl \
  suites/m1-repair-v0.execution-evidence.jsonl
```

The original-suite status is `upstream_source_verified_not_accepted`. The rights
decision split is recorded in `docs/m1-rights-qualification.md`, and the prepared
no-rerun independent review process is in
`docs/m1-independent-review-packet.md`. Model access was not used for M2 and
remains outside the verified scope.

## M3 clean direct-path candidate package

A separate clean-path proposal now has a structurally validated direct-upstream
manifest, source evidence and execution evidence for five candidate tasks. The
manifest supports both the original benchmark-derived provenance shape and the
new direct-upstream shape without treating either as acceptance. The 17 November
M3 run verified the three changed candidates (Xarray rebase, Click replacement
and pytest rebase); Flask and Requests keep their applicable M2 evidence. The
package status is `upstream_source_verified_not_accepted`: five upstream-source
verified candidates, zero accepted tasks, pending rights and independent review.

```sh
python -m harnesslab.cli acceptance-status \
  proposals/m1-direct-parent-clean-path.research.jsonl \
  proposals/m1-direct-parent-clean-path.source-evidence.jsonl \
  proposals/m1-direct-parent-clean-path.execution-evidence.jsonl
```

See `docs/m3-clean-direct-verification-run.md` for the one-shot M3 run record
and `docs/m3-m4-independent-review.md` for the read-only independent review.
See `docs/m4-intended-use-research.md` for the current benchmark intended-use
and dataset-terms boundary, and `docs/m5-review-gate-reconciliation.md` for the
machine-readable review/acceptance gate split.
This package is candidate evidence only; it is not an adopted suite, model
result, coding-agent benchmark or completed harness milestone.

## M4 runner-manifest contract

`prepare-run-manifest` converts a task suite, source evidence and execution
evidence into a deterministic future-runner contract. It records runner name,
version and configuration hash, task/verifier/provenance hashes, trial count,
concurrency, timeout budget, execution policy and approval gates. It does not
start a runner or call a model.

```sh
python -m harnesslab.cli prepare-run-manifest \
  proposals/m1-direct-parent-clean-path.research.jsonl \
  proposals/m1-direct-parent-clean-path.source-evidence.jsonl \
  proposals/m1-direct-parent-clean-path.execution-evidence.jsonl \
  proposals/m3-m4-independent-review.evidence.jsonl \
  --runner-name fixture-runner \
  --runner-version 0.1.0 \
  --runner-config-sha256 0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef
```

The current clean-path package exits with code 3 and status
`blocked_not_runnable`. The machine-readable review evidence records that
independent read-only review exists, while owner task acceptance and repository
rights remain pending. `validate-run-manifest` recomputes the contract from the
same suite, source, execution and review evidence, and rejects altered task
commands, verifier identity, provenance, runner identity, trial plan, review
scope or approval state. This is usable fail-closed harness behavior, not an
Inspect or promptfoo adapter claim.

## M6 result-intake validation

`validate-run-results` checks supplied `m6-run-result-v0` JSONL records against
a ready M4 manifest. It requires one complete record per planned task/trial,
matching runner/task/verifier identity, ordinary base failure and fixed pass,
and no model access, benchmark data, secrets, artifact uploads or retries. It
rejects results for a blocked manifest. The command validates records only; it
does not execute, replay or authenticate a runner. See
`docs/m6-run-result-intake.md` and the one-shot M7 run record in
`docs/m7-direct-upstream-verifier-run.md`. The M7 records validate against the
prepared manifest; they verify harness execution and intake only, not AI
evaluation.

## Not yet verified

- No real-model call, coding-agent run or benchmark result.
- No published package or always-on service.
- No verified free inference credentials or account quota.
- No coding-agent, model or benchmark-data rights review or run. The five-task
  historical-repair suite is accepted only for direct-upstream verification.
- No statistical coverage/power calibration or independent validation.

The local development environment has no Docker daemon and around 2 GB RAM.
The local missing-Docker refusal and the successful remote pilot are separate
checks. The first build milestone remains incomplete.

## Optional integration check

Inspect requires Python 3.11+. Dependencies are pinned and hash-locked.

```sh
uv venv --python 3.12 .venv
uv pip sync --python .venv/bin/python --require-hashes requirements-runtime.lock
.venv/bin/python scripts/inspect_mock_contract.py
```

The container smoke is deliberately separate:

```sh
python scripts/container_smoke.py
```

It uses fixed test code, not an agent or downloaded target. It requires an
existing Docker engine, at least 8 GiB free disk and a pinned public Python image.
It sets no network, no host mounts, a read-only root filesystem, no capabilities,
no new privileges, a non-root user and resource limits. The local refusal path and the remote fixed-code runtime checks have both been
exercised. The linked pilot is the evidence for the remote checks, not for an
agent run.

## Authorship and license

Prepared by Instinct under the owner's direction. Not a claim of unaided personal
authorship. Original project code is released under the MIT license with owner approval. Upstream software and datasets keep their own terms.
