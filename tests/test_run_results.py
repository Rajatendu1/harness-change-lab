import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest

from harnesslab.cli import main
from harnesslab.run_manifest import build_run_manifest
from harnesslab.run_results import load_run_results, parse_run_result, validate_run_results
from harnesslab.tasks import ManifestError, parse_task
from harnesslab.verification import parse_evidence, parse_execution_evidence, parse_review_evidence

from test_run_manifest import CLEAN_EVIDENCE, CLEAN_EXECUTION, CLEAN_REVIEW, CLEAN_SUITE, RUNNER_CONFIG, fixture_manifest
from test_tasks import task_dict
from test_verification import evidence_dict, execution_dict, review_dict
from harnesslab.tasks import load_suite
from harnesslab.verification import load_evidence, load_execution_evidence, load_review_evidence


def accepted_fixture_manifest(trials=2):
    task_data = task_dict(status="accepted")
    task_data["rights"] = {
        "status": "accepted",
        "license": "MIT",
        "license_url": "https://github.com/example/project/blob/main/LICENSE",
        "data_use": "direct upstream issue, pull-request and pinned repository metadata only; no benchmark dataset metadata; fixture acceptance only",
        "notes": "Fixture acceptance exercises the contract and is not a real suite acceptance.",
    }
    task = parse_task(task_data)
    evidence = parse_evidence(evidence_dict(task.id, task.source_ref))
    execution = parse_execution_evidence(execution_dict(task.id, task.source_ref, evidence.fixed_commit))
    review = parse_review_evidence(review_dict(task))
    return build_run_manifest(
        [task],
        [evidence],
        [execution],
        [review],
        runner_name="fixture-runner",
        runner_version="0.1.0",
        runner_config_sha256=RUNNER_CONFIG,
        trials_per_task=trials,
        max_concurrency=1,
    )


def result_dict(manifest, trial=1, **overrides):
    task = manifest["tasks"][0]
    item = {
        "schema": "m6-run-result-v0",
        "run_id": "fixture-run-001",
        "manifest_sha256": manifest["manifest_sha256"],
        "task": {
            "id": task["id"],
            "revision": task["task_revision"],
            "task_sha256": task["task_sha256"],
            "verifier_sha256": task["verifier_sha256"],
        },
        "trial_index": trial,
        "status": "completed",
        "runner": manifest["runner"],
        "base": {"exit_code": 1, "duration_s": 1, "failed_count": 1},
        "fixed": {"exit_code": 0, "duration_s": 1, "passed_count": 1},
        "policy": {
            "model_access": False,
            "benchmark_data_used": False,
            "secrets_used": False,
            "artifact_upload_count": 0,
            "automatic_retry": False,
        },
    }
    item.update(overrides)
    return item


class RunResultTests(unittest.TestCase):
    def test_valid_fixture_results_validate_without_execution(self):
        manifest = accepted_fixture_manifest(trials=2)
        self.assertEqual(manifest["status"], "ready_not_executed")
        rows = [parse_run_result(result_dict(manifest, 1)), parse_run_result(result_dict(manifest, 2))]
        summary = validate_run_results(manifest, rows)
        self.assertEqual(summary["status"], "results_contract_valid")
        self.assertEqual(summary["task_count"], 1)
        self.assertEqual(summary["trial_count"], 2)
        self.assertEqual(summary["model_or_agent_runs"], 0)
        self.assertFalse(summary["benchmark_data_used"])
        self.assertIn("did not execute", summary["evidence_scope"])

    def test_missing_trial_fails_closed(self):
        manifest = accepted_fixture_manifest(trials=2)
        row = parse_run_result(result_dict(manifest, 1))
        with self.assertRaisesRegex(ManifestError, "missing task/trial"):
            validate_run_results(manifest, [row])

    def test_duplicate_trial_fails_closed(self):
        manifest = accepted_fixture_manifest(trials=2)
        rows = [parse_run_result(result_dict(manifest, 1)), parse_run_result(result_dict(manifest, 1))]
        with self.assertRaisesRegex(ManifestError, "duplicate task/trial"):
            validate_run_results(manifest, rows)

    def test_changed_task_identity_fails_closed(self):
        manifest = accepted_fixture_manifest(trials=1)
        changed = result_dict(manifest)
        changed["task"]["verifier_sha256"] = "f" * 64
        with self.assertRaisesRegex(ManifestError, "task identity"):
            validate_run_results(manifest, [parse_run_result(changed)])

    def test_policy_violation_fails_closed(self):
        manifest = accepted_fixture_manifest(trials=1)
        changed = result_dict(manifest)
        changed["policy"]["model_access"] = True
        with self.assertRaisesRegex(ManifestError, "policy violates"):
            validate_run_results(manifest, [parse_run_result(changed)])

    def test_blocked_manifest_cannot_accept_results(self):
        manifest = fixture_manifest()
        self.assertEqual(manifest["status"], "blocked_not_runnable")
        with self.assertRaisesRegex(ManifestError, "blocked"):
            validate_run_results(manifest, [])

    def test_result_parse_rejects_base_infrastructure_error(self):
        manifest = accepted_fixture_manifest(trials=1)
        changed = result_dict(manifest)
        changed["base"]["exit_code"] = 2
        with self.assertRaisesRegex(ManifestError, "ordinary pytest failure"):
            parse_run_result(changed)


class RunResultCliTests(unittest.TestCase):
    def test_validate_run_results_cli(self):
        manifest = accepted_fixture_manifest(trials=2)
        with tempfile.TemporaryDirectory() as tmp:
            manifest_path = Path(tmp) / "manifest.json"
            results_path = Path(tmp) / "results.jsonl"
            manifest_path.write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")
            results_path.write_text(
                json.dumps(result_dict(manifest, 1), sort_keys=True) + "\n" +
                json.dumps(result_dict(manifest, 2), sort_keys=True) + "\n",
                encoding="utf-8",
            )
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(main(["validate-run-results", str(manifest_path), str(results_path)]), 0)
            payload = json.loads(output.getvalue())
            self.assertEqual(payload["status"], "results_contract_valid")
            self.assertEqual(payload["trial_count"], 2)


if __name__ == "__main__":
    unittest.main()
