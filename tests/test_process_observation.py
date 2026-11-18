import unittest

from harnesslab.process_observation import KeeperIdentity, ExportGate, check_keeper_only

IDENTITY=KeeperIdentity(12345,1001,65534)
TOP=b'UID     PID\n1001    12345\n'
STATE={'Running':True,'Paused':False,'Restarting':False,'Dead':False,'Pid':12345,'OOMKilled':False}


class ProcessObservationTests(unittest.TestCase):
    def test_keeper_snapshot_not_hostile_eradication_claim(self):
        result=check_keeper_only(TOP,STATE,IDENTITY)
        self.assertEqual(result['observation'],'keeper_only_snapshot')
        self.assertEqual(result['hostile_process_eradication'],'not_verified')

    def test_unknown_agent_duplicate_missing_or_malformed_process_denies(self):
        for raw in (b'UID PID\n',TOP+b'65534 12346\n',TOP+b'1001 12347\n',TOP+TOP.splitlines()[1]+b'\n',
                    b'UID PID\nroot 12345\n',b'USER PID\n1001 12345\n',b'UID PID\n1001 12345 extra\n',
                    b'UID PID\n1001 0\n',b'UID PID\n1001 12345\n\n',b'UID PID\n\xff 12345\n'):
            with self.subTest(raw=raw),self.assertRaises(ValueError): check_keeper_only(raw,STATE,IDENTITY)

    def test_changed_or_uncertain_container_state_denies(self):
        for key,value in (('Pid',12346),('Pid',True),('Running',False),('Paused',True),
                          ('Restarting',True),('Dead',True),('OOMKilled',True),('Paused',None)):
            state=dict(STATE);state[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError): check_keeper_only(TOP,state,IDENTITY)

    def test_nonroot_distinct_explicit_identity_required(self):
        for values in ((0,1001,65534),(12345,0,65534),(12345,1001,0),(12345,1001,1001),
                       (True,1001,65534)):
            with self.assertRaises(ValueError): KeeperIdentity(*values)
        with self.assertRaises(ValueError): check_keeper_only(TOP,STATE,None)

    def test_export_only_once_after_cleanup_and_observation(self):
        gate=ExportGate(IDENTITY)
        gate.candidate_cleanup_finished(b'candidate-cleanup-ok\n')
        gate.observe(TOP,STATE)
        self.assertEqual(gate.consume_export(),'fixed_export_only')
        with self.assertRaises(ValueError): gate.consume_export()

    def test_early_or_failed_observation_poison_gate(self):
        gate=ExportGate(IDENTITY)
        with self.assertRaises(ValueError): gate.observe(TOP,STATE)
        with self.assertRaises(ValueError): gate.candidate_cleanup_finished(b'candidate-cleanup-ok\n')
        with self.assertRaises(ValueError): gate.consume_export()
        gate=ExportGate(IDENTITY);gate.candidate_cleanup_finished(b'candidate-cleanup-ok\n')
        with self.assertRaises(ValueError): gate.observe(TOP+b'65534 12346\n',STATE)
        with self.assertRaises(ValueError): gate.consume_export()

    def test_wrong_marker_or_skipped_observation_denies(self):
        for marker in (b'partial',b'candidate-cleanup-ok\nprivate-dummy',b''):
            gate=ExportGate(IDENTITY)
            with self.assertRaises(ValueError): gate.candidate_cleanup_finished(marker)
            with self.assertRaises(ValueError): gate.consume_export()
        gate=ExportGate(IDENTITY);gate.candidate_cleanup_finished(b'candidate-cleanup-ok\n')
        with self.assertRaises(ValueError): gate.consume_export()
