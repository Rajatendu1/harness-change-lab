# M1 candidate rights review

Reviewed on 17 November 2026 using the public GitHub license API and the public Hugging Face dataset metadata. This is a project rights review, not legal advice.

## Upstream repositories

| Project | Current license signal | Source |
| --- | --- | --- |
| Flask | BSD-3-Clause | https://github.com/pallets/flask/blob/main/LICENSE.txt |
| Requests | Apache-2.0 | https://github.com/psf/requests/blob/main/LICENSE |
| Xarray | Apache-2.0 | https://github.com/pydata/xarray/blob/main/LICENSE |
| Pylint | GPL-2.0 | https://github.com/pylint-dev/pylint/blob/main/LICENSE |
| pytest | MIT | https://github.com/pytest-dev/pytest/blob/main/LICENSE |

These licenses are recorded per candidate in `suites/m1-repair-v0.candidates.jsonl`. The registry references public repositories and pinned revisions; it does not vendor upstream source.

## Benchmark metadata

The SWE-bench code repository reports MIT:

- https://github.com/SWE-bench/SWE-bench/blob/main/LICENSE

The Hugging Face metadata for `princeton-nlp/SWE-bench_Lite` currently has no `license` field and no license tag. The candidate registry therefore keeps every candidate at `rights.status = "pending"`. Before a task is accepted, resolve the dataset terms or rebuild the task from the original public issue, repository and tests without relying on unclear dataset metadata.

## Acceptance rule

A candidate can become accepted only when both are true:

1. Its upstream repository and benchmark-metadata terms are accepted for the intended local evaluation use.
2. Its base-fail/fixed-pass verifier behavior is executed and recorded in the approved isolated runner.

No candidate is accepted yet.
