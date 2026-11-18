from pathlib import Path
import unittest
from unittest.mock import patch

from harnesslab.fixed_fixture_score import score_fixed_fixture,EXPECTED
from harnesslab.docker_fixture_adapter import run_fixture
from harnesslab.image_policy import ImagePolicy

PYTHON='/tmp/harness-verifier-runtime/bin/python'
ROOT='/tmp/harness-verifier-runtime'
POLICY=ImagePolicy('python@sha256:'+'a'*64,'sha256:'+'b'*64,(),1024**3)


@unittest.skipUnless(Path(PYTHON).exists(),'Existing pinned local scorer required')
class FixedFixtureScoreTests(unittest.TestCase):
    def test_actual_local_protected_test_pass_has_explicit_boundary(self):
        result=score_fixed_fixture(EXPECTED,python=PYTHON,runtime_root=ROOT)
        self.assertTrue(result['passed'])
        self.assertEqual(result['score']['tests'],1)
        self.assertFalse(result['adversarial_integrity_verified'])
        self.assertEqual(result['real_model_repairs'],0)

    def test_wrong_changed_edit_fails_and_unchanged_has_no_repair(self):
        wrong=score_fixed_fixture({'example.py':b'def answer():\n    return 2\n'},python=PYTHON,runtime_root=ROOT)
        self.assertFalse(wrong['passed'])
        self.assertEqual(wrong['score']['outcome'],'verifier_fail')
        unchanged=score_fixed_fixture({'example.py':b'def answer():\n    return 0\n'},python=PYTHON,runtime_root=ROOT)
        self.assertFalse(unchanged['passed'])
        self.assertEqual(unchanged['score']['outcome'],'no_source_change')

    def test_input_and_setup_errors_do_not_pass(self):
        self.assertFalse(score_fixed_fixture({'unexpected.py':b'x'},python=PYTHON,runtime_root=ROOT)['passed'])
        result=score_fixed_fixture(EXPECTED,python='/missing/python',runtime_root=ROOT)
        self.assertFalse(result['passed'])
        self.assertEqual(result['score']['outcome'],'verifier_setup_error')


class ScorerOrderingTests(unittest.TestCase):
    def test_failed_collection_never_calls_scorer_or_exposes_candidate(self):
        scorer=lambda candidate:self.fail('Scorer must not run')
        class Adapter:
            def __init__(self,**kwargs):pass
        with patch('harnesslab.docker_fixture_adapter.DockerFixtureAdapter',Adapter), \
             patch('harnesslab.docker_fixture_adapter.FixtureEditingSession.run',return_value={
                'status':'failed','stage':'container_cleanup','candidate':None}):
            result=run_fixture(image_policy=POLICY,scorer=scorer)
        self.assertEqual(result['protected_score_boundary'],'not_run_collection_failed')
        self.assertNotIn('candidate',result)
        self.assertFalse(result['runtime_qualified'])
