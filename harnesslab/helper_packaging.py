"""Deterministic stdlib-only trusted-helper wheel packaging, no build hooks.

Source files are controller repository inputs. No candidate/repository-history
or runtime credentials should enter this archive. This is not a package audit.
"""
import base64
import csv
import hashlib
import io
from pathlib import Path
import zipfile

DIST='harness_fixture_helpers-0.0.1.dist-info'


def helper_wheel(source_root, *, role='agent'):
    if role not in ('agent','verifier'):
        raise ValueError('Expected fixed helper role')
    root=Path(source_root)
    package=root/'harnesslab'
    if package.is_symlink() or not package.is_dir():
        raise ValueError('Expected trusted helper source directory')
    records={}
    for file in sorted(package.glob('*.py')):
        if role=='agent' and file.name in ('fixed_hidden_test.py','docker_verifier_child.py','fixed_fixture_score.py','docker_fixture_score.py','protected_score.py',
                                           'click_verifier_child.py','click_docker_score.py','click_pilot.py','click_diagnostic.py','evidence_intake.py','flask_preparation.py','flask_verifier_child.py','flask_docker_score.py','flask_task.py','flask_image_plan.py'):
            continue
        if file.is_symlink() or not file.is_file() or file.stat().st_size>1024*1024:
            raise ValueError('Unsafe helper input')
        records['harnesslab/'+file.name]=file.read_bytes()
    if 'harnesslab/__init__.py' not in records or len(records)>100:
        raise ValueError('Unexpected helper package')
    records[DIST+'/METADATA']=b'Metadata-Version: 2.1\nName: harness-fixture-helpers\nVersion: 0.0.1\nRequires-Python: >=3.10,<3.11\n\nPrivate model-free fixture helpers.\n'
    records[DIST+'/WHEEL']=b'Wheel-Version: 1.0\nGenerator: fixed-stdlib-packager\nRoot-Is-Purelib: true\nTag: py3-none-any\n'
    rows=[]
    for name,data in sorted(records.items()):
        digest=base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b'=').decode()
        rows.append((name,'sha256='+digest,str(len(data))))
    rows.append((DIST+'/RECORD','',''))
    stream=io.StringIO(newline='');csv.writer(stream,lineterminator='\n').writerows(rows)
    records[DIST+'/RECORD']=stream.getvalue().encode()
    buffer=io.BytesIO()
    with zipfile.ZipFile(buffer,'w',compression=zipfile.ZIP_DEFLATED) as archive:
        for name,data in sorted(records.items()):
            info=zipfile.ZipInfo(name,date_time=(1980,1,1,0,0,0))
            info.compress_type=zipfile.ZIP_DEFLATED
            info.external_attr=0o100644<<16
            archive.writestr(info,data)
    raw=buffer.getvalue()
    return raw, {'filename':'harness_fixture_helpers-0.0.1-py3-none-any.whl',
                 'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),
                 'source_sha256':{name:hashlib.sha256(data).hexdigest() for name,data in records.items()
                                  if name.startswith('harnesslab/')},
                 'role':role,
                 'build_hooks_executed':False,'installed':False,'runtime_verified':False}
