# M1 independent task-spec review packet

Status: `prepared_not_reviewed`

This packet lets a separate reviewer inspect the M1 candidates against `docs/task-spec.md` without rerunning upstream code. A review recorded here is evidence-quality review only; it does not resolve rights acceptance or authorize a coding-agent, model or benchmark-data run.

## Reviewer requirements

- The reviewer must be a separate person or task agent from the author of the M1 registry, M2 workflow and M2 evidence record.
- The reviewer should use this packet, the public GitHub pages and a fresh read of the repository files.
- The reviewer must not run upstream tests or dispatch a workflow. The existing M2 run is the execution evidence under review.
- The reviewer must record any uncertainty instead of treating it as acceptance.
- The reviewer must not change task acceptance status. Only the project owner can accept rights and mark tasks accepted after review.

## Materials

- Task specification: `docs/task-spec.md`
- Candidate registry: `suites/m1-repair-v0.candidates.jsonl`
- M2 source-evidence generation script: `scripts/generate_m2_source_evidence.py`
- M2 source evidence: `suites/m1-repair-v0.source-evidence.jsonl`
- M2 workflow: `.github/workflows/m2-upstream-verification.yml`
- M2 execution record: `docs/m2-verification-run.md`
- M2 execution evidence: `suites/m1-repair-v0.execution-evidence.jsonl`
- Current status command: `python -m harnesslab.cli acceptance-status suites/m1-repair-v0.candidates.jsonl suites/m1-repair-v0.source-evidence.jsonl suites/m1-repair-v0.execution-evidence.jsonl`
- GitHub run page: https://github.com/Rajatendu1/harness-change-lab/actions/runs/44074746698

## Checks for every candidate

1. The registry has one JSONL record and the required task-spec fields.
2. The base is a public upstream repository and a fixed full commit SHA.
3. The fixed version is identified by an exact upstream merge commit or release tag, not a branch name.
4. The focused fail-to-pass command is recorded.
5. The upstream source-evidence record gives the base license URL, base license file hash, fixed merge commit, fixed-merge first parent and test patch URL.
6. The fixed-merge first parent matches the selected base commit, so the fixed commit is a direct child of the base.
7. The execution evidence names the workflow SHA and workflow file hash used for the run.
8. The M2 execution evidence records one upstream test patch file and applies that patch only to the base checkout.
9. The base run is expected to fail and the fixed run is expected to pass.
10. The execution record gives the runner Python/dependency compatibility evidence and run timing.
11. No benchmark dataset rows, saved artifacts, secrets, model credentials, paid fallback or automatic retry are present.
12. Any license or dataset-rights concern remains marked pending rather than accepted.
13. The candidate remains `candidate` until rights acceptance and this independent review are both recorded.

## Review record template

Reviewer:

Date:

Reviewer identity and independence:

Repository revision reviewed:

M2 run URL reviewed:

| Task | Evidence-quality verdict | Rights verdict | Notes |
| --- | --- | --- | --- |
| `flask-2-2-x-dev-requirements-install` | pass / fail / needs-changes | pending | |
| `requests-2-28-x-certifi-install` | pass / fail / needs-changes | pending | |
| `xarray-2022-03-0-numpy-1-22-install` | pass / fail / needs-changes | pending | |
| `pylint-2-13-x-astroid-install` | pass / fail / needs-changes | pending | |
| `pytest-7-2-x-legacy-py-removal` | pass / fail / needs-changes | pending | |

Overall evidence-quality verdict: pass / fail / needs-changes

Reviewer comments:

Signed review hash or transcript URL:

## Boundary

A passing evidence-quality review means the task cards and M2 run are internally consistent with `docs/task-spec.md`. It does not mean the suite is accepted for agent evaluation. Acceptance still needs the rights decisions in `docs/m1-rights-qualification.md` and separate authority before any coding-agent, model or benchmark-data execution.
