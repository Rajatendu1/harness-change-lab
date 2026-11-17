# M1 candidate rights and source review

Reviewed on 17 November 2026 using the public GitHub API, public Hugging Face dataset metadata and pinned public license files. This is a project rights review, not legal advice.

## Benchmark metadata

- SWE-bench code repository license: MIT, observed at https://github.com/SWE-bench/SWE-bench/blob/main/LICENSE.
- Hugging Face dataset: https://huggingface.co/datasets/princeton-nlp/SWE-bench_Lite.
- Observed dataset repository SHA: `6ec7bb89b9342f664a54a6e0a6ea6501d3437cc2`.
- The dataset metadata currently has no `license` field and no license tag. The README also has no license section.

Because dataset-level terms are not declared, the registry still keeps all five candidates at `rights.status = "pending"`. The new source-evidence file lets the future verification run use original GitHub issues, pull requests and pinned repository content rather than relying on Hugging Face patch or test content. Candidate selection and provenance remain SWE-bench-derived and labelled as such.

## Pinned upstream source evidence

| Candidate | Original issue | Fix PR | Pinned license signal | Fixed merge |
| --- | --- | --- | --- | --- |
| `m1-flask-dotted-blueprint` | https://github.com/pallets/flask/issues/4041 | https://github.com/pallets/flask/pull/4045 | BSD-3-Clause at pinned base | `08e459e823235eecd86c635653f4bd6d6003c2b3` |
| `m1-requests-decode-unicode` | https://github.com/psf/requests/issues/3359 | https://github.com/psf/requests/pull/3362 | Pinned LICENSE text states Apache-2.0; GitHub API detection returned `NOASSERTION` | `92fe51c0afd9239388d2c8bb17dc46babdf7881f` |
| `m1-xarray-unstack-single-dim` | https://github.com/pydata/xarray/issues/4049 | https://github.com/pydata/xarray/pull/4094 | Apache-2.0 at pinned base | `329cefb99220042a586c2b5fdbea679fd8a89cd5` |
| `m1-pylint-punctuation-notes` | https://github.com/pylint-dev/pylint/issues/5840 | https://github.com/pylint-dev/pylint/pull/5859 | GPL-2.0 at pinned base | `a1df7685a4e6a05b519ea011f16a2f0d49d08032` |
| `m1-pytest-number-docstring` | https://github.com/pytest-dev/pytest/issues/11140 | https://github.com/pytest-dev/pytest/pull/11143 | MIT at pinned base | `084d756ae6a03bba7a257ebae3c83095b228988f` |

The full machine-readable evidence is `suites/m1-repair-v0.source-evidence.jsonl`. It includes license-file SHA-256 hashes. No upstream source or test content is vendored into this repository.

## Acceptance rule

A candidate can become accepted only when both are true:

1. Its repository and issue/test source terms are accepted for the intended local evaluation use, including any decision about GPL-licensed Pylint source and the undeclared SWE-bench Lite dataset metadata.
2. Its base-fail/fixed-pass verifier behavior is executed and recorded in a separately approved isolated runner.

No candidate is accepted yet. The M2 run in `docs/m2-verification-run.md` completed the base-fail/fixed-pass execution condition for all five candidates, but the rights condition above remains unresolved and independent task-spec review is not recorded.
