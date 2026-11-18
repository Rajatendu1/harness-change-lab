"""Prepared Flask verifier-only operation. No host or editing operation.

Inputs enter an empty disposable verifier through controller stdin. Docker
identity/cgroup checks precede imports and writes. Not a hostile-code oracle.
"""
import importlib.metadata
import json
import os
from pathlib import Path
import stat
import subprocess
import sys

from .docker_fixture_child import guard
from .flask_preparation import SCORE_NAMES, TEST_NAME, MAX_REPORT, validate_score_input, parse_protected_result
from .source_bundle import MAX_ARCHIVE
from .source_io import import_sources

REPORT = Path('/tmp/flask-controller-score.xml')


def read_report(path):
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(descriptor, 'rb') as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > MAX_REPORT:
            raise ValueError('Unsafe protected report')
        data = stream.read(MAX_REPORT + 1)
    if len(data) > MAX_REPORT:
        raise ValueError('Protected report exceeded limit')
    return data


def score():
    guard()
    if sys.version_info[:2] != (3, 10) or importlib.metadata.version('pytest') != '8.3.5':
        raise ValueError('Pinned verifier required')
    raw = sys.stdin.buffer.read(MAX_ARCHIVE + 1)
    validate_score_input(raw)
    if REPORT.exists() or REPORT.is_symlink():
        raise ValueError('Unexpected prior report')
    import_sources(raw, expected_names=SCORE_NAMES, root='/work')
    invocation = ('import sys; sys.path.insert(0,"/work/src"); import pytest; '
                  'raise SystemExit(pytest.main(' + repr(['-q', '-p', 'no:cacheprovider',
                  '--import-mode=importlib', '--override-ini=addopts=', '--junitxml=' + str(REPORT),
                  '/work/' + TEST_NAME + '::test_dotted_name_not_allowed']) + '))')
    run = subprocess.run([sys.executable, '-I', '-c', invocation], stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=20,
        env={'PATH':'/opt/verifier/bin:/usr/local/bin:/usr/bin:/bin', 'HOME':'/tmp',
             'PYTEST_DISABLE_PLUGIN_AUTOLOAD':'1', 'PYTHONDONTWRITEBYTECODE':'1'}, close_fds=True)
    result = parse_protected_result(read_report(REPORT), run.returncode)
    result['status'] = 'flask_verifier_result'
    return result


def main():
    try:
        print(json.dumps(score(), sort_keys=True))
        return 0
    except Exception:
        return 3


if __name__ == '__main__':
    raise SystemExit(main())
