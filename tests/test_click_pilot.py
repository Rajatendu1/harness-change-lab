import contextlib
import json
import unittest
from unittest.mock import patch

from harnesslab.click_pilot import run_one_click,prepare_policy

SCORE={'status':'click_verifier_result','outcome':'source_patch_verifier_pass','passed':True,
       'tests':3,'failures':0,'skipped':0,'adversarial_integrity_verified':False,'reference_mode':False}


class PilotJoinTests(unittest.TestCase):
    def invoke(self,score=None,attempt=True,collected=True,raises=False):
        candidate={'private_source.py':b'not for report'}
        transport_calls=[];score_calls=[]
        def transport(body):transport_calls.append(body);return b'{}'
        @contextlib.contextmanager
        def gateway(budget,**kwargs):
            if attempt:budget.send(b'{}')
            yield 'not-external'
        def run(_self,base):
            return {'status':'collected' if collected else 'excluded','candidate':candidate,
                    'provider_attempts':1 if attempt else 0,'runtime_qualified':False}
        def scorer(value):
            score_calls.append(value)
            if raises:raise RuntimeError('sensitive error')
            return dict(SCORE) if score is None else score
        with patch('harnesslab.click_pilot.validate_base',return_value=True), \
             patch('harnesslab.click_pilot.trial_gateway',gateway), \
             patch('harnesslab.click_pilot.ClickEditingSession.run',run):
            result=run_one_click(base={'source':b'base'},image_policy='reviewed',transport=transport,
                token_counter=lambda _:1,scorer=scorer,adapter_factory=lambda **k:object())
        return result,transport_calls,score_calls

    def test_fixed_policy(self):
        policy=prepare_policy()
        self.assertEqual((policy.max_input_tokens,policy.max_output_tokens),(5750,2048))

    def test_success_drops_candidate_and_requires_real_request_audit(self):
        result,calls,scores=self.invoke()
        self.assertEqual(result['status'],'scored')
        self.assertEqual(result['outcome'],'source_patch_verifier_pass')
        self.assertEqual(len(calls),1)
        self.assertEqual(len(scores),1)
        self.assertNotIn('candidate',result)
        self.assertNotIn('private_source',json.dumps(result))

    def test_zero_request_blocks_score_even_if_adapter_claims_collected(self):
        result,calls,scores=self.invoke(attempt=False)
        self.assertEqual(result['status'],'excluded')
        self.assertEqual(result['stage'],'request_audit')
        self.assertEqual(scores,[])

    def test_reference_and_mismatch_scores_never_count(self):
        for field,value in [('reference_mode',True),('tests',2),('skipped',1),
                            ('passed',False),('failures',2),('outcome','reference_verifier_pass')]:
            row=dict(SCORE);row[field]=value
            result,_,_=self.invoke(score=row)
            self.assertEqual(result['status'],'excluded')
            self.assertNotIn('outcome',result)

    def test_failure_is_redacted(self):
        result,_,_=self.invoke(raises=True)
        self.assertEqual(result['score_status'],'verifier_unverified')
        self.assertNotIn('sensitive',json.dumps(result))

    def test_counter_cleanup_uncertainty_invalidates_collected_score(self):
        from harnesslab.click_pilot import run_with_isolated_counter
        for removed in (True,False):
            @contextlib.contextmanager
            def counter_factory(**kwargs):
                state={'cleanup_confirmed':False}
                yield lambda _:1,state
                state['cleanup_confirmed']=removed
            with patch('harnesslab.click_pilot.run_one_click',return_value={
                    'status':'scored','outcome':'source_patch_verifier_pass'}):
                result=run_with_isolated_counter(base={},image_policy='reviewed',transport=lambda _:b'{}',
                    scorer=lambda _:{},counter_factory=counter_factory)
            self.assertEqual(result['tokenizer_container_cleanup_confirmed'],removed)
            if not removed:
                self.assertEqual(result['status'],'excluded')
                self.assertNotIn('outcome',result)

    def test_excluded_collection_never_scored(self):
        result,_,scores=self.invoke(collected=False)
        self.assertEqual(scores,[])
        self.assertEqual(result['score_status'],'not_run_collection_excluded')


if __name__=='__main__':unittest.main()
