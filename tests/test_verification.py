import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest

from harnesslab.cli import main
from harnesslab.tasks import ManifestError, load_suite
from harnesslab.verification import build_verification_plan, load_evidence, parse_evidence

from test_tasks import task_dict


SUITE = Path("suites/m1-repair-v0.candidates.jsonl")
EVIDENCE = Path("suites/m1-repair-v0.source-evidence.jsonl")


def evidence_dict(task_id="m1-example-task", source_ref="a" * 40, **overrides):
    item = {
        "id": task_id,
        "status": "metadata-verified",
        "source": {
            "repo": "example/project",
            "base_commit": source_ref,
            "fixed_merge_commit": "b" * 40,
            "issue_url": "https://github.com/example/project/issues/1",
            "issue_title": "Fix the documented example edge case",
            "pr_url": "https://github.com/example/project/pull/2",
            "pr_title": "Fix the documented example edge case",
            "test_files": ["tests/test_example.py"],
        },
        "license": {
            "spdx_id": "MIT",
            "url": "https://github.com/example/project/blob/main/LICENSE",
            "file_sha256": "c" * 64,
            "notes": "License metadata was checked at the pinned revision.",
        },
        "benchmark": {
            "dataset": "example-benchmark",
            "url": "https://example.invalid/dataset",
            "sha": "d" * 40,
            "license_status": "not declared",
        },
    }
    item.update(overrides)
    return item


class SourceEvidenceTests(unittest.TestCase):
    def test_real_registry_plan_is_deterministic_and_not_approved(self):
        tasks = load_suite(SUITE)
        evidence = load_evidence(EVIDENCE)
        first = build_verification_plan(tasks, evidence)
        second = build_verification_plan(tasks, evidence)
        self.assertEqual(first, second)
        self.assertEqual(first["status"], "prepared_not_approved")
        self.assertFalse(first["model_access_required"])
        self.assertEqual(first["upstream_code_execution"], "not_run")
        self.assertEqual(first["task_count"], 5)
        self.assertEqual(len(first["plan_sha256"]), 64)

    def test_mismatched_source_fails_closed(self):
        task = next(iter(load_suite(SUITE)))
        evidence = parse_evidence(evidence_dict(task.id, "0" * 40))
        with self.assertRaisesRegex(ManifestError, "does not match task source"):
            build_verification_plan([task], [evidence])

    def test_missing_evidence_fails_closed(self):
        task = next(iter(load_suite(SUITE)))
        with self.assertRaisesRegex(ManifestError, "missing source evidence"):
            build_verification_plan([task], [])

    def test_evidence_requires_fixed_merge_commit(self):
        bad = evidence_dict()
        bad["source"]["fixed_merge_commit"] = "main"
        with self.assertRaisesRegex(ManifestError, "fixed_merge_commit"):
            parse_evidence(bad)


class VerificationCliTests(unittest.TestCase):
    def test_plan_verification_prints_json(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(main(["plan-verification", str(SUITE), str(EVIDENCE)]), 0)
        payload = json.loads(output.getvalue())
        self.assertEqual(payload["schema"], "m1-verification-plan-v0")
        self.assertEqual(payload["status"], "prepared_not_approved")
        self.assertEqual(payload["task_count"], 5)

    def test_plan_verification_rejects_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            suite = Path(tmp) / "suite.jsonl"
            evidence = Path(tmp) / "evidence.jsonl"
            suite.write_text(json.dumps(task_dict()) + "\n", encoding="utf-8")
            evidence.write_text(json.dumps(evidence_dict(source_ref="0" * 40)) + "\n", encoding="utf-8")
            with contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as raised:
                    main(["plan-verification", str(suite), str(evidence)])
            self.assertEqual(raised.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
