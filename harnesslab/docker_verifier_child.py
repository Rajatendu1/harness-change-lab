"""Fixed verifier-image operation, not host execution or independent oracle."""
import json
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET


def protected_score():
    from .docker_fixture_child import guard
    guard()
    import importlib.metadata
    if importlib.metadata.version('pytest')!='8.3.5':
        raise ValueError('Wrong verifier runtime')
    report=Path('/tmp/fixed-controller-score.xml')
    if report.exists() or report.is_symlink():
        raise ValueError('Unexpected prior report')
    test=Path(__file__).with_name('fixed_hidden_test.py')
    result=subprocess.run([sys.executable,'-I','-m','pytest','-q','-p','no:cacheprovider',
        '--import-mode=importlib','--override-ini=addopts=',
        '--junitxml='+str(report),str(test)+'::test_fixed_answer'],
        stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
        timeout=10,env={'PATH':'/usr/local/bin:/usr/bin:/bin','HOME':'/tmp',
                        'PYTEST_DISABLE_PLUGIN_AUTOLOAD':'1'})
    if report.is_symlink() or not report.is_file() or report.stat().st_size>1024*1024:
        raise ValueError('Protected report unavailable')
    root=ET.fromstring(report.read_bytes());cases=list(root.iter('testcase'))
    if len(cases)!=1 or any(case.find('error') is not None or case.find('skipped') is not None for case in cases):
        raise ValueError('Exact protected collection failed')
    failures=sum(case.find('failure') is not None for case in cases)
    if result.returncode not in (0,1) or (result.returncode==0)!=(failures==0):
        raise ValueError('Protected result mismatch')
    return {'status':'fixed_verifier_result','passed':result.returncode==0,
            'tests':1,'failures':failures,'skipped':0,'adversarial_integrity_verified':False}


if __name__=='__main__':
    try:
        print(json.dumps(protected_score(),sort_keys=True))
    except Exception:
        raise SystemExit(3)
