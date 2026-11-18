from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from harnesslab.runtime_preflight import inspect_os_isolation, inspect_runtime


class RuntimePreflightTests(unittest.TestCase):
    def test_missing_isolation_reports_unavailable_not_pass(self):
        with patch('harnesslab.runtime_preflight.shutil.which', return_value=None):
            self.assertEqual(inspect_os_isolation()['namespace_probe'], 'unavailable')

    @unittest.skipUnless(shutil.which('bwrap'), 'Linux namespaces required')
    def test_real_namespace_probe_does_not_claim_aggregate_controls(self):
        result = inspect_os_isolation()
        self.assertEqual(result['namespace_probe'], 'passed')
        self.assertEqual(result['aggregate_resources'], 'not_verified')

    @unittest.skipUnless(Path('/tmp/harness-verifier-runtime/bin/python').exists(), 'Pinned runtime required')
    def test_real_pinned_runtime(self):
        result = inspect_runtime('/tmp/harness-verifier-runtime/bin/python', '/tmp/harness-verifier-runtime')
        self.assertEqual(result['pytest'], '8.3.5')

    def test_runtime_symlink_escape_rejected_before_execution(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'python').symlink_to('/bin/false')
            # /bin/false resolves in /usr, but is not Python and must still fail.
            with self.assertRaises(ValueError):
                inspect_runtime(root / 'python', root)


class RuntimePreflightCliTests(unittest.TestCase):
    def test_cli_reports_no_authority_and_unverified_aggregate_limits(self):
        import contextlib, io, json
        from harnesslab.cli import main
        output=io.StringIO()
        with patch('harnesslab.cli.inspect_runtime', return_value={'pytest':'8.3.5'}), \
             patch('harnesslab.cli.inspect_os_isolation', return_value={'namespace_probe':'passed','aggregate_resources':'not_verified'}), \
             contextlib.redirect_stdout(output):
            code=main(['runtime-preflight','--python','fixture','--runtime-root','fixture'])
        self.assertEqual(code,0)
        data=json.loads(output.getvalue())
        self.assertEqual(data['execution_authority'],'none')
        self.assertEqual(data['provider_calls'],0)
        self.assertEqual(data['isolation']['aggregate_resources'],'not_verified')

    def test_cli_missing_isolation_abstains(self):
        import contextlib, io
        from harnesslab.cli import main
        with patch('harnesslab.cli.inspect_runtime',return_value={}), \
             patch('harnesslab.cli.inspect_os_isolation',return_value={'namespace_probe':'unavailable'}), \
             contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(['runtime-preflight','--python','fixture','--runtime-root','fixture']),3)


class MalformedProbeTests(unittest.TestCase):
    def test_successful_exit_with_garbage_is_failure(self):
        import subprocess
        for output in ('garbage','{}','[]'):
            with patch('harnesslab.runtime_preflight.shutil.which',return_value='/fixture/bwrap'), \
                 patch('harnesslab.runtime_preflight.subprocess.run',return_value=subprocess.CompletedProcess([],0,output,'')):
                self.assertEqual(inspect_os_isolation()['namespace_probe'],'failed')
