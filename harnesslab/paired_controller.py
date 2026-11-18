"""Pair controller-scored records without turning infrastructure errors into failures.

Records are supplied evidence, not authenticated executions. This module does not
run an agent, approve a run, or upgrade trusted-process scoring to robust scoring.
"""
from dataclasses import asdict

from .compare import Outcome, compare


VALID_SCORES = {'source_patch_verifier_pass': True, 'verifier_fail': False}
EXCLUDED = {'no_source_change', 'invalid_patch', 'invalid_input', 'verifier_setup_error',
            'verifier_timeout', 'transport_failure', 'agent_timeout', 'agent_process_failure'}


def paired_report(records, *, tasks, configurations, trials, fixture_only, min_tasks=20, margin=0.05, confidence=0.95, resamples=10000, seed=0, configuration_order=None):
    if type(fixture_only) is not bool or len(configurations) != 2:
        raise ValueError('Declare evidence class and exactly two configurations')
    names = tuple(configurations) if configuration_order is None else tuple(configuration_order)
    if len(names) != 2 or set(names) != set(configurations):
        raise ValueError('Baseline/candidate order must exactly name the two configurations')
    if names[0] == names[1] or any(not isinstance(value, str) or len(value) != 64
                                or any(c not in '0123456789abcdef' for c in value)
                                for value in configurations.values()):
        raise ValueError('Configurations require distinct names and SHA-256 identities')
    if type(trials) is not int or trials <= 0 or not tasks:
        raise ValueError('Declare nonempty tasks and positive trial count')
    for task in tasks.values():
        if set(task) != {'revision', 'verifier_sha256'} or not task['revision']:
            raise ValueError('Task revision and verifier identity required')
        digest = task['verifier_sha256']
        if not isinstance(digest, str) or len(digest) != 64 or any(c not in '0123456789abcdef' for c in digest):
            raise ValueError('Verifier SHA-256 identity required')
    expected = {(name, task, trial) for name in names for task in tasks for trial in range(trials)}
    indexed = {}
    for record in records:
        key = (record['configuration'], record['task_id'], record['trial'])
        if key not in expected or key in indexed or type(record['trial']) is not int:
            raise ValueError('Unexpected or duplicate task/configuration/trial record')
        identity = tasks[key[1]]
        if (record['configuration_sha256'] != configurations[key[0]]
                or record['task_revision'] != identity['revision']
                or record['verifier_sha256'] != identity['verifier_sha256']
                or record['fixture_only'] is not fixture_only):
            raise ValueError('Changed configuration, task, verifier or evidence class')
        if record['outcome'] not in VALID_SCORES and record['outcome'] not in EXCLUDED:
            raise ValueError('Unknown outcome class')
        indexed[key] = record
    if indexed.keys() != expected:
        raise ValueError('Incomplete planned records; missing trials are not silently dropped')
    paired = {name: [] for name in names}
    exclusions = []
    for task_id in sorted(tasks):
        for trial in range(trials):
            rows = [indexed[(name, task_id, trial)] for name in names]
            if any(row['outcome'] not in VALID_SCORES for row in rows):
                exclusions.append({'task_id': task_id, 'trial': trial,
                                   'outcomes': {name: row['outcome'] for name, row in zip(names, rows)}})
                continue
            for name, row in zip(names, rows):
                paired[name].append(Outcome(task_id, trial, VALID_SCORES[row['outcome']],
                                            row['task_revision'], row['verifier_sha256']))
    result = asdict(compare(paired[names[0]], paired[names[1]], min_tasks=min_tasks, margin=margin, confidence=confidence, resamples=resamples, seed=seed)) if paired[names[0]] else None
    # A complete-case statistic remains descriptive when exclusions exist.
    verdict = 'insufficient_evidence' if fixture_only or exclusions or result is None else result['verdict']
    return {'schema': 'paired-controller-report-v0', 'fixture_only': fixture_only,
            'provenance': 'supplied records, not authenticated by this report',
            'planned_pairs': len(tasks) * trials, 'included_pairs': len(paired[names[0]]),
            'excluded_pairs': exclusions, 'configurations': dict(configurations),
            'roles': {'baseline': names[0], 'candidate': names[1]},
            'comparison': result, 'verdict': verdict,
            'abstention_scope': 'Any excluded pair or fixture evidence prevents a verdict in either direction; descriptive failures remain visible.',
            'interpretation': 'Synthetic or excluded evidence cannot clear a regression gate; trusted-process scoring is not adversarial integrity.'}
