import contextlib
from dataclasses import asdict
import io
import json
from pathlib import Path
import tempfile
import unittest

from harnesslab.cli import main
from harnesslab.compare import Outcome, compare


def outcome(task, passed, trial=0, **kw):
    return Outcome(str(task), trial, passed, kw.get('revision', 'abc'),
                   kw.get('verifier', 'sha256-example'))


def fixture(n=24, regressions=20):
    return ([outcome(i, True) for i in range(n)],
            [outcome(i, i >= regressions) for i in range(n)])


class CompareTests(unittest.TestCase):
    def test_regression(self):
        result = compare(*fixture(), resamples=2000)
        self.assertEqual(result.verdict, 'regression')
        self.assertLess(result.upper, -0.05)

    def test_improvement(self):
        a, b = fixture()
        result = compare(b, a, resamples=1000)
        self.assertEqual(result.verdict, 'no_detected_regression')
        self.assertGreater(result.lower, 0)

    def test_tiny_sample_abstains(self):
        self.assertEqual(compare(*fixture(5, 4), resamples=100).verdict,
                         'insufficient_evidence')

    def test_degenerate_sample_abstains(self):
        a, _ = fixture()
        self.assertEqual(compare(a, a, resamples=100).verdict,
                         'insufficient_evidence')

    def test_uncertain_effect_abstains(self):
        a, b = fixture(24, 2)
        self.assertEqual(compare(a, b, resamples=3000).verdict,
                         'insufficient_evidence')

    def test_reproducible_and_order_invariant(self):
        a, b = fixture()
        self.assertEqual(compare(a, b, resamples=500),
                         compare(reversed(a), reversed(b), resamples=500))

    def test_repeated_trials_are_not_independent_tasks(self):
        a, b = fixture(5, 4)
        a = [outcome(x.task_id, x.passed, t) for x in a for t in range(10)]
        b = [outcome(x.task_id, x.passed, t) for x in b for t in range(10)]
        r = compare(a, b, resamples=100)
        self.assertEqual((r.tasks, r.pairs), (5, 50))
        self.assertEqual(r.verdict, 'insufficient_evidence')

    def test_tasks_are_equally_weighted(self):
        a = [outcome('a', True, t) for t in range(10)] + [outcome('b', False)]
        b = [outcome('a', False, t) for t in range(10)] + [outcome('b', True)]
        r = compare(a, b, resamples=100)
        self.assertEqual(r.delta, 0)
        self.assertEqual(r.baseline_rate, 0.5)

    def test_missing_pair(self):
        a, b = fixture()
        with self.assertRaisesRegex(ValueError, 'keys'):
            compare(a, b[:-1])

    def test_duplicates(self):
        a, b = fixture()
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            compare(a + a[:1], b)

    def test_changed_revision_or_verifier(self):
        for change in ({'revision':'other'}, {'verifier':'other'}):
            a, b = fixture()
            b[0] = outcome(0, True, **change)
            with self.assertRaisesRegex(ValueError, 'identity'):
                compare(a, b)

    def test_changed_identity_across_trials(self):
        a = [outcome(0, True), outcome(0, True, 1, revision='changed')]
        with self.assertRaisesRegex(ValueError, 'across trials'):
            compare(a, a)

    def test_empty_rejected(self):
        with self.assertRaisesRegex(ValueError, 'No outcomes'):
            compare([], [])

    def test_invalid_parameters(self):
        a, b = fixture()
        for kwargs in ({'margin':float('nan')}, {'margin':-1}, {'margin':2},
                       {'confidence':0}, {'confidence':1}, {'resamples':99},
                       {'min_tasks':1}, {'seed':False}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                compare(a, b, **kwargs)

    def test_invalid_outcome(self):
        for kwargs in ({'passed':1}, {'passed':'false'}, {'trial':True},
                       {'trial':-1}, {'status':'infrastructure_error'},
                       {'task_id':''}):
            fields = dict(task_id='a', trial=0, passed=True,
                          task_revision='x', verifier_sha256='y')
            fields.update(kwargs)
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                Outcome(**fields)


class CliTests(unittest.TestCase):
    def test_json_and_exit_codes(self):
        with tempfile.TemporaryDirectory() as directory:
            a, b = fixture()
            files = [str(Path(directory)/f'{x}.jsonl') for x in ('a','b')]
            for path, rows in zip(files, (a, b)):
                Path(path).write_text('\n'.join(json.dumps(asdict(r)) for r in rows))
            with contextlib.redirect_stdout(io.StringIO()) as out:
                status = main(['compare', *files, '--resamples', '100'])
            self.assertEqual(status, 1)
            self.assertEqual(json.loads(out.getvalue())['verdict'], 'regression')

    def test_malformed_json_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory)/'bad.jsonl'
            p.write_text('{bad')
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as exc:
                main(['compare', str(p), str(p)])
            self.assertEqual(exc.exception.code, 2)


if __name__ == '__main__':
    unittest.main()
