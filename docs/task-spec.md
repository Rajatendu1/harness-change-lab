# Task suite spec (M1 pilot: 5 tasks)

Each task is one JSONL line:

{
  "id": "small-repo-001",
  "source": {"type": "git", "url": "https://github.com/<owner>/<repo>", "ref": "<sha>"},
  "issue": "natural-language description of the defect to fix",
  "setup": ["pip install -e .", "..."],
  "verify": ["pytest -q tests/test_x.py"],
  "timeout_s": 900,
  "tags": ["python", "bugfix", "small"]
}

Rules:
- Verifiable only: the verifier must pass/fail deterministically, no LLM-judge in M1.
- Public repos only, pinned to a commit sha.
- The base verifier must FAIL on the untouched repo and PASS after a correct fix (validated before the task enters the suite).
