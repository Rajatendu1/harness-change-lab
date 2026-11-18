"""Prepare-only protected pytest scoring on a disposable candidate copy.

The controller supplies the editable-file allowlist, protected test directory,
pytest runtime and arguments. The agent workspace is never scored in place.
No provider route is available to the scoring transport.
"""
from dataclasses import dataclass
from pathlib import Path
import shutil
import json
import os
import stat
import tempfile
import xml.etree.ElementTree as ET

from .isolated_trial import isolated_trial
from .request_budget import TrialRequestBudget
from .runtime_preflight import inspect_runtime


@dataclass(frozen=True)
class Score:
    outcome: str
    changed_files: tuple = ()
    tests: int = 0
    failures: int = 0
    errors: int = 0
    skipped: int = 0
    verifier_exit_code: object = None
    evidence_class: str = "local_protected_pytest_trusted_process"
    adversarial_integrity_verified: bool = False


def _files(root):
    """Bounded post-execution snapshot, never follow links or read special files.

    Caller must stop the entire candidate process tree before using this helper.
    It is not a concurrent-filesystem sandbox or an adversarial scoring oracle.
    """
    root = Path(root)
    if root.is_symlink() or not root.is_dir():
        raise ValueError('Expected real tree directory')
    result, entries, total = {}, 0, 0
    def walk_error(error):
        raise error
    for directory, directories, files in os.walk(root, followlinks=False, onerror=walk_error):
        directories[:] = [name for name in directories
                          if name != '.git' and not name.startswith('.aider')]
        for name in directories + files:
            if name == '.git' or name.startswith('.aider'):
                continue  # Same exclusion policy as the disposable scorer copy.
            entries += 1
            if entries > 20000:
                raise ValueError('Tree exceeds entry bound')
            path = Path(directory) / name
            metadata = path.lstat()
            if stat.S_ISDIR(metadata.st_mode):
                continue
            if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
                raise ValueError('Nonregular or linked file in candidate tree')
            if metadata.st_size > 8 * 1024 * 1024:
                raise ValueError('Tree exceeds per-file bound')
            # Refuse symlink substitution at the final component and bound the
            # read even if a supposedly stopped producer is still present.
            fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
            with os.fdopen(fd, 'rb') as stream:
                opened = os.fstat(stream.fileno())
                if not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1:
                    raise ValueError('File changed during snapshot')
                data = stream.read(8 * 1024 * 1024 + 1)
            total += len(data)
            if len(data) > 8 * 1024 * 1024 or total > 64 * 1024 * 1024:
                raise ValueError('Tree exceeds byte bound')
            result[path.relative_to(root).as_posix()] = data
    return result


def score_candidate(*, base, candidate, editable_files, protected_tests,
                    python, runtime_root, timeout_s=30, allowed_skips=(), source_import_directory=None, test_node=None, plugins=(), reference_mode=False):
    try:
        inspect_runtime(python, runtime_root)
    except (ValueError, OSError, TimeoutError):
        return Score('verifier_setup_error')
    try:
        original, proposed = _files(base), _files(candidate)
        changed = tuple(sorted(name for name in original.keys() | proposed.keys()
                               if original.get(name) != proposed.get(name)))
        allowed = set(editable_files)
        skip_policy = set(allowed_skips)
        if any(not isinstance(name, str) or not name for name in skip_policy):
            return Score('invalid_input')
        if not allowed or any(name not in allowed for name in changed):
            return Score('invalid_patch', changed)
        if type(reference_mode) is not bool:
            return Score('invalid_input')
        if not changed and not reference_mode:
            return Score('no_source_change')
        if any(name not in original or name not in proposed for name in changed):
            return Score('invalid_patch', changed)
        protected_tests = Path(protected_tests).resolve(strict=True)
        if source_import_directory is not None:
            relative = Path(source_import_directory)
            if relative.is_absolute() or '..' in relative.parts or not (Path(candidate) / relative).is_dir():
                return Score('invalid_input')
        if test_node is not None:
            relative_node = test_node.split('::', 1)[0]
            if Path(relative_node).is_absolute() or '..' in Path(relative_node).parts:
                return Score('invalid_input')
            if not (protected_tests / relative_node).is_file():
                return Score('invalid_input')
        if any(not isinstance(plugin, str) or not plugin.replace('_','').isalnum() for plugin in plugins):
            return Score('invalid_input')
        _files(protected_tests)  # Reject symlinks in controller-supplied tests too.
    except (ValueError, OSError):
        return Score('invalid_input')
    with tempfile.TemporaryDirectory(prefix='protected-score-') as directory:
        checkout = Path(directory) / 'workspace'
        shutil.copytree(candidate, checkout, ignore=shutil.ignore_patterns('.git', '.aider*'))
        # Never trust a report left by the agent.
        report = checkout / '.controller-score.xml'
        report.unlink(missing_ok=True)
        def no_provider(body):
            raise RuntimeError('Scoring has no provider transport')
        budget = TrialRequestBudget(1, no_provider)
        command = [str(python), '-m', 'pytest', '-q', '-p', 'no:cacheprovider',
                   '--import-mode=importlib', '--override-ini=addopts=',
                   '--junitxml=/work/.controller-score.xml',
                   str(protected_tests) + ('/' + test_node if test_node else '')]
        for plugin in plugins:
            command.extend(['-p', plugin])
        if source_import_directory is not None:
            # Controller-declared src-layout import, never derived from agent output.
            invocation = ('import sys; sys.path.insert(0, ' + json.dumps('/work/' + source_import_directory)
                          + '); import pytest; raise SystemExit(pytest.main(' + repr(command[3:]) + '))')
            command = [str(python), '-c', invocation]
        execution = isolated_trial(command, workspace=checkout, budget=budget,
                                   model='disabled-scoring', max_output_tokens=1,
                                   timeout_s=timeout_s,
                                   read_only_paths=[runtime_root, protected_tests])
        if execution.status == 'wall_clock_timeout':
            return Score('verifier_timeout', changed)
        try:
            if report.is_symlink() or report.stat().st_size > 1024 * 1024:
                raise ValueError()
            root = ET.fromstring(report.read_bytes())
            cases = list(root.iter('testcase'))
            tests = len(cases)
            failures = sum(case.find('failure') is not None for case in cases)
            errors = sum(case.find('error') is not None for case in cases)
            skipped_cases = [case for case in cases if case.find('skipped') is not None]
            skipped = len(skipped_cases)
            actual_skips = {(case.get('classname', '') + '::' + case.get('name', ''))
                            for case in skipped_cases}
            # Exact controller policy: no undeclared or stale skip allowances.
            skips_match = actual_skips == skip_policy
        except (OSError, ValueError, ET.ParseError):
            return Score('verifier_setup_error', changed, verifier_exit_code=execution.exit_code)
        details = dict(changed_files=changed, tests=tests, failures=failures,
                       errors=errors, skipped=skipped, verifier_exit_code=execution.exit_code)
        if execution.exit_code not in (0, 1) or tests - skipped <= 0 or errors or not skips_match:
            return Score('verifier_setup_error', **details)
        if execution.exit_code == 0 and not failures:
            return Score('reference_verifier_pass' if reference_mode else 'source_patch_verifier_pass', **details)
        return Score('reference_verifier_fail' if reference_mode else 'verifier_fail', **details)
