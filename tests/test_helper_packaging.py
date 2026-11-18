import base64
import csv
import hashlib
import io
from pathlib import Path
import tempfile
import unittest
import zipfile

from harnesslab.helper_packaging import helper_wheel,DIST


class HelperPackagingTests(unittest.TestCase):
    def test_reproducible_source_only_archive_and_valid_record(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);package=root/'harnesslab';package.mkdir()
            (package/'__init__.py').write_bytes(b'')
            (package/'fixture.py').write_bytes(b'x=1\n')
            (root/'private-dummy').write_bytes(b'must-not-package')
            (package/'__pycache__').mkdir();(package/'__pycache__/compiled.pyc').write_bytes(b'ignored')
            raw,manifest=helper_wheel(root)
            again,second=helper_wheel(root)
            self.assertEqual(raw,again);self.assertEqual(manifest,second)
            with zipfile.ZipFile(io.BytesIO(raw)) as archive:
                self.assertEqual(len(archive.namelist()),5)
                self.assertNotIn(b'must-not-package',raw)
                for name,digest,size in csv.reader(io.StringIO(archive.read(DIST+'/RECORD').decode())):
                    if name.endswith('/RECORD'):continue
                    data=archive.read(name)
                    self.assertEqual(str(len(data)),size)
                    self.assertEqual('sha256='+base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b'=').decode(),digest)
            self.assertFalse(manifest['build_hooks_executed'])
            self.assertFalse(manifest['runtime_verified'])

    def test_source_change_changes_content_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            package=Path(directory)/'harnesslab';package.mkdir();(package/'__init__.py').write_bytes(b'')
            before=helper_wheel(directory)[1]['sha256']
            (package/'new.py').write_bytes(b'x=2')
            self.assertNotEqual(before,helper_wheel(directory)[1]['sha256'])

    def test_symlink_inputs_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'harnesslab').mkdir();(root/'harnesslab/__init__.py').write_bytes(b'')
            (root/'outside').write_bytes(b'private-dummy')
            (root/'harnesslab/link.py').symlink_to(root/'outside')
            with self.assertRaises(ValueError):helper_wheel(root)

    def test_agent_artifact_excludes_hidden_test_and_scorer_sources(self):
        with tempfile.TemporaryDirectory() as directory:
            package=Path(directory)/'harnesslab';package.mkdir();(package/'__init__.py').write_bytes(b'')
            for name in ('fixed_hidden_test.py','docker_verifier_child.py','fixed_fixture_score.py','protected_score.py',
                         'click_verifier_child.py','click_docker_score.py','click_pilot.py','click_diagnostic.py','evidence_intake.py',
                         'flask_preparation.py','flask_verifier_child.py','flask_docker_score.py','flask_task.py','flask_image_plan.py'):
                (package/name).write_bytes(b'hidden-proof-sentinel')
            agent,_=helper_wheel(directory,role='agent')
            verifier,_=helper_wheel(directory,role='verifier')
            with zipfile.ZipFile(io.BytesIO(agent)) as archive:
                self.assertFalse(any('fixed_hidden_test' in name or 'protected_score' in name or 'click_verifier' in name
                                     or 'click_docker_score' in name or 'click_pilot' in name or 'click_diagnostic' in name
                                     or 'evidence_intake' in name or '/flask_' in name for name in archive.namelist()))
            with zipfile.ZipFile(io.BytesIO(verifier)) as archive:
                self.assertEqual(archive.read('harnesslab/fixed_hidden_test.py'),b'hidden-proof-sentinel')
