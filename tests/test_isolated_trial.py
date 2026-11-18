import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest

from harnesslab.isolated_trial import isolated_trial
from harnesslab.request_budget import TrialRequestBudget


@unittest.skipUnless(shutil.which('bwrap'), 'Linux bubblewrap required')
class IsolatedTrialTests(unittest.TestCase):
    def run_child(self, script, *, timeout=5, transport=None):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'probe.py').write_text(script)
            budget = TrialRequestBudget(1, transport or (lambda body: b'{"choices":[]}'))
            result = isolated_trial(['/usr/bin/python3', 'probe.py'], workspace=root,
                                    budget=budget, model='fixture', max_output_tokens=32,
                                    timeout_s=timeout)
            data = (root / 'result.json').read_text() if (root / 'result.json').exists() else None
            return result, json.loads(data) if data else None

    def test_os_network_files_processes_and_environment_are_separate(self):
        os.environ['TRIAL_TEST_SECRET'] = 'not-a-real-secret'
        try:
            result, data = self.run_child('''
import json, os, socket, resource
s=socket.socket(); s.settimeout(1)
result={'interfaces':socket.if_nameindex(), 'external':s.connect_ex(('1.1.1.1',443)),
        'secret_present':'TRIAL_TEST_SECRET' in os.environ,
        'host_root_present':os.path.exists('/root'),
        'bootstrap_writable':os.access('/bootstrap.py',os.W_OK),
        'pid':os.getpid(), 'gateway_writable':os.access('/gateway',os.W_OK),
        'limits':{str(k):resource.getrlimit(k) for k in [resource.RLIMIT_AS,resource.RLIMIT_CPU,resource.RLIMIT_FSIZE,resource.RLIMIT_NOFILE,resource.RLIMIT_CORE]}}
try:
    os.unlink('/gateway/provider.sock')
    result['socket_unlink']='allowed'
except OSError:
    result['socket_unlink']='refused'
open('result.json','w').write(json.dumps(result))
''')
        finally:
            del os.environ['TRIAL_TEST_SECRET']
        self.assertEqual(result.status, 'process_exited')
        self.assertEqual([row[1] for row in data['interfaces']], ['lo'])
        self.assertNotEqual(data['external'], 0)
        self.assertFalse(data['secret_present'])
        self.assertFalse(data['host_root_present'])
        self.assertFalse(data['bootstrap_writable'])
        self.assertLess(data['pid'], 20)
        self.assertEqual(data['socket_unlink'], 'refused')
        import resource
        self.assertEqual(data['limits'][str(resource.RLIMIT_CORE)], [0,0])
        self.assertEqual(data['limits'][str(resource.RLIMIT_NOFILE)], [128,128])
        self.assertEqual(data['limits'][str(resource.RLIMIT_CPU)], [60,60])

    def test_unix_bridge_forwards_one_attempt_and_stops_excess(self):
        calls = []
        result, data = self.run_child('''
import json, os, urllib.request, urllib.error
statuses=[]
for _ in range(2):
    req=urllib.request.Request(os.environ['OPENAI_API_BASE']+'/chat/completions',
        data=b'{"model":"fixture","messages":[{"role":"user","content":"test"}]}',method='POST')
    try:
        with urllib.request.urlopen(req,timeout=2) as response: statuses.append(response.status)
    except urllib.error.HTTPError as error: statuses.append(error.code)
open('result.json','w').write(json.dumps(statuses))
''', transport=lambda body: calls.append(json.loads(body)) or b'{"choices":[]}')
        self.assertEqual(result.status, 'process_exited')
        self.assertEqual(data, [200, 400])
        self.assertEqual(result.provider_attempts, 1)
        self.assertEqual(calls[0]['max_tokens'], 32)

    def test_timeout_does_not_claim_task_success(self):
        result, data = self.run_child('import time; time.sleep(30)', timeout=0.3)
        self.assertEqual(result.status, 'wall_clock_timeout')
        self.assertIsNone(result.exit_code)
        self.assertIsNone(data)
        self.assertEqual(result.provider_attempts, 0)

    def test_nonzero_process_exit_is_distinct(self):
        result, _ = self.run_child('raise SystemExit(4)')
        self.assertEqual(result.status, 'process_failed')
        self.assertEqual(result.exit_code, 4)

    def test_no_isolation_means_no_fallback(self):
        from unittest.mock import patch
        with patch('harnesslab.isolated_trial.shutil.which', return_value=None):
            with self.assertRaises(RuntimeError):
                isolated_trial(['true'], workspace='.', budget=None, model='fixture',
                               max_output_tokens=32, timeout_s=1)

    def test_file_size_limit_stops_oversized_write(self):
        result, data = self.run_child("with open('oversized','wb') as f: f.write(b'x' * (17 * 1024 * 1024))")
        self.assertEqual(result.status, 'process_failed')
        self.assertEqual(result.provider_attempts, 0)


    def test_native_syscall_filter_is_active(self):
        result,data=self.run_child('''
import ctypes,json,errno
libc=ctypes.CDLL(None,use_errno=True)
ctypes.set_errno(0)
status=libc.unshare(0)
code=ctypes.get_errno()
open('result.json','w').write(json.dumps({'status':status,'errno':code}))
''')
        self.assertEqual(result.status,'process_exited')
        self.assertEqual(data,{'status':-1,'errno':13})


    def test_missing_filter_library_has_no_weaker_fallback(self):
        from unittest.mock import patch
        from harnesslab.syscall_filter import syscall_filter
        with patch('harnesslab.syscall_filter.ctypes.util.find_library',return_value=None):
            with self.assertRaises(RuntimeError):
                with syscall_filter():
                    self.fail('Unavailable filter must not execute')
