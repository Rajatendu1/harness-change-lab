#!/usr/bin/env python3
"""Offline release preflight. No downloads, builds, providers or workflow dispatch.

Checks an explicitly selected reviewed archive, not arbitrary repository source.
A pass proves package coherence only, never runtime or model qualification.
"""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import runpy
import tarfile
import tempfile


# Exact reviewed no-key workflow template, with only filename and digest variable.
# This is a deliberately narrow allowlist, not a general YAML security parser.
WORKFLOW_TEMPLATE_SHA256 = '1af376cfdd1fbd53b5f61ad299733a3edb49b8d9689b7d347384e2df27c150a0'


def check_working_tree(root):
    """Fail on stale current-source helper metadata, independent of old releases."""
    root = Path(root).resolve(strict=True)
    builder = runpy.run_path(str(root / 'harnesslab/helper_packaging.py'))['helper_wheel']
    expected = json.loads((root / 'proposals/click-runtime/helper-manifest.json').read_text())
    result = {}
    for role in ('agent', 'verifier'):
        first, metadata = builder(root, role=role)
        second, repeated = builder(root, role=role)
        if first != second or metadata != repeated or metadata != expected[role]:
            raise ValueError('Working-tree helper rebuild mismatch: ' + role)
        result[role] = metadata['sha256']
    return {'status': 'offline_working_tree_helpers_coherent', 'helper_sha256': result,
            'runtime_qualified': False, 'provider_calls': 0}


def check_package(archive_path, expected_sha256, workflow_path=None):
    archive_path = Path(archive_path)
    if not re.fullmatch('[a-f0-9]{64}', expected_sha256):
        raise ValueError('Expected lowercase SHA256')
    if archive_path.stat().st_size > 8 * 1024 * 1024:
        raise ValueError('Archive transfer limit exceeded')
    raw = archive_path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected_sha256:
        raise ValueError('Archive SHA256 mismatch')
    if workflow_path is not None:
        workflow = Path(workflow_path).read_text()
        binding = expected_sha256 + '  ' + archive_path.name
        if workflow.count(binding) != 1:
            raise ValueError('Workflow must bind exact archive filename and SHA256 once')
        if workflow.count('tar -xzf ' + archive_path.name + ' ') != 1:
            raise ValueError('Workflow extraction filename mismatch')
        normalized = workflow.replace(expected_sha256, 'ARCHIVE_SHA256').replace(archive_path.name, 'ARCHIVE_FILENAME')
        if hashlib.sha256(normalized.encode()).hexdigest() != WORKFLOW_TEMPLATE_SHA256:
            raise ValueError('Workflow differs from reviewed enforcing no-key template')
    with tarfile.open(archive_path, 'r:gz') as source:
        members = source.getmembers()
        if not 1 <= len(members) <= 256:
            raise ValueError('Archive member limit exceeded')
        names = set()
        content = {}
        total = 0
        for item in members:
            name = item.name
            path = PurePosixPath(name)
            if (not item.isfile() or path.is_absolute() or '..' in path.parts
                    or str(path) != name or name in names):
                raise ValueError('Unsafe or duplicate archive member')
            names.add(name)
            total += item.size
            if item.size > 1024 * 1024 or total > 16 * 1024 * 1024:
                raise ValueError('Expanded archive limit exceeded')
            content[name] = source.extractfile(item).read()
    manifest_name = 'runtime-subset-manifest.json'
    manifest = json.loads(content[manifest_name])['files']
    if not isinstance(manifest, dict) or names != set(manifest) | {manifest_name}:
        raise ValueError('Manifest file set mismatch')
    for name, digest in manifest.items():
        if hashlib.sha256(content[name]).hexdigest() != digest:
            raise ValueError('Manifest content mismatch')
    # Rebuild real helper wheels from the selected release's source. Never use
    # latest main: changing source invalidates the helper and outer manifests.
    with tempfile.TemporaryDirectory(prefix='release-preflight-') as directory:
        root = Path(directory)
        for name, data in content.items():
            target = root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        builder = runpy.run_path(str(root / 'harnesslab/helper_packaging.py'))['helper_wheel']
        expected = json.loads(content['proposals/click-runtime/helper-manifest.json'])
        helper_hashes = {}
        for role in ('agent', 'verifier'):
            first, metadata = builder(root, role=role)
            second, repeated = builder(root, role=role)
            if first != second or metadata != repeated or metadata != expected[role]:
                raise ValueError('Helper rebuild mismatch: ' + role)
            helper_hashes[role] = metadata['sha256']
    return {'status': 'offline_package_coherent', 'runtime_qualified': False,
            'evidence_class': 'offline_exact_archive_and_helper_rebuild',
            'archive_sha256': expected_sha256, 'manifest_files': len(manifest),
            'helper_sha256': helper_hashes, 'workflow_binding_checked': workflow_path is not None,
            'downloads': 0, 'container_builds': 0, 'provider_calls': 0,
            'interpretation': 'Package consistency only. No runtime, authorization or model efficacy claim.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    parser.add_argument('--sha256', required=True)
    parser.add_argument('--workflow', type=Path)
    parser.add_argument('--working-tree', type=Path, help='Also check current-source helper coherence, separately from selected release')
    args = parser.parse_args()
    try:
        result = check_package(args.archive, args.sha256, args.workflow)
        if args.working_tree is not None:
            result['working_tree'] = check_working_tree(args.working_tree)
    except (ValueError, KeyError, OSError, tarfile.TarError) as exc:
        parser.exit(2, 'Release preflight failed: ' + str(exc) + '\n')
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main()
