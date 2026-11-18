"""Prepared isolated tokenizer mapping, distinct container, never candidate IO.

Owns removal in every branch; call under approved runtime effects only.
"""
from contextlib import contextmanager
import json
import os
import tempfile

from .docker_fixture_adapter import DockerFixtureAdapter
from .process_observation import check_keeper_only


@contextmanager
def click_token_counter(*,image_policy,adapter_factory=DockerFixtureAdapter):
    state={'cleanup_confirmed':False,'status':'not_started'}
    with tempfile.TemporaryDirectory(prefix='click-counter-empty-') as directory:
        adapter=adapter_factory(image_policy=image_policy,socket_directory=directory,gateway_gid=os.getgid())
        try:
            identity=adapter.create_keeper()
            if adapter.verify_denials()!=b'fixed-denials-ok\n':raise ValueError('Counter denial preflight failed')
            check_keeper_only(*adapter.observe(),identity)
            def count(pairs):
                raw=json.dumps(pairs,ensure_ascii=False,allow_nan=False).encode()
                if len(raw)>32768:raise ValueError('Counter input oversized')
                check_keeper_only(*adapter.observe(),identity)
                args=['docker','exec','-i','--user',f'65534:{adapter.gid}',adapter.name,
                      'python3','-I','-m','harnesslab.click_tokenizer']
                response=adapter.call(args,timeout=15,max_bytes=1024,input_data=raw)
                check_keeper_only(*adapter.observe(),identity)
                row=json.loads(response)
                if (not isinstance(row,dict) or set(row)!={'estimated_tokens'}
                        or type(row['estimated_tokens']) is not int or row['estimated_tokens']<0):
                    raise ValueError('Tokenizer result unverified')
                return row['estimated_tokens']
            state['status']='prepared_counter_available'
            yield count,state
        finally:
            try:state['cleanup_confirmed']=adapter.remove_and_confirm_absent() is True
            except Exception:state['cleanup_confirmed']=False
            state['status']='counter_removed' if state['cleanup_confirmed'] else 'counter_cleanup_unconfirmed'
