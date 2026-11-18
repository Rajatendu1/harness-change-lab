"""Prepared Click lifecycle tests with simulated adapter, never Docker/model."""
import json
import unittest
from unittest.mock import patch

from harnesslab.click_task import BASE_HASHES,BASE_NAMES,EDITABLE,validate_base
from harnesslab.click_editing_child import agent_command
from harnesslab.click_editing_session import ClickEditingSession
from harnesslab.click_docker_score import validate_score_result
from harnesslab.request_budget import TrialRequestBudget
from harnesslab.process_observation import KeeperIdentity
from harnesslab.source_bundle import pack_sources

IDENTITY=KeeperIdentity(12345,1001,65534)
BASE={name:b'base' for name in BASE_NAMES}


class FakeAdapter:
    def __init__(self,budget,fail=None,requests=1,removed=True):
        self.budget=budget;self.fail=fail;self.requests=requests;self.removed=removed;self.calls=[]
    def action(self,name,value):
        self.calls.append(name)
        if self.fail==name:raise ValueError('untrusted private error')
        return value
    def create_keeper(self):return self.action('create',IDENTITY)
    def verify_denials(self):return self.action('denials',b'fixed-denials-ok\n')
    def import_click(self,raw,names):return self.action('import',b'source-import-ok\n')
    def run_click_agent(self):
        self.action('agent',None)
        for _ in range(self.requests):
            try:self.budget.send(b'{}')
            except Exception:pass
        return b'click-agent-finished\n'
    def stop_candidate(self):return self.action('cleanup',b'candidate-cleanup-ok\n')
    def observe(self):return self.action('observe',(b'UID PID\n1001 12345\n',
        {'Running':True,'Paused':False,'Restarting':False,'Dead':False,'Pid':12345,'OOMKilled':False}))
    def export_click(self,names):return self.action('export',pack_sources({EDITABLE[0]:b'changed'}))
    def remove_and_confirm_absent(self):return self.action('remove',self.removed)


class ClickPreparationTests(unittest.TestCase):
    def execute(self,**kwargs):
        calls=[]
        def provider(raw):calls.append(raw);return b'{}'
        budget=TrialRequestBudget(1,provider)
        adapter=FakeAdapter(budget,**kwargs)
        session=ClickEditingSession(adapter,budget)
        with patch('harnesslab.click_editing_session.validate_base',return_value=True):
            result=session.run(BASE)
        return result,adapter,session,calls

    def test_complete_candidate_only_after_removal(self):
        result,adapter,session,calls=self.execute()
        self.assertEqual(result['status'],'collected')
        self.assertEqual(result['candidate'][EDITABLE[0]],b'changed')
        self.assertEqual(adapter.calls,['create','denials','import','agent','cleanup','observe','export','remove'])
        self.assertEqual(len(calls),1)
        self.assertFalse(result['runtime_qualified'])
        with self.assertRaises(ValueError):session.run(BASE)

    def test_every_failed_stage_discards_candidate_and_attempts_removal(self):
        for stage in ('create','denials','import','agent','cleanup','observe','export','remove'):
            with self.subTest(stage=stage):
                result,adapter,_,_=self.execute(fail=stage)
                self.assertEqual(result['status'],'excluded')
                self.assertIsNone(result['candidate'])
                self.assertEqual(adapter.calls[-1],'remove')
                self.assertNotIn('private',json.dumps(result))

    def test_zero_request_cannot_count_as_collection(self):
        result,adapter,_,calls=self.execute(requests=0)
        self.assertEqual(result['stage'],'request_audit')
        self.assertIsNone(result['candidate'])
        self.assertEqual(calls,[])
        self.assertNotIn('export',adapter.calls)

    def test_two_agent_requests_still_only_one_transport_attempt(self):
        result,_,_,calls=self.execute(requests=2)
        self.assertEqual(len(calls),1)
        self.assertEqual(result['provider_attempts'],1)
        self.assertEqual(result['provider_outcomes'],['returned'])

    def test_failed_provider_attempt_excluded_even_if_agent_exit_success(self):
        def failure(_):raise RuntimeError('sensitive provider error')
        budget=TrialRequestBudget(1,failure);adapter=FakeAdapter(budget)
        with patch('harnesslab.click_editing_session.validate_base',return_value=True):
            result=ClickEditingSession(adapter,budget).run(BASE)
        self.assertEqual(result['stage'],'request_audit')
        self.assertEqual(result['provider_outcomes'],['failed'])
        self.assertIsNone(result['candidate'])

    def test_unconfirmed_removal_always_excludes(self):
        result,_,_,_=self.execute(removed=False)
        self.assertEqual(result['stage'],'container_cleanup')
        self.assertIsNone(result['candidate'])

    def test_pinned_base_never_accepts_placeholder_or_missing_files(self):
        for candidate in (BASE,{EDITABLE[0]:b'base'},{}):
            with self.assertRaises(ValueError):validate_base(candidate)

    def test_fixed_agent_surface_no_hidden_or_shell_commands(self):
        command=agent_command()
        self.assertIn('--no-stream',command)
        self.assertIn('--no-suggest-shell-commands',command)
        self.assertIn('--no-auto-test',command)
        self.assertIn('--no-auto-lint',command)
        self.assertEqual(command[-1],EDITABLE[0])
        self.assertFalse(any('protected' in a or 'known-fix' in a or 'shell-command'==a for a in command))
        self.assertEqual(len(BASE_HASHES),19)

    def test_exact_verifier_shape_and_no_skips(self):
        row={'status':'click_verifier_result','passed':True,'tests':3,'failures':0,
             'skipped':0,'adversarial_integrity_verified':False}
        self.assertTrue(validate_score_result(json.dumps(row).encode())['passed'])
        for field,value in [('tests',0),('tests',2),('skipped',1),('passed',False),
                            ('failures',True),('adversarial_integrity_verified',True)]:
            changed=dict(row);changed[field]=value
            with self.assertRaises(ValueError):validate_score_result(json.dumps(changed).encode())
        with self.assertRaises(ValueError):validate_score_result(b'not json')


if __name__=='__main__':unittest.main()
