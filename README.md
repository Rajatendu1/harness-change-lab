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

## Not yet verified

- No real-model call, coding-agent run, container execution or benchmark result.
- No live deployment, published package, container result or real-agent run.
- Repository publication and a bounded manual isolation test are approved; actual
  CI execution is reported separately from this source state.
- No verified free inference credentials, account quota or always-on hosting.
- No finished five-task historical-repair suite or benchmark-data rights review.
- No statistical coverage/power calibration or independent validation.

The current development environment has no Docker daemon and around 2 GB RAM.
The container smoke script exits without a fallback in this environment. An
isolated, explicitly approved execution route is needed before a container run.

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
no new privileges, a non-root user and resource limits. This script has only been
syntax-checked and its missing-Docker refusal tested locally. Its runtime checks
have not yet passed on an actual container host.

## Authorship and license

Prepared by Instinct under the owner's direction. Not a claim of unaided personal
authorship. Original project code is released under the MIT license with owner approval. Upstream software and datasets keep their own terms.
