"""Controller-side cgroup-v2 event snapshots, no probes/containers launched.

Read only after independently verifying keeper host PID. Linux namespace/path
layout may differ; unresolvable metadata is a failed gate, never bypassed.
"""
from pathlib import Path,PurePosixPath


def resolve_cgroup(relative):
    if not isinstance(relative,str) or not relative.startswith('/') or '..' in PurePosixPath(relative).parts:
        raise ValueError('Invalid controller cgroup path')
    root=Path('/sys/fs/cgroup').resolve(strict=True)
    directory=(root/relative.lstrip('/')).resolve(strict=True)
    if not directory.is_relative_to(root) or directory==root:
        raise ValueError('Refusing root or escaped cgroup')
    return directory


def read_snapshot(keeper_pid):
    if type(keeper_pid) is not int or keeper_pid<=1:
        raise ValueError('Explicit keeper host PID required')
    rows=Path(f'/proc/{keeper_pid}/cgroup').read_text().splitlines()
    if len(rows)!=1 or not rows[0].startswith('0::/'):
        raise ValueError('Unified cgroup metadata unavailable')
    directory=resolve_cgroup(rows[0][3:])
    def pairs(name):
        return {k:int(v) for k,v in (line.split() for line in (directory/name).read_text().splitlines())}
    snapshot={'memory_max':(directory/'memory.max').read_text().strip(),
              'swap_max':(directory/'memory.swap.max').read_text().strip(),
              'pids_max':(directory/'pids.max').read_text().strip(),
              'cpu_max':(directory/'cpu.max').read_text().strip(),
              'memory_events':pairs('memory.events'),'pids_events':pairs('pids.events'),
              'cpu_stat':pairs('cpu.stat')}
    validate_limits(snapshot)
    return snapshot


def validate_limits(snapshot):
    if (snapshot['memory_max']!='2147483648' or snapshot['swap_max']!='0'
            or snapshot['pids_max']!='64'):
        raise ValueError('Controller-observed limits mismatch')
    quota,period=map(int,snapshot['cpu_max'].split())
    if quota<=0 or quota!=period:
        raise ValueError('Controller-observed CPU quota mismatch')


def corroborate(before,after,*,probe):
    validate_limits(before);validate_limits(after)
    fields={'memory':('memory_events','oom_kill'),'pids':('pids_events','max'),
            'cpu':('cpu_stat','nr_throttled')}
    if probe not in fields:raise ValueError('Unsupported event corroboration')
    group,key=fields[probe]
    start,end=before[group][key],after[group][key]
    if type(start) is not int or type(end) is not int or start<0 or end<=start:
        raise ValueError('Controller-observed enforcement event did not increase')
    return {'probe':probe,'external_event_delta':end-start,'runtime_qualified':False}


def check_memory_probe_survivor(top,state,identity,before,after):
    """Only a deliberate fixed OOM probe may report an expected OOM event.

    Generic keeper/candidate gates remain unchanged. The same keeper must be
    running alone after command completion, with independent exact-limit and
    increased OOM-event corroboration. A historical OOM flag is not proof of
    keeper death, and never substitutes for survival or process checks.
    """
    from .process_observation import check_keeper_only
    event=corroborate(before,after,probe='memory')
    if type(state.get('OOMKilled')) is not bool:
        raise ValueError('Explicit OOM state required')
    normalized=dict(state);normalized['OOMKilled']=False
    check_keeper_only(top,normalized,identity)
    return dict(event,expected_memory_pressure=True,
                docker_oom_flag=state['OOMKilled'])
