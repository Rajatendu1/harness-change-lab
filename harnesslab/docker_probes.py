"""Fixed bounded enforcement probes. Never run these on the host.

Every program independently refuses to allocate/spawn/write before checking
exact expected cgroup-v2 settings. Execute each in a fresh reviewed container.
Programs alone are not runtime evidence or a complete qualification runner.
"""
GUARD = r'''
from pathlib import Path
import os, time, subprocess, sys
root=Path('/sys/fs/cgroup')
assert (root/'memory.max').read_text().strip()=='2147483648'
assert (root/'memory.swap.max').read_text().strip()=='0'
assert (root/'pids.max').read_text().strip()=='64'
quota,period=map(int,(root/'cpu.max').read_text().split())
assert quota==period and quota>0
assert os.getuid()!=0
'''

PID = GUARD + r'''
import errno
children=[]
limited=False
try:
    for _ in range(70):
        try:
            children.append(subprocess.Popen([sys.executable,'-I','-c','import time; time.sleep(30)'],
                                             stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL))
        except OSError as e:
            if e.errno!=errno.EAGAIN:
                raise
            limited=True
            break
    assert limited
finally:
    for p in children: p.kill()
    for p in children: p.wait(timeout=3)
print('pids-ok')
'''

MEMORY = GUARD + r'''
def events():
    return {k:int(v) for k,v in (line.split() for line in (root/'memory.events').read_text().splitlines())}
before=events()['oom_kill']
children=[]
try:
    # Nine fixed 256 MiB requests exceed aggregate 2 GiB. No exponential
    # allocator/fork bomb. Host upper bound remains the reviewed cgroup.
    for _ in range(9):
        children.append(subprocess.Popen([sys.executable,'-I','-c',
            'import time; x=bytearray(256*1024*1024); time.sleep(15)'],
            stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL))
    deadline=time.monotonic()+10
    while time.monotonic()<deadline and events()['oom_kill']==before:
        time.sleep(.1)
    assert events()['oom_kill']>before
finally:
    for p in children:
        if p.poll() is None: p.kill()
    for p in children: p.wait(timeout=3)
print('memory-ok')
'''

CPU = GUARD + r'''
def stats():
    return {k:int(v) for k,v in (line.split() for line in (root/'cpu.stat').read_text().splitlines())}
children=[]
before=stats(); started=time.monotonic()
try:
    for _ in range(2):
        children.append(subprocess.Popen([sys.executable,'-I','-c',
            'import time; end=time.monotonic()+3\nwhile time.monotonic()<end: pass'],
            stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL))
    for p in children:
        assert p.wait(timeout=6)==0
finally:
    for p in children:
        if p.poll() is None: p.kill()
    for p in children: p.wait(timeout=3)
elapsed=time.monotonic()-started; after=stats()
assert after['nr_throttled']>before['nr_throttled']
assert 0 < after['usage_usec']-before['usage_usec'] <= elapsed*1_000_000*1.25
print('cpu-ok')
'''

DISK = GUARD + r'''
import errno
for directory,expected in (('/work',64*1024*1024),('/tmp',16*1024*1024)):
    info=os.statvfs(directory)
    assert info.f_blocks*info.f_frsize<=expected
    filename=directory+'/bounded-space-probe'
    denied=False
    try:
        with open(filename,'wb',buffering=0) as stream:
            for _ in range(expected//(1024*1024)+2):
                stream.write(b'x'*(1024*1024))
    except OSError as e:
        if e.errno!=errno.ENOSPC:
            raise
        denied=True
    finally:
        Path(filename).unlink(missing_ok=True)
    assert denied
print('disk-ok')
'''

ENFORCEMENT_PROBES = {'pids':PID, 'memory':MEMORY, 'cpu':CPU, 'disk':DISK}
