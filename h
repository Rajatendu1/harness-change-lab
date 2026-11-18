"""Fixed candidate cleanup selection and future container-only helper.

No automatic execution. Helper refuses host-like identities/cgroups. Only the
separately approved Docker adapter may invoke it after stopping new launches.
"""
import re


def process_uids(status):
    rows=[line.split()[1:] for line in status.splitlines() if line.startswith('Uid:')]
    if len(rows)!=1 or len(rows[0])!=4 or any(not re.fullmatch('[0-9]+',x) for x in rows[0]):
        raise ValueError('Process UID metadata unavailable')
    return tuple(map(int,rows[0]))


def cleanup_targets(statuses, *, agent_uid, keeper_uid, self_pid):
    """Fail closed on unknown identities; never use process names or commands."""
    if (any(type(x) is not int or x<=0 for x in (agent_uid,keeper_uid,self_pid))
            or agent_uid==keeper_uid or self_pid==1 or not isinstance(statuses,dict)
            or not statuses or len(statuses)>64 or 1 not in statuses or self_pid not in statuses):
        raise ValueError('Invalid bounded cleanup inventory')
    expected_keeper=(keeper_uid,)*4
    expected_agent=(agent_uid,)*4
    parsed={}
    for pid,status in statuses.items():
        if type(pid) is not int or pid<=0 or not isinstance(status,str):
            raise ValueError('Invalid process metadata')
        parsed[pid]=process_uids(status)
    if parsed[1]!=expected_keeper or parsed[self_pid]!=expected_agent:
        raise ValueError('Keeper or cleanup identity mismatch')
    if any(uids not in (expected_keeper,expected_agent) for uids in parsed.values()):
        raise ValueError('Unexpected process UID')
    if any(pid!=1 and uids==expected_keeper for pid,uids in parsed.items()):
        raise ValueError('Unexpected keeper-UID process')
    return tuple(sorted(pid for pid,uids in parsed.items() if uids==expected_agent and pid!=self_pid))


# This source is not executed by importing this module. The future image must
# package this module read-only and run python3 -I -c with reviewed fixed IDs.
KEEPER_PROGRAM = r'''
import os,time
from pathlib import Path
assert os.getuid()==1001 and os.geteuid()==1001 and os.getpid()==1
assert Path('/sys/fs/cgroup/pids.max').read_text().strip()=='64'
status=Path('/proc/self/status').read_text()
assert 'NoNewPrivs:\t1' in status
assert int(next(x.split()[1] for x in status.splitlines() if x.startswith('CapEff:')),16)==0
# Never imports candidate code or launches children. Reap orphaned agent
# descendants so cleanup can require their real disappearance, not just zombies.
while True:
    try:
        while os.waitpid(-1,os.WNOHANG)[0]:
            pass
    except ChildProcessError:
        pass
    time.sleep(.05)
'''

CLEANUP_PROGRAM = r'''
import os,signal,time
from pathlib import Path
from harnesslab.candidate_cleanup import cleanup_targets
AGENT_UID=65534
KEEPER_UID=1001
assert os.getuid()==AGENT_UID and os.geteuid()==AGENT_UID and os.getpid()!=1
root=Path('/sys/fs/cgroup')
assert (root/'memory.max').read_text().strip()=='2147483648'
assert (root/'memory.swap.max').read_text().strip()=='0'
assert (root/'pids.max').read_text().strip()=='64'
status=Path('/proc/self/status').read_text()
assert 'NoNewPrivs:\t1' in status
assert int(next(x.split()[1] for x in status.splitlines() if x.startswith('CapEff:')),16)==0
for sweep in range(5):
    statuses={}
    for path in Path('/proc').iterdir():
        if path.name.isdigit():
            try:
                statuses[int(path.name)]=(path/'status').read_text()
            except FileNotFoundError:
                continue
    targets=cleanup_targets(statuses,agent_uid=AGENT_UID,keeper_uid=KEEPER_UID,self_pid=os.getpid())
    if not targets:
        print('candidate-cleanup-ok')
        break
    for pid in targets:
        try:
            os.kill(pid,signal.SIGKILL)
        except ProcessLookupError:
            pass
    time.sleep(.1)
else:
    raise SystemExit(3)
'''
