import hashlib
import json
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "m8-coding-agent-smoke-run.md"
RUN = ROOT / "proposals" / "m8-coding-agent-smoke.run.json"
RESULTS = ROOT / "proposals" / "m8-coding-agent-smoke.results.jsonl"
RUN_URL = "https://github.com/Rajatendu1/harness-change-lab/actions/runs/44092986637"
M7_RUN_URL = "https://github.com/Rajatendu1/harness-change-lab/actions/runs/44089045408"
RESULTS_SHA256 = "a28e7eee03dfbab9d54c24b0a64213b729bddc8a288bb666ce6a6a32d4824d8f"


class M8RunRecordTests(unittest.TestCase):
    def test_run_metadata_has_non_empty_run_and_results_identity(self):
        payload = json.loads(RUN.read_text(encoding="utf-8"))
        self.assertEqual(payload["schema"], "m8-agent-smoke-run-v0")
        self.assertEqual(payload["status"], "completed_consumed")
        self.assertEqual(payload["run"]["id"], 44092986637)
        self.assertEqual(payload["run"]["attempt"], 1)
        self.assertEqual(payload["run"]["event"], "workflow_dispatch")
        self.assertEqual(payload["run"]["url"], RUN_URL)
        self.assertEqual(payload["run"]["head_sha"], "bff560754ae9b90ab7250cb6284366a05b6c0a17")
        self.assertEqual(payload["run"]["pre_rewrite_head_sha"], "6bac63fa98a6a6783089b05ee564fb57e0115a63")
        self.assertEqual(payload["results"]["sha256"], RESULTS_SHA256)
        actual = hashlib.sha256(RESULTS.read_bytes()).hexdigest()
        self.assertEqual(actual, RESULTS_SHA256)

    def test_execution_approval_is_per_run_and_consumed(self):
        payload = json.loads(RUN.read_text(encoding="utf-8"))["approval_scope"]
        self.assertIn("not standing execution authority", payload["task_rights"])
        self.assertEqual(payload["m7_execution"]["status"], "consumed")
        self.assertEqual(payload["m7_execution"]["run_url"], M7_RUN_URL)
        self.assertEqual(payload["m8_execution"]["status"], "consumed")
        self.assertEqual(payload["m8_execution"]["run_url"], RUN_URL)
        self.assertEqual(payload["remaining_execution_authority"], "none")
        self.assertNotIn("approval_id", json.dumps(payload))

    def test_run_metadata_is_not_live_execution_authority(self):
        payload = json.loads(RUN.read_text(encoding="utf-8"))
        self.assertEqual(payload["interpretation"], "descriptive record only; not consulted by manifest or acceptance code; grants no execution authority")
        for doc in (
            ROOT / "docs" / "m5-review-gate-reconciliation.md",
            ROOT / "docs" / "m6-run-result-intake.md",
            ROOT / "docs" / "m7-direct-upstream-verifier-run.md",
        ):
            text = doc.read_text(encoding="utf-8")
            self.assertIn("proposals/m8-coding-agent-smoke.run.json", text)
            self.assertIn("prepare-only", text)

    def test_run_doc_distinguishes_protocol_gaps_from_model_failure(self):
        text = DOC.read_text(encoding="utf-8")
        normalized = " ".join(text.split())
        self.assertIn("Run ID: `44092986637`", text)
        self.assertIn("treated as 45 trials", normalized)
        self.assertIn("harness setup failure, not an assertion failure or model-quality signal", normalized)
        self.assertIn("exit 4, setup failure", text)
        self.assertIn("agent effectiveness remains unproven", normalized)
        self.assertIn("reason the agent made no source edit remains a hypothesis", normalized)

    def test_public_record_excludes_private_channel_identifiers(self):
        patterns = [
            re.compile("wa" + r"mid\."),
            re.compile(r"\+[0-9]{10,15}\b"),
            re.compile(r"\b91[6-9][0-9]{9}\b"),
        ]
        for path in (DOC, RUN, RESULTS):
            text = path.read_text(encoding="utf-8")
            for pattern in patterns:
                self.assertIsNone(pattern.search(text), f"{pattern.pattern} in {path}")


if __name__ == "__main__":
    unittest.main()
