# M8 coding-agent smoke run

This is the run record for the bounded M8 coding-agent smoke approved for one
manual execution after the corrected workflow was verified locally. It is
pipeline evidence only: it does not claim model quality, coding-agent
effectiveness, benchmark adoption, or production readiness.

## Inputs and bounds

- Workflow: `.github/workflows/m8-coding-agent-smoke.yml`
- Run: <https://github.com/Rajatendu1/harness-change-lab/actions/runs/44092986637>
- Run outcome: success in 2 minutes 17 seconds
- Commit under test: `bff560754ae9b90ab7250cb6284366a05b6c0a17` (rewritten equivalent; the Actions run page preserves the original run reference)
- Workflow SHA-256: `7a83245ee2c44a65dbb7677c50c442d6e945e0c0d4180649257d329435efbd1b`
- Agent: Aider 0.86.2
- Model route: `groq/openai/gpt-oss-120b`
- Tasks: five accepted M1 cases
- Bounds enforced by the workflow: one trial per accepted case, one agent
  message per task, no automatic retry, no benchmark data, no artifact upload,
  no model chat publication, and a fixed hidden verifier patch applied only
  after agent exit.
- Provider spend: none; the Groq dashboard showed the Free plan before the run.

## Result summary

All five agent jobs started from the correct base commits, ran Aider once, and
exited successfully. The resulting diffs only changed `.gitignore` by one line.
All five hidden-test verifier runs failed, so the smoke found no source fix for
any task.

| Task | Agent | Diff | Verifier |
| --- | --- | --- | --- |
| `m1-flask-dotted-blueprint` | exit 0, 68s | `.gitignore` only | exit 1 |
| `m1-requests-decode-unicode` | exit 0, 70s | `.gitignore` only | exit 1 |
| `m1-xarray-unstack-single-dim` | exit 0, 70s | `.gitignore` only | exit 1 |
| `m1-click-hyphenated-help-wrap` | exit 0, 70s | `.gitignore` only | exit 1 |
| `m1-pytest-number-docstring` | exit 0, 69s | `.gitignore` only | exit 4 |

The machine-readable records are in
`proposals/m8-coding-agent-smoke.results.jsonl` (SHA-256 `a28e7eee03dfbab9d54c24b0a64213b729bddc8a288bb666ce6a6a32d4824d8f`).

## Provider usage and cleanup

The Groq API Keys page recorded 45 API calls in the previous 24 hours for the
single-purpose M8 key after the run. The dashboard's 30-day token-usage tile
had not reflected the run when checked, so no token count is claimed here.

After the completed run, the single-purpose M8 key was revoked and the
repository Actions secret used by the workflow was deleted. The pre-existing
llmgate key was not read, used, changed, or exposed.

## Interpretation

The smoke proves the corrected pipeline plumbing end-to-end for these five
executions: matrix preparation, isolated checkout, one-message agent invocation,
hidden-test patch application, verifier execution, and job-summary result
capture. It does not show that the coding agent can fix these tasks. All five
verifier outcomes failed and every produced diff was bookkeeping-only, so agent
effectiveness remains unproven on this suite.
