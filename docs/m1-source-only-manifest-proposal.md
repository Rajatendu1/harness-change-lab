# M1 source-only manifest proposal

Status: `proposal_not_accepted`

This is a draft route for removing undeclared benchmark metadata from the M1 task cards. It does not replace `suites/m1-repair-v0.candidates.jsonl`, does not accept any task and does not authorize another external run.

## Draft artifact

Machine-readable draft: `proposals/m1-repair-v0.source-only.proposed.jsonl`

The draft keeps the same five task IDs, upstream base commits, fixed commits, setup commands, verifier commands, timeouts, statuses and pending rights state. It replaces benchmark-specific provenance with direct upstream issue and pull-request provenance.

## Direct upstream evidence checked

On 17 November 2026, the GitHub API showed these issues and fix pull requests closed, with these fixed commits:

| Task | Issue | Fix PR | Fixed commit |
| --- | --- | --- | --- |
| `m1-flask-dotted-blueprint` | https://github.com/pallets/flask/issues/4041 | https://github.com/pallets/flask/pull/4045 | `08e459e823235eecd86c635653f4bd6d6003c2b3` |
| `m1-requests-decode-unicode` | https://github.com/psf/requests/issues/3359 | https://github.com/psf/requests/pull/3362 | `92fe51c0afd9239388d2c8bb17dc46babdf7881f` |
| `m1-xarray-unstack-single-dim` | https://github.com/pydata/xarray/issues/4049 | https://github.com/pydata/xarray/pull/4094 | `329cefb99220042a586c2b5fdbea679fd8a89cd5` |
| `m1-pylint-punctuation-notes` | https://github.com/pylint-dev/pylint/issues/5840 | https://github.com/pylint-dev/pylint/pull/5859 | `a1df7685a4e6a05b519ea011f16a2f0d49d08032` |
| `m1-pytest-number-docstring` | https://github.com/pytest-dev/pytest/issues/11140 | https://github.com/pytest-dev/pytest/pull/11143 | `084d756ae6a03bba7a257ebae3c83095b228988f` |

## Concrete unresolved effect

The active candidate registry and source-evidence file still contain SWE-bench Lite names, URLs, dataset SHA and instance IDs. Because both Hugging Face Lite dataset repos currently expose no license field or license tag, accepting or redistributing those task cards as suite content would carry unresolved dataset-metadata provenance. This does not invalidate the M2 execution evidence: the approved workflow cloned upstream repositories and used upstream fixed-commit diffs, not Hugging Face rows or patches.

Removing the fields from a new manifest fixes the metadata boundary, but it does not rewrite history or prove that the original five-case selection was independent of SWE-bench Lite. The project must not claim independent direct-upstream selection unless a separate selection review establishes that claim from direct upstream criteria.

## Proposed source-only schema changes

For a future `m1-task-card-source-only-v0` schema:

- Keep `id`, `issue`, `source`, `setup`, `verify`, `timeout_s`, `tags`, `status` and `rights`.
- Require `provenance.selection_source = "direct-upstream"`.
- Require `issue_url`, `issue_title`, `fix_pr_url`, `fix_pr_title`, `fixed_commit`, `test_files`, `regression_test_source` and `fail_to_pass`.
- Require the matching source-evidence record to carry `fixed_first_parent`, `base_relation`, `ancestor_gap_commits`, `fixed_commit_kind`, `implementation_files` and `test_patch_url`, so the direct-parent/ancestor distinction cannot disappear again.
- Reject `benchmark`, `instance_id`, `dataset_url`, `environment_setup_commit` and `source_version` in source-only task cards.
- Keep every task `candidate` and `rights.status = "pending"` until the owner accepts the source terms and independent review is recorded.

A matching source-evidence v1 schema should keep upstream license and fixed-commit evidence but remove the current top-level `benchmark` object. The active schemas should not change until this proposal is reviewed.

## Hash and evidence effects

The draft preserves every verifier hash because the verifier commands and timeouts are unchanged. Task hashes change because provenance and rights text are part of the deterministic task identity. After the corrected `fixed_commit` naming, the proposed suite hash is `815890ef1089065882ba8cd06bb43c877ca53d1159a672943465ea0c4f9f5115`, compared with active suite hash `b70c18f9d6be2044e5db385d4988f3762170301eafea6156662cc338143d2834`.

The existing M2 evidence can be reviewed against the draft without a new run because task IDs, base commits, fixed commits, setup commands, verifier commands and timeouts are unchanged. That is an evidence-applicability review, not automatic acceptance.

## Remaining decisions

1. Choose the conservative selection route:
   - adopt this source-only manifest as a metadata cleanup while preserving the historical SWE-bench-derived selection caveat; or
   - rebuild candidate selection from direct upstream issue/PR criteria before calling the suite source-only.
2. Decide whether ancestor bases are acceptable for Xarray and pytest, replace/re-base those candidates under separate authority, or keep both evidence-qualified.
3. Decide whether to keep the GPL-2.0 Pylint task under a no-vendoring/no-bundling distribution boundary.
4. Record reconciled independent task-spec review before any acceptance.
5. Obtain separate authority before any coding-agent, model, benchmark-data or third runner execution.

## Structural check performed locally

The draft has five lines, preserves task IDs/source/setup/verify/timeout values, matches the direct issue and PR URLs and fixed commits in the existing source evidence, and contains no `benchmark`, `instance_id`, `dataset_url`, `environment_setup_commit` or `source_version` fields.
