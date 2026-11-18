"""Static preparation checks only. Never executes resource probes on this host."""
import ast
import tempfile
import unittest

from harnesslab.docker_probes import ENFORCEMENT_PROBES, GUARD
from harnesslab.docker_qualification import DockerPolicy, create_command


class DockerProbePreparationTests(unittest.TestCase):
    def test_every_probe_compiles_and_begins_with_exact_cgroup_guard(self):
        self.assertEqual(set(ENFORCEMENT_PROBES),{'pids','memory','cpu','disk'})
        for name,program in ENFORCEMENT_PROBES.items():
            with self.subTest(name=name):
                self.assertTrue(program.startswith(GUARD))
                compile(program,'fixed-'+name,'exec')
                tree=ast.parse(program)
                for node in ast.walk(tree):
                    if isinstance(node,ast.keyword):
                        self.assertNotEqual(node.arg,'shell')
                    if isinstance(node,ast.Constant) and isinstance(node.value,str):
                        self.assertNotIn('https://',node.value)
                        self.assertNotIn('docker.sock',node.value)

    def test_command_selects_fixed_probe_and_rejects_arbitrary_code(self):
        with tempfile.TemporaryDirectory() as directory:
            args=('harness-preflight-'+'a'*32,'python@sha256:'+'b'*64,directory,1001,1001,DockerPolicy())
            for name,program in ENFORCEMENT_PROBES.items():
                self.assertEqual(create_command(*args,probe_name=name)[-1],program)
            with self.assertRaises(ValueError):
                create_command(*args,probe_name='print(arbitrary)')

    def test_probe_allocation_and_process_loops_are_fixed(self):
        self.assertIn('range(70)',ENFORCEMENT_PROBES['pids'])
        self.assertIn('range(9)',ENFORCEMENT_PROBES['memory'])
        self.assertIn('bytearray(256*1024*1024)',ENFORCEMENT_PROBES['memory'])
        self.assertIn('range(2)',ENFORCEMENT_PROBES['cpu'])
        self.assertIn('elapsed*1_000_000*1.25',ENFORCEMENT_PROBES['cpu'])
        self.assertIn('errno.ENOSPC',ENFORCEMENT_PROBES['disk'])
