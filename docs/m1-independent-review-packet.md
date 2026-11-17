# M1 independent task-spec review packet

Status: `repaired_pending_reconciliation`

This packet lets a separate reviewer inspect the M1 candidates against `docs/task-spec.md` without rerunning upstream code. A review recorded here is evidence-quality review only; it does not resolve rights acceptance or authorize a coding-agent, model or benchmark-data run.

The first independent review returned `needs-changes`: it corroborated the core five-case M2 run claim, but found absent actual first-parent and test-patch fields, two ancestor-base relations, nonexistent template task IDs and stale documentation links. This revision repairs those records. A fresh reviewer reconciliation is still required before any accepted-suite or fully supported evidence claim.

## Reviewer requirements

- The reviewer must be a separate person or task agent from the author of the M1 registry, M2 workflow and M2 evidence record.
- The reviewer should use this packet, the public GitHub pages and a fresh read of the repository files.
- The reviewer must not run upstream tests or dispatch a workflow. The existing M2 run is the execution evidence under review.
- The reviewer must record any uncertainty instead of treating it as acceptance.
- The reviewer must not change task acceptance status. Only the project owner can accept rights and mark tasks accepted after review.
- For an ancestor-base pair, the reviewer must not silently apply direct-parent acceptance. The reviewer should either qualify the pair or record why the fixed-diff test patch isolates the claimed fix despite intermediate upstream commits.

## Materials

- Task specification: `docs/task-spec.md`
- Candidate registry: `suites/m1-repair-v0.candidates.jsonl`
- M2 source evidence: `suites/m1-repair-v0.source-evidence.jsonl`
- M2 workflow: `.github/workflows/m2-upstream-verification.yml`
- M2 execution record: `docs/m2-verification-run.md`
- M2 execution evidence: `suites/m1-repair-v0.execution-evidence.jsonl`
- Current status command: `python -m harnesslab.cli acceptance-status suites/m1-repair-v0.candidates.jsonl suites/m1-repair-v0.source-evidence.jsonl suites/m1-repair-v0.execution-evidence.jsonl`
- GitHub run page: https://github.com/Rajatendu1/harness-change-lab/actions/runs/44074746698

## Checks for every candidate

1. The registry has one JSONL record and the required task-spec fields.
2. The base is a public upstream repository and a fixed full commit SHA.
3. The fixed version is identified by an exact upstream commit, not a branch name.
4. The focused fail-to-pass command is recorded.
5. The upstream source-evidence record gives the base license URL, base license file hash, fixed commit, fixed-commit kind, actual fixed first parent, base relation, ancestor gap, implementation files, test files and fixed-commit test patch URL.
6. For a `direct-parent` relation, the fixed first parent matches the selected base commit and the ancestor gap is zero. Flask, Requests and Pylint currently satisfy this direct-parent check.
7. For an `ancestor` relation, the actual fixed first parent and positive ancestor gap are recorded and the pair stays evidence-qualified. Xarray is 7 commits back from its fixed commit and pytest is 18 commits back; neither is accepted by direct-parent evidence alone.
8. The execution evidence names the workflow SHA and workflow file hash used for the run.
9. The M2 execution evidence records the exact local patch identity (`git diff --binary <fixed>^ <fixed> -- <matrix.test_path>`) and one applied test file per task. The `.diff` URL is a public full-diff review locator, not the exact applied patch identity.
10. The base run is expected to fail and the fixed run is expected to pass.
11. The execution record gives the runner Python/dependency compatibility evidence and run timing.
12. No benchmark dataset rows, saved artifacts, secrets, model credentials, paid fallback or automatic retry are present.
13. Any license or dataset-rights concern remains marked pending rather than accepted.
14. The candidate remains `candidate` until rights acceptance, ancestor-base resolution where applicable and this independent review are all recorded.

## Review record template

Reviewer:

Date:

Reviewer identity and independence:

Repository revision reviewed:

M2 run URL reviewed:

| Task | Evidence-quality verdict | Rights verdict | Notes |
| --- | --- | --- | --- |
| `m1-flask-dotted-blueprint` | pass / fail / needs-changes | pending | |
| `m1-requests-decode-unicode` | pass / fail / needs-changes | pending | |
| `m1-xarray-unstack-single-dim` | pass / fail / needs-changes | pending | |
| `m1-pylint-punctuation-notes` | pass / fail / needs-changes | pending | |
| `m1-pytest-number-docstring` | pass / fail / needs-changes | pending | |

Overall evidence-quality verdict: pass / fail / needs-changes

Reviewer comments:

Signed review hash or transcript URL:

## Boundary

A passing evidence-quality review means the task cards and M2 run are internally consistent with `docs/task-spec.md`. It does not mean the suite is accepted for agent evaluation. Acceptance still needs the rights decisions in `docs/m1-rights-qualification.md`, explicit ancestor-base resolution for Xarray and pytest, and separate authority before any coding-agent, model or benchmark-data execution.
