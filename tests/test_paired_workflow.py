import copy
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from harnesslab.experiment_journal import ExperimentJournal
from scripts.paired_workflow import report_text, observed_tokens, observed_duration, main


class PairedWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.directory = Path(self.tmp.name) / 'journal'
        self.plan = {'tasks': {'fixture': {'revision': 'r1', 'verifier_sha256': 'c' * 64}},
            'configurations': {'baseline': 'a' * 64, 'candidate': 'b' * 64},
            'trials': 1, 'fixture_only': True, 'execution_authority': 'none',
            'configuration_order': ['baseline', 'candidate'],
            'policy': {'min_tasks': 20, 'margin': 0.05, 'confidence': 0.95, 'resamples': 100, 'seed': 0}}
        self.records = [{'task_id': 'fixture', 'task_revision': 'r1', 'verifier_sha256': 'c' * 64,
            'configuration': name, 'configuration_sha256': digest, 'trial': 0,
            'fixture_only': True, 'outcome': 'verifier_fail'} for name, digest in self.plan['configurations'].items()]

    def save(self, complete=True):
        journal = ExperimentJournal(self.directory, self.plan)
        for record in self.records[:2 if complete else 1]:
            journal.append(record)
        if complete:
            journal.finalize()

    def test_review_unknown_observations_never_become_zero(self):
        self.save()
        text = report_text(self.directory)
        self.assertIn('SYNTHETIC CANNED FIXTURE', text)
        self.assertIn('insufficient_evidence', text)
        self.assertIn('edit_seconds=unknown', text)
        self.assertIn('canned_fixture_tokens=unknown', text)
        self.assertIn('Cost: not computed', text)

    def test_excluded_pair_remains_visible(self):
        self.records[0]['outcome'] = 'verifier_setup_error'
        self.save()
        text = report_text(self.directory)
        self.assertIn('0 included / 1 planned; 1 excluded', text)
        self.assertIn('verifier_setup_error', text)

    def test_partial_journal_has_no_valid_review(self):
        self.save(complete=False)
        with self.assertRaises(ValueError):
            report_text(self.directory)

    def test_tampered_record_refused(self):
        self.save()
        path = self.directory / 'records.jsonl'
        path.write_text(path.read_text().replace('verifier_fail', 'source_patch_verifier_pass', 1))
        with self.assertRaises(ValueError):
            report_text(self.directory)

    def test_unknown_usage_and_invalid_usage_not_zero(self):
        self.assertIsNone(observed_tokens({}))
        self.assertIsNone(observed_tokens({'execution': {'provider_attempts': 0, 'provider_usage': []}}))
        self.assertIsNone(observed_tokens({'execution': {'provider_attempts': 1, 'provider_usage': [{}]}}))

    def test_valid_canned_usage_is_reported_only_as_fixture(self):
        usage = {'number': 1, 'outcome': 'returned', 'usage_status': 'provider_reported',
                 'prompt_tokens': 1, 'completion_tokens': 1, 'total_tokens': 2}
        for record in self.records:
            record['execution'] = {'elapsed_s': 1.5, 'provider_attempts': 1, 'provider_usage': [usage]}
        self.save()
        text = report_text(self.directory)
        self.assertIn('edit_seconds=1.500 canned_fixture_tokens=2', text)
        self.assertIn('invented transport plumbing values', text)
        self.assertNotIn('$0', text)

    def test_bad_duration_refused(self):
        for value in (True, -1, float('nan'), float('inf')):
            with self.assertRaises(ValueError):
                observed_duration({'execution': {'elapsed_s': value}})

    def test_review_launches_no_child_and_abstains(self):
        self.save()
        with patch('scripts.paired_workflow.subprocess.run', side_effect=AssertionError('unexpected child')), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(['review', str(self.directory)]), 3)

    def test_unsafe_identifiers_not_echoed(self):
        task = self.plan['tasks'].pop('fixture')
        self.plan['tasks']['unsafe\ntext'] = task
        for record in self.records:
            record['task_id'] = 'unsafe\ntext'
        self.save()
        with self.assertRaises(ValueError):
            report_text(self.directory)

    def test_fixture_existing_output_never_reused(self):
        self.directory.mkdir()
        with tempfile.TemporaryDirectory() as runtime:
            root = Path(runtime)
            for role in ('agent', 'verifier'):
                path = root / role / 'bin/python'
                path.parent.mkdir(parents=True)
                path.touch()
            with patch('scripts.paired_workflow.subprocess.run', side_effect=AssertionError('unexpected child')), contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as error:
                    main(['fixture', '--runtime-root', runtime, '--output-directory', str(self.directory)])
            self.assertEqual(error.exception.code, 2)
