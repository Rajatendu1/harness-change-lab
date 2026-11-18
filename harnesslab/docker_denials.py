"""Fixed denial source for future approved Docker fixture; never run on host."""
import re


def denial_source(dummy_path):
    if not isinstance(dummy_path,str) or not re.fullmatch(r'/tmp/harness-private-probe-[a-f0-9]{32}/sentinel',dummy_path):
        raise ValueError('Expected controller-created dummy sentinel path')
    return r'''
import errno,os,socket
from pathlib import Path
from harnesslab.docker_fixture_child import guard
guard()
assert 'HARNESS_PRIVATE_DUMMY' not in os.environ
'''+'dummy='+repr(dummy_path)+'\n'+r'''
try:
    Path(dummy).read_bytes()
except OSError as e:
    assert e.errno in (errno.ENOENT,errno.EACCES)
else:
    raise AssertionError('Controller private file visible')
assert not Path('/var/run/docker.sock').exists()
for destination in ('/gateway/provider.sock','/gateway/new-socket'):
    try:
        Path(destination).unlink(missing_ok=False)
    except OSError as e:
        assert e.errno in (errno.ENOENT,errno.EROFS,errno.EACCES)
    else:
        raise AssertionError('Gateway unlink succeeded')
s=socket.socket();s.settimeout(.2)
try:
    s.connect(('192.0.2.1',80))
except OSError:
    pass
else:
    raise AssertionError('External network reachable')
finally:s.close()
print('fixed-denials-ok')
'''
