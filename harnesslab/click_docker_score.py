"""Prepared fixed Click fresh verifier mapping. No provider or runtime claim."""
import hashlib
import json
import os
import tempfile

from .click_task import BASE_NAMES,EDITABLE,validate_base
from .click_verifier_child import TEST_NAME,TEST_HASH,validate_score_input
from .docker_fixture_adapter import DockerFixtureAdapter
from .process_observation import check_keeper_only
from .source_bundle import pack_sources


def validate_score_result(raw):
    if not isinstance(raw,bytes) or len(raw)>4096:raise ValueError('Bounded score required')
    row=json.loads(raw)
    if (not isinstance(row,dict) or set(row)!={'status','passed','tests','failures','skipped','adversarial_integrity_verified'}
            or row['status']!='click_verifier_result' or type(row['passed']) is not bool
            or type(row['tests']) is not int or row['tests']!=3
            or type(row['failures']) is not int or row['failures'] not in (0,1,2,3)
            or type(row['skipped']) is not int or row['skipped']!=0
            or row['passed']!=(row['failures']==0)
            or row['adversarial_integrity_verified'] is not False):
        raise ValueError('Exact score/report mismatch')
    return row


def score_click(candidate,*,base,protected_test,image_policy,adapter_factory=DockerFixtureAdapter,reference_mode=False):
    # Validate and build transfer before any container creation.
    validate_base(base)
    if type(reference_mode) is not bool:raise ValueError('Explicit reference mode required')
    if not isinstance(candidate,dict) or set(candidate)!=set(BASE_NAMES):
        raise ValueError('Exact candidate source files required')
    changed=tuple(n for n in BASE_NAMES if base[n]!=candidate[n])
    if any(n not in EDITABLE for n in changed):
        return {'status':'invalid_patch','passed':False,'runtime_qualified':False}
    if not changed and not reference_mode:
        return {'status':'no_source_change','passed':False,'runtime_qualified':False}
    if not isinstance(protected_test,bytes) or hashlib.sha256(protected_test).hexdigest()!=TEST_HASH:
        raise ValueError('Controller protected test required')
    inputs=dict(candidate);inputs[TEST_NAME]=protected_test
    raw=pack_sources(inputs);validate_score_input(raw)
    result=None
    with tempfile.TemporaryDirectory(prefix='click-score-empty-') as directory:
        adapter=adapter_factory(image_policy=image_policy,socket_directory=directory,gateway_gid=os.getgid())
        try:
            identity=adapter.create_keeper()
            if adapter.verify_denials()!=b'fixed-denials-ok\n':raise ValueError('Denials unverified')
            check_keeper_only(*adapter.observe(),identity)
            # This new container never executes agent or mounts a gateway socket.
            args=['docker','exec','-i','--user',f'65534:{adapter.gid}',adapter.name,
                  '/opt/verifier/bin/python','-I','-m','harnesslab.click_verifier_child']
            row=validate_score_result(adapter.call(args,timeout=30,max_bytes=4096,input_data=raw))
            check_keeper_only(*adapter.observe(),identity)
            result=dict(row)
            result['outcome']=('reference_verifier_pass' if row['passed'] else 'reference_verifier_fail') if reference_mode else ('source_patch_verifier_pass' if row['passed'] else 'verifier_fail')
        except Exception:
            result={'status':'verifier_setup_or_execution_error','passed':False}
        finally:
            try:removed=adapter.remove_and_confirm_absent() is True
            except Exception:removed=False
    if not removed:result={'status':'verifier_cleanup_unconfirmed','passed':False}
    result.update(runtime_qualified=False,adversarial_integrity_verified=False,
                  evidence_class='prepared_fresh_container_trusted_process_score',reference_mode=reference_mode)
    return result
