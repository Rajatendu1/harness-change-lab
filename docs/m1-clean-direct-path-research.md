# M1 clean direct-path research

Status: accepted for the approved M7 direct-upstream verification batch, 17 Nov 2026. The original five-case selection was SWE-bench Lite-derived; this record preserves that history while making the forward path direct-upstream and direct-parent. The acceptance applies only to the five open-source test cases and one bounded 15-trial verification batch; it is not AI evaluation, benchmark-data or paid-service approval.

## Goal

Find a five-task path that is direct-upstream, clearly licensed and direct-parent throughout, so the owner is not asked to waive benchmark metadata uncertainty, ancestor-base policy or a GPL distribution boundary.

Draft cards: `proposals/m1-direct-parent-clean-path.research.jsonl`.

Proposed research-suite identity hash (canonical task objects): `8620bb20b3530dfa2d65b7f47de60f569ab436cd7c6dd323b9118ed4300b492a`. The manifest file raw-byte SHA-256 is `0004c108e34b55adc2ae8a4097e40b7d927e2cb18a9a060c1f6532bfb8ca9559`.

## Result

| Task | Path | License at pinned base | Remaining gate |
|---|---|---|---|
| `m1-flask-dotted-blueprint` | Keep Flask #4041 / #4045 at base `d8c37f43724cd9fb0870f77877b7c4c7e38a19e0`; already direct-parent. | BSD-3-Clause, SHA-256 `489a8e1108509ed98a37bb983e11e0f7e1d31f0bd8f99a79c8448e7ff37d07ea` | Accepted for the M7 batch; M2 evidence applies to this base. |
| `m1-requests-decode-unicode` | Keep Requests #3359 / #3362 at base `36453b95b13079296776d11b09cab2567ea3e703`; already direct-parent. | Apache-2.0, SHA-256 `c12dd61a3868c674312e979d0ec179ee84c82e8e63c742875238ac912fbd1bac` | Accepted for the M7 batch; M2 evidence applies to this base. |
| `m1-xarray-unstack-single-dim` | Rebase Xarray #4049 / #4094 from ancestor `a64cf2d5476e7bbda099b34c40b7be1880dbd39a` to fixed first parent `03d409ec35034d78a3a625dcaf1744117587b93c`. | Apache-2.0, SHA-256 `73ba74dfaa520b49a401b5d21459a8523a146f3b7518a833eea5efa85130bf68` | Accepted for the M7 batch; M3 evidence applies to this direct-parent base. |
| `m1-click-hyphenated-help-wrap` | Replace Pylint with Click #3362 / #3902 at fixed first parent `8abb77a8432e03ed14a95f972b44f905279415a7`, fixed commit `a46a95c733d0ed72f63cd2915f2bc4a09a7179f9`. The full fixed commit changed `tests/test_compat.py` and `tests/test_formatting.py`; the focused execution scope is only `tests/test_formatting.py`. | BSD-3-Clause, SHA-256 `9a8ad106a394e853bfe21f42f4e72d592819a22805d991b5f3275029292b658d` | Accepted for the M7 batch; M3 evidence applies to this replacement. |
| `m1-pytest-number-docstring` | Rebase pytest #11140 / #11143 from ancestor `6995257cf470d2143ad1683824962de4071c0eb7` to fixed first parent `d7dbadbffcccc61876aa084affcee4240e3eb64a`. | MIT, SHA-256 `ca836a5f9ecca3b2f350230faa20a48fb8b145653b5568d784862df864706b9b` | Accepted for the M7 batch; M3 evidence applies to this direct-parent base. |

## Why this avoids the current waivers

- No benchmark dataset metadata is used in the draft. Every candidate is grounded in an upstream issue, pull request, pinned base commit, fixed commit, fixed-diff test file and pinned license file. The retained Flask/Requests and rebased Xarray/pytest cards explicitly retain the historical caveat that the original five-case selection was SWE-bench Lite-derived.
- Every proposed base is the fixed commit's first parent. No ancestor-base policy waiver is needed.
- Replacing GPL-2.0 Pylint with BSD-3-Clause Click removes the GPL distribution-boundary decision from this path.
- The existing acceptance standard stays unchanged. Two retained tasks have applicable M2 evidence; the two rebases and the Click replacement have separately authorized M3 evidence. Execution evidence is not acceptance.

## New candidate details

- Click issue: [pallets/click#3362, `HelpFormatter.write_usage` breaks options at a hyphen](https://github.com/pallets/click/issues/3362)
- Click fix PR: [pallets/click#3902, Help pages no longer break a line within a hyphenated word](https://github.com/pallets/click/pull/3902)
- Click fixed commit: [`a46a95c733d0ed72f63cd2915f2bc4a09a7179f9`](https://github.com/pallets/click/commit/a46a95c733d0ed72f63cd2915f2bc4a09a7179f9)
- Click fixed-diff locator: [full fixed-commit diff](https://github.com/pallets/click/commit/a46a95c733d0ed72f63cd2915f2bc4a09a7179f9.diff)
- Click pinned license: [BSD-3-Clause `LICENSE.txt` at the proposed base](https://github.com/pallets/click/blob/8abb77a8432e03ed14a95f972b44f905279415a7/LICENSE.txt)

The fixed commit's first parent is `8abb77a8432e03ed14a95f972b44f905279415a7`, which is the proposed base. The full fixed commit changed `tests/test_compat.py` and `tests/test_formatting.py`; the focused execution scope is only `tests/test_formatting.py`, with proposed fail-to-pass selector `tests/test_formatting.py::test_wrap_text_keeps_words_whole`.

## Fixed bounded execution proposal

The manifest to execute is `proposals/m1-direct-parent-clean-path.research.jsonl` with raw-byte SHA-256 `0004c108e34b55adc2ae8a4097e40b7d927e2cb18a9a060c1f6532bfb8ca9559` and canonical suite identity hash `8620bb20b3530dfa2d65b7f47de60f569ab436cd7c6dd323b9118ed4300b492a`. The prepared workflow is `.github/workflows/m3-clean-direct-verification.yml`.

The workflow is fixed to exactly three changed candidates: the Xarray rebase, the Click replacement and the pytest rebase. Flask and Requests are not rerun. It uses one explicit `workflow_dispatch`, public upstream clones, pinned base/fixed commits, focused fixed-commit test diffs, `ubuntu-22.04`, a 20-minute per-candidate timeout, no benchmark dataset download, no model or provider access, no secrets, no paid services, no cache, no artifacts and no automatic retry. A base exit other than an ordinary pytest failure fails closed, and any fixed-side failure fails the job. Results would be candidate execution evidence only, not acceptance.

Execution outcome: the fixed workflow was dispatched once under that exact scope and completed successfully. The three changed candidates now have base-fail/fixed-pass execution evidence in `docs/m3-clean-direct-verification-run.md` and `proposals/m1-direct-parent-clean-path.execution-evidence.jsonl`. This is candidate execution evidence only, not acceptance.

## Decision split

Engineering work within the current project grant: documentation and validator repairs, this research draft, hash computation, structural validation and publication of the proposal for review.

M7 owner acceptance resolved repository rights and task acceptance for this five-case direct-upstream package and one bounded verification batch. Independent engineering review remains read-only evidence and does not accept tasks. All five tasks have upstream-source execution evidence without model or benchmark-data use.

No owner waiver was needed for this clean path. A waiver would only be needed if the owner preferred to retain the ancestor-base candidates, the GPL candidate or benchmark-derived selection metadata.
