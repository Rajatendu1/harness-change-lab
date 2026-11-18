import hashlib
import io
import zipfile
import unittest
from unittest.mock import patch
from harnesslab import flask_preparation as prep, flask_task as task
from harnesslab.source_bundle import pack_sources


def report(*, name=prep.EXPECTED_TEST, classname='test_selected', failures='0', errors='0', skipped='0', tests='1', children=''):
    return (f'<testsuites><testsuite tests="{tests}" failures="{failures}" errors="{errors}" skipped="{skipped}">'
            f'<testcase classname="{classname}" name="{name}">{children}</testcase>'
            '</testsuite></testsuites>').encode()


class FlaskPreparationTests(unittest.TestCase):
    def setUp(self):
        self.base = {name: name.encode() for name in task.BASE_NAMES}
        self.hashes = {name: hashlib.sha256(data).hexdigest() for name, data in self.base.items()}
        self.hidden = b'controller supplied placeholder, not an upstream test'
        self.sources = {**self.base, prep.TEST_NAME: self.hidden}
        self.patches = [patch.object(task, 'BASE_HASHES', self.hashes),
                        patch.object(prep, 'BASE_HASHES', self.hashes),
                        patch.object(prep, 'TEST_HASH', hashlib.sha256(self.hidden).hexdigest())]
        for p in self.patches: p.start(); self.addCleanup(p.stop)

    def test_exact_base(self):
        self.assertTrue(task.validate_base(self.base))

    def test_modified_base_rejected(self):
        for mode in ('changed', 'missing', 'extra'):
            with self.subTest(mode=mode):
                sources = dict(self.base)
                if mode == 'changed': sources[task.EDITABLE[0]] = b'edited'
                elif mode == 'missing': sources.pop(task.EDITABLE[0])
                else: sources['extra.py'] = b'x'
                with self.assertRaises(ValueError): task.validate_base(sources)

    def test_score_accepts_only_editable_replacement(self):
        self.sources[task.EDITABLE[0]] = b'edited'
        self.assertEqual(prep.validate_score_input(pack_sources(self.sources)), self.sources)

    def test_changed_uneditable_rejected(self):
        self.sources['src/flask/app.py'] = b'edited'
        with self.assertRaises(ValueError): prep.validate_score_input(pack_sources(self.sources))

    def test_changed_test_rejected(self):
        self.sources[prep.TEST_NAME] = b'forged'
        with self.assertRaises(ValueError): prep.validate_score_input(pack_sources(self.sources))

    def test_missing_test_rejected(self):
        with self.assertRaises(ValueError): prep.validate_score_input(pack_sources(self.base))

    def test_extra_source_rejected(self):
        self.sources['conftest.py'] = b'pytest hook'
        with self.assertRaises(ValueError): prep.validate_score_input(pack_sources(self.sources))

    def test_pass_report(self):
        result = prep.parse_protected_result(report(), 0)
        self.assertTrue(result['passed']); self.assertFalse(result['adversarial_integrity_verified'])

    def test_failure_report(self):
        result = prep.parse_protected_result(report(failures='1', children='<failure/>'), 1)
        self.assertFalse(result['passed']); self.assertEqual(result['failures'], 1)

    def test_wrong_collection_rejected(self):
        for kwargs in ({'name':'other'}, {'classname':'other'}, {'tests':'2'}, {'errors':'1'}, {'skipped':'1'},
                       {'children':'<skipped/>'}, {'children':'<error/>'}, {'children':'<testcase/>'}):
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(ValueError): prep.parse_protected_result(report(**kwargs), 0)

    def test_exit_mismatches_rejected(self):
        for xml, code in [(report(), 1), (report(failures='1',children='<failure/>'), 0),
                          (report(), 2), (report(), True), (report(), -9)]:
            with self.subTest(code=code):
                with self.assertRaises(ValueError): prep.parse_protected_result(xml, code)

    def test_invalid_report_rejected(self):
        for xml in (b'', b'<invalid', b'<testcase/>', b'x'*(prep.MAX_REPORT+1),
                    b'<!DOCTYPE r><testsuites/>', report(children='<failure/><failure/>', failures='2')):
            with self.assertRaises(ValueError): prep.parse_protected_result(xml, 0)

    def test_duplicate_case_rejected(self):
        xml = report().replace(b'</testsuite>', b'<testcase name="test_dotted_name_not_allowed" classname="test_selected"/></testsuite>')
        with self.assertRaises(ValueError): prep.parse_protected_result(xml, 0)

    def test_multiple_suites_rejected(self):
        xml = report().replace(b'</testsuites>', b'<testsuite/></testsuites>')
        with self.assertRaises(ValueError): prep.parse_protected_result(xml, 0)

    def test_scorer_contract_not_in_editing_helper(self):
        from pathlib import Path
        from harnesslab.helper_packaging import helper_wheel
        root = Path(__file__).resolve().parents[1]
        agent, _ = helper_wheel(root, role='agent')
        verifier, _ = helper_wheel(root, role='verifier')
        with zipfile.ZipFile(io.BytesIO(agent)) as archive:
            self.assertNotIn('harnesslab/flask_preparation.py', archive.namelist())
        with zipfile.ZipFile(io.BytesIO(verifier)) as archive:
            self.assertIn('harnesslab/flask_preparation.py', archive.namelist())

    def test_expected_task_scope(self):
        self.assertEqual(task.EDITABLE, ('src/flask/blueprints.py',))
        self.assertEqual(len(task.BASE_NAMES), 25)
        self.assertNotIn(prep.TEST_NAME, task.BASE_NAMES)
        self.assertEqual(task.TASK_ID, 'prepared-flask-blueprint-dotted-name')


if __name__ == '__main__': unittest.main()
