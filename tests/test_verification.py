import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest

from harnesslab.cli import main
from harnesslab.tasks import ManifestError, load_suite
from harnesslab.verification import (
    build_acceptance_status,
    build_verification_plan,
    load_evidence,
    load_execution_evidence,
    parse_evidence,
    parse_execution_evidence,
)

from test_tasks import task_dict


SUITE = Path("suites/m1-repair-v0.candidates.jsonl")
EVIDENCE = Path("suites/m1-repair-v0.source-evidence.jsonl")
EXECUTION = Path("suites/m1-repair-v0.execution-evidence.jsonl")
CLEAN_SUITE = Path("proposals/m1-direct-parent-clean-path.research.jsonl")
CLEAN_EVIDENCE = Path("proposals/m1-direct-parent-clean-path.source-evidence.jsonl")
CLEAN_EXECUTION = Path("proposals/m1-direct-parent-clean-path.execution-evidence.jsonl")


def evidence_dict(task_id="m1-example-task", source_ref="a" * 40, **overrides):
    item = {
        "id": task_id,
        "status": "metadata-verified",
        "source": {
            "repo": "example/project",
            "base_commit": source_ref,
            "fixed_commit": "b" * 40,
            "fixed_first_parent": source_ref,
            "base_relation": "direct-parent",
            "ancestor_gap_commits": 0,
            "fixed_commit_kind": "single-parent",
            "issue_url": "https://github.com/example/project/issues/1",
            "issue_title": "Fix the documented example edge case",
            "pr_url": "https://github.com/example/project/pull/2",
            "pr_title": "Fix the documented example edge case",
            "test_files": ["tests/test_example.py"],
            "implementation_files": ["src/example.py"],
            "test_patch_url": "https://github.com/example/project/commit/" + "b" * 40 + ".diff",
            "test_patch_scope": "filter the fixed-commit diff to test_files",
            "evidence_qualification": "Fixed first parent matches the selected base commit.",
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


def execution_dict(task_id="m1-example-task", source_ref="a" * 40, fixed_ref="b" * 40, **overrides):
    item = {
        "id": task_id,
        "status": "upstream-source-verified",
        "run": {
            "url": "https://github.com/example/project/actions/runs/123456789",
            "workflow_commit": "e" * 40,
            "workflow_sha256": "f" * 64,
            "runner_label": "ubuntu-22.04",
            "job_timeout_minutes": 20,
            "benchmark_data_used": False,
            "secrets_model_credentials_cache_artifacts": False,
            "artifacts_count": 0,
            "summary_caveat": "Example summary caveat.",
        },
        "runtime": {
            "python": "3.11.0",
            "package_name": "example",
            "package_version": "1.0",
            "pytest": "7.0.0",
        },
        "base": {"exit_code": 1, "duration_s": 1, "failed_count": 1},
        "fixed": {"exit_code": 0, "duration_s": 1, "passed_count": 1},
        "source": {"base_commit": source_ref, "fixed_commit": fixed_ref},
        "test_patch": {
            "identity": f"git diff --binary {fixed_ref}^ {fixed_ref} -- tests/test_example.py",
            "source_url": "https://github.com/example/project/commit/" + fixed_ref + ".diff",
            "applied_files": ["tests/test_example.py"],
            "scope": "M2 applied only this matrix test_path; source-evidence test_files lists all upstream fixed-commit test-file changes.",
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
        rows = {item["id"]: item for item in first["tasks"]}
        for row in rows.values():
            source = row["source"]
            self.assertTrue(source["test_patch_url"].endswith(".diff"))
            self.assertIn(source["fixed_commit"], source["test_patch_url"])
            self.assertTrue(source["implementation_files"])
        self.assertEqual(rows["m1-xarray-unstack-single-dim"]["source"]["ancestor_gap_commits"], 7)
        self.assertEqual(rows["m1-pytest-number-docstring"]["source"]["ancestor_gap_commits"], 18)

    def test_mismatched_source_fails_closed(self):
        task = next(iter(load_suite(SUITE)))
        evidence = parse_evidence(evidence_dict(task.id, "0" * 40))
        with self.assertRaisesRegex(ManifestError, "does not match task source"):
            build_verification_plan([task], [evidence])

    def test_missing_evidence_fails_closed(self):
        task = next(iter(load_suite(SUITE)))
        with self.assertRaisesRegex(ManifestError, "missing source evidence"):
            build_verification_plan([task], [])

    def test_evidence_requires_fixed_commit(self):
        bad = evidence_dict()
        bad["source"]["fixed_commit"] = "main"
        with self.assertRaisesRegex(ManifestError, "fixed_commit"):
            parse_evidence(bad)

    def test_evidence_requires_test_patch_url(self):
        bad = evidence_dict()
        del bad["source"]["test_patch_url"]
        with self.assertRaisesRegex(ManifestError, "test_patch_url"):
            parse_evidence(bad)

    def test_direct_parent_mismatch_fails_closed(self):
        bad = evidence_dict(source_ref="0" * 40)
        bad["source"]["fixed_first_parent"] = "1" * 40
        with self.assertRaisesRegex(ManifestError, "direct-parent evidence"):
            parse_evidence(bad)

    def test_ancestor_requires_positive_gap(self):
        bad = evidence_dict(source_ref="0" * 40)
        bad["source"]["base_relation"] = "ancestor"
        bad["source"]["fixed_first_parent"] = "1" * 40
        bad["source"]["ancestor_gap_commits"] = 0
        with self.assertRaisesRegex(ManifestError, "ancestor evidence"):
            parse_evidence(bad)


class ExecutionEvidenceTests(unittest.TestCase):
    def test_real_acceptance_status_records_verified_sources_and_blockers(self):
        status = build_acceptance_status(
            load_suite(SUITE),
            load_evidence(EVIDENCE),
            load_execution_evidence(EXECUTION),
        )
        self.assertEqual(status["status"], "upstream_source_verified_not_accepted")
        self.assertEqual(status["task_count"], 5)
        self.assertEqual(status["upstream_source_verified_count"], 5)
        self.assertEqual(status["accepted_count"], 0)
        self.assertEqual(status["rights_pending_count"], 5)
        self.assertEqual(status["model_or_agent_runs"], 0)
        self.assertFalse(status["benchmark_data_used"])
        self.assertTrue(any("accept repository and benchmark-data rights" in item for item in status["remaining_acceptance_work"]))
        self.assertTrue(all(row["base_exit_code"] == 1 for row in status["tasks"]))
        self.assertTrue(all(row["fixed_exit_code"] == 0 for row in status["tasks"]))
        self.assertTrue(all("independent task-spec review" in row["blockers"][-1] for row in status["tasks"]))
        execution = {row["id"]: row for row in status["execution"]}
        self.assertEqual(execution["m1-flask-dotted-blueprint"]["test_patch_applied_files"], ["tests/test_blueprints.py"])
        self.assertIn("git diff --binary", execution["m1-flask-dotted-blueprint"]["test_patch_identity"])
        ancestor_rows = {row["id"] for row in status["tasks"] if row["base_relation"] == "ancestor"}
        self.assertEqual(ancestor_rows, {"m1-xarray-unstack-single-dim", "m1-pytest-number-docstring"})
        self.assertIn("ancestor-base evidence qualification", status["remaining_acceptance_work"][0])

    def test_clean_path_package_records_five_verified_candidates(self):
        status = build_acceptance_status(
            load_suite(CLEAN_SUITE),
            load_evidence(CLEAN_EVIDENCE),
            load_execution_evidence(CLEAN_EXECUTION),
        )
        self.assertEqual(status["status"], "upstream_source_verified_not_accepted")
        self.assertEqual(status["task_count"], 5)
        self.assertEqual(status["upstream_source_verified_count"], 5)
        self.assertEqual(status["accepted_count"], 0)
        self.assertEqual(status["model_or_agent_runs"], 0)
        rows = {row["id"]: row for row in status["tasks"]}
        self.assertEqual(rows["m1-click-hyphenated-help-wrap"]["base_relation"], "direct-parent")
        self.assertEqual(rows["m1-xarray-unstack-single-dim"]["ancestor_gap_commits"], 0)
        self.assertEqual(rows["m1-pytest-number-docstring"]["ancestor_gap_commits"], 0)
        self.assertTrue(all(row["base_exit_code"] == 1 for row in status["tasks"]))
        self.assertTrue(all(row["fixed_exit_code"] == 0 for row in status["tasks"]))

    def test_source_evidence_allows_no_benchmark_for_direct_upstream_candidate(self):
        evidence = evidence_dict()
        evidence["benchmark"] = None
        parsed = parse_evidence(evidence)
        self.assertIsNone(parsed.benchmark_dataset)

    def test_execution_source_mismatch_fails_closed(self):
        task = next(iter(load_suite(SUITE)))
        evidence = parse_evidence(evidence_dict(task.id, task.source_ref))
        execution = parse_execution_evidence(execution_dict(task.id, "0" * 40, evidence.fixed_commit))
        with self.assertRaisesRegex(ManifestError, "base commit does not match"):
            build_acceptance_status([task], [evidence], [execution])

    def test_execution_requires_ordinary_base_failure(self):
        bad = execution_dict()
        bad["base"]["exit_code"] = 2
        with self.assertRaisesRegex(ManifestError, "ordinary pytest failure"):
            parse_execution_evidence(bad)

    def test_execution_requires_test_patch_identity(self):
        bad = execution_dict()
        del bad["test_patch"]
        with self.assertRaisesRegex(ManifestError, "test_patch"):
            parse_execution_evidence(bad)

    def test_m2_workflow_summary_label_matches_actual_runner(self):
        workflow = Path(".github/workflows/m2-upstream-verification.yml").read_text(encoding="utf-8")
        self.assertIn("runs-on: ubuntu-22.04", workflow)
        self.assertIn("Runner | `ubuntu-22.04`", workflow)
        self.assertNotIn("Runner | `ubuntu-24.04`", workflow)
        self.assertIn("Fixed commit |", workflow)
        self.assertNotIn("Fixed merge commit |", workflow)


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

    def test_acceptance_status_prints_verified_not_accepted(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(main(["acceptance-status", str(SUITE), str(EVIDENCE), str(EXECUTION)]), 0)
        payload = json.loads(output.getvalue())
        self.assertEqual(payload["schema"], "m1-acceptance-status-v0")
        self.assertEqual(payload["status"], "upstream_source_verified_not_accepted")
        self.assertEqual(payload["upstream_source_verified_count"], 5)
        self.assertEqual(payload["accepted_count"], 0)


if __name__ == "__main__":
    unittest.main()
