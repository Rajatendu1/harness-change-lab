# M8 coding-agent smoke decision

Date: 17 November 2026.

Status: execution complete. One bounded coding-agent smoke ran under the approved free route; see `docs/m8-coding-agent-smoke-run.md`. Any further coding-agent execution requires separate approval.

## Purpose

M7 proved that the accepted five-task direct-upstream suite can execute on a bounded public GitHub runner and that M6 result intake validates the resulting records. The next functional gap is an end-to-end coding-agent smoke: an agent receives a base repository and issue statement, edits the code, and the harness scores its patch with the hidden fixed-side tests.

M8 would be pipeline evidence only. Five tasks and one trial per task cannot support a model-quality, benchmark or production-readiness claim.

## Current route under consideration

- Runner: Aider, because it supports scripted single-message runs and OpenAI-compatible providers.
- Provider and model: privately verified as free, active and sufficiently provisioned before dispatch; the public run record identifies the route used.
- Credential: a fresh M8-specific provider key was created only after approval, stored only as a GitHub Actions secret for this repository's manual workflow, and revoked after the completed run.
- Platform: one manually dispatched GitHub Actions workflow on the public repository.
- Trial plan: five accepted tasks, one agent trial per task, five trials total.
- Time bound: 20 minutes per task.
- Retry policy: no automatic retries.

No provider account, credential name or quota detail is recorded in this public document. The private approval and preflight record must identify the actual provider route before execution.

## Isolation rule

A normal full-history clone can reveal the upstream fix. Before any M8 run, the runner must create the agent workspace so the agent cannot inspect the fixed commit, fixed-side test patch, M7 result records or benchmark metadata:

1. Initialize an empty repository.
2. Fetch only the accepted base commit with depth one.
3. Give the agent only the base checkout, task issue statement and ordinary repository contents available at that base.
4. Let the agent edit the checkout without shell-command suggestions, automatic tests, linting or commits.
5. Stop the agent and capture its diff.
6. In a separate harness phase after the agent has exited, fetch the fixed-side test patch and apply it to the scored copy.
7. Run the pinned verifier and emit an M6-compatible result record.

If the runner cannot prove this isolation, it must fail closed.

## Required preflight checks

Before dispatch, the run owner must verify and record:

- explicit owner approval for the selected model/provider route;
- the selected provider account remains on a free route and requires no payment-method upgrade;
- the selected model is active and its current account quota can cover five bounded trials;
- a fresh M8-specific API key is available only as a GitHub Actions secret for this repository's manual workflow;
- the workflow has no artifact upload and publishes no raw model chat logs;
- the workflow does not use benchmark data or automatic retries.

Any payment requirement, missing credential, paid-plan upgrade, quota failure or isolation failure stops the run.

## Publication boundary

A completed M8 run may publish aggregate pass/fail, task/model/provider identity, token and duration counts, workflow/configuration hashes and validation records. Raw prompts, model chat logs, API keys, private approval identifiers and private channel identifiers stay out of public evidence.

## Approval question

The exact owner decision needed is:

> Approve one free M8 coding-agent smoke on public GitHub runners, using a privately verified provider/model route and a fresh M8-specific API key stored as a repository Actions secret. Run each of the five accepted tasks once, five trials total, one Aider message per task, 20 minutes per task, no automatic retries, benchmark data, artifacts, paid plan, spending or published model chat logs. The agent sees only the base commit and issue statement; the fixed test patch remains hidden until scoring. This is an end-to-end agent pipeline smoke, not a model-quality benchmark.

## Sources

- Aider scripted runs: https://aider.chat/docs/scripting.html
- Aider model/provider connection surface: https://aider.chat/docs/llms.html
