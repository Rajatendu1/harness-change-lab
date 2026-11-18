"""Fixed source IO primitives for a future Docker exec helper.

No container execution/CLI. Requires trusted empty import root or quiescent
export root. Directory-fd traversal refuses link substitution. Not an oracle.
"""
import os
from pathlib import Path
import stat

from .source_bundle import MAX_FILE, MAX_BYTES, pack_sources, unpack_sources, validate_sources, source_name

DIRECTORY_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW


def _root_fd(root):
    return os.open(Path(root), DIRECTORY_FLAGS)


def _parent_fd(root_fd, name, *, create=False):
    parts = source_name(name).split('/')
    current = os.dup(root_fd)
    try:
        for part in parts[:-1]:
            if create:
                try:
                    os.mkdir(part, mode=0o700, dir_fd=current)
                except FileExistsError:
                    pass
            following = os.open(part, DIRECTORY_FLAGS, dir_fd=current)
            os.close(current)
            current = following
        return current, parts[-1]
    except BaseException:
        os.close(current)
        raise


def import_sources(raw, *, expected_names, root):
    """Validate entire archive before writes. On IO failure discard container.

    No rollback/success claim for ENOSPC or filesystem failure. Import root must
    be controller-designated, initially empty and have no concurrent writers.
    """
    sources = unpack_sources(raw, expected_names=expected_names)
    descriptor = _root_fd(root)
    try:
        if os.listdir(descriptor):
            raise ValueError('Import root must be empty')
        for name, data in sorted(sources.items()):
            parent, leaf = _parent_fd(descriptor, name, create=True)
            try:
                file_fd = os.open(leaf, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                                  0o600, dir_fd=parent)
                with os.fdopen(file_fd, 'wb') as stream:
                    stream.write(data)
            finally:
                os.close(parent)
    finally:
        os.close(descriptor)
    return 'source-import-ok'


def export_sources(*, expected_names, root):
    """Read declared files only, no archive extraction or candidate imports.

    Requires controller-verified absence of all candidate processes first.
    Bounded transport capture remains mandatory outside this function.
    """
    names = tuple(expected_names)
    validate_sources({source_name(name):b'' for name in names})
    if len(set(names)) != len(names):
        raise ValueError('Duplicate requested source name')
    sources, total = {}, 0
    descriptor = _root_fd(root)
    try:
        for name in sorted(names):
            parent, leaf = _parent_fd(descriptor, name)
            try:
                file_fd = os.open(leaf, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
                with os.fdopen(file_fd, 'rb') as stream:
                    info = os.fstat(stream.fileno())
                    if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1
                            or info.st_size > MAX_FILE):
                        raise ValueError('Unsafe source output')
                    sources[name] = stream.read(MAX_FILE + 1)
                total += len(sources[name])
                if len(sources[name]) > MAX_FILE or total > MAX_BYTES:
                    raise ValueError('Source output exceeds byte bound')
            finally:
                os.close(parent)
    finally:
        os.close(descriptor)
    return pack_sources(sources)
