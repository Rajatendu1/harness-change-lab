import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest

from harnesslab.cli import main
from harnesslab.tasks import ManifestError, load_suite, parse_task, suite_summary


def task_dict(**overrides):
    task = {
        "id": "m1-example-task",
        "status": "candidate",
        "source": {
            "type": "git",
            "url": "https://github.com/example/project.git",
            "ref": "a" * 40,
        },
        "issue": "Fix the documented edge case in the example project.",
        "setup": ["python -m pip install -e ."],
        "verify": ["python -m pytest -q tests/test_example.py"],
        "timeout_s": 600,
        "tags": ["python", "repair"],
        "provenance": {
            "benchmark": "example-benchmark",
            "instance_id": "example-1",
            "dataset_url": "https://example.invalid/dataset",
            "fail_to_pass": ["tests/test_example.py"],
        },
        "rights": {
            "status": "pending",
            "license": "pending source review",
            "license_url": "pending source review",
            "data_use": "candidate metadata only until the source terms are reviewed",
            "notes": "The task is not accepted until license and execution checks pass.",
        },
    }
    task.update(overrides)
    return task


class TaskSpecTests(unittest.TestCase):
    def test_valid_candidate_hashes_task_and_verifier(self):
        task = parse_task(task_dict())
        self.assertEqual(task.task_revision, "a" * 40)
        self.assertEqual(len(task.verifier_sha256), 64)
        self.assertEqual(len(task.task_sha256), 64)
        self.assertNotEqual(task.task_sha256, task.verifier_sha256)

    def test_duplicate_ids_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "suite.jsonl"
            line = json.dumps(task_dict())
            path.write_text(line + "\n" + line + "\n", encoding="utf-8")
            with self.assertRaisesRegex(ManifestError, "duplicate task id"):
                load_suite(path)

    def test_source_must_be_pinned(self):
        bad = task_dict(source={"type": "git", "url": "https://github.com/example/project.git", "ref": "main"})
        with self.assertRaisesRegex(ManifestError, "commit SHA"):
            parse_task(bad)

    def test_accepted_task_requires_accepted_rights(self):
        with self.assertRaisesRegex(ManifestError, "accepted rights"):
            parse_task(task_dict(status="accepted"))

    def test_verifier_hash_changes_with_verifier(self):
        left = parse_task(task_dict())
        changed = task_dict(verify=["python -m pytest -q tests/test_other.py"])
        right = parse_task(changed)
        self.assertNotEqual(left.verifier_sha256, right.verifier_sha256)

    def test_suite_summary_counts_candidates(self):
        summary = suite_summary([parse_task(task_dict())])
        self.assertEqual(summary["task_count"], 1)
        self.assertEqual(summary["accepted_count"], 0)
        self.assertEqual(summary["candidate_count"], 1)
        self.assertEqual(summary["rights_pending_count"], 1)


class SuiteCliTests(unittest.TestCase):
    def test_validate_suite_json_and_acceptance_exit(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "suite.jsonl"
            path.write_text(json.dumps(task_dict()) + "\n", encoding="utf-8")
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(main(["validate-suite", str(path)]), 0)
                self.assertEqual(main(["validate-suite", str(path), "--min-accepted", "1"]), 3)
            self.assertIn('"suite_sha256"', output.getvalue())

    def test_validate_suite_rejects_bad_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "suite.jsonl"
            path.write_text("not json\n", encoding="utf-8")
            with contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as raised:
                    main(["validate-suite", str(path)])
            self.assertEqual(raised.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
