"""Simulated lifecycle tests, no Docker/model execution."""
import io
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

from harnesslab import flask_docker_score as mapping, flask_verifier_child as child
from harnesslab.flask_task import BASE_NAMES, EDITABLE
from harnesslab.flask_preparation import MAX_REPORT
from test_click_docker_score import ScoreAdapter

BASE = {name:b'base' for name in BASE_NAMES}
CANDIDATE = dict(BASE); CANDIDATE[EDITABLE[0]] = b'changed'
TEST = b'controller protected placeholder'
ROW = {'status':'flask_verifier_result','passed':True,'tests':1,'failures':0,'skipped':0,'adversarial_integrity_verified':False}
XML = b'<testsuites><testsuite tests="1" failures="0" errors="0" skipped="0"><testcase name="test_dotted_name_not_allowed" classname=".controller-hidden.test_selected"/></testsuite></testsuites>'


class FlaskMappingTests(unittest.TestCase):
    def invoke(self, *, candidate=CANDIDATE, reference_mode=False, removed=True, row=None):
        adapter = ScoreAdapter(removed=removed, row=ROW if row is None else row)
        with patch.object(mapping,'validate_base',return_value=True), \
             patch.object(mapping,'TEST_HASH',hashlib.sha256(TEST).hexdigest()), \
             patch.object(mapping,'validate_score_input',return_value=True):
            result = mapping.score_flask(candidate,base=BASE,protected_test=TEST,image_policy='reviewed-placeholder',
                       adapter_factory=lambda **kwargs:adapter,reference_mode=reference_mode)
        return result, adapter

    def test_fresh_verifier_stdin_mapping(self):
        result, adapter = self.invoke()
        self.assertEqual(result['outcome'],'source_patch_verifier_pass')
        calls = [x for x in adapter.calls if isinstance(x,tuple)]
        self.assertEqual(len(calls),1)
        args,kwargs = calls[0]
        self.assertEqual(args[-1],'harnesslab.flask_verifier_child')
        self.assertIn(TEST,kwargs['input_data']); self.assertIn('-i',args)
        self.assertEqual(adapter.calls[-1],'remove')
        self.assertFalse(result['runtime_qualified'])

    def test_unchanged_not_called(self):
        result, adapter = self.invoke(candidate=BASE)
        self.assertEqual(result['status'],'no_source_change'); self.assertEqual(adapter.calls,[])

    def test_reference_separate(self):
        result, _ = self.invoke(candidate=BASE,reference_mode=True)
        self.assertEqual(result['outcome'],'reference_verifier_pass')

    def test_outside_editable_not_called(self):
        candidate = dict(CANDIDATE); candidate['LICENSE.rst'] = b'bad'
        result, adapter = self.invoke(candidate=candidate)
        self.assertEqual(result['status'],'invalid_patch'); self.assertEqual(adapter.calls,[])

    def test_cleanup_required(self):
        result, _ = self.invoke(removed=False)
        self.assertEqual(result['status'],'verifier_cleanup_unconfirmed'); self.assertNotIn('outcome',result)

    def test_bad_result_excluded(self):
        for field,value in [('tests',True),('failures',2),('passed',False),('skipped',1),('status','click_verifier_result')]:
            row = dict(ROW);row[field] = value
            result, adapter = self.invoke(row=row)
            self.assertEqual(result['status'],'verifier_setup_or_execution_error')
            self.assertEqual(adapter.calls[-1],'remove')

    def test_duplicate_json_rejected(self):
        raw=json.dumps(ROW).encode().replace(b'"passed": true',b'"passed": false, "passed": true')
        with self.assertRaises(ValueError): mapping.validate_score_result(raw)

    def test_bad_test_prevents_container_creation(self):
        with patch.object(mapping,'validate_base',return_value=True):
            factory = unittest.mock.Mock()
            with self.assertRaises(ValueError):
                mapping.score_flask(CANDIDATE,base=BASE,protected_test=TEST,image_policy=None,adapter_factory=factory)
            factory.assert_not_called()


class FlaskChildTests(unittest.TestCase):
    def test_identity_guard_first(self):
        with patch.object(child,'guard',side_effect=ValueError('host forbidden')), patch.object(child,'validate_score_input') as validate:
            with self.assertRaises(ValueError): child.score()
            validate.assert_not_called()

    def test_bad_input_never_imported(self):
        with patch.object(child,'guard'), patch.object(child.importlib.metadata,'version',return_value='8.3.5'), \
             patch.object(child.sys,'stdin',SimpleNamespace(buffer=io.BytesIO(b'invalid'))), \
             patch.object(child,'import_sources') as importer:
            with self.assertRaises(ValueError): child.score()
            importer.assert_not_called()

    def test_report_regular_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'report.xml';path.write_bytes(XML)
            self.assertEqual(child.read_report(path),XML)

    def test_report_links_refused(self):
        import os
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);target=root/'report.xml';target.write_bytes(XML)
            link=root/'link';link.symlink_to(target)
            with self.assertRaises(OSError): child.read_report(link)
            hard=root/'hard';os.link(target,hard)
            with self.assertRaises(ValueError): child.read_report(hard)

    def test_report_size_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'report.xml';path.write_bytes(b'x'*(MAX_REPORT+1))
            with self.assertRaises(ValueError): child.read_report(path)

    def test_child_launch_uses_fixed_command_and_hidden_test(self):
        with tempfile.TemporaryDirectory() as directory:
            report=Path(directory)/'report.xml'
            def run(args,**kwargs):
                self.assertEqual(args[1:3],['-I','-c'])
                self.assertIn('/work/.controller-hidden/test_selected.py::test_dotted_name_not_allowed',args[-1])
                self.assertEqual(kwargs['timeout'],20)
                self.assertEqual(kwargs['env']['PYTEST_DISABLE_PLUGIN_AUTOLOAD'],'1')
                report.write_bytes(XML)
                return SimpleNamespace(returncode=0)
            with patch.object(child,'guard'), patch.object(child,'REPORT',report), \
                 patch.object(child.importlib.metadata,'version',return_value='8.3.5'), \
                 patch.object(child.sys,'stdin',SimpleNamespace(buffer=io.BytesIO(b'placeholder'))), \
                 patch.object(child,'validate_score_input'), patch.object(child,'import_sources'), \
                 patch.object(child.subprocess,'run',side_effect=run):
                result=child.score()
                self.assertEqual(result,ROW)

    def test_child_errors_do_not_print_details(self):
        output=io.StringIO()
        with patch.object(child,'score',side_effect=ValueError('sensitive outside content')),patch('sys.stdout',output):
            self.assertEqual(child.main(),3)
        self.assertEqual(output.getvalue(),'')


if __name__=='__main__':unittest.main()
