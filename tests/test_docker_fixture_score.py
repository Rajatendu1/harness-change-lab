import json
import unittest

from harnesslab.docker_fixture_score import validate_score,score_controls,score_in_fresh_container,ALLOWED
from harnesslab.process_observation import KeeperIdentity


def result(passed):
    return {'status':'fixed_verifier_result','passed':passed,'tests':1,'failures':int(not passed),
            'skipped':0,'adversarial_integrity_verified':False}


class PortableScoreTests(unittest.TestCase):
    def test_strict_collection_shape_denies_bool_counts_skips_extra_or_inconsistent(self):
        self.assertTrue(validate_score(json.dumps(result(True)).encode())['passed'])
        for key,value in (('tests',True),('tests',0),('skipped',1),('failures',1),('extra','private'),
                          ('adversarial_integrity_verified',True)):
            data=result(True);data[key]=value
            with self.assertRaises(ValueError):validate_score(json.dumps(data).encode())

    def test_controls_stop_on_first_mismatch_no_fake_qualification(self):
        calls=[]
        def scorer(candidate,**kwargs):
            calls.append(candidate);return result(candidate==ALLOWED[1])
        summary=score_controls(image_policy=None,scorer=scorer)
        self.assertEqual(summary['status'],'fixed_controls_passed')
        self.assertEqual(len(calls),3);self.assertFalse(summary['runtime_qualified'])
        calls.clear()
        def wrong(candidate,**kwargs):calls.append(candidate);return result(True)
        self.assertEqual(score_controls(image_policy=None,scorer=wrong)['status'],'controls_failed')
        self.assertEqual(len(calls),1)

    def test_portable_mapping_uses_verifier_interpreter_empty_gateway_and_final_removal(self):
        calls=[]
        class Adapter:
            def __init__(self,**kwargs):
                from pathlib import Path
                assert not list(Path(kwargs['socket_directory']).iterdir())
                self.name='fixture';self.gid=1001
            def create_keeper(self):calls.append('create');return KeeperIdentity(12345,1001,65534)
            def exec(self,*args,**kwargs):calls.append('import');return b'source-import-ok\n'
            def stop_candidate(self):calls.append('cleanup');return b'candidate-cleanup-ok\n'
            def observe(self):
                calls.append('observe');return b'UID PID\n1001 12345\n',{'Running':True,'Paused':False,
                    'Restarting':False,'Dead':False,'Pid':12345,'OOMKilled':False}
            def call(self,args,**kwargs):
                calls.append('score');assert '/opt/verifier/bin/python' in args
                assert kwargs['max_bytes']==4096
                return json.dumps(result(True)).encode()
            def remove_and_confirm_absent(self):calls.append('remove');return True
        summary=score_in_fresh_container(ALLOWED[1],image_policy=None,adapter_factory=Adapter)
        self.assertTrue(summary['passed']);self.assertFalse(summary['runtime_qualified'])
        self.assertEqual(calls,['create','import','cleanup','observe','score','remove'])

    def test_missing_container_cleanup_discards_success(self):
        class Adapter:
            def __init__(self,**kwargs):pass
            def create_keeper(self):raise ValueError('private-dummy')
            def remove_and_confirm_absent(self):return False
        summary=score_in_fresh_container(ALLOWED[1],image_policy=None,adapter_factory=Adapter)
        self.assertFalse(summary['passed'])
        self.assertEqual(summary['status'],'verifier_cleanup_unconfirmed')
        self.assertNotIn('private',str(summary))
