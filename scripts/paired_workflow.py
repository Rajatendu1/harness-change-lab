#!/usr/bin/env python3
"""Local fixture workflow and verified journal report. No live-model mode.

Run with python -m scripts.paired_workflow. The fixture command uses an existing
local runtime, never installs one. Review invokes no children or providers.
"""
import argparse
import json
import math
from pathlib import Path
import re
import subprocess
import sys

from harnesslab.journal_review import read_journal


def safe_identifier(value):
    if type(value) is not str or re.fullmatch(r'[A-Za-z0-9_.-]{1,128}', value) is None:
        raise ValueError('Unsafe report identifier')
    return value


def observed_duration(record):
    value = record.get('execution', {}).get('elapsed_s')
    if value is None:
        return None
    if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
        raise ValueError('Invalid observed duration')
    return value


def observed_tokens(record):
    """Never use an empty/malformed usage collection as zero consumption."""
    execution = record.get('execution', {})
    attempts = execution.get('provider_attempts')
    usage = execution.get('provider_usage')
    if (type(attempts) is not int or attempts < 1 or type(usage) is not list
            or len(usage) != attempts or execution.get('provider_pending_attempts', 0) != 0):
        return None
    total = 0
    for index, row in enumerate(usage, 1):
        if (type(row) is not dict or row.get('number') != index
                or row.get('outcome') != 'returned' or row.get('usage_status') != 'provider_reported'):
            return None
        values = [row.get(key) for key in ('prompt_tokens', 'completion_tokens', 'total_tokens')]
        if any(type(value) is not int or value < 0 for value in values) or values[2] != values[0] + values[1]:
            return None
        total += values[2]
    return total


def report_text(directory):
    plan, records, report = read_journal(directory)
    baseline = safe_identifier(report['roles']['baseline'])
    candidate = safe_identifier(report['roles']['candidate'])
    lines = ['Paired experiment review',
        'Evidence: ' + ('SYNTHETIC CANNED FIXTURE, not AI repair evidence' if plan['fixture_only'] else 'SUPPLIED RECORDS, not authenticated execution'),
        'Roles: baseline=' + baseline + '; candidate=' + candidate,
        'Verdict: ' + report['verdict'],
        'Pairs: %d included / %d planned; %d excluded' % (report['included_pairs'], report['planned_pairs'], len(report['excluded_pairs'])),
        'Plan SHA256: ' + report['plan_sha256'],
        'Records SHA256: ' + report['records_sha256'], '',
        'Per-task observations (child editing time, not complete workflow latency):']
    for record in sorted(records, key=lambda row: (row['task_id'], row['trial'], row['configuration'])):
        task = safe_identifier(record['task_id'])
        name = safe_identifier(record['configuration'])
        outcome = safe_identifier(record['outcome'])
        elapsed = observed_duration(record)
        tokens = observed_tokens(record)
        lines.append('%s trial=%d %s outcome=%s edit_seconds=%s %s=%s' % (
            task, record['trial'], name, outcome,
            'unknown' if elapsed is None else '%.3f' % elapsed,
            'canned_fixture_tokens' if plan['fixture_only'] else 'supplied_reported_tokens',
            'unknown' if tokens is None else str(tokens)))
    lines += ['', 'Cost: not computed. No verified price or billing observation is supplied.',
        'Fixture token counts, when present, are invented transport plumbing values, not model usage.',
        'Unknown usage or duration is not zero. Excluded failures remain visible, never dropped.',
        'No new tasks, providers, keys, installs or hosted jobs were invoked by this review.',
        'Hashes establish consistency only. Trusted-process scoring is not adversarial integrity.']
    return '\n'.join(lines) + '\n'


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    review = commands.add_parser('review', help='Read and verify an existing complete journal')
    review.add_argument('directory', type=Path)
    fixture = commands.add_parser('fixture', help='Run local canned fixture only using already-provisioned runtime')
    fixture.add_argument('--runtime-root', type=Path, required=True)
    fixture.add_argument('--output-directory', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == 'fixture':
            runtime = args.runtime_root.resolve(strict=True)
            if not all((runtime / role / 'bin/python').is_file() for role in ('agent', 'verifier')):
                raise ValueError('Existing local runtime required; no installation fallback')
            if args.output_directory.exists():
                raise ValueError('Output directory already exists; no implicit resume')
            # Existing local fixture runner: one request budget per trial, no
            # real provider option. It writes a plan before the first child.
            result = subprocess.run([sys.executable, '-m', 'scripts.offline_paired_smoke',
                '--runtime-root', str(runtime), '--output-directory', str(args.output_directory)],
                cwd=Path(__file__).resolve().parents[1],
                stdin=subprocess.DEVNULL, capture_output=True, timeout=300)
            if result.returncode != 0:
                raise ValueError('Local fixture failed; partial journal retained for inspection')
            directory = args.output_directory
        else:
            directory = args.directory
        print(report_text(directory), end='')
        # Recompute the saved comparison; never turn regression into success.
        verdict = read_journal(directory)[2]['verdict']
        return {'no_detected_regression': 0, 'regression': 1, 'insufficient_evidence': 3}[verdict]
    except (ValueError, OSError, KeyError, TypeError, subprocess.TimeoutExpired):
        parser.exit(2, 'Invalid or incomplete local workflow; no valid review produced.\n')


if __name__ == '__main__':
    raise SystemExit(main())
