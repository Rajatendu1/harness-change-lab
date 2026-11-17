import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest

from harnesslab.cli import main
from harnesslab.run_manifest import build_run_manifest, validate_run_manifest
from harnesslab.tasks import ManifestError, load_suite
from harnesslab.verification import load_evidence, load_execution_evidence, load_review_evidence

from test_verification import evidence_dict, execution_dict
from test_tasks import task_dict
from harnesslab.tasks import parse_task
from harnesslab.verification import parse_evidence, parse_execution_evidence


CLEAN_SUITE = Path("proposals/m1-direct-parent-clean-path.research.jsonl")
CLEAN_EVIDENCE = Path("proposals/m1-direct-parent-clean-path.source-evidence.jsonl")
CLEAN_EXECUTION = Path("proposals/m1-direct-parent-clean-path.execution-evidence.jsonl")
CLEAN_REVIEW = Path("proposals/m3-m4-independent-review.evidence.jsonl")
RUNNER_CONFIG = "0" * 64


def fixture_manifest():
    task = parse_task(task_dict())
    evidence = parse_evidence(evidence_dict(task.id, task.source_ref))
    execution = parse_execution_evidence(execution_dict(task.id, task.source_ref, evidence.fixed_commit))
    return build_run_manifest(
        [task],
        [evidence],
        [execution],
        runner_name="fixture-runner",
        runner_version="0.1.0",
        runner_config_sha256=RUNNER_CONFIG,
        trials_per_task=2,
        max_concurrency=1,
    )


class RunManifestTests(unittest.TestCase):
    def test_clean_path_manifest_is_ready_not_executed(self):
        manifest = build_run_manifest(
            load_suite(CLEAN_SUITE),
            load_evidence(CLEAN_EVIDENCE),
            load_execution_evidence(CLEAN_EXECUTION),
            load_review_evidence(CLEAN_REVIEW),
            runner_name="fixture-runner",
            runner_version="0.1.0",
            runner_config_sha256=RUNNER_CONFIG,
            trials_per_task=3,
            max_concurrency=1,
        )
        self.assertEqual(manifest["schema"], "m4-run-manifest-v0")
        self.assertEqual(manifest["status"], "ready_not_executed")
        self.assertEqual(manifest["suite"]["task_count"], 5)
        self.assertEqual(manifest["suite"]["accepted_count"], 5)
        self.assertEqual(manifest["suite"]["engineering_review_status"], "recorded_read_only_not_acceptance")
        self.assertEqual(manifest["suite"]["engineering_review_recorded_count"], 5)
        self.assertEqual(manifest["trial_plan"]["total_trials"], 15)
        self.assertFalse(manifest["execution_policy"]["benchmark_data_use"])
        self.assertEqual(manifest["execution_policy"]["model_access"], "not_authorized_by_this_manifest")
        self.assertEqual(manifest["blocked_reasons"], [])
        for row in manifest["tasks"]:
            self.assertEqual(len(row["task_sha256"]), 64)
            self.assertEqual(len(row["verifier_sha256"]), 64)
            self.assertEqual(len(row["provenance_sha256"]), 64)
            self.assertEqual(row["acceptance"]["execution_status"], "upstream-source-verified")

    def test_validate_recomputes_contract(self):
        task = parse_task(task_dict())
        evidence = parse_evidence(evidence_dict(task.id, task.source_ref))
        execution = parse_execution_evidence(execution_dict(task.id, task.source_ref, evidence.fixed_commit))
        manifest = fixture_manifest()
        self.assertEqual(manifest["status"], "blocked_not_runnable")
        self.assertIs(validate_run_manifest(manifest, [task], [evidence], [execution]), manifest)

    def test_validate_rejects_changed_verifier(self):
        task = parse_task(task_dict())
        evidence = parse_evidence(evidence_dict(task.id, task.source_ref))
        execution = parse_execution_evidence(execution_dict(task.id, task.source_ref, evidence.fixed_commit))
        manifest = fixture_manifest()
        manifest["tasks"][0]["verify"] = ["python -m pytest -q tests/test_other.py"]
        with self.assertRaisesRegex(ManifestError, "does not match the recomputed"):
            validate_run_manifest(manifest, [task], [evidence], [execution])

    def test_validate_rejects_changed_runner_identity(self):
        task = parse_task(task_dict())
        evidence = parse_evidence(evidence_dict(task.id, task.source_ref))
        execution = parse_execution_evidence(execution_dict(task.id, task.source_ref, evidence.fixed_commit))
        manifest = fixture_manifest()
        manifest["runner"]["version"] = "0.2.0"
        with self.assertRaisesRegex(ManifestError, "does not match the recomputed"):
            validate_run_manifest(manifest, [task], [evidence], [execution])

    def test_runner_config_hash_is_required(self):
        task = parse_task(task_dict())
        evidence = parse_evidence(evidence_dict(task.id, task.source_ref))
        execution = parse_execution_evidence(execution_dict(task.id, task.source_ref, evidence.fixed_commit))
        with self.assertRaisesRegex(ManifestError, "config_sha256"):
            build_run_manifest(
                [task],
                [evidence],
                [execution],
                runner_name="fixture-runner",
                runner_version="0.1.0",
                runner_config_sha256="not-a-hash",
            )


class RunManifestCliTests(unittest.TestCase):
    def test_prepare_and_validate_cli(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = main([
                "prepare-run-manifest",
                str(CLEAN_SUITE),
                str(CLEAN_EVIDENCE),
                str(CLEAN_EXECUTION),
                str(CLEAN_REVIEW),
                "--runner-name", "fixture-runner",
                "--runner-version", "0.1.0",
                "--runner-config-sha256", RUNNER_CONFIG,
            ])
        self.assertEqual(code, 0)
        payload = json.loads(output.getvalue())
        self.assertEqual(payload["status"], "ready_not_executed")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "manifest.json"
            path.write_text(output.getvalue(), encoding="utf-8")
            valid = io.StringIO()
            with contextlib.redirect_stdout(valid):
                self.assertEqual(main([
                    "validate-run-manifest",
                    str(path),
                    str(CLEAN_SUITE),
                    str(CLEAN_EVIDENCE),
                    str(CLEAN_EXECUTION),
                    str(CLEAN_REVIEW),
                ]), 0)
            self.assertEqual(json.loads(valid.getvalue())["status"], "contract-valid")

    def test_prepare_rejects_invalid_trial_count(self):
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as raised:
                main([
                    "prepare-run-manifest",
                    str(CLEAN_SUITE),
                    str(CLEAN_EVIDENCE),
                    str(CLEAN_EXECUTION),
                    "--runner-name", "fixture-runner",
                    "--runner-version", "0.1.0",
                    "--runner-config-sha256", RUNNER_CONFIG,
                    "--trials-per-task", "0",
                ])
        self.assertEqual(raised.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
