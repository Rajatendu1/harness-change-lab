import hashlib
import json
import unittest
from unittest.mock import patch

from harnesslab.click_docker_adapter import ClickDockerAdapter
from harnesslab.click_docker_score import score_click
from harnesslab.click_task import BASE_NAMES,EDITABLE
from harnesslab.click_verifier_child import TEST_NAME,validate_score_input
from harnesslab.process_observation import KeeperIdentity
from harnesslab.source_bundle import pack_sources

BASE={name:b'base' for name in BASE_NAMES}
CANDIDATE=dict(BASE);CANDIDATE[EDITABLE[0]]=b'changed'
TEST=b'controller protected fixture'
IDENTITY=KeeperIdentity(12345,1001,65534)
ROW={'status':'click_verifier_result','passed':True,'tests':3,'failures':0,'skipped':0,
     'adversarial_integrity_verified':False}


class ScoreAdapter:
    def __init__(self,*,removed=True,row=None,**kwargs):
        self.gid=1001;self.name='fixed-scoring-container';self.calls=[];self.removed=removed
        self.row=ROW if row is None else row
    def create_keeper(self):self.calls.append('create');return IDENTITY
    def verify_denials(self):self.calls.append('denials');return b'fixed-denials-ok\n'
    def observe(self):
        self.calls.append('observe')
        return b'UID PID\n1001 12345\n',{'Running':True,'Paused':False,'Restarting':False,
            'Dead':False,'Pid':12345,'OOMKilled':False}
    def call(self,args,**kwargs):
        self.calls.append((args,kwargs))
        return json.dumps(self.row).encode()
    def remove_and_confirm_absent(self):self.calls.append('remove');return self.removed


class ClickScoreMappingTests(unittest.TestCase):
    def invoke(self,**options):
        adapter=ScoreAdapter(removed=options.pop('removed',True),row=options.pop('row',None))
        def factory(**kwargs):
            self.assertEqual(kwargs['image_policy'],'reviewed-image')
            return adapter
        with patch('harnesslab.click_docker_score.validate_base',return_value=True), \
             patch('harnesslab.click_docker_score.TEST_HASH',hashlib.sha256(TEST).hexdigest()), \
             patch('harnesslab.click_docker_score.validate_score_input',return_value=True):
            result=score_click(options.pop('candidate',CANDIDATE),base=BASE,protected_test=TEST,
                               image_policy='reviewed-image',adapter_factory=factory,**options)
        return result,adapter

    def test_fresh_scorer_receives_test_only_as_controller_stdin(self):
        result,adapter=self.invoke()
        self.assertEqual(result['outcome'],'source_patch_verifier_pass')
        calls=[call for call in adapter.calls if isinstance(call,tuple)]
        self.assertEqual(len(calls),1)
        args,kwargs=calls[0]
        self.assertEqual(args[-1],'harnesslab.click_verifier_child')
        self.assertNotIn('click_editing_child',str(args))
        self.assertIn('-i',args)
        self.assertIn(TEST,kwargs['input_data'])
        self.assertEqual(adapter.calls[-1],'remove')
        self.assertFalse(result['runtime_qualified'])

    def test_no_source_change_never_launches_scorer(self):
        result,adapter=self.invoke(candidate=BASE)
        self.assertEqual(result['status'],'no_source_change')
        self.assertEqual(adapter.calls,[])

    def test_reference_mode_remains_separate(self):
        result,_=self.invoke(candidate=BASE,reference_mode=True)
        self.assertEqual(result['outcome'],'reference_verifier_pass')
        self.assertTrue(result['reference_mode'])

    def test_other_changed_file_refused_before_container(self):
        candidate=dict(CANDIDATE);candidate['LICENSE.txt']=b'bad'
        result,adapter=self.invoke(candidate=candidate)
        self.assertEqual(result['status'],'invalid_patch')
        self.assertEqual(adapter.calls,[])

    def test_cleanup_uncertainty_discards_valid_score(self):
        result,_=self.invoke(removed=False)
        self.assertEqual(result['status'],'verifier_cleanup_unconfirmed')
        self.assertNotIn('outcome',result)

    def test_bad_collection_excluded_and_removed(self):
        for field,value in [('tests',0),('tests',2),('skipped',1),('passed',False)]:
            row=dict(ROW);row[field]=value
            result,adapter=self.invoke(row=row)
            self.assertEqual(result['status'],'verifier_setup_or_execution_error')
            self.assertEqual(adapter.calls[-1],'remove')

    def test_portable_input_hash_validation_before_import(self):
        inputs=dict(BASE);inputs[TEST_NAME]=TEST
        hashes={n:hashlib.sha256(v).hexdigest() for n,v in BASE.items()}
        with patch('harnesslab.click_verifier_child.BASE_HASHES',hashes), \
             patch('harnesslab.click_verifier_child.TEST_HASH',hashlib.sha256(TEST).hexdigest()):
            self.assertEqual(validate_score_input(pack_sources(inputs)),inputs)
            inputs['LICENSE.txt']=b'changed'
            with self.assertRaises(ValueError):validate_score_input(pack_sources(inputs))
            inputs=dict(BASE);inputs[TEST_NAME]=b'changed test'
            with self.assertRaises(ValueError):validate_score_input(pack_sources(inputs))

    def test_adapter_fixed_operation_mapping_without_docker(self):
        class Keeper:
            gid=1001;name='simulated';calls=[]
            def call(self,args,**kwargs):self.calls.append((args,kwargs));return b'marker'
        adapter=object.__new__(ClickDockerAdapter);adapter.keeper=Keeper()
        self.assertEqual(adapter.run_click_agent(),b'marker')
        args,kwargs=adapter.keeper.calls[-1]
        self.assertEqual(args[-2:],['harnesslab.click_editing_child','edit'])
        self.assertEqual(kwargs['timeout'],190)
        with self.assertRaises(ValueError):adapter._operation('shell')
        with self.assertRaises(ValueError):adapter.export_click(('other.py',))
        with self.assertRaises(ValueError):adapter.import_click(b'',('other.py',))


if __name__=='__main__':unittest.main()
