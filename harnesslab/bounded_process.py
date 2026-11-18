"""Bounded controller subprocess IO, no shell and no raw diagnostics on errors.

This is an IO/lifecycle helper, not authorization or a resource sandbox. Docker
containers survive client termination: caller still MUST force-remove/check them.
"""
from dataclasses import dataclass
import os
import selectors
import signal
import subprocess
import time


class ControlledProcessError(RuntimeError):
    def __init__(self, category):
        self.category = category
        super().__init__(category)


@dataclass(frozen=True)
class Captured:
    stdout: bytes
    returncode: int


def capture(command, *, timeout_s=10, max_bytes=1024*1024, input_data=None):
    """Bound stdout+stderr before buffering. Stderr never leaves this helper."""
    if (not isinstance(command, (list, tuple)) or not command
            or any(not isinstance(arg, str) or '\x00' in arg for arg in command)
            or type(timeout_s) not in (int, float) or not 0 < timeout_s <= 300
            or type(max_bytes) is not int or not 0 < max_bytes <= 80*1024*1024
            or (input_data is not None and (not isinstance(input_data, bytes)
                                           or len(input_data) > 80*1024*1024))):
        raise ValueError('Invalid bounded process arguments')
    try:
        process = subprocess.Popen(command, stdin=subprocess.PIPE if input_data is not None else subprocess.DEVNULL, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, start_new_session=True,
                                   env={'PATH':'/usr/bin:/bin'}, close_fds=True)
    except OSError:
        raise ControlledProcessError('launch_failed') from None
    output, total, sent = bytearray(), 0, 0
    deadline = time.monotonic() + timeout_s
    try:
        with selectors.DefaultSelector() as selector:
            for stream in (process.stdout, process.stderr):
                os.set_blocking(stream.fileno(), False)
                selector.register(stream, selectors.EVENT_READ)
            if input_data:
                os.set_blocking(process.stdin.fileno(), False)
                selector.register(process.stdin, selectors.EVENT_WRITE)
            elif process.stdin:
                process.stdin.close()
            while selector.get_map():
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise ControlledProcessError('wall_timeout')
                for key, _ in selector.select(remaining):
                    if key.fileobj is process.stdin:
                        try:
                            sent += os.write(key.fd, memoryview(input_data)[sent:sent+65536])
                        except BrokenPipeError:
                            raise ControlledProcessError('input_not_consumed') from None
                        if sent == len(input_data):
                            selector.unregister(process.stdin)
                            process.stdin.close()
                        continue
                    # Read at most one byte past the remaining total allowance.
                    data = os.read(key.fd, min(65536, max_bytes-total+1))
                    if not data:
                        selector.unregister(key.fileobj)
                        continue
                    total += len(data)
                    if total > max_bytes:
                        raise ControlledProcessError('output_limit')
                    if key.fileobj is process.stdout:
                        output.extend(data)
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise ControlledProcessError('wall_timeout')
            try:
                code = process.wait(timeout=remaining)
            except subprocess.TimeoutExpired:
                raise ControlledProcessError('wall_timeout') from None
            if code:
                raise ControlledProcessError('nonzero_exit')
            return Captured(bytes(output), code)
    except OSError:
        raise ControlledProcessError('io_failed') from None
    finally:
        # Includes descendants that inherited closed/no pipe descriptors. This
        # kills controller-client descendants, NOT daemon-owned Docker children.
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        if process.stdin:
            process.stdin.close()
        process.stdout.close()
        process.stderr.close()
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            raise ControlledProcessError('client_cleanup_unconfirmed') from None
