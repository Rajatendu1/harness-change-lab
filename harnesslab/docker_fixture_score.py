"""Portable fixed Docker scorer: fresh container, no agent/provider execution.

Prepared but unexecuted. Uses same reviewed helper image with separate verifier
interpreter, never host bwrap paths. Still trusted-process pytest, not adversarial.
"""
import json
import os
from pathlib import Path
import tempfile

from .docker_fixture_adapter import DockerFixtureAdapter
from .docker_fixture_child import BASE,NAMES
from .process_observation import check_keeper_only
from .source_bundle import pack_sources

ALLOWED=(BASE,{'example.py':b'def answer():\n    return 1\n'},
         {'example.py':b'def answer():\n    return 2\n'})


def validate_score(raw):
    if not isinstance(raw,bytes) or len(raw)>4096:
        raise ValueError('Invalid bounded verifier result')
    value=json.loads(raw)
    if (not isinstance(value,dict) or set(value)!={'status','passed','tests','failures','skipped','adversarial_integrity_verified'}
            or value['status']!='fixed_verifier_result' or type(value['passed']) is not bool
            or type(value['tests']) is not int or value['tests']!=1
            or type(value['failures']) is not int or value['failures'] not in (0,1)
            or type(value['skipped']) is not int or value['skipped']!=0
            or value['passed']!=(value['failures']==0)
            or value['adversarial_integrity_verified'] is not False):
        raise ValueError('Verifier collection/result mismatch')
    return value


def score_in_fresh_container(candidate, *, image_policy, adapter_factory=DockerFixtureAdapter):
    """Only three fixed controls, no generic candidate execution surface.

    Must be invoked under separate model-free runtime approval. No gateway mount
    carries a socket or token. Cleanup uncertainty always discards score.
    """
    if candidate not in ALLOWED:
        return {'status':'invalid_fixed_input','passed':False,'runtime_qualified':False}
    result=None
    with tempfile.TemporaryDirectory(prefix='score-empty-mount-') as directory:
        adapter=adapter_factory(image_policy=image_policy,socket_directory=directory,gateway_gid=os.getgid())
        try:
            identity=adapter.create_keeper()
            marker=adapter.exec('import',input_data=pack_sources(candidate))
            if marker!=b'source-import-ok\n':raise ValueError('Import failed')
            if adapter.stop_candidate()!=b'candidate-cleanup-ok\n':raise ValueError('Import process cleanup failed')
            top,state=adapter.observe();check_keeper_only(top,state,identity)
            args=['docker','exec','--user',f'65534:{adapter.gid}',adapter.name,
                  '/opt/verifier/bin/python','-I','-m','harnesslab.docker_verifier_child']
            raw=adapter.call(args,timeout=15,max_bytes=4096)
            result=validate_score(raw)
        except Exception:
            result={'status':'verifier_setup_or_execution_error','passed':False}
        finally:
            try:removed=adapter.remove_and_confirm_absent() is True
            except Exception:removed=False
    if not removed:
        result={'status':'verifier_cleanup_unconfirmed','passed':False}
    result.update(runtime_qualified=False,real_model_repairs=0,
                  evidence='prepared_portable_trusted_process_verifier')
    return result


def score_controls(*,image_policy,scorer=score_in_fresh_container):
    records=[]
    for candidate,expected in ((BASE,False),(ALLOWED[2],False),(ALLOWED[1],True)):
        record=scorer(candidate,image_policy=image_policy)
        records.append(record)
        if record.get('status')!='fixed_verifier_result' or record.get('passed') is not expected:
            return {'status':'controls_failed','records':records,'runtime_qualified':False}
    return {'status':'fixed_controls_passed','records':records,'runtime_qualified':False,
            'adversarial_integrity_verified':False}
