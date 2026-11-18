"""Read-only packaged protected test for the fixed synthetic fixture only."""
import sys
sys.path.insert(0,'/work')
from example import answer


def test_fixed_answer():
    assert answer()==1
