"""Conservative controller observation gate for a future distinct-UID adapter.

No Docker launch, kill or export. Docker-top snapshot is corroboration only, not
proof of adversarial containment. Caller must stop launches and keep a fixed
keeper that never spawns. User-namespace UID remapping is not supported yet.
"""
from dataclasses import dataclass
import re


@dataclass(frozen=True)
class KeeperIdentity:
    host_pid: int
    host_uid: int
    agent_uid: int

    def __post_init__(self):
        if (any(type(x) is not int or x <= 0 for x in (self.host_pid,self.host_uid,self.agent_uid))
                or self.host_uid == self.agent_uid):
            raise ValueError('Expected distinct nonroot keeper and agent identities')


def check_keeper_only(top_output, inspect_state, identity):
    """Accept exact docker top -eo uid,pid snapshot + independently known keeper.

    Reject unknowns, duplicates, alternate headers, truncated/malformed tables,
    PID changes, stopped/paused/restarting/dead state and any extra process.
    Never infer keeper identity from the untrusted candidate or table itself.
    """
    if not isinstance(identity, KeeperIdentity) or not isinstance(top_output,bytes):
        raise ValueError('Explicit keeper identity and bounded bytes required')
    if len(top_output)>65536:
        raise ValueError('Process observation exceeds bound')
    try:
        lines=top_output.decode('ascii').splitlines()
    except UnicodeError:
        raise ValueError('Non-numeric process observation') from None
    if not lines or lines[0].split()!=['UID','PID']:
        raise ValueError('Unexpected process observation header')
    observed=[]
    for line in lines[1:]:
        if not re.fullmatch(r'\s*[0-9]+\s+[0-9]+\s*',line):
            raise ValueError('Malformed process observation row')
        uid,pid=map(int,line.split())
        if pid<=0 or uid<0:
            raise ValueError('Invalid process identity')
        observed.append((uid,pid))
    if observed!=[(identity.host_uid,identity.host_pid)]:
        raise ValueError('Candidate or unknown processes remain')
    state=inspect_state
    if (state.get('Running') is not True or state.get('Paused') is not False
            or state.get('Restarting') is not False or state.get('Dead') is not False
            or type(state.get('Pid')) is not int or state['Pid']!=identity.host_pid
            or state.get('OOMKilled') is not False):
        raise ValueError('Keeper state changed or unverified')
    return {'observation':'keeper_only_snapshot','candidate_processes_observed':0,
            'hostile_process_eradication':'not_verified'}


class ExportGate:
    """One-use transition, not an authorization grant or race-free guarantee."""
    def __init__(self, identity):
        if not isinstance(identity,KeeperIdentity):
            raise ValueError('Expected keeper identity')
        self.identity=identity
        self._phase='agent_may_run'

    def candidate_cleanup_finished(self, marker):
        if self._phase!='agent_may_run' or marker!=b'candidate-cleanup-ok\n':
            self._phase='failed'
            raise ValueError('Cleanup not confirmed')
        self._phase='awaiting_observation'

    def observe(self, top_output, inspect_state):
        if self._phase!='awaiting_observation':
            self._phase='failed'
            raise ValueError('Process observation out of order')
        try:
            result=check_keeper_only(top_output,inspect_state,self.identity)
        except (ValueError,TypeError,AttributeError):
            self._phase='failed'
            raise ValueError('Process quiescence unverified') from None
        self._phase='one_export_ready'
        return result

    def consume_export(self):
        if self._phase!='one_export_ready':
            self._phase='failed'
            raise ValueError('Export denied without fresh observation')
        self._phase='export_consumed'
        return 'fixed_export_only'
