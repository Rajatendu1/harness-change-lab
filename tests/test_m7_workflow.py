from pathlib import Path
import unittest


class M7WorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workflow = Path(".github/workflows/m7-direct-upstream-verifier.yml").read_text(encoding="utf-8")

    def test_dispatch_is_manual_and_runner_is_free_public_shape(self):
        self.assertIn("workflow_dispatch:", self.workflow)
        self.assertIn("runs-on: ubuntu-22.04", self.workflow)
        self.assertIn("contents: read", self.workflow)

    def test_trial_and_concurrency_bounds_are_fixed(self):
        self.assertIn("timeout-minutes: 20", self.workflow)
        self.assertIn("max-parallel: 5", self.workflow)
        self.assertIn("--trials-per-task 3", self.workflow)
        self.assertIn("--max-concurrency 5", self.workflow)
        self.assertIn("plan['trials_per_task'] != 3", self.workflow)
        self.assertIn("plan['total_trials'] != 15", self.workflow)

    def test_policy_excludes_models_benchmark_data_secrets_artifacts_and_retries(self):
        self.assertIn("'benchmark_data_use'] or policy['automatic_retry'", self.workflow)
        self.assertIn("'model_access': False", self.workflow)
        self.assertIn("'benchmark_data_used': False", self.workflow)
        self.assertIn("'secrets_used': False", self.workflow)
        self.assertIn("'artifact_upload_count': 0", self.workflow)
        self.assertIn("'automatic_retry': False", self.workflow)
        self.assertNotIn("upload-artifact", self.workflow)
        self.assertNotIn("secrets.", self.workflow)


if __name__ == "__main__":
    unittest.main()
