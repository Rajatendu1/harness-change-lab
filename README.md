# Harness change lab

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

The current status is `upstream_source_verified_not_accepted`. Model access was
not used for M2 and remains outside the verified scope.

## Not yet verified

- No real-model call, coding-agent run or benchmark result.
- No published package or always-on service.
- No verified free inference credentials or account quota.
- No accepted five-task historical-repair suite or benchmark-data rights review.
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
