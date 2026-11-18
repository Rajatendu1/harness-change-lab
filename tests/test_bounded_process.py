import os
from pathlib import Path
import signal
import sys
import tempfile
import time
import unittest

from harnesslab.bounded_process import ControlledProcessError, capture


class BoundedProcessTests(unittest.TestCase):
    def python(self, program, **kwargs):
        return capture([sys.executable,'-I','-c',program],**kwargs)

    def test_success_stdout_only_and_environment_cleared(self):
        os.environ['BOUNDED_TEST_SENTINEL']='dummy-not-secret'
        try:
            result=self.python('import os,sys; assert "BOUNDED_TEST_SENTINEL" not in os.environ; print("ok"); print("discard",file=sys.stderr)')
        finally:
            del os.environ['BOUNDED_TEST_SENTINEL']
        self.assertEqual(result.stdout,b'ok\n')
        self.assertEqual(result.returncode,0)

    def test_stdout_and_stderr_count_together_before_buffering(self):
        for fd in (1,2):
            with self.subTest(fd=fd),self.assertRaises(ControlledProcessError) as raised:
                self.python(f'import os; os.write({fd},b"x"*10000)',max_bytes=100)
            self.assertEqual(raised.exception.category,'output_limit')
        with self.assertRaises(ControlledProcessError) as raised:
            self.python('import os; os.write(1,b"a"*60); os.write(2,b"b"*60)',max_bytes=100)
        self.assertEqual(raised.exception.category,'output_limit')

    def test_nonzero_output_is_not_exception_content(self):
        with self.assertRaises(ControlledProcessError) as raised:
            self.python('import sys; print("private-dummy"); print("private-error",file=sys.stderr); sys.exit(4)')
        self.assertEqual(str(raised.exception),'nonzero_exit')
        self.assertNotIn('private',repr(raised.exception))

    def test_timeout_with_and_without_open_pipes(self):
        for program in ('import time; time.sleep(20)',
                        'import os,time; os.close(1); os.close(2); time.sleep(20)'):
            with self.assertRaises(ControlledProcessError) as raised:
                self.python(program,timeout_s=.1)
            self.assertEqual(raised.exception.category,'wall_timeout')

    def test_descendant_holding_pipe_does_not_escape_deadline(self):
        with tempfile.TemporaryDirectory() as directory:
            pidfile=Path(directory)/'pid'
            program=('import os,time; pid=os.fork()\n'
                     'if pid==0: time.sleep(30)\n'
                     f'else: open({str(pidfile)!r},"w").write(str(pid))\n')
            started=time.monotonic()
            with self.assertRaises(ControlledProcessError) as raised:
                self.python(program,timeout_s=.2)
            self.assertEqual(raised.exception.category,'wall_timeout')
            self.assertLess(time.monotonic()-started,3)
            pid=int(pidfile.read_text())
            # A killed orphan may remain zombie until host init reaps it.
            status=Path(f'/proc/{pid}/status')
            deadline=time.monotonic()+1
            while status.exists():
                try:
                    text=status.read_text()
                except (FileNotFoundError, ProcessLookupError):
                    break
                if 'State:\tZ' in text:
                    break
                if time.monotonic()>=deadline:
                    self.fail('Descendant did not stop after bounded kill grace')
                time.sleep(.01)

    def test_no_shell_and_invalid_limits_refused(self):
        for kwargs in ({'timeout_s':0},{'timeout_s':float('nan')},{'max_bytes':0},
                       {'max_bytes':True},{'max_bytes':81*1024*1024}):
            with self.assertRaises(ValueError): self.python('pass',**kwargs)
        with self.assertRaises(ValueError): capture('echo unsafe')
        with self.assertRaises(ControlledProcessError) as raised:
            capture(['/this-path-does-not-exist'])
        self.assertEqual(raised.exception.category,'launch_failed')

    def test_bounded_input_roundtrip_and_empty_eof(self):
        payload=b'0123456789'*100000
        result=self.python('import sys,hashlib; print(hashlib.sha256(sys.stdin.buffer.read()).hexdigest())',
                           input_data=payload)
        import hashlib
        self.assertEqual(result.stdout.strip(),hashlib.sha256(payload).hexdigest().encode())
        self.assertEqual(self.python('import sys; print(len(sys.stdin.buffer.read()))',input_data=b'').stdout,b'0\n')

    def test_full_duplex_drain_prevents_input_output_deadlock(self):
        result=self.python('import os,sys; os.write(2,b"x"*200000); data=sys.stdin.buffer.read(); print(len(data))',
                           input_data=b'a'*200000,max_bytes=210000)
        self.assertEqual(result.stdout,b'200000\n')

    def test_blocked_input_times_out_and_early_pipe_close_is_controlled(self):
        with self.assertRaises(ControlledProcessError) as raised:
            self.python('import time; time.sleep(30)',input_data=b'x'*1000000,timeout_s=.1)
        self.assertEqual(raised.exception.category,'wall_timeout')
        with self.assertRaises(ControlledProcessError) as raised:
            self.python('import os,time; os.close(0); time.sleep(.2)',input_data=b'x'*1000000)
        self.assertEqual(raised.exception.category,'input_not_consumed')

    def test_input_type_and_size_rejected_before_launch(self):
        for data in ('text',bytearray(b'x'),b'x'*(80*1024*1024+1)):
            with self.assertRaises(ValueError): self.python('pass',input_data=data)
