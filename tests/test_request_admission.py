import copy
import json
import unittest
import urllib.error
import urllib.request

from harnesslab.request_admission import TextRequestPolicy
from harnesslab.request_budget import TrialRequestBudget
from harnesslab.trial_gateway import trial_gateway


class AdmissionTests(unittest.TestCase):
    def setUp(self):
        self.policy = TextRequestPolicy('chosen-model', 6000, 2048)
        self.payload = {'model':'chosen-model', 'messages':[
            {'role':'system','content':'system instructions'},
            {'role':'user','content':'public source only'}],
            'stream':False,'max_tokens':2048}

    def test_complete_context_counter_and_exact_boundary(self):
        seen=[]
        raw=self.policy.admit(self.payload,count_tokens=lambda pairs: seen.append(pairs) or 6000)
        self.assertEqual(json.loads(raw),self.payload)
        self.assertEqual(seen[0],(('system','system instructions'),('user','public source only')))
        with self.assertRaises(ValueError):
            self.policy.admit(self.payload,count_tokens=lambda _:6001)

    def test_refuse_missing_or_failed_tokenizer(self):
        for counter in (None, lambda _:True, lambda _:None, lambda _:-1):
            with self.assertRaises(ValueError):
                self.policy.admit(self.payload,count_tokens=counter)
        def unavailable(_): raise RuntimeError('private diagnostic')
        with self.assertRaisesRegex(ValueError,'accounting unavailable'):
            self.policy.admit(self.payload,count_tokens=unavailable)

    def test_refuse_nontext_and_side_channels(self):
        for field,value in [('content',[{'type':'image_url','image_url':'not read'}]),
                            ('tool_calls',[]),('name','other')]:
            payload=copy.deepcopy(self.payload)
            payload['messages'][0][field]=value
            with self.assertRaises(ValueError):
                self.policy.admit(payload,count_tokens=lambda _:1)
        for field,value in [('model','other'),('stream',True),('tools',[]),
                            ('max_tokens',2049),('max_tokens',True),('temperature',float('nan'))]:
            payload=dict(self.payload);payload[field]=value
            with self.assertRaises(ValueError):
                self.policy.admit(payload,count_tokens=lambda _:1)

    def test_byte_rejection_precedes_counter(self):
        payload=copy.deepcopy(self.payload)
        payload['messages'][1]['content']='a'*32768
        def must_not_run(_): self.fail('oversized request reached tokenizer')
        with self.assertRaisesRegex(ValueError,'byte bound'):
            self.policy.admit(payload,count_tokens=must_not_run)

    def test_gateway_refusal_never_reaches_provider_budget(self):
        calls=[]
        budget=TrialRequestBudget(1,lambda raw: calls.append(raw) or b'{}')
        with trial_gateway(budget,expected_model='chosen-model',max_output_tokens=2048,
                           request_policy=self.policy,token_counter=lambda _:6001) as base:
            request=urllib.request.Request(base+'/chat/completions',
                data=json.dumps(self.payload).encode(),headers={'Content-Type':'application/json'})
            with self.assertRaises(urllib.error.HTTPError) as error:
                urllib.request.urlopen(request,timeout=2)
            self.assertEqual(error.exception.code,400)
        self.assertEqual(budget.attempts,0)
        self.assertEqual(calls,[])

    def test_gateway_one_provider_attempt_despite_second_call(self):
        calls=[]
        budget=TrialRequestBudget(1,lambda raw: calls.append(raw) or b'{}')
        with trial_gateway(budget,expected_model='chosen-model',max_output_tokens=2048,
                           request_policy=self.policy,token_counter=lambda _:100) as base:
            def request():
                return urllib.request.urlopen(urllib.request.Request(base+'/chat/completions',
                    data=json.dumps(self.payload).encode(),headers={'Content-Type':'application/json'}),timeout=2)
            with request() as result: self.assertEqual(result.status,200)
            with self.assertRaises(urllib.error.HTTPError) as error: request()
            self.assertEqual(error.exception.code,400)
        self.assertEqual(budget.attempts,1)
        self.assertEqual(len(calls),1)

    def test_gateway_refuses_policy_identity_or_unpaired_configuration(self):
        budget=TrialRequestBudget(1,lambda _:b'{}')
        for kwargs in ({'request_policy':self.policy},
                       {'token_counter':lambda _:1},
                       {'request_policy':TextRequestPolicy('other',6000,2048),'token_counter':lambda _:1},
                       {'request_policy':TextRequestPolicy('chosen-model',6000,2047),'token_counter':lambda _:1}):
            with self.assertRaises(ValueError):
                with trial_gateway(budget,expected_model='chosen-model',max_output_tokens=2048,**kwargs):
                    self.fail('invalid policy was allowed')


if __name__=='__main__': unittest.main()
