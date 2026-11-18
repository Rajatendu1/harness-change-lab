import copy
import unittest
from harnesslab.cgroup_observation import corroborate,validate_limits
from harnesslab.docker_denials import denial_source


def snapshot():
    return {'memory_max':'2147483648','swap_max':'0','pids_max':'64','cpu_max':'100000 100000',
            'memory_events':{'oom_kill':0},'pids_events':{'max':0},'cpu_stat':{'nr_throttled':0}}


class ControllerEvidenceTests(unittest.TestCase):
    def test_external_event_delta_requires_correct_limits_and_increase(self):
        for probe,group,key in (('memory','memory_events','oom_kill'),('pids','pids_events','max'),
                                ('cpu','cpu_stat','nr_throttled')):
            before=snapshot();after=copy.deepcopy(before);after[group][key]=2
            self.assertEqual(corroborate(before,after,probe=probe)['external_event_delta'],2)
            with self.assertRaises(ValueError):corroborate(before,before,probe=probe)
            after['memory_max']='max'
            with self.assertRaises(ValueError):corroborate(before,after,probe=probe)

    def test_unlimited_or_wrong_controller_limits_refused(self):
        for key,value in (('memory_max','max'),('swap_max','max'),('pids_max','max'),
                          ('cpu_max','max 100000'),('cpu_max','200000 100000')):
            data=snapshot();data[key]=value
            with self.assertRaises(ValueError):validate_limits(data)

    def test_denial_source_fixed_controller_path_not_arbitrary_input(self):
        program=denial_source('/tmp/harness-private-probe-'+'a'*32+'/sentinel')
        compile(program,'fixed-denial','exec') # Never execute host/container denial code.
        self.assertIn('guard()',program)
        for path in ('/etc/passwd','/tmp/arbitrary',None,'/tmp/harness-private-probe-'+'a'*32+'/../sentinel'):
            with self.assertRaises(ValueError):denial_source(path)

class ExpectedMemoryPressureTests(unittest.TestCase):
    def test_only_explicit_corroborated_memory_survival_can_tolerate_flag(self):
        from harnesslab.cgroup_observation import check_memory_probe_survivor
        from harnesslab.process_observation import KeeperIdentity,check_keeper_only
        identity=KeeperIdentity(12345,1001,65534);top=b'UID PID\n1001 12345\n'
        state={'Running':True,'Paused':False,'Restarting':False,'Dead':False,'Pid':12345,'OOMKilled':True}
        before=snapshot();after=copy.deepcopy(before);after['memory_events']['oom_kill']=2
        self.assertEqual(check_memory_probe_survivor(top,state,identity,before,after)['external_event_delta'],2)
        with self.assertRaises(ValueError):check_keeper_only(top,state,identity)
        with self.assertRaises(ValueError):check_memory_probe_survivor(top,state,identity,before,before)
        for key,value in [('Running',False),('Paused',True),('Dead',True),('Restarting',True),('Pid',54321),('OOMKilled',None)]:
            changed=dict(state);changed[key]=value
            with self.assertRaises(ValueError):check_memory_probe_survivor(top,changed,identity,before,after)
        with self.assertRaises(ValueError):check_memory_probe_survivor(top+b'65534 12346\n',state,identity,before,after)
        after['memory_max']='max'
        with self.assertRaises(ValueError):check_memory_probe_survivor(top,state,identity,before,after)
