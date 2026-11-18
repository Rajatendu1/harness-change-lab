"""Strict supplied Click runner evidence intake for paired analysis.

Hashes detect inconsistent files, not a lying producer. This validates supplied
records, never authenticates execution, proves approval or starts a process.
The current adapter accepts only the versioned Click result classes below.
"""
import hashlib
import json
import re
from .compare import Outcome, compare
from .paired_controller import paired_report

LIVE_CLASS='one_public_task_live_attempt_trusted_process_not_adversarial'
CANNED_CLASS='public_real_task_known_canned_edit_not_model'
PLAN_FIELDS={'schema','tasks','configurations','configuration_order','trials','fixture_only','policy'}
ROW_FIELDS={'schema','plan_sha256','configuration','task_id','trial','execution_ref','result_sha256','result'}
POLICY_FIELDS={'min_tasks','margin','confidence','resamples','seed'}


def digest(value):
    raw=json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
    return hashlib.sha256(raw).hexdigest()


def strict_json(text):
    def pairs(items):
        out={}
        for name,value in items:
            if name in out:raise ValueError('Duplicate JSON key')
            out[name]=value
        return out
    def invalid(value):raise ValueError('Non-finite JSON number')
    return json.loads(text,object_pairs_hook=pairs,parse_constant=invalid)


def validate_plan(plan):
    if type(plan) is not dict or set(plan)!=PLAN_FIELDS or plan['schema']!='click-paired-intake-plan-v1':
        raise ValueError('Exact versioned intake plan required')
    if type(plan['fixture_only']) is not bool or type(plan['trials']) is not int or not 1<=plan['trials']<=20:
        raise ValueError('Explicit evidence class and bounded trial count required')
    if type(plan['tasks']) is not dict or not 1<=len(plan['tasks'])<=1000:
        raise ValueError('Bounded task map required')
    if type(plan['configurations']) is not dict or len(plan['configurations'])!=2:
        raise ValueError('Exactly two configurations required')
    if type(plan['configuration_order']) is not list or len(plan['configuration_order'])!=2:
        raise ValueError('Explicit baseline and candidate order required')
    if set(plan['configuration_order'])!=set(plan['configurations']):
        raise ValueError('Configuration order mismatch')
    for name in list(plan['tasks'])+list(plan['configurations']):
        if type(name) is not str or not 1<=len(name)<=128 or not all(c.isascii() and (c.isalnum() or c in '-_.') for c in name):
            raise ValueError('Safe bounded identifiers required')
    # The Click adapter currently validates one fixed 3-case task only.
    from .click_task import TASK_ID,BASE_COMMIT
    from .click_verifier_child import TEST_HASH
    if plan['tasks']!={TASK_ID:{'revision':BASE_COMMIT,'verifier_sha256':TEST_HASH}}:
        raise ValueError('Current intake supports exact pinned Click task only')
    for value in plan['configurations'].values():
        if type(value) is not str or len(value)!=64 or any(c not in '0123456789abcdef' for c in value):
            raise ValueError('Configuration SHA-256 required')
    if len(set(plan['configurations'].values()))!=2:
        raise ValueError('Distinct configuration identities required')
    policy=plan['policy']
    if type(policy) is not dict or set(policy)!=POLICY_FIELDS:
        raise ValueError('Exact comparison policy required')
    if any(type(policy[k]) not in (int,float) for k in ('margin','confidence')):
        raise ValueError('Numeric policy cannot be booleans or strings')
    # Validate policy even if every pair will be excluded.
    dummy=[Outcome('policy-check',0,False,'r1','0'*64)]
    compare(dummy,dummy,**policy)
    return digest(plan)


def classify_click(result):
    if type(result) is not dict:raise ValueError('Runner result must be an object')
    kind=result.get('evidence_class')
    if kind==CANNED_CLASS:
        return 'invalid_input','canned_response_not_live_model'
    if result.get('reference_mode') is True or result.get('outcome') in ('reference_verifier_pass','reference_verifier_fail'):
        return 'invalid_input','reference_control_not_repair'
    if kind!=LIVE_CLASS:
        return 'invalid_input','unsupported_or_missing_runner_evidence_class'
    controls=result.get('reference_controls')
    if type(controls) is not list or len(controls)!=2:
        return 'invalid_input','reference_controls_unverified'
    for row,label,outcome,passed,failures in zip(controls,
            ('unchanged_base','known_upstream_fix'),('reference_verifier_fail','reference_verifier_pass'),
            (False,True),(3,0)):
        if type(row) is not dict or row.get('stage')!=label or type(row.get('score')) is not dict:
            return 'invalid_input','reference_controls_unverified'
        score=row['score']
        if (score.get('outcome')!=outcome or score.get('passed') is not passed
                or score.get('reference_mode') is not True or type(score.get('tests')) is not int
                or score['tests']!=3 or type(score.get('failures')) is not int or score['failures']!=failures
                or type(score.get('skipped')) is not int or score['skipped']!=0):
            return 'invalid_input','reference_controls_unverified'
    # Never reinterpret setup/transport/cleanup problems as model test failures.
    if result.get('image_cleanup_confirmed') is not True or result.get('tokenizer_container_cleanup_confirmed') is not True:
        return 'invalid_input','runtime_cleanup_unconfirmed'
    audit=result.get('provider_audit')
    if (type(result.get('provider_attempts')) is not int or result['provider_attempts']!=1
            or type(audit) is not list or len(audit)!=1 or type(audit[0]) is not dict
            or type(audit[0].get('number')) is not int or audit[0]['number']!=1):
        return 'invalid_input','request_audit_unverified'
    if audit[0].get('outcome')=='failed':
        return 'transport_failure','provider_transport_failed_cause_not_inferred'
    if audit[0].get('outcome')!='returned' or result.get('provider_outcomes')!=['returned']:
        return 'invalid_input','request_audit_unverified'
    if (result.get('status')!='scored' or result.get('stage')!='complete'
            or type(result.get('public_input_files')) is not int or result['public_input_files']!=19
            or result.get('score_status')!='verified_focused_collection'
            or type(result.get('focused_tests')) is not int or result['focused_tests']!=3
            or result.get('adversarial_integrity_verified') is not False):
        return 'invalid_input','collection_or_scoring_unverified'
    outcome=result.get('outcome')
    if outcome not in ('source_patch_verifier_pass','verifier_fail'):
        return 'invalid_input','unsupported_scored_outcome'
    expected=int(outcome=='source_patch_verifier_pass')
    if type(result.get('real_model_repairs')) is not int or result['real_model_repairs']!=expected:
        return 'invalid_input','repair_count_contradicts_score'
    return outcome,'supplied_live_trusted_process_score_not_authenticated'


def intake_report(plan,envelopes):
    plan_hash=validate_plan(plan)
    if type(envelopes) is not list or len(envelopes)!=2*len(plan['tasks'])*plan['trials']:
        raise ValueError('Complete planned evidence required, no dropped trials')
    rows=[];intake=[];seen=set();executions=set()
    for envelope in envelopes:
        if type(envelope) is not dict or set(envelope)!=ROW_FIELDS or envelope['schema']!='click-runner-evidence-v1':
            raise ValueError('Exact versioned result envelope required')
        if envelope['plan_sha256']!=plan_hash or envelope['result_sha256']!=digest(envelope['result']):
            raise ValueError('Evidence or plan digest mismatch')
        name,task,trial=(envelope[k] for k in ('configuration','task_id','trial'))
        if (type(name) is not str or name not in plan['configurations'] or type(task) is not str
                or task not in plan['tasks'] or type(trial) is not int or not 0<=trial<plan['trials']):
            raise ValueError('Evidence outside declared plan')
        key=(name,task,trial)
        if key in seen:raise ValueError('Duplicate configuration/task/trial')
        seen.add(key)
        execution=envelope['execution_ref']
        if (type(execution) is not str or len(execution)>250 or not re.fullmatch(
                r'https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/actions/runs/[0-9]+/job/[0-9]+',execution)):
            raise ValueError('Observed GitHub job URL required as supplied execution reference')
        if execution in executions:raise ValueError('An execution reference cannot fill multiple planned slots')
        executions.add(execution)
        outcome,reason=classify_click(envelope['result'])
        identity=plan['tasks'][task]
        rows.append(dict(configuration=name,configuration_sha256=plan['configurations'][name],task_id=task,
            trial=trial,task_revision=identity['revision'],verifier_sha256=identity['verifier_sha256'],
            fixture_only=plan['fixture_only'],outcome=outcome))
        intake.append(dict(configuration=name,task_id=task,trial=trial,execution_ref=execution,result_sha256=envelope['result_sha256'],
            outcome=outcome,reason=reason))
    report=paired_report(rows,tasks=plan['tasks'],configurations=plan['configurations'],
        configuration_order=plan['configuration_order'],trials=plan['trials'],
        fixture_only=plan['fixture_only'],**plan['policy'])
    report.update(schema='click-paired-evidence-report-v1',plan_sha256=plan_hash,intake=intake,
        evidence_authentication='none: supplied producer claims; hashes are consistency checks only',
        execution_authority='none',provider_calls_by_intake=0,
        integrity_scope='trusted_process_not_adversarial',
        task_scope='one_pinned_Click_task_only_not_benchmark_coverage')
    return report
