# M1 clean direct-path research

Status: recommended engineering composition, candidate-only, 17 Nov 2026. This does not change the active suite, acceptance state, source evidence or execution evidence, and it does not authorize another run. The original five-case selection was SWE-bench Lite-derived; this record preserves that history while making the forward path direct-upstream and direct-parent.

## Goal

Find a five-task path that is direct-upstream, clearly licensed and direct-parent throughout, so the owner is not asked to waive benchmark metadata uncertainty, ancestor-base policy or a GPL distribution boundary.

Draft cards: `proposals/m1-direct-parent-clean-path.research.jsonl`.

Proposed research-suite hash: `8620bb20b3530dfa2d65b7f47de60f569ab436cd7c6dd323b9118ed4300b492a`.

## Result

| Task | Path | License at pinned base | Remaining gate |
|---|---|---|---|
| `m1-flask-dotted-blueprint` | Keep Flask #4041 / #4045 at base `d8c37f43724cd9fb0870f77877b7c4c7e38a19e0`; already direct-parent. | BSD-3-Clause, SHA-256 `489a8e1108509ed98a37bb983e11e0f7e1d31f0bd8f99a79c8448e7ff37d07ea` | Owner acceptance; M2 evidence already applies to this base. |
| `m1-requests-decode-unicode` | Keep Requests #3359 / #3362 at base `36453b95b13079296776d11b09cab2567ea3e703`; already direct-parent. | Apache-2.0, SHA-256 `c12dd61a3868c674312e979d0ec179ee84c82e8e63c742875238ac912fbd1bac` | Owner acceptance; M2 evidence already applies to this base. |
| `m1-xarray-unstack-single-dim` | Rebase Xarray #4049 / #4094 from ancestor `a64cf2d5476e7bbda099b34c40b7be1880dbd39a` to fixed first parent `03d409ec35034d78a3a625dcaf1744117587b93c`. | Apache-2.0, SHA-256 `73ba74dfaa520b49a401b5d21459a8523a146f3b7518a833eea5efa85130bf68` | New execution required before any pass claim; prior ancestor-base M2 evidence does not transfer. |
| `m1-click-hyphenated-help-wrap` | Replace Pylint with Click #3362 / #3902 at fixed first parent `8abb77a8432e03ed14a95f972b44f905279415a7`, fixed commit `a46a95c733d0ed72f63cd2915f2bc4a09a7179f9`. The full fixed commit changed `tests/test_compat.py` and `tests/test_formatting.py`; the focused execution scope is only `tests/test_formatting.py`. | BSD-3-Clause, SHA-256 `9a8ad106a394e853bfe21f42f4e72d592819a22805d991b5f3275029292b658d` | New candidate and new execution required before any pass claim. |
| `m1-pytest-number-docstring` | Rebase pytest #11140 / #11143 from ancestor `6995257cf470d2143ad1683824962de4071c0eb7` to fixed first parent `d7dbadbffcccc61876aa084affcee4240e3eb64a`. | MIT, SHA-256 `ca836a5f9ecca3b2f350230faa20a48fb8b145653b5568d784862df864706b9b` | New execution required before any pass claim; prior ancestor-base M2 evidence does not transfer. |

## Why this avoids the current waivers

- No benchmark dataset metadata is used in the draft. Every candidate is grounded in an upstream issue, pull request, pinned base commit, fixed commit, fixed-diff test file and pinned license file. The retained Flask/Requests and rebased Xarray/pytest cards explicitly retain the historical caveat that the original five-case selection was SWE-bench Lite-derived.
- Every proposed base is the fixed commit's first parent. No ancestor-base policy waiver is needed.
- Replacing GPL-2.0 Pylint with BSD-3-Clause Click removes the GPL distribution-boundary decision from this path.
- The existing acceptance standard stays unchanged. Two retained tasks have applicable M2 evidence; the two rebases and the Click replacement are not treated as passed until separately authorized and executed.

## New candidate details

- Click issue: [pallets/click#3362, `HelpFormatter.write_usage` breaks options at a hyphen](https://github.com/pallets/click/issues/3362)
- Click fix PR: [pallets/click#3902, Help pages no longer break a line within a hyphenated word](https://github.com/pallets/click/pull/3902)
- Click fixed commit: [`a46a95c733d0ed72f63cd2915f2bc4a09a7179f9`](https://github.com/pallets/click/commit/a46a95c733d0ed72f63cd2915f2bc4a09a7179f9)
- Click fixed-diff locator: [full fixed-commit diff](https://github.com/pallets/click/commit/a46a95c733d0ed72f63cd2915f2bc4a09a7179f9.diff)
- Click pinned license: [BSD-3-Clause `LICENSE.txt` at the proposed base](https://github.com/pallets/click/blob/8abb77a8432e03ed14a95f972b44f905279415a7/LICENSE.txt)

The fixed commit's first parent is `8abb77a8432e03ed14a95f972b44f905279415a7`, which is the proposed base. The full fixed commit changed `tests/test_compat.py` and `tests/test_formatting.py`; the focused execution scope is only `tests/test_formatting.py`, with proposed fail-to-pass selector `tests/test_formatting.py::test_wrap_text_keeps_words_whole`.

## Decision split

Engineering work within the current project grant: documentation and validator repairs, this research draft, hash computation, structural validation and publication of the proposal for review.

Owner gates that remain: authorize any new M2 execution and accept rights/review outcomes. Suite composition here is the engineering recommendation under the existing project-ownership grant; candidate status stays unchanged, and only Flask/Requests have applicable old run evidence.

No owner waiver is needed to continue preparing this clean path. A waiver would only be needed if the owner preferred to retain the ancestor-base candidates, the GPL candidate or benchmark-derived selection metadata.
