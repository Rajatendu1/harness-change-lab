"""Prepared controller join for one Click pilot, no live-provider CLI.

Caller must establish owner authority, free account/model/quota preflight and
reviewed image/input identities before constructing any external transport.
This function does not grant those effects. Do not call during import/tests.
"""
from dataclasses import asdict
import json
import os
from pathlib import Path
import tempfile

from .click_token_counter import click_token_counter
from .click_task import MODEL,validate_base
from .click_docker_score import validate_score_result
from .click_docker_adapter import ClickDockerAdapter
from .click_editing_session import ClickEditingSession
from .request_admission import TextRequestPolicy
from .request_budget import TrialRequestBudget
from .trial_gateway import trial_gateway


def prepare_policy():
    return TextRequestPolicy(MODEL,5750,2048)


def run_one_click(*,base,image_policy,transport,token_counter,scorer,
                  adapter_factory=ClickDockerAdapter):
    """One lifetime request budget. No retry/resume/callback transport fallback.

    transport is a trusted fixed controller function, never candidate input.
    scorer must be a separate fresh-container mapping after confirmed removal.
    No raw request, response, candidate, endpoint, credential or exception text
    leaves the summary. Returned usage is metadata, not inferred model success.
    """
    validate_base(base)
    if not all(callable(value) for value in (transport,token_counter,scorer)):
        raise ValueError('Explicit trusted transport, tokenizer and scorer required')
    budget=TrialRequestBudget(1,transport)
    policy=prepare_policy()
    with tempfile.TemporaryDirectory(prefix='click-pilot-socket-') as directory:
        with trial_gateway(budget,expected_model=MODEL,max_output_tokens=policy.max_output_tokens,
                           unix_path=str(Path(directory)/'provider.sock'),shared_group=os.getgid(),
                           request_policy=policy,token_counter=token_counter):
            adapter=adapter_factory(image_policy=image_policy,socket_directory=directory,gateway_gid=os.getgid())
            result=ClickEditingSession(adapter,budget).run(base)
    candidate=result.pop('candidate',None)
    result['provider_audit']=[asdict(row) for row in budget.audit]
    if result['status']=='collected' and (budget.attempts!=1 or len(budget.audit)!=1
            or budget.audit[0].outcome!='returned'):
        result.update(status='excluded',stage='request_audit')
        candidate=None
    if result['status']!='collected':
        result['score_status']='not_run_collection_excluded'
        return result
    try:
        score=scorer(candidate)
        valid=isinstance(score,dict) and score.get('outcome') in ('source_patch_verifier_pass','verifier_fail')
        # Reference records never count as pilot repairs.
        valid=valid and score.get('reference_mode') is False and score.get('status')=='click_verifier_result'
        valid=valid and score.get('tests')==3 and score.get('skipped')==0
        valid=valid and score.get('adversarial_integrity_verified') is False
        if valid:
            fields=('status','passed','tests','failures','skipped','adversarial_integrity_verified')
            validate_score_result(json.dumps({name:score[name] for name in fields}).encode())
            valid=(score['outcome']=='source_patch_verifier_pass') is score['passed']
        result['score_status']='verified_focused_collection' if valid else 'unverified_or_excluded'
        if valid:
            result['outcome']=score['outcome']
            result['status']='scored'
            result['focused_tests']=3
        else:
            result['status']='excluded'
    except Exception:
        result.update(status='excluded',score_status='verifier_unverified')
    result['evidence_class']='prepared_single_task_pilot_trusted_process_not_adversarial'
    return result


def run_with_isolated_counter(*,base,image_policy,transport,scorer,
                              adapter_factory=ClickDockerAdapter,
                              counter_factory=click_token_counter):
    """Counter removal is part of terminal outcome, never an afterthought.

    The caller owns outer image and credential cleanup even on any exception.
    Those independent side effects are not asserted complete by this function.
    """
    state={}
    try:
        with counter_factory(image_policy=image_policy) as (counter,state):
            result=run_one_click(base=base,image_policy=image_policy,transport=transport,
                token_counter=counter,scorer=scorer,adapter_factory=adapter_factory)
    except Exception:
        result={'status':'excluded','stage':'counter_setup_or_execution',
                'runtime_qualified':False,'adversarial_integrity_verified':False}
    if state.get('cleanup_confirmed') is not True:
        result.pop('outcome',None)
        result.update(status='excluded',stage='counter_cleanup_unconfirmed')
    result['tokenizer_container_cleanup_confirmed']=state.get('cleanup_confirmed') is True
    return result
