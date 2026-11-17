# M1 clean direct-path research

Status: research proposal only, 17 Nov 2026. This does not change the active suite, acceptance state, source evidence or execution evidence, and it does not authorize another run.

## Goal

Find a five-task path that is direct-upstream, clearly licensed and direct-parent throughout, so the owner is not asked to waive benchmark metadata uncertainty, ancestor-base policy or a GPL distribution boundary.

Draft cards: `proposals/m1-direct-parent-clean-path.research.jsonl`.

Proposed research-suite hash: `77c985d1fb3e8e426b5f09abe1e54382615a3624f09cae0fc84a30e15aa0be11`.

## Result

| Task | Path | License at pinned base | Remaining gate |
|---|---|---|---|
| `m1-flask-dotted-blueprint` | Keep Flask #4041 / #4045 at base `d8c37f43724cd9fb0870f77877b7c4c7e38a19e0`; already direct-parent. | BSD-3-Clause, SHA-256 `489a8e1108509ed98a37bb983e11e0f7e1d31f0bd8f99a79c8448e7ff37d07ea` | Owner acceptance; M2 evidence already applies to this base. |
| `m1-requests-decode-unicode` | Keep Requests #3359 / #3362 at base `36453b95b13079296776d11b09cab2567ea3e703`; already direct-parent. | Apache-2.0, SHA-256 `c12dd61a3868c674312e979d0ec179ee84c82e8e63c742875238ac912fbd1bac` | Owner acceptance; M2 evidence already applies to this base. |
| `m1-xarray-unstack-single-dim` | Rebase Xarray #4049 / #4094 from ancestor `a64cf2d5476e7bbda099b34c40b7be1880dbd39a` to fixed first parent `03d409ec35034d78a3a625dcaf1744117587b93c`. | Apache-2.0, SHA-256 `73ba74dfaa520b49a401b5d21459a8523a146f3b7518a833eea5efa85130bf68` | New execution required before any pass claim; prior ancestor-base M2 evidence does not transfer. |
| `m1-click-hyphenated-help-wrap` | Replace Pylint with Click #3362 / #3902 at fixed first parent `8abb77a8432e03ed14a95f972b44f905279415a7`, fixed commit `a46a95c733d0ed72f63cd2915f2bc4a09a7179f9`. | BSD-3-Clause, SHA-256 `9a8ad106a394e853bfe21f42f4e72d592819a22805d991b5f3275029292b658d` | New candidate and new execution required before any pass claim. |
| `m1-pytest-number-docstring` | Rebase pytest #11140 / #11143 from ancestor `6995257cf470d2143ad1683824962de4071c0eb7` to fixed first parent `d7dbadbffcccc61876aa084affcee4240e3eb64a`. | MIT, SHA-256 `ca836a5f9ecca3b2f350230faa20a48fb8b145653b5568d784862df864706b9b` | New execution required before any pass claim; prior ancestor-base M2 evidence does not transfer. |

## Why this avoids the current waivers

- No benchmark dataset metadata is used in the draft. Every candidate is grounded in an upstream issue, pull request, pinned base commit, fixed commit, fixed-diff test file and pinned license file.
- Every proposed base is the fixed commit's first parent. No ancestor-base policy waiver is needed.
- Replacing GPL-2.0 Pylint with BSD-3-Clause Click removes the GPL distribution-boundary decision from this path.
- The existing acceptance standard stays unchanged. Two retained tasks have applicable M2 evidence; the two rebases and the Click replacement are not treated as passed until separately authorized and executed.

## New candidate details

Click issue: <https://github.com/pallets/click/issues/3362>

Click fix PR: <https://github.com/pallets/click/pull/3902>

Click fixed commit: <https://github.com/pallets/click/commit/a46a95c733d0ed72f63cd2915f2bc4a09a7179f9>

Click fixed-diff locator: <https://github.com/pallets/click/commit/a46a95c733d0ed72f63cd2915f2bc4a09a7179f9.diff>

Click pinned license: <https://github.com/pallets/click/blob/8abb77a8432e03ed14a95f972b44f905279415a7/LICENSE.txt>

The fixed commit's first parent is `8abb77a8432e03ed14a95f972b44f905279415a7`, which is the proposed base. The focused test file is `tests/test_formatting.py`; proposed fail-to-pass selector is `tests/test_formatting.py::test_wrap_text_keeps_words_whole`.

## Decision split

Engineering work within the current project grant: documentation and validator repairs, this research draft, hash computation, structural validation and publication of the proposal for review.

Owner gates that remain: adopt or reject the source-only suite path, accept the proposed suite composition, authorize any new M2 execution, and decide whether the two existing direct-parent tasks plus three new direct-parent executions become the next acceptance attempt.

No owner waiver is needed to continue preparing this clean path. A waiver would only be needed if the owner preferred to retain the ancestor-base candidates, the GPL candidate or benchmark-derived selection metadata.
