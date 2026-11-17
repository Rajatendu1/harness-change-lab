"""Explicit Docker isolation smoke test, not a coding-agent evaluation.

No install/fallback is attempted if Docker is missing. The program placed inside
this container is fixed test code, not a model output or downloaded repository.
"""
import json
from pathlib import Path
import shutil
import subprocess
import uuid

IMAGE = 'python@sha256:0f086103b026048cc50cb5da25ec435c023c5241a83fc44daea593377abc61c4'
PROGRAM = r'''
import errno, json, os, socket
assert os.geteuid() == 65534
assert not os.path.exists('/var/run/docker.sock')
status = open('/proc/self/status').read()
assert 'NoNewPrivs:\t1' in status
assert int(next(line.split()[1] for line in status.splitlines() if line.startswith('CapEff:')), 16) == 0
try:
    open('/root-write-probe', 'w').write('must fail')
except OSError as exc:
    assert exc.errno in (errno.EROFS, errno.EACCES)
else:
    raise AssertionError('Root filesystem writable')
with open('/tmp/writable-probe', 'w') as f:
    f.write('temporary only')
sock = socket.socket()
sock.settimeout(0.2)
try:
    sock.connect(('192.0.2.1', 80))
except OSError:
    pass
else:
    raise AssertionError('Unexpected external network connectivity')
finally:
    sock.close()
print(json.dumps({'uid':os.geteuid(), 'root_readonly':True, 'no_new_privileges':True, 'effective_capabilities':0, 'external_network_probe_blocked':True, 'docker_socket_present':False}))
'''


def run(*args, check=True, timeout=60):
    return subprocess.run(['docker', *args], check=check, timeout=timeout,
                          capture_output=True, text=True)


def main() -> int:
    if not shutil.which('docker'):
        print(json.dumps({'status':'unavailable', 'reason':'Docker executable missing',
                          'executed':False, 'fallback':False}))
        return 2
    free = shutil.disk_usage(Path.cwd()).free
    if free < 8 * 1024**3:
        print(json.dumps({'status':'unavailable', 'reason':'Less than 8 GiB free disk',
                          'executed':False, 'free_bytes':free}))
        return 2
    run('version')
    run('pull', '--platform', 'linux/amd64', IMAGE, timeout=180)
    image_info = json.loads(run('image','inspect',IMAGE).stdout)[0]
    if image_info['Size'] > 512 * 1024**2:
        raise RuntimeError('Base image exceeds pilot size limit')
    name = 'harness-isolation-smoke-' + uuid.uuid4().hex[:12]
    try:
        run('create','--name',name,'--platform','linux/amd64',
            '--network','none','--read-only','--cap-drop','ALL',
            '--security-opt','no-new-privileges','--pids-limit','64',
            '--memory','256m','--cpus','1','--user','65534:65534',
            '--tmpfs','/tmp:rw,noexec,nosuid,size=16m',
            IMAGE,'python','-I','-c',PROGRAM)
        info = json.loads(run('inspect',name).stdout)[0]
        host = info['HostConfig']
        assert host['ReadonlyRootfs'] is True
        assert host['NetworkMode'] == 'none'
        assert host['Privileged'] is False
        assert not host['Binds']
        assert not host.get('Devices')
        assert host['Memory'] == 256 * 1024**2
        assert host['PidsLimit'] == 64
        result = run('start','--attach',name,timeout=15)
        state = json.loads(run('inspect',name).stdout)[0]['State']
        if state['ExitCode'] != 0 or state.get('OOMKilled'):
            raise RuntimeError(f'Isolation check failed: exit={state["ExitCode"]}')
        detail = json.loads(result.stdout)
        print(json.dumps({'status':'success',
                          'evidence_class':'fixed_code_container_smoke_only',
                          'agent_benchmark':False,
                          'image':IMAGE,'image_bytes':image_info['Size'],
                          'free_disk_before_bytes':free,
                          'checks':detail},indent=2))
        return 0
    finally:
        removed = run('rm','--force',name,check=False)
        if removed.returncode != 0:
            raise RuntimeError('Could not confirm container cleanup')


if __name__ == '__main__':
    raise SystemExit(main())
