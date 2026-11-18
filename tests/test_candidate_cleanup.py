import ast
import unittest

from harnesslab.candidate_cleanup import (cleanup_targets,process_uids,
                                          KEEPER_PROGRAM,CLEANUP_PROGRAM)


def status(uid):
    return f'Name:\tfixture\nUid:\t{uid}\t{uid}\t{uid}\t{uid}\n'


def select(rows):
    return cleanup_targets(rows,agent_uid=65534,keeper_uid=1001,self_pid=7)


class CandidateCleanupTests(unittest.TestCase):
    def test_only_agent_processes_other_than_self_selected(self):
        self.assertEqual(select({1:status(1001),7:status(65534),5:status(65534),8:status(65534)}),(5,8))
        self.assertEqual(select({1:status(1001),7:status(65534)}),())

    def test_missing_changed_or_extra_identity_denies(self):
        for rows in ({7:status(65534)},{1:status(1001)},{1:status(65534),7:status(65534)},
                     {1:status(1001),7:status(1001)},
                     {1:status(1001),7:status(65534),8:status(0)},
                     {1:status(1001),7:status(65534),8:status(1001)},
                     {1:status(1001),7:'Uid:\t65534 0 65534 65534'}):
            with self.assertRaises(ValueError): select(rows)

    def test_malformed_or_oversized_process_inventory_denies(self):
        for raw in ('','Uid: unknown','Uid: 1 1 1','Uid: 1 1 1 1\nUid: 1 1 1 1',
                    'Uid: 1 1 1 -1'):
            with self.assertRaises(ValueError): process_uids(raw)
        with self.assertRaises(ValueError): select({i:status(65534) for i in range(1,66)})
        with self.assertRaises(ValueError): select({1:status(1001),7:status(65534),'8':status(65534)})

    def test_helper_sources_compile_but_are_never_run_in_tests(self):
        for name,program in (('keeper',KEEPER_PROGRAM),('cleanup',CLEANUP_PROGRAM)):
            compile(program,name,'exec')
        self.assertIn('range(5)',CLEANUP_PROGRAM)
        self.assertIn("os.getpid()==1",KEEPER_PROGRAM)
        self.assertIn('os.waitpid(-1,os.WNOHANG)',KEEPER_PROGRAM)
        keeper=ast.parse(KEEPER_PROGRAM)
        calls=[n.func for n in ast.walk(keeper) if isinstance(n,ast.Call)]
        self.assertFalse(any(isinstance(f,ast.Attribute) and f.attr in ('fork','execv','execve','spawn','Popen') for f in calls))
