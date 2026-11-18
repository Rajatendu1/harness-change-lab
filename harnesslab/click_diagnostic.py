"""One no-key model-free Click task diagnostic, not live model evaluation."""
import ast
import hashlib
import json
from .click_task import EDITABLE,MODEL,validate_base
from .click_docker_score import score_click
from .click_pilot import run_with_isolated_counter
from .click_verifier_child import TEST_HASH


def select_protected_test(raw):
    text=raw.decode('utf-8');tree=ast.parse(text)
    nodes=[node for node in tree.body if isinstance(node,ast.FunctionDef)
           and node.name=='test_wrap_text_keeps_words_whole']
    if len(nodes)!=1:raise ValueError('Exact regression function required')
    node=nodes[0];start=min([node.lineno]+[item.lineno for item in node.decorator_list])
    selected=('import pytest\nimport click\n\n'+'\n'.join(text.splitlines()[start-1:node.end_lineno])+'\n').encode()
    if hashlib.sha256(selected).hexdigest()!=TEST_HASH:raise ValueError('Protected test identity mismatch')
    return selected


def small_canned_edit(base):
    text=base[EDITABLE[0]].decode()
    search='        replace_whitespace=False,\n'
    if text.count(search)!=1:raise ValueError('Fixed known edit anchor mismatch')
    replacement=search+'        break_on_hyphens=False,\n        break_long_words=False,\n'
    content=EDITABLE[0]+'\n```python\n<<<<<<< SEARCH\n'+search+'=======\n'+replacement+'>>>>>>> REPLACE\n```'
    return json.dumps({'id':'canned-reference','object':'chat.completion','created':0,'model':MODEL,
        'choices':[{'index':0,'finish_reason':'stop','message':{'role':'assistant','content':content}}]}).encode()


def qualify_click(*,base,known_fixed_source,protected_test,image_policy,verifier_policy,
                  score=score_click,pilot=run_with_isolated_counter):
    validate_base(base)
    if image_policy.content_id==verifier_policy.content_id:raise ValueError('Distinct images required')
    if hashlib.sha256(protected_test).hexdigest()!=TEST_HASH:raise ValueError('Exact protected test required')
    fixed=dict(base);fixed[EDITABLE[0]]=known_fixed_source
    records=[]
    for label,candidate,expected in [('unchanged_base',base,'reference_verifier_fail'),
                                     ('known_upstream_fix',fixed,'reference_verifier_pass')]:
        row=score(candidate,base=base,protected_test=protected_test,image_policy=verifier_policy,reference_mode=True)
        records.append({'stage':label,'score':row})
        if (row.get('outcome')!=expected or row.get('tests')!=3 or row.get('skipped')!=0):
            return {'status':'click_controls_unverified','records':records,'real_provider_calls':0,'real_model_repairs':0}
    response=small_canned_edit(base)
    result=pilot(base=base,image_policy=image_policy,transport=lambda _:response,
        scorer=lambda candidate:score(candidate,base=base,protected_test=protected_test,image_policy=verifier_policy))
    records.append({'stage':'actual_Aider_canned_edit_and_fresh_score','result':result})
    passed=(result.get('status')=='scored' and result.get('outcome')=='source_patch_verifier_pass'
            and result.get('provider_attempts')==1 and result.get('tokenizer_container_cleanup_confirmed') is True)
    return {'status':'click_model_free_task_mapping_passed' if passed else 'click_task_mapping_unverified',
            'records':records,'real_provider_calls':0,'real_model_repairs':0,
            'evidence_class':'public_real_task_known_canned_edit_not_model',
            'adversarial_integrity_verified':False}
