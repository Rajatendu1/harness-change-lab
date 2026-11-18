#!/usr/bin/env python3
"""Provision explicit local fixture runtimes. No credentials or provider calls.

Network package installation occurs only with --allow-package-downloads. Existing
paths are refused rather than overwritten. This does not configure a live run.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import venv


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--destination', required=True)
    parser.add_argument('--allow-package-downloads', action='store_true')
    args = parser.parse_args()
    root = Path(args.destination).resolve()
    if not args.allow_package_downloads:
        parser.error('Explicit --allow-package-downloads required; no changes made')
    if root.exists():
        parser.error('Destination already exists; refusing overwrite')
    # Python must resolve in the system mount used by the isolated controller.
    if not Path(sys.executable).resolve().is_relative_to('/usr'):
        parser.error('Use a system Python resolving under /usr')
    root.mkdir(parents=True)
    try:
        for name, requirement in (('agent', 'aider-chat==0.86.2'), ('verifier', 'pytest==8.3.5')):
            directory = root / name
            venv.EnvBuilder(with_pip=True, symlinks=True).create(directory)
            python = directory / 'bin' / 'python'
            subprocess.run([str(python), '-m', 'pip', 'install', requirement], check=True,
                           stdin=subprocess.DEVNULL)
            freeze = subprocess.run([str(python), '-m', 'pip', 'freeze', '--all'],
                                    check=True, text=True, capture_output=True).stdout
            (root / (name + '-installed.txt')).write_text(freeze)
            if not python.resolve().is_relative_to('/usr'):
                raise ValueError('Runtime Python resolves outside isolated system mounts')
        inventory = {name: {'sha256': hashlib.sha256((root / (name + '-installed.txt')).read_bytes()).hexdigest()}
                     for name in ('agent', 'verifier')}
        record = {'schema': 'local-runtime-provision-v0', 'status': 'installed_not_run',
                  'python': sys.version.split()[0], 'inventory': inventory,
                  'provider_calls': 0, 'credentials_created': 0, 'execution_authority': 'none',
                  'limits': 'Installed versions recorded, not a hash-locked or fully hermetic build; Linux bubblewrap and namespace support are separate prerequisites.'}
        (root / 'runtime-record.json').write_text(json.dumps(record, sort_keys=True, indent=2) + '\n')
        print(json.dumps(record, sort_keys=True, indent=2))
        return 0
    except Exception:
        # Keep failed installs inspectable, explicitly not a usable runtime record.
        (root / 'PROVISION_FAILED').write_text('Provisioning failed. No live run was configured. Remove this directory before retrying.\n')
        raise


if __name__ == '__main__':
    raise SystemExit(main())
