import contextlib
import io
import json
import os
from pathlib import Path
import runpy
import unittest
from unittest.mock import patch


class ClickLiveEntryTests(unittest.TestCase):
    def setUp(self):
        self.module=runpy.run_path(str(Path('proposals/click-runtime/run_pilot.py').resolve()))
        self.main=self.module['main'];self.g=self.main.__globals__

    def exercise(self,*,scope=True,key=True,controls=True,build=True,cleanup=True,
                 pilot_result=None,pilot_error=False):
        events=[]
        def assemble(directory):
            events.append('assemble')
            return {'amd64_manifest_digest':'sha256:'+'a'*64},{'agent':{},'verifier':{}},{},'license'
        def inputs():return {'src/click/formatting.py':b'base'},b'fixed',b'protected'
        def capture(args,**kwargs):
            self.assertNotIn(self.g['SECRET_NAME'],os.environ)
            events.append('remove' if args[:3]==['docker','image','rm'] else 'pull')
            if args[:3]==['docker','image','rm'] and not cleanup:raise RuntimeError('fake cleanup failure')
        def images(*args,**kwargs):
            kwargs['created_ids'].extend(['sha256:'+'b'*64,'sha256:'+'c'*64])
            if not build:raise RuntimeError('fake build failure')
            class Policy:
                def __init__(self,identity):self.content_id=identity
            return {'agent':Policy('agent'),'verifier':Policy('verifier')},{}
        def score(candidate,**kwargs):
            events.append('reference')
            self.assertTrue(kwargs['reference_mode'])
            return {'outcome':('reference_verifier_pass' if candidate['src/click/formatting.py']==b'fixed'
                    else 'reference_verifier_fail') if controls else 'bad', 'tests':3,'skipped':0}
        def transport(endpoint,token,timeout):
            events.append('transport');self.assertEqual(endpoint,self.g['ENDPOINT'])
            self.assertEqual(token,'unit-test-placeholder');self.assertEqual(timeout,60)
            self.assertEqual(events.count('reference'),2)
            return object()
        def pilot(**kwargs):
            events.append('pilot')
            self.assertNotIn(self.g['SECRET_NAME'],os.environ)
            if pilot_error:raise RuntimeError('fake private failure not to be printed')
            return dict(pilot_result or {'status':'scored','outcome':'source_patch_verifier_pass',
                'provider_attempts':1,'tokenizer_container_cleanup_confirmed':True})
        env={}
        if scope:env['HARNESS_CLICK_SCOPE']=self.g['SCOPE']
        if key:env[self.g['SECRET_NAME']]='unit-test-placeholder'
        out=io.StringIO()
        with patch.dict(self.g,assemble=assemble,task_inputs=inputs,capture=capture,
                build_click_images=images,score_click=score,https_transport=transport,
                run_with_isolated_counter=pilot),patch.dict(os.environ,env,clear=True),contextlib.redirect_stdout(out):
            code=self.main()
            self.assertNotIn(self.g['SECRET_NAME'],os.environ)
        text=out.getvalue();self.assertNotIn('unit-test-placeholder',text)
        self.assertNotIn('private failure',text)
        return code,json.loads(text),events

    def test_import_does_not_touch_environment_or_network(self):
        self.assertEqual(self.g['ENDPOINT'],'https://api.groq.com/openai/v1/chat/completions')
        self.assertNotIn('small_canned_edit',Path('proposals/click-runtime/run_pilot.py').read_text())

    def test_scope_refusal_precedes_all_work(self):
        code,row,events=self.exercise(scope=False,key=False)
        self.assertEqual(code,3);self.assertEqual(events,[])
        self.assertEqual(row['status'],'live_scope_marker_missing')

    def test_success_is_not_credential_cleanup(self):
        code,row,events=self.exercise()
        self.assertEqual(code,0);self.assertEqual(row['real_model_repairs'],1)
        self.assertTrue(row['image_cleanup_confirmed'])
        self.assertFalse(row['credential_revocation_confirmed'])
        self.assertFalse(row['actions_secret_removal_confirmed'])
        self.assertEqual(events.count('transport'),1);self.assertEqual(events.count('pilot'),1)
        self.assertEqual(events.count('remove'),2)

    def test_missing_key_never_constructs_transport(self):
        code,row,events=self.exercise(key=False)
        self.assertEqual(code,3);self.assertNotIn('transport',events)
        self.assertEqual(events.count('remove'),2)

    def test_controls_fail_before_transport(self):
        code,row,events=self.exercise(controls=False)
        self.assertEqual(code,3);self.assertNotIn('transport',events)
        self.assertNotIn('pilot',events);self.assertEqual(events.count('remove'),2)

    def test_partial_build_removes_created_images(self):
        code,row,events=self.exercise(build=False)
        self.assertEqual(code,3);self.assertNotIn('transport',events)
        self.assertFalse(row['image_cleanup_confirmed']);self.assertEqual(events.count('remove'),2)

    def test_cleanup_failure_discards_patch_success(self):
        code,row,events=self.exercise(cleanup=False)
        self.assertEqual(code,3);self.assertNotIn('outcome',row)
        self.assertEqual(row['real_model_repairs'],0);self.assertFalse(row['image_cleanup_confirmed'])

    def test_thrown_pilot_failure_does_not_retry(self):
        code,row,events=self.exercise(pilot_error=True)
        self.assertEqual(code,3);self.assertEqual(events.count('pilot'),1)
        self.assertEqual(row['provider_attempts'],'unverified_do_not_retry')
        self.assertEqual(events.count('remove'),2)

    def test_scored_model_failure_is_not_repair(self):
        code,row,events=self.exercise(pilot_result={'status':'scored','outcome':'verifier_fail',
            'provider_attempts':1,'tokenizer_container_cleanup_confirmed':True})
        self.assertEqual(code,0);self.assertEqual(row['real_model_repairs'],0)
        self.assertEqual(row['outcome'],'verifier_fail')

    def test_excluded_attempt_has_no_repair(self):
        code,row,events=self.exercise(pilot_result={'status':'excluded','stage':'request_audit'})
        self.assertEqual(code,3);self.assertEqual(row['real_model_repairs'],0)
        self.assertEqual(events.count('pilot'),1)


if __name__=='__main__':unittest.main()
