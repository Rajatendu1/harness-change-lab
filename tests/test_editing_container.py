import os
from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import patch

from harnesslab.editing_container import editing_create_command, fixed_exec_command
from harnesslab.candidate_cleanup import KEEPER_PROGRAM,CLEANUP_PROGRAM
from harnesslab.trial_gateway import trial_gateway
from harnesslab.request_budget import TrialRequestBudget

NAME='harness-preflight-'+'d'*32
IMAGE='python@sha256:'+'a'*64


class EditingPolicyTests(unittest.TestCase):
    def test_distinct_identity_workspace_and_fixed_keeper_policy(self):
        with tempfile.TemporaryDirectory() as directory:
            args=editing_create_command(NAME,IMAGE,directory,gateway_gid=1001)
        self.assertEqual(args[args.index('--user')+1],'1001:1001')
        self.assertEqual(args[args.index('--group-add')+1],'1001')
        self.assertTrue(any(x.startswith('/work:') and 'uid=65534,gid=1001' in x for x in args))
        self.assertEqual(args[-1],KEEPER_PROGRAM)
        self.assertEqual(args[args.index('--network')+1],'none')
        self.assertEqual(args[args.index('--cap-drop')+1],'ALL')
        self.assertNotIn('--privileged',args)

    def test_exec_has_no_arbitrary_program_or_root_fallback(self):
        args=fixed_exec_command(NAME,operation='cleanup')
        self.assertIn('65534:65534',args)
        self.assertEqual(args[-1],CLEANUP_PROGRAM)
        for operation in ('agent','import','export','arbitrary'):
            with self.assertRaises(ValueError): fixed_exec_command(NAME,operation=operation)

    def test_shared_gateway_socket_only_group_permissions_restored(self):
        if os.getgid()==0:
            self.skipTest('Nonroot primary group required')
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); path=root/'provider.sock'
            with trial_gateway(TrialRequestBudget(1,lambda body:b'{}'),expected_model='fixture',
                               max_output_tokens=1,unix_path=str(path),shared_group=os.getgid()):
                self.assertEqual(stat.S_IMODE(root.stat().st_mode),0o750)
                self.assertEqual(stat.S_IMODE(path.stat().st_mode),0o660)
                self.assertEqual(list(root.iterdir()),[path])
            self.assertEqual(stat.S_IMODE(root.stat().st_mode),0o700)

    def test_shared_gateway_rejects_nonprivate_or_nonempty_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            for unsafe in ('nonempty','permissions'):
                if unsafe=='nonempty': (root/'controller-dummy').write_text('private-dummy')
                else: os.chmod(root,0o750)
                with self.assertRaises(ValueError):
                    with trial_gateway(None,expected_model='fixture',max_output_tokens=1,
                                       unix_path=str(root/'socket'),shared_group=os.getgid()):
                        self.fail('Unsafe directory accepted')
                (root/'controller-dummy').unlink(missing_ok=True)
                os.chmod(root,0o700)

    def test_shared_gateway_rejects_different_or_root_group(self):
        for group in (0,os.getgid()+1):
            with self.assertRaises(ValueError):
                with trial_gateway(None,expected_model='fixture',max_output_tokens=1,
                                   unix_path='/unused/socket',shared_group=group):
                    self.fail('Unsupported group accepted')
