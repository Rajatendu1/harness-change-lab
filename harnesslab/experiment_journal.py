"""Local experiment journal. Consistency evidence, never approval/authentication.

A plan is written before execution and each result is flushed separately. A
failed/partial run remains inspectable and cannot be finalized as complete.
"""
import hashlib
import json
import os
from pathlib import Path

from .paired_controller import paired_report
from .compare import Outcome, compare


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


class ExperimentJournal:
    def __init__(self, directory, plan):
        self.directory = Path(directory)
        # Exclusive creation, never resume/reuse a result directory implicitly.
        self.directory.mkdir(parents=True, exist_ok=False)
        self.plan = json.loads(json.dumps(plan))
        self.plan_hash = digest(self.plan)
        self.plan_path = self.directory / 'plan.json'
        self.records_path = self.directory / 'records.jsonl'
        self.plan_path.write_text(json.dumps({'plan': self.plan, 'plan_sha256': self.plan_hash},
                                             sort_keys=True, indent=2) + '\n')
        self.records_path.touch(exist_ok=False)
        self._completed = False
        # Validate the report-policy shape before any supplied child executes.
        order = self.plan['configuration_order']
        if len(order) != 2 or set(order) != set(self.plan['configurations']):
            raise ValueError('Predeclare baseline/candidate order explicitly')
        policy = self.plan['policy']
        if set(policy) != {'min_tasks', 'margin', 'confidence', 'resamples', 'seed'}:
            raise ValueError('Explicit complete comparison policy required')
        # Validate numeric policy before any trial, even if every result is later excluded.
        dummy = [Outcome('policy-check', 0, False, 'r1', '0' * 64)]
        compare(dummy, dummy, **policy)
        if self.plan.get('execution_authority') != 'none':
            raise ValueError('Journal cannot supply execution authority')

    def _verify(self):
        if self._completed:
            raise ValueError('Journal already finalized')
        saved = json.loads(self.plan_path.read_text())
        if digest(saved.get('plan')) != self.plan_hash or saved != {'plan': self.plan, 'plan_sha256': self.plan_hash}:
            raise ValueError('Plan changed after journal creation')

    def append(self, record):
        self._verify()
        envelope = {'plan_sha256': self.plan_hash, 'record': record, 'record_sha256': digest(record)}
        with self.records_path.open('a', encoding='utf-8') as stream:
            stream.write(json.dumps(envelope, sort_keys=True, separators=(',', ':')) + '\n')
            stream.flush()
            os.fsync(stream.fileno())

    def finalize(self):
        self._verify()
        records = []
        for line in self.records_path.read_text().splitlines():
            envelope = json.loads(line)
            if envelope['plan_sha256'] != self.plan_hash or envelope['record_sha256'] != digest(envelope['record']):
                raise ValueError('Journal record changed')
            records.append(envelope['record'])
        report = paired_report(records, tasks=self.plan['tasks'],
                               configurations=self.plan['configurations'], trials=self.plan['trials'],
                               fixture_only=self.plan['fixture_only'], configuration_order=self.plan['configuration_order'],
                               **self.plan['policy'])
        report['plan_sha256'] = self.plan_hash
        report['records_sha256'] = hashlib.sha256(self.records_path.read_bytes()).hexdigest()
        destination = self.directory / 'report.json'
        with destination.open('x') as stream:
            stream.write(json.dumps(report, sort_keys=True, indent=2) + '\n')
        self._completed = True
        return report
