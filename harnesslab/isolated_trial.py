"""Linux local trial controller prototype. No model execution CLI is exposed.

OS namespaces isolate the supplied child from host network, processes and files.
This is not resource-hardening, verifier execution, or approval enforcement.
"""
from dataclasses import asdict, dataclass
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import tempfile
import time

from .trial_gateway import trial_gateway
from .syscall_filter import syscall_filter


@dataclass(frozen=True)
class ChildResult:
    status: str
    exit_code: object
    elapsed_s: float
    provider_attempts: int
    provider_outcomes: tuple
    provider_usage: tuple = ()
    provider_pending_attempts: int = 0
    syscall_policy: str = "native_denylist_v0"


def isolated_trial(command, *, workspace, budget, model, max_output_tokens,
                   timeout_s, read_only_paths=(), resource_limits=None,
                   request_policy=None, token_counter=None):
    if not command or timeout_s <= 0:
        raise ValueError('Expected command and positive wall-clock bound')
    limits = dict(address_space_bytes=2 * 1024**3, cpu_seconds=60,
                  file_bytes=16 * 1024**2, open_files=128)
    if resource_limits is not None:
        if set(resource_limits) != set(limits):
            raise ValueError('Expected exact resource-limit fields')
        limits.update(resource_limits)
    if any(type(value) is not int or value <= 0 for value in limits.values()):
        raise ValueError('Resource limits must be positive integers')
    executable = shutil.which('bwrap')
    if executable is None:
        raise RuntimeError('OS isolation unavailable; refusing unisolated fallback')
    workspace = Path(workspace).resolve(strict=True)
    if not workspace.is_dir():
        raise ValueError('Expected trial directory')
    helper = Path(__file__).with_name('isolated_child.py').resolve()
    with tempfile.TemporaryDirectory(prefix='trial-controller-') as controller_dir:
        socket_path = str(Path(controller_dir) / 'provider.sock')
        args = [executable, '--unshare-all', '--die-with-parent', '--new-session',
                '--ro-bind', '/usr', '/usr', '--ro-bind', '/lib', '/lib',
                '--ro-bind', '/lib64', '/lib64', '--proc', '/proc', '--dev', '/dev',
                '--tmpfs', '/tmp', '--tmpfs', '/home', '--dir', '/home/agent',
                '--bind', str(workspace), '/work',
                '--ro-bind', str(helper), '/bootstrap.py',
                '--dir', '/gateway', '--ro-bind', socket_path, '/gateway/provider.sock',
                '--chdir', '/work', '--clearenv',
                '--setenv', 'PATH', '/usr/bin:/bin', '--setenv', 'HOME', '/home/agent',
                '--setenv', 'TERM', 'dumb', '--setenv', 'PYTEST_DISABLE_PLUGIN_AUTOLOAD', '1', '--setenv', 'LITELLM_LOCAL_MODEL_COST_MAP', 'True']
        for path in read_only_paths:
            path = str(Path(path).resolve(strict=True))
            if path in ('/', '/tmp', '/home', '/proc', '/dev'):
                raise ValueError('Refusing broad host mount')
            args.extend(['--ro-bind', path, path])
        args += ['/usr/bin/python3', '/bootstrap.py', json.dumps(list(command)), json.dumps(limits)]
        started = time.monotonic()
        with trial_gateway(budget, expected_model=model, max_output_tokens=max_output_tokens,
                           unix_path=socket_path, request_policy=request_policy,
                           token_counter=token_counter), syscall_filter() as filter_fd:
            args[1:1] = ['--seccomp', str(filter_fd)]
            process = subprocess.Popen(args, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                       stderr=subprocess.DEVNULL, start_new_session=True, pass_fds=(filter_fd,))
            try:
                code = process.wait(timeout=timeout_s)
                status = 'process_exited' if code == 0 else 'process_failed'
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
                status, code = 'wall_clock_timeout', None
        audit = budget.audit
        return ChildResult(status, code, round(time.monotonic() - started, 3), budget.attempts,
                           tuple(row.outcome for row in audit),
                           tuple(asdict(row) for row in audit), budget.attempts - len(audit))
