import unittest

from harnesslab.fixture_editing_session import FixtureEditingSession
from harnesslab.process_observation import KeeperIdentity
from harnesslab.source_bundle import pack_sources,unpack_sources

BASE={'src/a.py':b'old','fixed.py':b'immutable'}
NAMES=['src/a.py']


class FakeAdapter:
    def __init__(self,fail=None): self.calls=[];self.fail=fail
    def step(self,name,value):
        self.calls.append(name)
        if self.fail==name: raise RuntimeError('private-dummy-path-and-output')
        return value
    def create_keeper(self): return self.step('create',KeeperIdentity(12345,1001,65534))
    def import_base(self,raw,names):
        assert unpack_sources(raw,expected_names=names)==BASE
        return self.step('import',b'source-import-ok\n')
    def run_canned_agent(self): return self.step('canned_agent',b'canned-agent-finished\n')
    def stop_candidate(self): return self.step('candidate_cleanup',b'candidate-cleanup-ok\n')
    def observe(self):
        return self.step('observe',(b'UID PID\n1001 12345\n',
            {'Running':True,'Paused':False,'Restarting':False,'Dead':False,'Pid':12345,'OOMKilled':False}))
    def export_sources(self,names): return self.step('export',pack_sources({'src/a.py':b'new'}))
    def remove_and_confirm_absent(self): return self.step('remove',True)


class FixtureEditingSessionTests(unittest.TestCase):
    def test_complete_fixture_lifecycle_keeps_immutable_base_and_cleans_before_return(self):
        adapter=FakeAdapter(); result=FixtureEditingSession(adapter).run(base=BASE,editable_names=NAMES)
        self.assertEqual(adapter.calls,['create','import','canned_agent','candidate_cleanup','observe','export','remove'])
        self.assertEqual(result['candidate'],{'src/a.py':b'new','fixed.py':b'immutable'})
        self.assertEqual(BASE['src/a.py'],b'old')
        self.assertFalse(result['qualification_complete'])
        self.assertEqual(result['evidence'],'injected_adapter_lifecycle_only')

    def test_every_stage_failure_removes_and_never_returns_candidate(self):
        stages=['create','import','canned_agent','candidate_cleanup','observe','export']
        for index,stage in enumerate(stages):
            with self.subTest(stage=stage):
                adapter=FakeAdapter(stage)
                result=FixtureEditingSession(adapter).run(base=BASE,editable_names=NAMES)
                self.assertEqual(result['stage'],stage)
                self.assertIsNone(result['candidate'])
                self.assertEqual(adapter.calls,stages[:index+1]+['remove'])
                self.assertNotIn('private',str(result))

    def test_failed_removal_overrides_candidate_and_earlier_failure(self):
        for earlier in (None,'import'):
            adapter=FakeAdapter(earlier)
            adapter.remove_and_confirm_absent=lambda:False
            result=FixtureEditingSession(adapter).run(base=BASE,editable_names=NAMES)
            self.assertEqual(result['stage'],'container_cleanup')
            self.assertIsNone(result['candidate'])
        adapter=FakeAdapter('remove')
        self.assertEqual(FixtureEditingSession(adapter).run(base=BASE,editable_names=NAMES)['stage'],'container_cleanup')

    def test_extra_process_denies_export_and_scoring(self):
        adapter=FakeAdapter()
        original=adapter.observe
        def observe():
            top,state=original();return top+b'65534 12346\n',state
        adapter.observe=observe
        result=FixtureEditingSession(adapter).run(base=BASE,editable_names=NAMES)
        self.assertEqual(result['stage'],'observe')
        self.assertNotIn('export',adapter.calls)
        self.assertIsNone(result['candidate'])

    def test_wrong_markers_or_archive_deny_downstream(self):
        for method,stage in (('import_base','import'),('run_canned_agent','canned_agent'),
                             ('stop_candidate','candidate_cleanup'),('export_sources','export')):
            adapter=FakeAdapter();setattr(adapter,method,lambda *args:b'wrong-or-private-dummy')
            result=FixtureEditingSession(adapter).run(base=BASE,editable_names=NAMES)
            self.assertEqual(result['stage'],stage)
            self.assertIsNone(result['candidate'])
            self.assertEqual(adapter.calls[-1],'remove')

    def test_invalid_input_has_no_effect_and_session_never_retries(self):
        for names in ([],['missing'],['src/a.py','src/a.py']):
            adapter=FakeAdapter();session=FixtureEditingSession(adapter)
            with self.assertRaises(ValueError):session.run(base=BASE,editable_names=names)
            self.assertEqual(adapter.calls,[])
            with self.assertRaises(ValueError):session.run(base=BASE,editable_names=NAMES)
        session=FixtureEditingSession(FakeAdapter());session.run(base=BASE,editable_names=NAMES)
        with self.assertRaises(ValueError):session.run(base=BASE,editable_names=NAMES)
