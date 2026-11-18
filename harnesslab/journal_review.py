"""Verify and summarize a saved local journal without executing any task."""
import hashlib
import json
from pathlib import Path

from .experiment_journal import digest
from .paired_controller import paired_report


def read_journal(directory):
    root = Path(directory)
    def read(name):
        path = root / name
        if path.is_symlink() or path.stat().st_size > 16 * 1024 * 1024:
            raise ValueError('Invalid or oversized journal file')
        return path.read_bytes()
    saved = json.loads(read('plan.json'))
    plan = saved['plan']
    if saved['plan_sha256'] != digest(plan):
        raise ValueError('Plan digest mismatch')
    order = plan['configuration_order']
    raw_records = read('records.jsonl')
    records = []
    for line in raw_records.splitlines():
        envelope = json.loads(line)
        if envelope['plan_sha256'] != saved['plan_sha256'] or envelope['record_sha256'] != digest(envelope['record']):
            raise ValueError('Record digest mismatch')
        records.append(envelope['record'])
    expected = paired_report(records, tasks=plan['tasks'], configurations=plan['configurations'],
                             trials=plan['trials'], fixture_only=plan['fixture_only'],
                             configuration_order=order, **plan['policy'])
    expected['plan_sha256'] = saved['plan_sha256']
    expected['records_sha256'] = hashlib.sha256(raw_records).hexdigest()
    report = json.loads(read('report.json'))
    if expected != report:
        raise ValueError('Saved report does not match declared policy and records')
    return plan, records, report


def summary(directory):
    plan, records, report = read_journal(directory)
    lines = ['Local experiment review',
             'Evidence: ' + ('canned-response fixture, not model results' if plan['fixture_only'] else 'supplied local records, not authenticated'),
             'Verdict: ' + report['verdict'],
             'Baseline: ' + report['roles']['baseline'],
             'Candidate: ' + report['roles']['candidate'],
             'Pairs: %d included / %d planned' % (report['included_pairs'], report['planned_pairs']),
             'Plan SHA-256: ' + report['plan_sha256']]
    for excluded in report['excluded_pairs']:
        reasons = ', '.join(name + '=' + outcome for name, outcome in excluded['outcomes'].items())
        lines.append('Excluded %s trial %s: %s' % (excluded['task_id'], excluded['trial'], reasons))
    lines.append(report['abstention_scope'])
    lines.append('Hashes check consistency, not authenticity. No tasks or providers were invoked by this review.')
    return '\n'.join(lines)
