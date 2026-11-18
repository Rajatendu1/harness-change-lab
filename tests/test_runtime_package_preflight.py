import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tarfile
import tempfile
import shutil
import runpy
from unittest.mock import patch
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('release_preflight', ROOT / 'scripts/check_runtime_package.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
ARCHIVE = ROOT / '1-click-coherent-runtime-r2.tar.gz'
SHA = '8dbe91adb61072b7e6e772a2cf4423d4a632900fc7f3f316c93761353ab0164a'
WORKFLOW = ROOT / '.github/workflows/manual-click-model-free.yml'


class PackagePreflight(unittest.TestCase):
    def repack(self, directory, edit, extra=None):
        with tarfile.open(ARCHIVE) as source:
            content = {m.name: source.extractfile(m).read() for m in source.getmembers()}
        edit(content)
        path = Path(directory) / ARCHIVE.name
        with tarfile.open(path, 'w:gz') as target:
            for name, data in content.items():
                info = tarfile.TarInfo(name)
                info.size = len(data)
                target.addfile(info, io.BytesIO(data))
            if extra:
                target.addfile(extra)
        return path, hashlib.sha256(path.read_bytes()).hexdigest()

    def test_exact_published_archive_rebuilds_both_helpers(self):
        result = module.check_package(ARCHIVE, SHA, WORKFLOW)
        self.assertEqual(result['manifest_files'], 64)
        self.assertFalse(result['runtime_qualified'])
        self.assertEqual(result['provider_calls'], 0)
        self.assertTrue(result['workflow_binding_checked'])

    def test_current_working_tree_helpers_coherent(self):
        result = module.check_working_tree(ROOT)
        self.assertEqual(result['status'], 'offline_working_tree_helpers_coherent')
        self.assertFalse(result['runtime_qualified'])

    def test_working_tree_actual_assembly_reaches_context_validation(self):
        assemble = runpy.run_path(str(ROOT / 'proposals/click-runtime/run_diagnostic.py'))['assemble']
        reached = []
        def context(*args, **kwargs):
            reached.append(kwargs['helper_manifest'])
        with tempfile.TemporaryDirectory() as d, patch.dict(assemble.__globals__, {
                'fetch': lambda *args, **kwargs: b'public-artifact-stub',
                'validate_click_context': context}):
            assemble(Path(d))
        self.assertEqual(len(reached), 1)
        self.assertEqual(reached[0], json.loads((ROOT / 'proposals/click-runtime/helper-manifest.json').read_text()))
        # Public inputs/context verification are stubbed in this local interface
        # test. Actual helper generation and metadata comparisons are not.

    def test_stale_working_tree_manifest_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            shutil.copytree(ROOT / 'harnesslab', root / 'harnesslab', ignore=shutil.ignore_patterns('__pycache__'))
            target = root / 'proposals/click-runtime'
            target.mkdir(parents=True)
            shutil.copyfile(ROOT / 'proposals/click-runtime/helper-manifest.json', target / 'helper-manifest.json')
            with (root / 'harnesslab/compare.py').open('ab') as stream:
                stream.write(b'\n# stale-manifest regression\n')
            with self.assertRaisesRegex(ValueError, 'Working-tree helper rebuild mismatch'):
                module.check_working_tree(root)

    def test_workflow_binding_without_enforcement_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            workflow = Path(d) / 'workflow.yml'
            workflow.write_text(WORKFLOW.read_text().replace('| sha256sum --check --strict', '| cat'))
            with self.assertRaisesRegex(ValueError, 'reviewed enforcing'):
                module.check_package(ARCHIVE, SHA, workflow)

    def test_workflow_automatic_trigger_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            workflow = Path(d) / 'workflow.yml'
            workflow.write_text(WORKFLOW.read_text().replace('  workflow_dispatch:', '  push:'))
            with self.assertRaisesRegex(ValueError, 'reviewed enforcing'):
                module.check_package(ARCHIVE, SHA, workflow)

    def test_wrong_outer_sha_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Archive SHA256'):
            module.check_package(ARCHIVE, '0' * 64)

    def test_workflow_filename_mismatch_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            workflow = Path(d) / 'workflow.yml'
            workflow.write_text(WORKFLOW.read_text().replace(ARCHIVE.name, 'wrong.tar.gz'))
            with self.assertRaisesRegex(ValueError, 'exact archive filename'):
                module.check_package(ARCHIVE, SHA, workflow)

    def test_source_change_with_stale_outer_manifest_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            path, sha = self.repack(d, lambda c: c.update({'harnesslab/compare.py': c['harnesslab/compare.py'] + b'\n# changed\n'}))
            with self.assertRaisesRegex(ValueError, 'Manifest content'):
                module.check_package(path, sha)

    def test_source_change_with_updated_outer_but_stale_helper_rejected(self):
        def edit(content):
            content['harnesslab/compare.py'] += b'\n# changed\n'
            manifest = json.loads(content['runtime-subset-manifest.json'])
            manifest['files']['harnesslab/compare.py'] = hashlib.sha256(content['harnesslab/compare.py']).hexdigest()
            content['runtime-subset-manifest.json'] = json.dumps(manifest).encode()
        with tempfile.TemporaryDirectory() as d:
            path, sha = self.repack(d, edit)
            with self.assertRaisesRegex(ValueError, 'Helper rebuild mismatch'):
                module.check_package(path, sha)

    def test_extra_unmanifested_file_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            path, sha = self.repack(d, lambda c: c.update({'unexpected.txt': b'no'}))
            with self.assertRaisesRegex(ValueError, 'file set'):
                module.check_package(path, sha)

    def test_symlink_rejected(self):
        info = tarfile.TarInfo('symlink')
        info.type = tarfile.SYMTYPE
        info.linkname = '/tmp/outside'
        with tempfile.TemporaryDirectory() as d:
            path, sha = self.repack(d, lambda c: None, info)
            with self.assertRaisesRegex(ValueError, 'Unsafe'):
                module.check_package(path, sha)

    def test_duplicate_rejected(self):
        info = tarfile.TarInfo('LICENSE')
        with tempfile.TemporaryDirectory() as d:
            path, sha = self.repack(d, lambda c: None, info)
            with self.assertRaisesRegex(ValueError, 'duplicate'):
                module.check_package(path, sha)

    def test_traversal_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            path, sha = self.repack(d, lambda c: c.update({'../escape': b'no'}))
            with self.assertRaisesRegex(ValueError, 'Unsafe'):
                module.check_package(path, sha)


if __name__ == '__main__':
    unittest.main()
