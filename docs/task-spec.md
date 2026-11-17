# Task suite spec (M1 pilot: 5 tasks)

Each task is one JSONL line:

{
  "id": "small-repo-001",
  "source": {"type": "git", "url": "https://github.com/<owner>/<repo>", "ref": "<sha>"},
  "issue": "natural-language description of the defect to fix",
  "setup": ["pip install -e .", "..."],
  "verify": ["pytest -q tests/test_x.py"],
  "timeout_s": 900,
  "tags": ["python", "bugfix", "small"],
  "status": "candidate",
  "provenance": {
    "benchmark": "source benchmark or issue tracker",
    "instance_id": "stable source identity",
    "dataset_url": "https://...",
    "environment_setup_commit": "<sha>",
    "fail_to_pass": ["tests/test_x.py::test_case"]
  },
  "rights": {
    "status": "pending",
    "license": "source license or pending source review",
    "license_url": "https://...",
    "data_use": "what the current rights review permits",
    "notes": "review caveats"
  }
}

Rules:
- Verifiable only: the verifier must pass/fail deterministically, no LLM-judge in M1.
- Public repos only, pinned to a commit sha.
- The base verifier must FAIL on the untouched repo and PASS after a correct fix (validated before the task enters the suite).
- The selected base should be the fixed commit's first parent. If it is an earlier ancestor, record the actual first parent and commit gap, keep the task evidence-qualified, and do not accept it until the owner explicitly permits ancestor bases and review records why the fixed-diff regression tests isolate the claimed fix.
- `candidate` tasks are not accepted benchmark tasks. An `accepted` task also needs an accepted rights review, reconciled independent review and recorded base-fail/fixed-pass execution evidence.
- Provenance must identify the benchmark or issue source and preserve the exact fail-to-pass test identity used by the verifier.
