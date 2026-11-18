"""Narrow native Linux syscall denylist, not a complete sandbox policy.

Allows ordinary file/process/thread/network syscalls. Namespace/network/mount
boundaries and resource limits remain separate. No aggregate fork control.
"""
from contextlib import contextmanager
import ctypes
import ctypes.util
import errno
import os


DENIED_SYSCALLS = (
    'ptrace', 'process_vm_readv', 'process_vm_writev', 'bpf', 'perf_event_open',
    'keyctl', 'add_key', 'request_key', 'userfaultfd', 'mount', 'umount2',
    'pivot_root', 'setns', 'unshare', 'kexec_load', 'open_by_handle_at',
    'init_module', 'finit_module', 'delete_module', 'reboot', 'swapon', 'swapoff',
)


@contextmanager
def syscall_filter():
    library = ctypes.util.find_library('seccomp')
    if not library or not hasattr(os, 'memfd_create'):
        raise RuntimeError('Required libseccomp/memfd unavailable; refusing weaker fallback')
    lib = ctypes.CDLL(library, use_errno=True)
    lib.seccomp_init.argtypes = [ctypes.c_uint32]
    lib.seccomp_init.restype = ctypes.c_void_p
    lib.seccomp_syscall_resolve_name.argtypes = [ctypes.c_char_p]
    lib.seccomp_syscall_resolve_name.restype = ctypes.c_int
    lib.seccomp_rule_add.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_int, ctypes.c_uint]
    lib.seccomp_rule_add.restype = ctypes.c_int
    lib.seccomp_export_bpf.argtypes = [ctypes.c_void_p, ctypes.c_int]
    lib.seccomp_export_bpf.restype = ctypes.c_int
    lib.seccomp_release.argtypes = [ctypes.c_void_p]
    context = lib.seccomp_init(0x7fff0000)  # SCMP_ACT_ALLOW
    if not context:
        raise RuntimeError('Cannot initialize syscall filter')
    fd = None
    try:
        for name in DENIED_SYSCALLS:
            number = lib.seccomp_syscall_resolve_name(name.encode())
            if number < 0:
                raise RuntimeError('Required syscall name unavailable on this architecture')
            # EACCES distinguishes filter rejection in direct local probes.
            if lib.seccomp_rule_add(context, 0x00050000 | errno.EACCES, number, 0):
                raise RuntimeError('Cannot build syscall filter')
        fd = os.memfd_create('trial-syscall-filter', os.MFD_CLOEXEC)
        if lib.seccomp_export_bpf(context, fd):
            raise RuntimeError('Cannot export syscall filter')
        os.lseek(fd, 0, os.SEEK_SET)
        yield fd
    finally:
        if fd is not None:
            os.close(fd)
        lib.seccomp_release(context)
