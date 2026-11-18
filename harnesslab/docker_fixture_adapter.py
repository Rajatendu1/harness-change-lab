"""Concrete model-free Docker fixture mapping. NOT executed or qualified.

No real task/provider accepts a parameter. Image must contain trusted installed
helpers/Aider/Git; no build/pull/install fallback. External execution approval
is required before calling run_fixture, despite fixed responses being free.
"""
import json
import os
from pathlib import Path
import tempfile
import uuid

from .bounded_process import capture
from .candidate_cleanup import CLEANUP_PROGRAM,KEEPER_PROGRAM
from .docker_fixture_child import BASE,NAMES
from .docker_qualification import DockerPolicy,validate_inspect
from .editing_container import editing_create_command
from .fixture_editing_session import FixtureEditingSession
from .image_policy import validate_image,ImagePolicy
from .process_observation import KeeperIdentity
from .request_budget import TrialRequestBudget
from .source_bundle import MAX_ARCHIVE,unpack_sources
from .trial_gateway import trial_gateway


class ResourceProbeFailure(RuntimeError):
    """Only fixed enums and bounded facts can reach a public diagnostic report."""
    PHASES = {'pre_observe','before_snapshot','probe_command','probe_marker',
              'post_observe','keeper_check','after_snapshot','corroborate'}
    CATEGORIES = {'launch_failed','wall_timeout','output_limit','input_not_consumed',
                  'nonzero_exit','io_failed','client_cleanup_unconfirmed',
                  'invariant_failed','unexpected_error'}

    def __init__(self,phase,error,observations):
        from .bounded_process import ControlledProcessError
        if phase not in self.PHASES:
            raise ValueError('Unknown diagnostic phase')
        category = (error.category if isinstance(error,ControlledProcessError)
                    else 'invariant_failed' if isinstance(error,(ValueError,AssertionError,KeyError,TypeError))
                    else 'unexpected_error')
        if category not in self.CATEGORIES: category='unexpected_error'
        safe={}
        for key in ('keeper_running','keeper_oom_killed','keeper_pid_unchanged'):
            if type(observations.get(key)) is bool: safe[key]=observations[key]
        delta=observations.get('memory_oom_kill_delta')
        if type(delta) is int and 0<=delta<=10000: safe['memory_oom_kill_delta']=delta
        self.diagnostic={'phase':phase,'error_category':category,'observations':safe}
        super().__init__('resource_probe_failed')


class DockerFixtureAdapter:
    def __init__(self, *, image_policy, socket_directory, gateway_gid, runner=capture):
        if not isinstance(image_policy,ImagePolicy) or os.getuid()!=1001 or gateway_gid!=os.getgid():
            raise ValueError('Reviewed image and fixed host identity required')
        self.policy=image_policy
        self.directory=socket_directory
        self.gid=gateway_gid
        self.runner=runner
        self.name='harness-preflight-'+uuid.uuid4().hex

    def call(self,args,*,timeout=10,max_bytes=1024*1024,input_data=None):
        return self.runner(args,timeout_s=timeout,max_bytes=max_bytes,input_data=input_data).stdout

    def inspect(self):
        data=json.loads(self.call(['docker','inspect',self.name]))
        if not isinstance(data,list) or len(data)!=1:
            raise ValueError('Expected one container')
        return data[0]

    def create_keeper(self):
        images=json.loads(self.call(['docker','image','inspect',self.policy.reference]))
        if not isinstance(images,list) or len(images)!=1:
            raise ValueError('Expected one reviewed image')
        validate_image(images[0],self.policy)
        self.call(editing_create_command(self.name,self.policy.reference,self.directory,gateway_gid=self.gid))
        info=self.inspect()
        validate_inspect(info,self.directory,1001,self.gid,DockerPolicy(),workspace_uid=65534)
        if (info.get('Image') != self.policy.content_id
                or info['Config'].get('Entrypoint') != ['python3']
                or info['Config'].get('Cmd') != ['-I','-c',KEEPER_PROGRAM]
                or sorted(info['Config'].get('Env') or []) != sorted(self.policy.environment)
                or info['HostConfig'].get('GroupAdd') != [str(self.gid)]):
            raise ValueError('Editing image/program/group configuration mismatch')
        # No remapped/rootless identities supported by this prototype.
        if info['HostConfig'].get('UsernsMode') not in ('',None):
            raise ValueError('UID remapping unsupported')
        self.call(['docker','start',self.name])
        state=self.inspect()['State']
        identity=KeeperIdentity(state['Pid'],1001,65534)
        # Read actual numeric host process UID independently of declared flags.
        top=self.call(['docker','top',self.name,'-eo','uid,pid'])
        from .process_observation import check_keeper_only
        check_keeper_only(top,state,identity)
        self.keeper_identity=identity
        return identity

    def verify_resource_event(self,probe):
        from .docker_probes import ENFORCEMENT_PROBES
        from .cgroup_observation import read_snapshot,corroborate,check_memory_probe_survivor
        if probe not in ('memory','pids','cpu') or not hasattr(self,'keeper_identity'):
            raise ValueError('Expected fixed event probe and known keeper')
        from .process_observation import check_keeper_only
        phase='pre_observe'; facts={}; before=None
        try:
            top,state=self.observe()
            check_keeper_only(top,state,self.keeper_identity)
            phase='before_snapshot'
            before=read_snapshot(self.keeper_identity.host_pid)
            phase='probe_command'
            raw=self.call(['docker','exec','--user',f'65534:{self.gid}',self.name,
                           'python3','-I','-c',ENFORCEMENT_PROBES[probe]],timeout=20,max_bytes=1024)
            phase='probe_marker'
            if raw!=(probe+'-ok\n').encode():
                raise ValueError('Resource probe incomplete')
            phase='post_observe'
            top,state=self.observe()
            facts.update(keeper_running=state.get('Running'),keeper_oom_killed=state.get('OOMKilled'),
                         keeper_pid_unchanged=state.get('Pid')==self.keeper_identity.host_pid)
            # The fixed memory probe intentionally OOM-kills children. Only
            # that stage uses event-corroborated survival semantics. No other
            # resource/candidate/process gate may clear an OOM flag.
            if probe!='memory':
                phase='keeper_check'
                check_keeper_only(top,state,self.keeper_identity)
            phase='after_snapshot'
            after=read_snapshot(self.keeper_identity.host_pid)
            facts['memory_oom_kill_delta']=after['memory_events']['oom_kill']-before['memory_events']['oom_kill']
            phase='corroborate'
            if probe=='memory':
                return check_memory_probe_survivor(top,state,self.keeper_identity,before,after)
            return corroborate(before,after,probe=probe)
        except Exception as error:
            # Diagnostic-only bounded reads. They never resume a failed gate.
            # No raw exception text, process table, PID, path or child stderr.
            try:
                state=self.inspect()['State']
                facts.update(keeper_running=state.get('Running'),keeper_oom_killed=state.get('OOMKilled'),
                             keeper_pid_unchanged=state.get('Pid')==self.keeper_identity.host_pid)
                if before is not None and facts['keeper_running'] is True and facts['keeper_pid_unchanged'] is True:
                    after=read_snapshot(self.keeper_identity.host_pid)
                    facts['memory_oom_kill_delta']=after['memory_events']['oom_kill']-before['memory_events']['oom_kill']
            except Exception:
                pass
            raise ResourceProbeFailure(phase,error,facts) from None

    def verify_denials(self):
        from .docker_denials import denial_source
        dummy=Path('/tmp')/('harness-private-probe-'+uuid.uuid4().hex)
        dummy.mkdir(mode=0o700)
        sentinel=dummy/'sentinel'
        try:
            sentinel.write_bytes(b'fixed-dummy-not-a-secret')
            os.chmod(sentinel,0o600)
            program=denial_source(str(sentinel))
            args=['docker','exec','--user',f'65534:{self.gid}',self.name,
                  'python3','-I','-c',program]
            return self.call(args,timeout=5,max_bytes=1024)
        finally:
            sentinel.unlink(missing_ok=True)
            dummy.rmdir()

    def exec(self,operation,*,input_data=None):
        if operation not in ('import','canned','export','cleanup'):
            raise ValueError('Only fixed operations')
        args=['docker','exec']
        if operation=='import': args+=['-i']
        args+=['--user',f'65534:{self.gid}',self.name,'python3','-I']
        if operation=='cleanup': args+=['-c',CLEANUP_PROGRAM]
        else: args+=['-m','harnesslab.docker_fixture_child',operation]
        return self.call(args,timeout=60 if operation=='canned' else 10,
                         max_bytes=MAX_ARCHIVE if operation=='export' else 1024,
                         input_data=input_data)

    def import_base(self,raw,names):
        if tuple(names)!=NAMES or unpack_sources(raw,expected_names=names)!=BASE:
            raise ValueError('Fixed fixture base only')
        return self.exec('import',input_data=raw)

    def run_canned_agent(self): return self.exec('canned')
    def stop_candidate(self): return self.exec('cleanup')
    def observe(self):
        return self.call(['docker','top',self.name,'-eo','uid,pid']),self.inspect()['State']
    def export_sources(self,names):
        if tuple(names)!=NAMES: raise ValueError('Fixed fixture names only')
        return self.exec('export')
    def remove_and_confirm_absent(self):
        # May fail if create never succeeded. Conservative no success claim in
        # that case; do not turn arbitrary daemon/client errors into absence.
        self.call(['docker','rm','--force',self.name])
        return self.call(['docker','ps','-aq','--filter',f'name=^/{self.name}$']).strip()==b''


def canned_completion(body):
    return json.dumps({'id':'fixture','object':'chat.completion','created':0,'model':'fixture-model',
        'choices':[{'index':0,'finish_reason':'stop','message':{'role':'assistant',
        'content':'example.py\n```python\ndef answer():\n    return 1\n```'}}],
        'usage':{'prompt_tokens':1,'completion_tokens':1,'total_tokens':2}}).encode()


def run_fixture(*,image_policy, scorer=None):
    """Externally approved model-free execution only. Never auto-call from CLI."""
    budget=TrialRequestBudget(1,canned_completion)
    with tempfile.TemporaryDirectory(prefix='fixture-socket-') as directory:
        with trial_gateway(budget,expected_model='fixture-model',max_output_tokens=256,
                           unix_path=str(Path(directory)/'provider.sock'),shared_group=os.getgid()):
            adapter=DockerFixtureAdapter(image_policy=image_policy,socket_directory=directory,gateway_gid=os.getgid())
            result=FixtureEditingSession(adapter).run(base=BASE,editable_names=NAMES)
    candidate=result.pop('candidate',None)  # Never expose candidate/source bytes.
    exact=(candidate=={'example.py':b'def answer():\n    return 1\n'})
    result['fixture_edit_matches']=exact
    result['fixture_attempts']=budget.attempts
    collected=(result['status']=='fixture_candidate_collected' and exact
               and budget.attempts==1 and len(budget.audit)==1)
    if scorer is not None:
        # Only trusted controller scoring callback; no source leaves summary.
        if collected:
            try:
                score=scorer(candidate)
                result['protected_score_passed']=isinstance(score,dict) and score.get('passed') is True
                result['protected_score_boundary']='trusted_process_not_adversarial'
            except Exception:
                result['protected_score_passed']=False
                result['protected_score_boundary']='setup_unverified'
        else:
            result['protected_score_passed']=False
            result['protected_score_boundary']='not_run_collection_failed'
    if result['status']=='fixture_candidate_collected':
        result['status']='fixture_collected_not_scored' if collected else 'fixture_failed'
        if scorer is not None and collected:
            result['status']='fixture_scored_local' if result['protected_score_passed'] else 'fixture_score_failed'
    result['runtime_qualified']=False
    return result
