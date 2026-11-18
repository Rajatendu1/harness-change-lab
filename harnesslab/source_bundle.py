"""Bounded source-only archive transfer, no Docker or filesystem extraction API.

The controller constructs an immutable base, then overlays only declared source
outputs. This does not prove an agent left every other workspace file unchanged.
Do not use on a live candidate: stop/remove its process tree before collection.
"""
import io
from pathlib import PurePosixPath
import tarfile

MAX_BYTES = 64 * 1024 * 1024
MAX_FILE = 8 * 1024 * 1024
MAX_FILES = 20000
MAX_ARCHIVE = 80 * 1024 * 1024


def source_name(value):
    if (not isinstance(value, str) or not value or len(value) > 1024
            or value.startswith('/') or '\\' in value or '\x00' in value):
        raise ValueError('Invalid relative source name')
    parts = value.split('/')
    if any(part in ('', '.', '..', '.git') or part.startswith('.aider') for part in parts):
        raise ValueError('Unsafe or bookkeeping source name')
    if PurePosixPath(value).as_posix() != value:
        raise ValueError('Noncanonical source name')
    return value


def validate_sources(sources):
    if not isinstance(sources, dict) or not sources or len(sources) > MAX_FILES:
        raise ValueError('Expected bounded source mapping')
    total = 0
    for name, data in sources.items():
        source_name(name)
        if not isinstance(data, bytes) or len(data) > MAX_FILE:
            raise ValueError('Expected bounded source bytes')
        total += len(data)
        if total > MAX_BYTES:
            raise ValueError('Source bundle exceeds byte cap')
        parts = name.split('/')
        if any('/'.join(parts[:index]) in sources for index in range(1, len(parts))):
            raise ValueError('Source file/directory conflict')


def pack_sources(sources):
    """Controller-created uncompressed tar. No owners, links, mtime or modes copied."""
    validate_sources(sources)
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode='w', format=tarfile.USTAR_FORMAT) as archive:
        for name, data in sorted(sources.items()):
            info = tarfile.TarInfo(name)
            info.size, info.mode = len(data), 0o600
            try:
                archive.addfile(info, io.BytesIO(data))
            except ValueError:
                raise ValueError('Source name cannot be represented in controlled archive') from None
            if buffer.tell() > MAX_ARCHIVE:
                raise ValueError('Archive exceeds transfer cap')
    if buffer.tell() > MAX_ARCHIVE:
        raise ValueError('Archive exceeds transfer cap')
    return buffer.getvalue()


def unpack_sources(raw, *, expected_names):
    """Read exact source-only archive into bounded bytes, never extract to disk.

    Caller must cap transport bytes before buffering them here. `expected_names`
    is controller-provided, not derived from archive names. No compressed tar.
    Docker cp prefix normalization, if needed, must be separately explicit.
    """
    expected = frozenset(source_name(name) for name in expected_names)
    if not expected or len(expected) > MAX_FILES:
        raise ValueError('Expected exact bounded source-name set')
    if not isinstance(raw, bytes) or len(raw) > MAX_ARCHIVE:
        raise ValueError('Archive exceeds transfer cap')
    sources, total = {}, 0
    try:
        with tarfile.open(fileobj=io.BytesIO(raw), mode='r|') as archive:
            for member in archive:
                name = source_name(member.name)
                if (name not in expected or name in sources or not member.isreg()
                        or member.pax_headers or member.size < 0 or member.size > MAX_FILE):
                    raise ValueError('Unexpected, linked, duplicate or oversized archive member')
                total += member.size
                if total > MAX_BYTES:
                    raise ValueError('Source bundle exceeds byte cap')
                with archive.extractfile(member) as stream:
                    data = stream.read(MAX_FILE + 1)
                if len(data) != member.size:
                    raise ValueError('Truncated source member')
                sources[name] = data
    except (tarfile.TarError, EOFError, OSError):
        raise ValueError('Invalid uncompressed source archive') from None
    if sources.keys() != expected:
        raise ValueError('Missing declared source output')
    validate_sources(sources)
    return sources


def overlay_candidate(base, proposed, *, editable_names):
    """Rebuild score candidate from immutable base and complete allowed outputs."""
    validate_sources(base)
    validate_sources(proposed)
    editable = frozenset(source_name(name) for name in editable_names)
    if not editable or proposed.keys() != editable or not editable <= base.keys():
        raise ValueError('Only exact existing editable source files may be replaced')
    candidate = dict(base)
    candidate.update(proposed)
    validate_sources(candidate)
    return candidate
