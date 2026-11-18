import contextlib
import copy
import io
import json
from pathlib import Path
import tempfile
import unittest
from harnesslab.cli import main
from harnesslab.click_task import TASK_ID,BASE_COMMIT
from harnesslab.click_verifier_child import TEST_HASH
from harnesslab.evidence_intake import (LIVE_CLASS,CANNED_CLASS,validate_plan,digest,
    strict_json,intake_report,classify_click)


def plan_fixture():
    return {'schema':'click-paired-intake-plan-v1','tasks':{TASK_ID:{'revision':BASE_COMMIT,
        'verifier_sha256':TEST_HASH}},'configurations':{'baseline':'a'*64,'candidate':'b'*64},
        'configuration_order':['baseline','candidate'],'trials':1,'fixture_only':True,
        'policy':{'min_tasks':20,'margin':0.05,'confidence':0.95,'resamples':100,'seed':0}}


def result_fixture(outcome='source_patch_verifier_pass'):
    controls=[]
    for label,passed in [('unchanged_base',False),('known_upstream_fix',True)]:
        controls.append({'stage':label,'score':{'outcome':'reference_verifier_pass' if passed else 'reference_verifier_fail',
            'passed':passed,'reference_mode':True,'tests':3,'failures':0 if passed else 3,'skipped':0}})
    return {'evidence_class':LIVE_CLASS,'reference_controls':controls,'image_cleanup_confirmed':True,
        'tokenizer_container_cleanup_confirmed':True,'provider_attempts':1,
        'provider_audit':[{'number':1,'outcome':'returned','usage_status':'unknown'}],
        'provider_outcomes':['returned'],'status':'scored','stage':'complete','public_input_files':19,
        'score_status':'verified_focused_collection','focused_tests':3,
        'adversarial_integrity_verified':False,'outcome':outcome,
        'real_model_repairs':int(outcome=='source_patch_verifier_pass')}


def rows_fixture(plan):
    return [{'schema':'click-runner-evidence-v1','plan_sha256':digest(plan),'configuration':name,
        'task_id':TASK_ID,'trial':0,'execution_ref':f'https://github.com/fixture/project/actions/runs/{i}/job/{i}',
        'result':result_fixture(outcome),'result_sha256':digest(result_fixture(outcome))}
        for i,(name,outcome) in enumerate([('baseline','verifier_fail'),('candidate','source_patch_verifier_pass')],1)]


class EvidenceIntakeTests(unittest.TestCase):
    def setUp(self):self.plan=plan_fixture();self.rows=rows_fixture(self.plan)
    def report(self):return intake_report(self.plan,self.rows)
    def mutate_result(self,key,value):
        self.rows[0]['result'][key]=value
        self.rows[0]['result_sha256']=digest(self.rows[0]['result'])
    def reason(self):return self.report()['intake'][0]['reason']

    def test_eligible_supplied_scores_keep_fixture_and_one_task_abstention(self):
        report=self.report()
        self.assertEqual(report['included_pairs'],1);self.assertEqual(report['comparison']['delta'],1)
        self.assertEqual(report['verdict'],'insufficient_evidence')
        self.assertIn('supplied',report['evidence_authentication'])
        self.assertEqual(report['execution_authority'],'none')
        self.assertEqual(report['provider_calls_by_intake'],0)

    def test_one_task_cannot_clear_gate_even_when_claimed_live(self):
        self.plan['fixture_only']=False;self.rows=rows_fixture(self.plan)
        self.assertEqual(self.report()['verdict'],'insufficient_evidence')

    def test_canned_real_task_never_counts_as_model_repair(self):
        self.mutate_result('evidence_class',CANNED_CLASS)
        self.assertEqual(self.reason(),'canned_response_not_live_model')
        self.assertEqual(self.report()['included_pairs'],0)
        self.assertIsNone(self.report()['comparison'])

    def test_reference_controls_never_count_as_repairs(self):
        for outcome in ('reference_verifier_pass','reference_verifier_fail'):
            self.mutate_result('outcome',outcome)
            self.assertEqual(self.reason(),'reference_control_not_repair')

    def test_missing_or_unknown_evidence_class_not_upgraded(self):
        for value in (None,'fixture','live','private text'):
            self.mutate_result('evidence_class',value)
            self.assertEqual(self.reason(),'unsupported_or_missing_runner_evidence_class')
            self.assertNotIn('private text',json.dumps(self.report()))

    def test_expected_reference_controls_required_before_scoring(self):
        controls=result_fixture()['reference_controls'];controls[0]['score']['passed']=True
        self.mutate_result('reference_controls',controls)
        self.assertEqual(self.reason(),'reference_controls_unverified')
        self.mutate_result('reference_controls',[])
        self.assertEqual(self.reason(),'reference_controls_unverified')

    def test_cleanup_missing_false_and_truthy_values_excluded(self):
        for field in ('image_cleanup_confirmed','tokenizer_container_cleanup_confirmed'):
            for value in (False,None,1,'true'):
                row=result_fixture();row[field]=value
                self.assertEqual(classify_click(row)[1],'runtime_cleanup_unconfirmed')

    def test_provider_failure_is_excluded_not_false_score(self):
        row=result_fixture();row['provider_audit'][0]['outcome']='failed'
        row['provider_outcomes']=['failed'];row['status']='excluded';row['stage']='request_audit'
        row['real_model_repairs']=0;row.pop('outcome')
        self.mutate_result('provider_audit',row['provider_audit'])
        report=self.report();self.assertEqual(report['included_pairs'],0)
        self.assertEqual(report['intake'][0]['outcome'],'transport_failure')
        self.assertEqual(report['verdict'],'insufficient_evidence')

    def test_request_audit_must_be_exact_one_integer_attempt(self):
        for key,value in [('provider_attempts',True),('provider_attempts',2),('provider_attempts',0),
                ('provider_audit',[]),('provider_audit',[{'number':True,'outcome':'returned'}]),
                ('provider_audit',[{'number':2,'outcome':'returned'}]),('provider_outcomes',['returned','returned'])]:
            row=result_fixture();row[key]=value
            self.assertEqual(classify_click(row)[1],'request_audit_unverified')

    def test_unsupported_score_and_contradictory_repair_count_excluded(self):
        for value in (True,0,2,'1'):
            row=result_fixture();row['real_model_repairs']=value
            self.assertEqual(classify_click(row)[1],'repair_count_contradicts_score')
        row=result_fixture();row['outcome']='success'
        self.assertEqual(classify_click(row)[1],'unsupported_scored_outcome')

    def test_score_class_drift_excluded(self):
        for key,value in [('status','collected'),('stage','request_audit'),('focused_tests',True),
                ('focused_tests',4),('public_input_files',20),('score_status','pass'),('adversarial_integrity_verified',True)]:
            row=result_fixture();row[key]=value
            self.assertEqual(classify_click(row)[1],'collection_or_scoring_unverified')

    def test_missing_duplicate_and_out_of_scope_slots_rejected(self):
        variants=[self.rows[:1],self.rows+[self.rows[0]],[self.rows[0],self.rows[0]]]
        for rows in variants:
            with self.assertRaises(ValueError):intake_report(self.plan,rows)
        for key,value in [('trial',True),('trial',1),('task_id','other'),('configuration','other')]:
            rows=copy.deepcopy(self.rows);rows[0][key]=value
            with self.assertRaises(ValueError):intake_report(self.plan,rows)

    def test_execution_reference_reuse_and_non_github_references_rejected(self):
        self.rows[1]['execution_ref']=self.rows[0]['execution_ref']
        with self.assertRaises(ValueError):self.report()
        for value in ('https://evil.invalid/private','javascript:private','https://github.com/x/y/actions/runs/1/job/1?private=1'):
            self.rows[1]['execution_ref']=value
            with self.assertRaises(ValueError):self.report()

    def test_result_and_plan_hash_drift_rejected(self):
        for field in ('plan_sha256','result_sha256'):
            rows=copy.deepcopy(self.rows);rows[0][field]='0'*64
            with self.assertRaises(ValueError):intake_report(self.plan,rows)
        self.rows[0]['result']['status']='excluded'
        with self.assertRaises(ValueError):self.report()

    def test_unknown_envelope_fields_cannot_smuggle_private_output(self):
        self.rows[0]['private']='private-body'
        with self.assertRaises(ValueError):self.report()

    def test_numeric_policy_validated_even_when_all_evidence_excluded(self):
        for field,value in [('min_tasks',1),('margin',float('nan')),('resamples',10),('seed',True)]:
            plan=plan_fixture();plan['policy'][field]=value
            with self.assertRaises((ValueError,TypeError)):validate_plan(plan)

    def test_plan_task_revision_verifier_and_configuration_identity_are_fixed(self):
        for value in ('different','0'*40):
            plan=plan_fixture();plan['tasks'][TASK_ID]['revision']=value
            with self.assertRaises(ValueError):validate_plan(plan)
        plan=plan_fixture();plan['configurations']['candidate']=plan['configurations']['baseline']
        with self.assertRaises(ValueError):validate_plan(plan)
        plan=plan_fixture();plan['tasks'][TASK_ID]['verifier_sha256']='0'*64
        with self.assertRaises(ValueError):validate_plan(plan)

    def test_strict_json_rejects_duplicate_keys_and_nonfinite_numbers(self):
        for text in ('{"status":1,"status":2}','{"x":NaN}','{"x":Infinity}','{"x":-Infinity}'):
            with self.assertRaises(ValueError):strict_json(text)

    def test_cli_returns_abstention_and_rejects_malformed_without_echo(self):
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)/'plan.json';r=Path(directory)/'evidence.json'
            p.write_text(json.dumps(self.plan));r.write_text(json.dumps(self.rows));out=io.StringIO()
            with contextlib.redirect_stdout(out):code=main(['compare-click-evidence',str(p),str(r)])
            self.assertEqual(code,3);self.assertEqual(json.loads(out.getvalue())['verdict'],'insufficient_evidence')
            r.write_text('{"private":"sensitive"}');err=io.StringIO()
            with contextlib.redirect_stderr(err),self.assertRaises(SystemExit) as caught:
                main(['compare-click-evidence',str(p),str(r)])
            self.assertEqual(caught.exception.code,2);self.assertNotIn('sensitive',err.getvalue())
            self.assertNotIn(str(r),err.getvalue())


if __name__=='__main__':unittest.main()
