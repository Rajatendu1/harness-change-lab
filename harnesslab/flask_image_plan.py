"""Separate Flask verifier build-context preparation. Never invokes a build.

A digest string is not proof that a base image is available or qualified.
Callers supply independently reviewed metadata and exact dependency manifests.
"""
import hashlib
from pathlib import Path
import re

MAX_CONTEXT = 64 * 1024 * 1024


def verifier_recipe(base_reference):
    if not isinstance(base_reference, str) or not re.fullmatch(r'python@sha256:[a-f0-9]{64}', base_reference):
        raise ValueError('Expected immutable Python base reference')
    return f'''FROM {base_reference} AS flask-verifier
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 PIP_NO_CACHE_DIR=1
COPY verifier-wheelhouse/ /opt/wheelhouse/
COPY verifier.hashes.txt /opt/locks/runtime.txt
COPY verifier-helper/ /opt/helper-wheelhouse/
COPY verifier-helper.hashes.txt /opt/locks/helper.txt
RUN --network=none python3 -m venv /opt/verifier && /opt/verifier/bin/python -m pip install --no-index --find-links=/opt/wheelhouse --only-binary=:all: --require-hashes -r /opt/locks/runtime.txt && /opt/verifier/bin/python -m pip install --no-index --no-deps --find-links=/opt/helper-wheelhouse --only-binary=:all: --require-hashes -r /opt/locks/helper.txt && /opt/verifier/bin/python -m pip check
RUN --network=none /opt/verifier/bin/python -I -c "import sys; import importlib.metadata as m; import harnesslab.flask_preparation; assert sys.version_info[:2]==(3,10); assert m.version('pytest')=='8.3.5'"
ENV PATH=/opt/verifier/bin:/usr/local/bin:/usr/bin:/bin
WORKDIR /work
'''


def digest(value):
    if not isinstance(value, str) or not re.fullmatch(r'[a-f0-9]{64}', value):
        raise ValueError('Expected SHA256 hex digest')
    return value


def requirements(manifest):
    """Return exact unambiguous requirement lines, not pip argument text."""
    if not isinstance(manifest, dict) or not isinstance(manifest.get('artifacts'), list):
        raise ValueError('Expected reviewed artifact manifest')
    items = manifest['artifacts']
    if not 1 <= len(items) <= 64:
        raise ValueError('Expected bounded dependency list')
    seen, filenames, lines = set(), set(), []
    for item in sorted(items, key=lambda x: x.get('name', '') if isinstance(x, dict) else ''):
        if not isinstance(item, dict): raise ValueError('Expected artifact record')
        name, version, filename = (item.get(k) for k in ('name', 'version', 'filename'))
        if not isinstance(name, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,100}', name):
            raise ValueError('Invalid dependency name')
        if not isinstance(version, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.+!]{0,100}', version):
            raise ValueError('Invalid dependency version')
        if not isinstance(filename, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.+!-]{0,240}\.whl', filename):
            raise ValueError('Expected safe wheel filename')
        canonical = re.sub(r'[-_.]+', '-', name).lower()
        if canonical in seen or filename in filenames:
            raise ValueError('Duplicate dependency or artifact')
        if type(item.get('bytes')) is not int or not 0 < item['bytes'] <= MAX_CONTEXT:
            raise ValueError('Expected bounded wheel size')
        seen.add(canonical); filenames.add(filename)
        lines.append(name + '==' + version + ' --hash=sha256:' + digest(item.get('sha256')) + '\n')
    return ''.join(lines).encode()


def validate_verifier_context(context, *, base_reference, dependency_manifest, helper_manifest):
    """Check supplied bytes against reviewed manifests, not provenance or safety."""
    root = Path(context)
    if root.is_symlink() or not root.is_dir(): raise ValueError('Expected context directory')
    lock = requirements(dependency_manifest)
    if not isinstance(helper_manifest, dict) or helper_manifest.get('role') != 'verifier':
        raise ValueError('Expected verifier helper manifest')
    if helper_manifest.get('filename') != 'harness_fixture_helpers-0.0.1-py3-none-any.whl':
        raise ValueError('Unexpected helper wheel name')
    helper_hash = digest(helper_manifest.get('sha256'))
    expected = {
        'Dockerfile': hashlib.sha256(verifier_recipe(base_reference).encode()).hexdigest(),
        'verifier.hashes.txt': hashlib.sha256(lock).hexdigest(),
        'verifier-helper.hashes.txt': hashlib.sha256(('harness-fixture-helpers==0.0.1 --hash=sha256:' + helper_hash + '\n').encode()).hexdigest(),
        'verifier-helper/' + helper_manifest['filename']: helper_hash,
    }
    sizes = {}
    for item in dependency_manifest['artifacts']:
        name = 'verifier-wheelhouse/' + item['filename']
        expected[name] = item['sha256']; sizes[name] = item['bytes']
    actual = {}
    for path in root.rglob('*'):
        if path.is_symlink(): raise ValueError('Linked context input refused')
        if path.is_file(): actual[path.relative_to(root).as_posix()] = path
        elif not path.is_dir(): raise ValueError('Special context input refused')
    if actual.keys() != expected.keys(): raise ValueError('Unexpected or missing build input')
    total = 0
    for name, path in actual.items():
        size = path.stat().st_size; total += size
        if total > MAX_CONTEXT or size > MAX_CONTEXT or (name in sizes and size != sizes[name]):
            raise ValueError('Context size mismatch or cap exceeded')
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected[name]:
            raise ValueError('Context hash mismatch')
    return {'status': 'flask_verifier_context_prepared_not_built', 'files': len(actual),
            'bytes': total, 'base_runtime_verified': False, 'image_built': False,
            'provider_calls': 0, 'adversarial_integrity_verified': False}
