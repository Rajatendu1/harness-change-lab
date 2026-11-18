"""Prepared Flask source-transfer and scorer contracts. No execution authority.

This narrower blueprint-name task is separate from the historical corpus card.
No Docker adapter, model run or comparison result is registered by this module.
"""
import hashlib
import xml.etree.ElementTree as ET
from .source_bundle import unpack_sources
from .flask_task import BASE_HASHES, BASE_NAMES, EDITABLE

TEST_NAME = '.controller-hidden/test_selected.py'
TEST_HASH = '8e44d33f91f5a8166bedcc61f179f75cb144055e356f0d97999a4a8730ae161a'
SCORE_NAMES = tuple(sorted(BASE_NAMES + (TEST_NAME,)))
EXPECTED_TEST = 'test_dotted_name_not_allowed'
EXPECTED_CLASS = '.controller-hidden.test_selected'
MAX_REPORT = 1024 * 1024


def validate_score_input(raw):
    sources = unpack_sources(raw, expected_names=SCORE_NAMES)
    if hashlib.sha256(sources[TEST_NAME]).hexdigest() != TEST_HASH:
        raise ValueError('Protected Flask test identity mismatch')
    for name in BASE_NAMES:
        if name not in EDITABLE and hashlib.sha256(sources[name]).hexdigest() != BASE_HASHES[name]:
            raise ValueError('Uneditable Flask base source changed')
    return sources


def parse_protected_result(report, exit_code):
    """Parse one expected case, not candidate-authenticated evidence.

    The caller must collect this in a fresh trusted-process verifier, not from
    the editing workspace. A malicious candidate can forge pytest reports.
    """
    if not isinstance(report, bytes) or len(report) > MAX_REPORT or not report:
        raise ValueError('Expected bounded report bytes')
    if type(exit_code) is not int or exit_code not in (0, 1):
        raise ValueError('Verifier did not complete normally')
    if b'<!DOCTYPE' in report.upper() or b'<!ENTITY' in report.upper():
        raise ValueError('Report declarations are not allowed')
    try:
        tree = ET.fromstring(report)
    except ET.ParseError:
        raise ValueError('Invalid protected report') from None
    if tree.tag != 'testsuites':
        raise ValueError('Expected pytest report root')
    suites = list(tree)
    if len(suites) != 1 or suites[0].tag != 'testsuite':
        raise ValueError('Expected one protected suite')
    suite = suites[0]
    if suite.get('tests') != '1' or suite.get('errors') != '0' or suite.get('skipped') != '0':
        raise ValueError('Exact protected collection failed')
    cases = list(suite.iter('testcase'))
    if len(cases) != 1 or cases[0].get('name') != EXPECTED_TEST or cases[0].get('classname') != EXPECTED_CLASS:
        raise ValueError('Protected case identity mismatch')
    case = cases[0]
    if any(tag.tag in ('error', 'skipped', 'testcase', 'testsuite') for tag in case.iter() if tag is not case):
        raise ValueError('Protected case did not run normally')
    failures = len(list(case.iter('failure')))
    if failures > 1 or suite.get('failures') != str(failures) or (exit_code == 0) != (failures == 0):
        raise ValueError('Verifier exit/report mismatch')
    return {'status': 'flask_local_protected_result', 'passed': exit_code == 0,
            'tests': 1, 'failures': failures, 'skipped': 0,
            'adversarial_integrity_verified': False}
