"""Combined fixed qualification owner, prepared not executed.

No real provider/task arguments. Every stage uses a new bounded container;
failure stops later stages. Approval for build/run is external to this code.
"""
import json
import os
import tempfile

from .bounded_process import ControlledProcessError
from .docker_fixture_adapter import DockerFixtureAdapter,ResourceProbeFailure,run_fixture
from .docker_fixture_score import score_controls,score_in_fresh_container
from .docker_probes import ENFORCEMENT_PROBES

VERSION_PROGRAM = r'''
import json,platform,subprocess,importlib.metadata as m
from harnesslab.docker_fixture_child import guard
guard()
assert platform.python_version().startswith('3.10.')
assert m.version('aider-chat')=='0.86.2'
git=subprocess.run(['git','--version'],capture_output=True,text=True,check=True,timeout=3).stdout.strip()
assert git.startswith('git version ')
print(json.dumps({'python':platform.python_version(),'aider':m.version('aider-chat'),'git':git},sort_keys=True))
'''
TIMEOUT_PROGRAM='from harnesslab.docker_fixture_child import guard; guard(); import time; time.sleep(30)'


def isolated_stage(name,*,image_policy,adapter_factory=DockerFixtureAdapter):
    record={'stage':name,'passed':False}
    with tempfile.TemporaryDirectory(prefix='qualify-empty-') as directory:
        adapter=adapter_factory(image_policy=image_policy,socket_directory=directory,gateway_gid=os.getgid())
        try:
            adapter.create_keeper()
            if name in ('memory','pids','cpu'):
                event=adapter.verify_resource_event(name)
                record.update(external_event_delta=event['external_event_delta'],passed=True)
            else:
                program=VERSION_PROGRAM if name=='identity' else TIMEOUT_PROGRAM if name=='timeout' else ENFORCEMENT_PROBES['disk'] if name=='disk' else None
                if program is None:raise ValueError('Unknown fixed stage')
                args=['docker','exec','--user',f'65534:{adapter.gid}',adapter.name,'python3','-I','-c',program]
                try:
                    raw=adapter.call(args,timeout=1 if name=='timeout' else 10,max_bytes=4096)
                except ControlledProcessError as error:
                    if name!='timeout' or error.category!='wall_timeout':raise
                    record.update(passed=True,timeout_observed=True)
                else:
                    if name=='timeout':raise ValueError('Timeout did not fire')
                    if name=='disk':
                        if raw!=b'disk-ok\n':raise ValueError('Disk probe incomplete')
                    else:
                        data=json.loads(raw)
                        if set(data)!={'python','aider','git'} or data['aider']!='0.86.2':raise ValueError('Identity invalid')
                        record['runtime']=data
                    record['passed']=True
        except ResourceProbeFailure as error:
            record={'stage':name,'passed':False,'reason':'stage_unverified',
                    'diagnostic':error.diagnostic}
        except Exception:
            record={'stage':name,'passed':False,'reason':'stage_unverified'}
        finally:
            try:removed=adapter.remove_and_confirm_absent() is True
            except Exception:removed=False
    if not removed:return {'stage':name,'passed':False,'reason':'cleanup_unconfirmed'}
    record['cleanup']='absence_confirmed'
    return record


def qualify_fixed(*,image_policy,verifier_policy,stage_runner=isolated_stage,controls=score_controls,fixture=run_fixture):
    if image_policy.content_id==verifier_policy.content_id:
        raise ValueError('Agent and protected verifier images must be distinct')
    records=[]
    for stage in ('identity','pids','memory','cpu','disk','timeout'):
        record=stage_runner(stage,image_policy=image_policy)
        records.append(record)
        if record.get('passed') is not True:
            return {'status':'qualification_failed','records':records,'real_provider_calls':0,'real_model_repairs':0}
    control=controls(image_policy=verifier_policy)
    records.append({'stage':'protected_controls','result':control})
    if control.get('status')!='fixed_controls_passed':
        return {'status':'qualification_failed','records':records,'real_provider_calls':0,'real_model_repairs':0}
    result=fixture(image_policy=image_policy,scorer=lambda candidate:score_in_fresh_container(candidate,image_policy=verifier_policy))
    records.append({'stage':'canned_edit_and_protected_score','result':result})
    passed=(result.get('status')=='fixture_scored_local' and result.get('protected_score_passed') is True)
    return {'status':'fixed_adapter_scope_passed' if passed else 'qualification_failed',
            'records':records,'real_provider_calls':0,'real_model_repairs':0,
            'adversarial_integrity_verified':False,'real_task_authorized':False}
