import hashlib
import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from harnesslab.click_diagnostic import qualify_click,small_canned_edit
from harnesslab.click_task import EDITABLE
from harnesslab.image_policy import ImagePolicy


class ClickDiagnosticTests(unittest.TestCase):
    def test_no_live_model_or_credential_surface(self):
        source=Path('proposals/click-runtime/run_diagnostic.py').read_text()
        self.assertNotIn('https_transport',source)
        self.assertNotIn('GROQ_API_KEY',source)
        self.assertNotIn('os.environ',source)
        self.assertIn('real_provider_calls=0',source)
        self.assertIn('image_cleanup_confirmed',source)

    def test_canned_small_edit_does_not_depend_on_response_or_private_data(self):
        body=small_canned_edit({EDITABLE[0]:b'        replace_whitespace=False,\n'})
        value=json.loads(body)
        self.assertIn('break_on_hyphens=False',value['choices'][0]['message']['content'])
        self.assertNotIn('usage',value)
        with self.assertRaises(ValueError):small_canned_edit({EDITABLE[0]:b'other source'})

    def test_public_reference_controls_precede_canned_trial(self):
        test=b'controller fixture';calls=[]
        class Policy:
            def __init__(self,identity):self.content_id=identity
        def score(candidate,**kwargs):
            self.assertTrue(kwargs['reference_mode']);calls.append('score')
            return {'outcome':'reference_verifier_fail' if len(calls)==1 else 'reference_verifier_pass',
                    'tests':3,'skipped':0}
        def pilot(**kwargs):
            calls.append('pilot');response=json.loads(kwargs['transport'](b'{}'))
            self.assertIn('canned',response['id'])
            return {'status':'scored','outcome':'source_patch_verifier_pass','provider_attempts':1,
                    'tokenizer_container_cleanup_confirmed':True}
        with patch('harnesslab.click_diagnostic.validate_base',return_value=True), \
             patch('harnesslab.click_diagnostic.TEST_HASH',hashlib.sha256(test).hexdigest()):
            result=qualify_click(base={EDITABLE[0]:b'        replace_whitespace=False,\n'},
                known_fixed_source=b'fixed',protected_test=test,image_policy=Policy('agent'),
                verifier_policy=Policy('verifier'),score=score,pilot=pilot)
        self.assertEqual(calls,['score','score','pilot'])
        self.assertEqual(result['status'],'click_model_free_task_mapping_passed')
        self.assertEqual(result['real_provider_calls'],0)
        self.assertEqual(result['real_model_repairs'],0)

    def test_failed_controls_stop_before_trial(self):
        test=b'controller fixture'
        class Policy:
            def __init__(self,identity):self.content_id=identity
        with patch('harnesslab.click_diagnostic.validate_base',return_value=True), \
             patch('harnesslab.click_diagnostic.TEST_HASH',hashlib.sha256(test).hexdigest()):
            result=qualify_click(base={},known_fixed_source=b'fixed',protected_test=test,
                image_policy=Policy('agent'),verifier_policy=Policy('verifier'),
                score=lambda *a,**k:{'status':'setup_error'},pilot=lambda **k:self.fail('not allowed'))
        self.assertEqual(result['status'],'click_controls_unverified')


if __name__=='__main__':unittest.main()
