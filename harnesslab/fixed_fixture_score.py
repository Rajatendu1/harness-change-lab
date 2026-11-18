"""Separate protected score for fixed Docker fixture after confirmed removal.

Local namespace scorer is a trusted-process oracle, not Docker-qualified or
adversarially independent. No model/provider. Never accepts a task/test argument.
"""
from dataclasses import asdict
from pathlib import Path
import tempfile

from .docker_fixture_child import BASE
from .protected_score import score_candidate

EXPECTED={'example.py':b'def answer():\n    return 1\n'}
TEST=b'import sys\nsys.path.insert(0,"/work")\nfrom example import answer\ndef test_answer():\n    assert answer()==1\n'


def score_fixed_fixture(candidate, *, python, runtime_root):
    """Candidate must come from removal-confirmed lifecycle, not raw agent IO.

    This function cannot prove provenance of its dictionary input. Controller
    ordering must enforce it; do not expose direct user/candidate score API.
    """
    if (not isinstance(candidate,dict) or set(candidate)!=set(BASE)
            or not isinstance(candidate['example.py'],bytes)
            or len(candidate['example.py'])>8*1024*1024):
        return {'status':'invalid_fixture','passed':False,'adversarial_integrity_verified':False}
    with tempfile.TemporaryDirectory(prefix='fixed-protected-score-') as directory:
        root=Path(directory)
        base,proposed,hidden=[root/name for name in ('base','candidate','hidden')]
        for path in (base,proposed,hidden):path.mkdir()
        (base/'example.py').write_bytes(BASE['example.py'])
        (proposed/'example.py').write_bytes(candidate['example.py'])
        (hidden/'test_fixed_hidden.py').write_bytes(TEST)
        score=score_candidate(base=base,candidate=proposed,editable_files=['example.py'],
            protected_tests=hidden,python=python,runtime_root=runtime_root,
            test_node='test_fixed_hidden.py::test_answer',timeout_s=10)
    return {'status':'fixture_protected_score','passed':score.outcome=='source_patch_verifier_pass'
            and score.tests==1 and score.skipped==0,'score':asdict(score),
            'real_model_repairs':0,'adversarial_integrity_verified':False,
            'runtime_boundary':'local_namespace_scorer_not_docker_qualification'}
