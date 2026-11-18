import copy
import hashlib
from pathlib import Path
import tempfile
import unittest
from harnesslab.flask_image_plan import requirements, verifier_recipe, validate_verifier_context

BASE = 'python@sha256:' + 'a' * 64


class FlaskImagePlanTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(); self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.wheel = b'unit test wheel placeholder, not installable'
        self.helper = b'unit test helper placeholder, not installable'
        self.manifest = {'artifacts': [{'name':'pytest','version':'8.3.5','filename':'pytest-8.3.5-py3-none-any.whl',
                         'sha256':hashlib.sha256(self.wheel).hexdigest(),'bytes':len(self.wheel)}]}
        self.helper_manifest = {'role':'verifier','filename':'harness_fixture_helpers-0.0.1-py3-none-any.whl',
                                'sha256':hashlib.sha256(self.helper).hexdigest()}
        self.write_context()

    def write_context(self):
        values = {'Dockerfile':verifier_recipe(BASE).encode(), 'verifier.hashes.txt':requirements(self.manifest),
                  'verifier-helper.hashes.txt':('harness-fixture-helpers==0.0.1 --hash=sha256:' + self.helper_manifest['sha256'] + '\n').encode(),
                  'verifier-helper/' + self.helper_manifest['filename']:self.helper,
                  'verifier-wheelhouse/' + self.manifest['artifacts'][0]['filename']:self.wheel}
        for name, value in values.items():
            p = self.root / name; p.parent.mkdir(exist_ok=True,parents=True); p.write_bytes(value)

    def validate(self):
        return validate_verifier_context(self.root,base_reference=BASE,dependency_manifest=self.manifest,helper_manifest=self.helper_manifest)

    def test_prepared_only(self):
        result = self.validate(); self.assertEqual(result['files'],5)
        self.assertFalse(result['image_built']); self.assertFalse(result['base_runtime_verified'])
        self.assertFalse(result['adversarial_integrity_verified'])

    def test_immutable_recipe_required(self):
        for value in ('python:latest', 'python@sha256:'+'g'*64, BASE+'\nRUN echo no', None):
            with self.assertRaises(ValueError): verifier_recipe(value)

    def test_no_online_or_install_hooks_in_recipe(self):
        text = verifier_recipe(BASE)
        self.assertEqual(text.count('RUN --network=none'),2)
        self.assertIn('--no-index',text); self.assertIn('--only-binary=:all:',text)
        self.assertNotIn('apt-get',text); self.assertNotIn('COPY .',text)

    def test_extra_file_rejected(self):
        (self.root/'credential.txt').write_bytes(b'do not include')
        with self.assertRaises(ValueError): self.validate()

    def test_missing_file_rejected(self):
        (self.root/'verifier.hashes.txt').unlink()
        with self.assertRaises(ValueError): self.validate()

    def test_changed_file_rejected(self):
        (self.root/'Dockerfile').write_bytes(b'FROM something-else')
        with self.assertRaises(ValueError): self.validate()

    def test_symlink_rejected(self):
        (self.root/'extra').symlink_to('/tmp')
        with self.assertRaises(ValueError): self.validate()

    def test_wrong_manifest_size_rejected(self):
        self.manifest['artifacts'][0]['bytes'] += 1
        with self.assertRaises(ValueError): self.validate()

    def test_non_verifier_helper_rejected(self):
        self.helper_manifest['role'] = 'agent'
        with self.assertRaises(ValueError): self.validate()

    def test_helper_name_fixed(self):
        self.helper_manifest['filename'] = '../helper.whl'
        with self.assertRaises(ValueError): self.validate()

    def test_manifest_value_injection_rejected(self):
        for field, value in [('filename','../escape.whl'),('filename','wheel.whl\nRUN echo no'),
                             ('name','pytest\n--index-url=bad'),('version','8.3.5 --no-deps'),
                             ('sha256','f'*63),('bytes',True)]:
            manifest = copy.deepcopy(self.manifest); manifest['artifacts'][0][field] = value
            with self.subTest(field=field):
                with self.assertRaises(ValueError): requirements(manifest)

    def test_duplicate_normalized_name_rejected(self):
        manifest = copy.deepcopy(self.manifest)
        manifest['artifacts'][0]['name'] = 'some-name'
        extra = dict(manifest['artifacts'][0],name='Some_Name',filename='other.whl')
        manifest['artifacts'].append(extra)
        with self.assertRaises(ValueError): requirements(manifest)

    def test_manifest_boundaries(self):
        for manifest in (None, {}, {'artifacts':[]}, {'artifacts':[None]}):
            with self.assertRaises(ValueError): requirements(manifest)


if __name__ == '__main__': unittest.main()
