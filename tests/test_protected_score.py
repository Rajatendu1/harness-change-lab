import dataclasses
from pathlib import Path
import shutil
import tempfile
import unittest

from harnesslab.protected_score import score_candidate


@unittest.skipUnless(shutil.which('bwrap') and Path('/tmp/harness-verifier-runtime/bin/python').exists(),
                     'Local OS-isolated pytest fixture runtime required')
class ProtectedScoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.base, self.candidate, self.protected = [self.root / name for name in ('base', 'candidate', 'protected')]
        for path in (self.base, self.candidate, self.protected):
            path.mkdir()
        (self.base / 'example.py').write_text('def answer():\n    return 0\n')
        (self.candidate / 'example.py').write_text('def answer():\n    return 1\n')
        (self.protected / 'test_hidden.py').write_text('import sys\nsys.path.insert(0,"/work")\nfrom example import answer\ndef test_answer():\n    assert answer() == 1\n')

    def score(self, **kwargs):
        options = dict(base=self.base, candidate=self.candidate, editable_files=['example.py'],
                       protected_tests=self.protected, python='/tmp/harness-verifier-runtime/bin/python',
                       runtime_root='/tmp/harness-verifier-runtime')
        options.update(kwargs)
        return score_candidate(**options)

    def test_source_patch_and_collected_protected_test_pass(self):
        result = self.score()
        self.assertEqual(result.outcome, 'source_patch_verifier_pass')
        self.assertEqual(result.tests, 1)
        self.assertEqual(result.verifier_exit_code, 0)
        self.assertFalse((self.candidate / '.controller-score.xml').exists())
        self.assertEqual((self.base / 'example.py').read_text(), 'def answer():\n    return 0\n')

    def test_wrong_source_patch_fails_assertion(self):
        (self.candidate / 'example.py').write_text('def answer():\n    return 2\n')
        result = self.score()
        self.assertEqual(result.outcome, 'verifier_fail')
        self.assertEqual(result.failures, 1)
        self.assertEqual(result.tests, 1)

    def test_exit_zero_without_source_change_is_not_success(self):
        shutil.copyfile(self.base / 'example.py', self.candidate / 'example.py')
        self.assertEqual(self.score().outcome, 'no_source_change')

    def test_editing_test_or_other_file_is_invalid(self):
        (self.candidate / 'test_forged.py').write_text('def test_fake(): pass\n')
        self.assertEqual(self.score().outcome, 'invalid_patch')

    def test_no_collected_test_is_setup_error(self):
        (self.protected / 'test_hidden.py').write_text('# no tests\n')
        self.assertEqual(self.score().outcome, 'verifier_setup_error')

    def test_collection_error_is_not_agent_failure(self):
        (self.protected / 'test_hidden.py').write_text('raise RuntimeError("fixture collection failure")\n')
        self.assertEqual(self.score().outcome, 'verifier_setup_error')

    def test_symlink_candidate_is_rejected(self):
        (self.candidate / 'link').symlink_to('/etc/passwd')
        self.assertEqual(self.score().outcome, 'invalid_input')

    def test_verifier_timeout_is_separate(self):
        (self.protected / 'test_hidden.py').write_text('import time\ndef test_wait(): time.sleep(30)\n')
        self.assertEqual(self.score(timeout_s=0.3).outcome, 'verifier_timeout')


    def test_skips_require_exact_controller_policy_and_a_scored_test(self):
        (self.protected / 'test_hidden.py').write_text('import pytest\ndef test_real(): assert True\n@pytest.mark.skip(reason="fixture")\ndef test_optional(): pass\n')
        self.assertEqual(self.score().outcome, 'verifier_setup_error')
        result = self.score(allowed_skips=['test_hidden::test_optional'])
        self.assertEqual(result.outcome, 'source_patch_verifier_pass')
        self.assertEqual(result.skipped, 1)
        self.assertFalse(result.adversarial_integrity_verified)
        self.assertEqual(self.score(allowed_skips=['other::test_optional']).outcome, 'verifier_setup_error')

    def test_all_skipped_is_never_success_even_if_declared(self):
        (self.protected / 'test_hidden.py').write_text('import pytest\n@pytest.mark.skip(reason="fixture")\ndef test_optional(): pass\n')
        self.assertEqual(self.score(allowed_skips=['test_hidden::test_optional']).outcome, 'verifier_setup_error')


    def test_reference_no_change_is_distinct_from_agent_repair(self):
        shutil.copyfile(self.base / 'example.py', self.candidate / 'example.py')
        result=self.score(reference_mode=True)
        self.assertEqual(result.outcome,'reference_verifier_fail')
        self.assertEqual(result.tests,1)
        self.assertEqual(result.changed_files,())

    def test_explicit_node_selects_only_declared_test(self):
        (self.protected/'test_hidden.py').write_text('def test_selected(): assert True\ndef test_not_selected(): assert False\n')
        result=self.score(test_node='test_hidden.py::test_selected')
        self.assertEqual(result.outcome,'source_patch_verifier_pass')
        self.assertEqual(result.tests,1)

    def test_src_layout_candidate_import(self):
        for root,value in ((self.base,0),(self.candidate,1)):
            (root/'src').mkdir()
            (root/'src/calc.py').write_text('value = '+str(value)+'\n')
            (root/'example.py').unlink()
        (self.protected/'test_hidden.py').write_text('import calc\ndef test_value(): assert calc.value==1\n')
        result=self.score(editable_files=['src/calc.py'],source_import_directory='src')
        self.assertEqual(result.outcome,'source_patch_verifier_pass')
        self.assertEqual(result.tests,1)

    def test_import_and_test_node_path_escape_rejected(self):
        for options in ({'source_import_directory':'../outside'}, {'test_node':'../escape.py'},
                        {'test_node':'/tmp/escape.py'}, {'plugins':['../outside']}):
            self.assertEqual(self.score(**options).outcome,'invalid_input')


    def test_known_fixed_reference_is_not_an_agent_repair(self):
        result=self.score(reference_mode=True)
        self.assertEqual(result.outcome,'reference_verifier_pass')
        self.assertEqual(result.tests,1)
