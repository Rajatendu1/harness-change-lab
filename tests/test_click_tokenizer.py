import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from harnesslab.click_tokenizer import verify_cache,CACHE_NAME,CACHE_SHA256,CACHE_BYTES,count_text_tokens
from harnesslab.click_image_plan import click_recipe,click_expected_environment
from harnesslab.click_token_counter import click_token_counter
from harnesslab.process_observation import KeeperIdentity


class TokenizerPreparationTests(unittest.TestCase):
    def test_missing_or_wrong_cache_refused_before_tiktoken_import(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch('harnesslab.click_tokenizer.importlib.metadata.version',return_value='0.12.0'):
                with self.assertRaises((ValueError,FileNotFoundError)):
                    count_text_tokens((('user','hello'),),directory=directory)
            path=Path(directory)/CACHE_NAME;path.write_bytes(b'wrong')
            with self.assertRaises(ValueError):verify_cache(directory)
            path.unlink();path.symlink_to('/unreadable-not-followed')
            with self.assertRaises((ValueError,FileNotFoundError)):verify_cache(directory)

    def test_pinned_cache_shape_and_separate_recipe(self):
        self.assertEqual(len(CACHE_SHA256),64)
        self.assertEqual(CACHE_BYTES,3613922)
        recipe=click_recipe('python@sha256:'+'a'*64)
        self.assertIn('COPY tokenizer-cache/ /opt/tokenizer-cache/',recipe)
        self.assertIn('RUN --network=none /opt/agent/bin/python -I -c',recipe)
        self.assertIn('TIKTOKEN_CACHE_DIR=/opt/tokenizer-cache',recipe)
        self.assertIn('tokenizer-LICENSE',recipe)
        self.assertIn('TIKTOKEN_CACHE_DIR=/opt/tokenizer-cache',click_expected_environment([], 'agent'))
        self.assertFalse(any('TIKTOKEN' in v for v in click_expected_environment([], 'verifier')))

    def test_counter_container_refuses_invalid_report_and_owns_cleanup(self):
        instances=[]
        class Adapter:
            def __init__(self,**kwargs):self.gid=1001;self.name='counter';self.calls=[];instances.append(self)
            def create_keeper(self):return KeeperIdentity(12345,1001,65534)
            def verify_denials(self):return b'fixed-denials-ok\n'
            def observe(self):return b'UID PID\n1001 12345\n',{'Running':True,'Paused':False,'Restarting':False,'Dead':False,'Pid':12345,'OOMKilled':False}
            def call(self,args,**kwargs):
                self.calls.append((args,kwargs))
                return b'{"estimated_tokens":100}'
            def remove_and_confirm_absent(self):self.calls.append('remove');return True
        with click_token_counter(image_policy='reviewed',adapter_factory=Adapter) as (counter,state):
            self.assertEqual(counter((('user','public input'),)),100)
            self.assertFalse(state['cleanup_confirmed'])
            args,kwargs=instances[0].calls[0]
            self.assertEqual(args[-1],'harnesslab.click_tokenizer')
            self.assertNotIn('click_editing_child',args)
            self.assertLess(len(kwargs['input_data']),32768)
        self.assertTrue(state['cleanup_confirmed'])
        self.assertEqual(instances[0].calls[-1],'remove')

    def test_counter_exception_still_removes_container(self):
        class Adapter:
            def __init__(self,**kwargs):pass
            def create_keeper(self):raise ValueError('setup failed')
            def remove_and_confirm_absent(self):removed.append(True);return True
        removed=[]
        with self.assertRaises(ValueError):
            with click_token_counter(image_policy='reviewed',adapter_factory=Adapter):pass
        self.assertEqual(removed,[True])


if __name__=='__main__':unittest.main()
