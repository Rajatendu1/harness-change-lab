import json
from pathlib import Path
import re
import unittest

from harnesslab.run_results import load_run_results, validate_run_results


ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "m7-direct-upstream-verifier-run.md"
MANIFEST = ROOT / "proposals" / "m7-direct-upstream-verifier.manifest.json"
RESULTS = ROOT / "proposals" / "m7-direct-upstream-verifier.results.jsonl"
VALIDATION = ROOT / "proposals" / "m7-direct-upstream-verifier.validation.json"
RUN_URL = "https://github.com/Rajatendu1/harness-change-lab/actions/runs/44089045408"
MANIFEST_IDENTITY = "ede5692cac16280eeec703d62d1fed419ebb2c93c0220f221c3ce58349df4bc9"
WORKFLOW_SHA256 = "704f4241652136846d921571596f54cc54afa4fe8e9e3dbfcfe9d8bd56df324d"


class M7RunRecordTests(unittest.TestCase):
    def test_real_results_validate_against_recorded_manifest(self):
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        rows = load_run_results(RESULTS)
        self.assertEqual(len(rows), 15)
        summary = validate_run_results(manifest, rows)
        self.assertEqual(summary["status"], "results_contract_valid")
        self.assertEqual(summary["task_count"], 5)
        self.assertEqual(summary["trial_count"], 15)
        self.assertEqual(summary["model_or_agent_runs"], 0)
        self.assertEqual(summary["automatic_retries"], 0)
        self.assertFalse(summary["benchmark_data_used"])
        self.assertEqual(summary["artifact_upload_count"], 0)

    def test_run_record_keeps_public_identity_and_boundaries(self):
        doc = DOC.read_text(encoding="utf-8")
        self.assertIn(RUN_URL, doc)
        self.assertIn(MANIFEST_IDENTITY, doc)
        self.assertIn(WORKFLOW_SHA256, doc)
        self.assertIn("not a coding-agent result", doc)
        self.assertIn("not a coding-agent result, model-quality result, benchmark-dataset run", doc)
        self.assertIn("does not execute, replay or authenticate", doc)
        self.assertIn("Further batches, retries, AI evaluation, benchmark-data use and paid services require separate authority", doc)

    def test_recorded_validation_matches_command_summary(self):
        payload = json.loads(VALIDATION.read_text(encoding="utf-8"))
        self.assertEqual(payload["schema"], "m6-run-result-validation-v0")
        self.assertEqual(payload["status"], "results_contract_valid")
        self.assertEqual(payload["manifest_sha256"], MANIFEST_IDENTITY)
        self.assertEqual(payload["results_sha256"], "1791f96e8981f9b1bbae3e9a7926606da28274950d33c1ae0d86c439a90d2020")
        self.assertEqual(payload["trial_count"], 15)

    def test_public_record_excludes_private_channel_identifiers(self):
        for path in [DOC, MANIFEST, RESULTS, VALIDATION]:
            text = path.read_text(encoding="utf-8")
            self.assertIsNone(re.search(r"wamid\.", text), path)
            self.assertIsNone(re.search(r"\+91\d{10}", text), path)


if __name__ == "__main__":
    unittest.main()
