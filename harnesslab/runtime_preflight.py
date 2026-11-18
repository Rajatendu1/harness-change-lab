"""Local runtime checks for preparation. No downloads, credentials or models."""
import json
from pathlib import Path
import shutil
import subprocess


def inspect_runtime(python, runtime_root):
    executable = Path(python)
    root = Path(runtime_root).resolve(strict=True)
    if not executable.exists() or not root.is_dir():
        raise ValueError('Runtime paths must exist')
    resolved = executable.resolve(strict=True)
    # System Python is already in the controller's read-only /usr mount.
    if not (resolved.is_relative_to('/usr') or resolved.is_relative_to(root)):
        raise ValueError('Python resolves outside declared runtime or system mount')
    try:
        result = subprocess.run([str(executable), '-I', '-c',
        'import json,sys,importlib.metadata as m; print(json.dumps({"python":sys.version.split()[0],"pytest":m.version("pytest")}))'],
        text=True, capture_output=True, timeout=10, env={'PATH': '/usr/bin:/bin'})
    except subprocess.TimeoutExpired:
        raise ValueError('Runtime metadata probe timed out') from None
    if result.returncode:
        raise ValueError('Runtime cannot import required pytest metadata')
    data = json.loads(result.stdout)
    if data['pytest'] != '8.3.5':
        raise ValueError('Prepared scorer requires pytest 8.3.5')
    return data


def inspect_os_isolation():
    bwrap = shutil.which('bwrap')
    if not bwrap:
        return {'namespace_probe': 'unavailable', 'aggregate_resources': 'not_verified'}
    command = [bwrap, '--unshare-all', '--die-with-parent', '--ro-bind', '/usr', '/usr',
               '--ro-bind', '/lib', '/lib', '--ro-bind', '/lib64', '/lib64',
               '--proc', '/proc', '--dev', '/dev', '--tmpfs', '/tmp', '--clearenv',
               '/usr/bin/python3', '-I', '-c',
               'import json,socket; print(json.dumps({"interfaces":[n for _,n in socket.if_nameindex()]}))']
    try:
        probe = subprocess.run(command, text=True, capture_output=True, timeout=10,
                               env={'PATH': '/usr/bin:/bin'})
    except subprocess.TimeoutExpired:
        return {'namespace_probe': 'timed_out', 'aggregate_resources': 'not_verified'}
    if probe.returncode:
        return {'namespace_probe': 'failed', 'aggregate_resources': 'not_verified'}
    try:
        data = json.loads(probe.stdout)
        interfaces = data['interfaces']
    except (ValueError, TypeError, KeyError):
        return {'namespace_probe': 'failed', 'aggregate_resources': 'not_verified'}
    return {'namespace_probe': 'passed' if interfaces == ['lo'] else 'failed',
            'aggregate_resources': 'not_verified'}
