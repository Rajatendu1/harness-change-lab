# Intended-use research: SWE-bench and SWE-bench Lite

Research date: 17 November 2026. This record informs the clean direct-upstream package and the M4 runner-manifest contract. It does not accept rights, download benchmark data, execute a model or make the candidate package an adopted benchmark suite.

## Authoritative findings

1. The official SWE-bench FAQ describes SWE-bench as a benchmark for evaluating language models on real-world software engineering tasks. Evaluation takes a model-produced patch, applies it in a Docker environment, runs repository tests and reports whether the issue was resolved. The FAQ's model-evaluation flow requires prediction records containing an `instance_id`, `model_name_or_path` and `model_patch`, and it names `SWE-bench_Lite` as a dataset choice. It also says Docker is required for consistent evaluation environments.
   Source: https://github.com/SWE-bench/SWE-bench/blob/main/docs/faq.md
2. The official SWE-bench Lite page describes Lite as a curated 300-task subset for faster, lower-cost evaluation and recommends it instead of the full benchmark when compute efficiency is a concern. It documents the Lite selection criteria and states that the source for creating Lite is available in the SWE-bench repository.
   Source: https://www.swebench.com/lite
3. The current Hugging Face Lite card says the dataset tests systems' ability to solve GitHub issues automatically and contains 300 test issue/pull-request pairs. Its fields include `problem_statement`, `base_commit`, `patch`, `test_patch`, `FAIL_TO_PASS`, `PASS_TO_PASS`, `version` and `environment_setup_commit`. Those fields are benchmark dataset content, not merely a statement that a task was historically selected from Lite.
   Source: https://huggingface.co/datasets/SWE-bench/SWE-bench_Lite/raw/main/README.md
4. The SWE-bench software repository has an MIT license. The current Hugging Face metadata for both `SWE-bench/SWE-bench_Lite` and `princeton-nlp/SWE-bench_Lite` exposes no license field, license tag or card-data license. The software license therefore does not establish a license for the Lite dataset rows, patches, issue text or test metadata.
   Sources: https://github.com/SWE-bench/SWE-bench/blob/main/LICENSE; https://huggingface.co/api/datasets/SWE-bench/SWE-bench_Lite; https://huggingface.co/api/datasets/princeton-nlp/SWE-bench_Lite

## Application to this repository

- The current clean package uses direct upstream issue, pull-request, commit, test-file and pinned-license evidence. It does not download Lite rows or redistribute Lite `problem_statement`, `patch`, `test_patch`, `FAIL_TO_PASS` or `PASS_TO_PASS` content.
- The recorded statement that the original five-case selection was SWE-bench Lite-derived is historical provenance. It is preserved because it is factual selection history, not because it licenses benchmark content. It does not make the package a SWE-bench Lite result and does not authorize future dataset use.
- For the current intended local harness evaluation, the required rights are the rights for the pinned upstream repositories and direct GitHub issue/PR/test evidence. A benchmark dataset download is not part of that path.
- For a future SWE-bench Lite-compatible evaluation or a public Lite-comparable claim, the project would need the actual task definitions or prediction records, a model-generated patch, the SWE-bench evaluation harness and Docker. That path would also need a decision about the undeclared Lite dataset terms before downloading, using or redistributing dataset content.
- No external request to SWE-bench maintainers has been sent. Asking for a license clarification would be a new external communication and would need separate approval.

## Remaining gate

Keep the clean package candidate-only. Do not download Lite, redistribute Lite content, call this a SWE-bench Lite result, or run a model against it unless the owner separately accepts the intended use and its data-rights path.
