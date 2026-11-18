import unittest
from types import SimpleNamespace
from harnesslab.fixed_qualification import qualify_fixed

class FixedQualificationTests(unittest.TestCase):
    def test_distinct_images_controls_then_fixture_no_real_authority(self):
        calls=[]
        agent=SimpleNamespace(content_id='agent');verifier=SimpleNamespace(content_id='verifier')
        def stage(name,**kwargs):calls.append(name);return {'passed':True}
        def controls(**kwargs):
            self.assertIs(kwargs['image_policy'],verifier);calls.append('controls');return {'status':'fixed_controls_passed'}
        def fixture(**kwargs):
            self.assertIs(kwargs['image_policy'],agent);calls.append('fixture');return {'status':'fixture_scored_local','protected_score_passed':True}
        summary=qualify_fixed(image_policy=agent,verifier_policy=verifier,stage_runner=stage,controls=controls,fixture=fixture)
        self.assertEqual(calls,['identity','pids','memory','cpu','disk','timeout','controls','fixture'])
        self.assertEqual(summary['status'],'fixed_adapter_scope_passed')
        self.assertFalse(summary['real_task_authorized'])
    def test_same_image_or_failed_stage_cannot_qualify(self):
        image=SimpleNamespace(content_id='same')
        with self.assertRaises(ValueError):qualify_fixed(image_policy=image,verifier_policy=image)
        summary=qualify_fixed(image_policy=image,verifier_policy=SimpleNamespace(content_id='different'),stage_runner=lambda *a,**k:{'passed':False})
        self.assertEqual(summary['status'],'qualification_failed')
        self.assertEqual(len(summary['records']),1)
