"""Prepared fresh-container Click verifier. Never part of editing operations.

Protected test bytes enter this disposable scorer only via controller stdin.
They are not installed in the agent helper image. Trusted-process pytest only.
"""
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

from .click_task import BASE_NAMES,BASE_HASHES,EDITABLE
from .docker_fixture_child import guard
from .source_bundle import MAX_ARCHIVE,unpack_sources
from .source_io import import_sources

TEST_NAME='.controller-hidden/test_selected.py'
TEST_HASH='2788ab3cd19b2821d74deadee824d8f002c8897cc2c78421f5493eb74b1b6018'
SCORE_NAMES=tuple(sorted(BASE_NAMES+(TEST_NAME,)))


def validate_score_input(raw):
    sources=unpack_sources(raw,expected_names=SCORE_NAMES)
    if hashlib.sha256(sources[TEST_NAME]).hexdigest()!=TEST_HASH:
        raise ValueError('Protected test identity mismatch')
    for name in BASE_NAMES:
        if name not in EDITABLE and hashlib.sha256(sources[name]).hexdigest()!=BASE_HASHES[name]:
            raise ValueError('Uneditable base source changed')
    return sources


def score():
    guard()
    if importlib.metadata.version('pytest')!='8.3.5':raise ValueError('Pinned verifier required')
    raw=sys.stdin.buffer.read(MAX_ARCHIVE+1)
    validate_score_input(raw)
    import_sources(raw,expected_names=SCORE_NAMES,root='/work')
    report=Path('/tmp/click-controller-score.xml')
    if report.exists() or report.is_symlink():raise ValueError('Unexpected prior report')
    invocation=('import sys; sys.path.insert(0,"/work/src"); import pytest; '
                'raise SystemExit(pytest.main('+repr(['-q','-p','no:cacheprovider',
                    '--import-mode=importlib','--override-ini=addopts=',
                    '--junitxml='+str(report),'/work/'+TEST_NAME+'::test_wrap_text_keeps_words_whole'])+'))')
    run=subprocess.run([sys.executable,'-I','-c',invocation],stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=20,
        env={'PATH':'/usr/local/bin:/usr/bin:/bin','HOME':'/tmp','PYTEST_DISABLE_PLUGIN_AUTOLOAD':'1'})
    if report.is_symlink() or not report.is_file() or report.stat().st_size>1024*1024:
        raise ValueError('Protected report unavailable')
    cases=list(ET.fromstring(report.read_bytes()).iter('testcase'))
    if len(cases)!=3 or any(c.find('error') is not None or c.find('skipped') is not None for c in cases):
        raise ValueError('Exact protected collection failed')
    failures=sum(c.find('failure') is not None for c in cases)
    if run.returncode not in (0,1) or (run.returncode==0)!=(failures==0):
        raise ValueError('Verifier exit/report mismatch')
    return {'status':'click_verifier_result','passed':run.returncode==0,'tests':3,
            'failures':failures,'skipped':0,'adversarial_integrity_verified':False}


if __name__=='__main__':
    try:print(json.dumps(score(),sort_keys=True))
    except Exception:raise SystemExit(3)
