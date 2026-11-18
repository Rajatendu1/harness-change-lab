"""Model-free Docker preflight candidate. Never pulls or builds an image.

Only fixed Python runs, no agent/model/credential entrypoint. Runtime execution
requires separate authority. A successful baseline is NOT full qualification.
"""
from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
from types import SimpleNamespace
import uuid

from .bounded_process import capture, ControlledProcessError

from .request_budget import TrialRequestBudget
from .trial_gateway import trial_gateway
from .docker_probes import ENFORCEMENT_PROBES
from .image_policy import ImagePolicy, validate_image


@dataclass(frozen=True)
class DockerPolicy:
    memory_bytes: int = 2 * 1024**3
    nano_cpus: int = 10**9
    pids: int = 64
    workspace_bytes: int = 64 * 1024**2
    temporary_bytes: int = 16 * 1024**2
    wall_seconds: int = 20

    def __post_init__(self):
        # Not a generic arbitrary-flags interface. Changes require source review.
        if tuple(self.__dict__.values()) != (2147483648, 1000000000, 64, 67108864, 16777216, 20):
            raise ValueError('Only the reviewed baseline policy is supported')


PROBE = r'''
import errno, http.client, json, os, socket
from pathlib import Path
assert os.getuid() != 0
assert not os.path.exists('/var/run/docker.sock')
assert 'HARNESS_PREFLIGHT_SENTINEL' not in os.environ
status=Path('/proc/self/status').read_text()
assert 'NoNewPrivs:\t1' in status
assert int(next(x.split()[1] for x in status.splitlines() if x.startswith('CapEff:')),16)==0
assert next(x.split()[1] for x in status.splitlines() if x.startswith('Seccomp:'))=='2'
root=Path('/sys/fs/cgroup')
assert (root/'memory.max').read_text().strip()=='2147483648'
assert (root/'memory.swap.max').read_text().strip()=='0'
assert (root/'pids.max').read_text().strip()=='64'
quota, period=map(int,(root/'cpu.max').read_text().split())
assert quota > 0 and quota==period
for path in ('/root-write-probe','/gateway/new-file'):
    try:
        Path(path).write_text('fixed probe')
    except OSError as e:
        assert e.errno in (errno.EROFS,errno.EACCES)
    else:
        raise AssertionError('unexpected write')
for path,limit in (('/work',67108864),('/tmp',16777216)):
    info=os.statvfs(path)
    assert info.f_blocks*info.f_frsize<=limit
    Path(path+'/probe').write_text('fixed probe')
try:
    os.unlink('/gateway/provider.sock')
except OSError as e:
    assert e.errno in (errno.EROFS,errno.EACCES)
else:
    raise AssertionError('socket unlink allowed')
s=socket.socket(); s.settimeout(.2)
try:
    s.connect(('192.0.2.1',80))
except OSError:
    pass
else:
    raise AssertionError('unexpected external network')
finally:
    s.close()
class Unix(http.client.HTTPConnection):
    def connect(self):
        self.sock=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
        self.sock.settimeout(3)
        self.sock.connect('/gateway/provider.sock')
for expected in (200,400):
    c=Unix('localhost')
    try:
        c.request('POST','/v1/chat/completions',json.dumps({'model':'fixture','messages':[{'role':'user','content':'fixed probe'}]}),{'Content-Type':'application/json'})
        r=c.getresponse(); r.read(); assert r.status==expected
    finally:
        c.close()
print('baseline-ok')
'''


def create_command(name, image, socket_directory, uid, gid, policy, *, probe_name='baseline'):
    if probe_name != 'baseline' and probe_name not in ENFORCEMENT_PROBES:
        raise ValueError('Only fixed reviewed probe names are supported')
    program = PROBE if probe_name == 'baseline' else ENFORCEMENT_PROBES[probe_name]
    if not re.fullmatch(r'harness-preflight-[a-f0-9]{32}', name):
        raise ValueError('Invalid controlled container name')
    if not (re.fullmatch(r'[a-z0-9./_-]+@sha256:[a-f0-9]{64}', image)
            or re.fullmatch(r'sha256:[a-f0-9]{64}', image)):
        raise ValueError('Expected immutable registry digest or local content ID')
    if type(uid) is not int or type(gid) is not int or uid <= 0 or gid <= 0:
        raise ValueError('Host identity must be nonroot')
    directory = Path(socket_directory).resolve(strict=True)
    if ',' in str(directory) or not directory.is_dir():
        raise ValueError('Invalid socket mount')
    return ['docker', 'create', '--pull', 'never', '--name', name, '--platform', 'linux/amd64',
            '--network', 'none', '--read-only', '--cap-drop', 'ALL',
            '--security-opt', 'no-new-privileges', '--user', f'{uid}:{gid}',
            '--memory', str(policy.memory_bytes), '--memory-swap', str(policy.memory_bytes),
            '--cpus', '1', '--pids-limit', str(policy.pids), '--log-driver', 'none',
            '--ulimit', 'core=0', '--ulimit', 'nofile=128:128',
            '--tmpfs', f'/work:rw,noexec,nosuid,nodev,size={policy.workspace_bytes},uid={uid},gid={gid}',
            '--tmpfs', f'/tmp:rw,noexec,nosuid,nodev,size={policy.temporary_bytes},uid={uid},gid={gid}',
            '--mount', f'type=bind,source={directory},target=/gateway,readonly',
            '--workdir', '/work', '--entrypoint', 'python3', image, '-I', '-c', program]


def validate_inspect(info, directory, uid, gid, policy, *, workspace_uid=None):
    host, config = info['HostConfig'], info['Config']
    required = {'ReadonlyRootfs': True, 'NetworkMode': 'none', 'Privileged': False,
                'Memory': policy.memory_bytes, 'MemorySwap': policy.memory_bytes,
                'NanoCpus': policy.nano_cpus, 'PidsLimit': policy.pids}
    if any(host.get(k) != v for k,v in required.items()):
        raise ValueError('Container policy mismatch')
    if (host.get('CapAdd') or host.get('Devices') or host.get('Binds')
            or host.get('PidMode') or host.get('IpcMode') == 'host'
            or set(host.get('SecurityOpt', [])) != {'no-new-privileges'}
            or host.get('CapDrop') != ['ALL']
            or host.get('LogConfig', {}).get('Type') != 'none'
            or config.get('User') != f'{uid}:{gid}'):
        raise ValueError('Unexpected privileges or logging')
    workspace_uid = uid if workspace_uid is None else workspace_uid
    tmpfs = host.get('Tmpfs')
    expected_tmpfs = {
        '/work': f'rw,noexec,nosuid,nodev,size={policy.workspace_bytes},uid={workspace_uid},gid={gid}',
        '/tmp': f'rw,noexec,nosuid,nodev,size={policy.temporary_bytes},uid={workspace_uid},gid={gid}'}
    if (not isinstance(tmpfs, dict) or tmpfs.keys() != expected_tmpfs.keys()
            or any(set(tmpfs[key].split(',')) != set(value.split(',')) for key,value in expected_tmpfs.items())):
        raise ValueError('Missing, unbounded or unexpected writable tmpfs policy')
    mounts = info.get('Mounts', [])
    # Docker may include tmpfs mounts in Mounts; every mount must be declared.
    binds = [m for m in mounts if m.get('Type') != 'tmpfs']
    if (len(binds) != 1 or binds[0].get('Type') != 'bind'
            or binds[0].get('Source') != str(Path(directory).resolve())
            or binds[0].get('Destination') != '/gateway' or binds[0].get('RW') is not False
            or any(m.get('Destination') not in ('/gateway','/work','/tmp') for m in mounts)):
        raise ValueError('Unexpected filesystem mount')


def fixed_probe_preflight(image, *, probe_name='baseline', reviewed_image=None):
    """Authorized fixed-code only. Missing Docker/image fails without install/pull."""
    if probe_name != 'baseline' and probe_name not in ENFORCEMENT_PROBES:
        raise ValueError('Only reviewed fixed probes may run')
    if not shutil.which('docker'):
        return {'status': 'unavailable', 'executed': False, 'qualification_complete': False}
    if not isinstance(reviewed_image, ImagePolicy) or reviewed_image.reference != image:
        raise ValueError('Reviewed matching image policy required before Docker execution')
    uid, gid = os.getuid(), os.getgid()
    policy = DockerPolicy()
    name = 'harness-preflight-' + uuid.uuid4().hex
    def run(args, timeout=10):
        result = capture(args, timeout_s=timeout, max_bytes=1024*1024)
        return SimpleNamespace(stdout=result.stdout.decode('utf-8'))
    with tempfile.TemporaryDirectory(prefix='harness-socket-') as directory:
        # The mount contains the socket alone, not controller files. Same nonroot
        # uid can connect to mode-0600 socket without world-writable permissions.
        command = create_command(name, image, directory, uid, gid, policy, probe_name=probe_name)
        budget = TrialRequestBudget(1, lambda _: b'{"choices":[]}')
        image_info = json.loads(run(['docker', 'image', 'inspect', image]).stdout)
        if not isinstance(image_info, list) or len(image_info) != 1:
            raise ValueError('Expected exact inspected image')
        validate_image(image_info[0], reviewed_image)  # No implicit network pull.
        with trial_gateway(budget, expected_model='fixture', max_output_tokens=32,
                           unix_path=str(Path(directory)/'provider.sock')):
            try:
                run(command)
                info = json.loads(run(['docker','inspect',name]).stdout)[0]
                validate_inspect(info, directory, uid, gid, policy)
                result = run(['docker','start','--attach',name], policy.wall_seconds)
                state = json.loads(run(['docker','inspect',name]).stdout)[0]['State']
                sentinel = 'baseline-ok' if probe_name == 'baseline' else probe_name + '-ok'
                if state['ExitCode'] != 0 or state.get('OOMKilled') or result.stdout.strip() != sentinel:
                    raise ValueError('Fixed probe did not complete')
                expected_attempts = 1 if probe_name == 'baseline' else 0
                if budget.attempts != expected_attempts or len(budget.audit) != expected_attempts:
                    raise ValueError('Fixture gateway accounting mismatch')
            finally:
                # Includes create/inspect/start failure and attach timeout. No
                # cleanup claim if removal or subsequent absence check fails.
                run(['docker','rm','--force',name])
                remaining=run(['docker','ps','-aq','--filter',f'name=^/{name}$']).stdout.strip()
                if remaining:
                    raise ValueError('Container cleanup not confirmed')
    return {'status':'probe_pass', 'probe':probe_name, 'qualification_complete':False,
            'cleanup':'absence_confirmed', 'real_provider_calls':0,
            'fixture_attempts':expected_attempts,
            'aider_adapter':'not_qualified', 'scoring_oracle':'not_qualified'}


def baseline_preflight(image, *, reviewed_image=None):
    result = fixed_probe_preflight(image, reviewed_image=reviewed_image)
    if result['status'] == 'probe_pass':
        result['status'] = 'baseline_pass'
        result['aggregate_exhaustion_probes'] = 'not_run'
    return result


def fixed_suite_summary(image, *, reviewed_image=None):
    """Sequential fresh-container probes, controlled results, fail closed.

    Requires explicit model-free execution approval. No complete qualification
    claim is possible: exact Aider/transfer/scoring integration is still absent.
    """
    records = []
    for name in ('baseline', 'pids', 'memory', 'cpu', 'disk'):
        try:
            record = fixed_probe_preflight(image, probe_name=name, reviewed_image=reviewed_image)
        except ControlledProcessError as error:
            record = {'status':'failed','probe':name,'reason':error.category}
        except (ValueError, KeyError, TypeError, IndexError, UnicodeError, OSError):
            record = {'status':'failed','probe':name,'reason':'policy_or_probe_invalid'}
        records.append(record)
        if record['status'] != 'probe_pass':
            break
    passed = len(records) == 5 and all(r['status'] == 'probe_pass' for r in records)
    return {'status':'fixed_probes_pass' if passed else 'incomplete_or_failed',
            'records':records, 'qualification_complete':False, 'real_provider_calls':0,
            'aider_adapter':'not_qualified', 'scoring_oracle':'not_qualified'}


def baseline_summary(image, *, reviewed_image=None):
    """Allowlisted reporting boundary. No raw command/stdout/diagnostics escape.

    Calling this still executes fixed Docker code when available and requires
    the same separate approval as baseline_preflight. It is not an auth gate.
    """
    try:
        return baseline_preflight(image, reviewed_image=reviewed_image)
    except ControlledProcessError as error:
        return {'status':'failed', 'reason':error.category, 'qualification_complete':False}
    except (ValueError, KeyError, TypeError, IndexError, UnicodeError, OSError):
        return {'status':'failed', 'reason':'policy_or_probe_invalid', 'qualification_complete':False}
