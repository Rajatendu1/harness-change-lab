"""Simulated diagnostics only, no resource probe/daemon launched."""
import copy
import tempfile
import unittest
from unittest.mock import patch
from harnesslab.bounded_process import ControlledProcessError
from harnesslab.docker_fixture_adapter import DockerFixtureAdapter,ResourceProbeFailure
from harnesslab.fixed_qualification import isolated_stage
from harnesslab.process_observation import KeeperIdentity


def snapshot():
    return {'memory_max':'2147483648','swap_max':'0','pids_max':'64','cpu_max':'100000 100000',
            'memory_events':{'oom_kill':0},'pids_events':{'max':0},'cpu_stat':{'nr_throttled':0}}


class ResourceDiagnosticsTests(unittest.TestCase):
    def adapter(self):
        a=object.__new__(DockerFixtureAdapter)
        a.keeper_identity=KeeperIdentity(12345,1001,65534);a.gid=1001;a.name='fixed-simulation'
        state={'Running':True,'Paused':False,'Restarting':False,'Dead':False,'Pid':12345,'OOMKilled':False}
        a.observe=lambda:(b'UID PID\n1001 12345\n',copy.deepcopy(state))
        a.inspect=lambda:{'State':copy.deepcopy(state)}
        return a,state

    def test_success_retains_strict_external_corroboration(self):
        a,state=self.adapter();a.call=lambda *args,**kwargs:b'memory-ok\n'
        before=snapshot();after=copy.deepcopy(before);after['memory_events']['oom_kill']=1
        with patch('harnesslab.cgroup_observation.read_snapshot',side_effect=[before,after]):
            self.assertEqual(a.verify_resource_event('memory')['external_event_delta'],1)

    def test_command_failure_only_emits_enum_and_bounded_facts(self):
        a,state=self.adapter()
        def fail(*args,**kwargs):raise ControlledProcessError('nonzero_exit')
        a.call=fail
        with patch('harnesslab.cgroup_observation.read_snapshot',return_value=snapshot()):
            with self.assertRaises(ResourceProbeFailure) as got:a.verify_resource_event('memory')
        self.assertEqual(got.exception.diagnostic,{'phase':'probe_command','error_category':'nonzero_exit',
             'observations':{'keeper_running':True,'keeper_oom_killed':False,'keeper_pid_unchanged':True,'memory_oom_kill_delta':0}})
        self.assertNotIn('12345',repr(got.exception.diagnostic))

    def test_expected_oom_flag_requires_memory_event_and_survival(self):
        a,state=self.adapter()
        def run(*args,**kwargs):state['OOMKilled']=True;return b'memory-ok\n'
        a.call=run
        before=snapshot();after=copy.deepcopy(before);after['memory_events']['oom_kill']=1
        with patch('harnesslab.cgroup_observation.read_snapshot',side_effect=[before,after]):
            result=a.verify_resource_event('memory')
        self.assertTrue(result['expected_memory_pressure'])
        self.assertTrue(result['docker_oom_flag'])
        self.assertEqual(result['external_event_delta'],1)

    def test_arbitrary_error_and_facts_do_not_escape(self):
        e=ResourceProbeFailure('probe_command',ValueError('private sentinel data'),
            {'keeper_running':'raw','memory_oom_kill_delta':10001,'raw':'private sentinel data'})
        self.assertEqual(e.diagnostic,{'phase':'probe_command','error_category':'invariant_failed','observations':{}})
        with self.assertRaises(ValueError):ResourceProbeFailure('private phase',Exception(),{})

    def test_stage_retains_failure_and_cleanup(self):
        class A:
            def __init__(self,**kwargs):pass
            def create_keeper(self):pass
            def verify_resource_event(self,name):raise ResourceProbeFailure('probe_command',ControlledProcessError('wall_timeout'),{})
            def remove_and_confirm_absent(self):return True
        result=isolated_stage('memory',image_policy=None,adapter_factory=A)
        self.assertFalse(result['passed']);self.assertEqual(result['cleanup'],'absence_confirmed')
        self.assertEqual(result['diagnostic']['error_category'],'wall_timeout')
