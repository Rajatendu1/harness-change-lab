import json
import tempfile
import unittest
from unittest.mock import patch

from harnesslab.bounded_process import Captured
from harnesslab.candidate_cleanup import KEEPER_PROGRAM
from harnesslab.docker_fixture_adapter import DockerFixtureAdapter,run_fixture
from harnesslab.docker_fixture_child import BASE,NAMES
from harnesslab.fixture_editing_session import FixtureEditingSession
from harnesslab.image_policy import ImagePolicy
from harnesslab.source_bundle import pack_sources

POLICY=ImagePolicy('python@sha256:'+'a'*64,'sha256:'+'b'*64,(),1024**3)


class DockerMappingTests(unittest.TestCase):
    def test_concrete_mapping_with_simulated_daemon_no_docker_execution(self):
        with tempfile.TemporaryDirectory() as directory:
            calls=[]; started=False
            def runner(args,**kwargs):
                nonlocal started
                calls.append((args,kwargs))
                if args[1:3]==['image','inspect']:
                    raw=json.dumps([{'Id':POLICY.content_id,'RepoDigests':[POLICY.reference],
                        'Os':'linux','Architecture':'amd64','Size':1024,'Config':{'Env':[]}}]).encode()
                elif args[1]=='inspect':
                    raw=json.dumps([{'HostConfig':{'ReadonlyRootfs':True,'NetworkMode':'none',
                        'Privileged':False,'Memory':2147483648,'MemorySwap':2147483648,
                        'NanoCpus':10**9,'PidsLimit':64,'GroupAdd':['1001'],'Tmpfs':{'/work':'rw,noexec,nosuid,nodev,size=67108864,uid=65534,gid=1001','/tmp':'rw,noexec,nosuid,nodev,size=16777216,uid=65534,gid=1001'},'CapDrop':['ALL'],
                        'SecurityOpt':['no-new-privileges'],'LogConfig':{'Type':'none'}},
                        'Image':POLICY.content_id,'Config':{'User':'1001:1001','Entrypoint':['python3'],'Cmd':['-I','-c',KEEPER_PROGRAM],'Env':[]},'Mounts':[{'Type':'bind','Source':directory,
                        'Destination':'/gateway','RW':False}],
                        'State':{'Running':started,'Paused':False,'Restarting':False,'Dead':False,
                                 'Pid':12345,'OOMKilled':False}}]).encode()
                elif args[1]=='start':started=True;raw=b''
                elif args[1]=='top': raw=b'UID PID\n1001 12345\n'
                elif args[1]=='exec':
                    operation=args[-1]
                    if operation=='import':
                        self.assertEqual(kwargs['input_data'],pack_sources(BASE));raw=b'source-import-ok\n'
                    elif operation=='canned':raw=b'canned-agent-finished\n'
                    elif operation=='export':raw=pack_sources({'example.py':b'def answer():\n    return 1\n'})
                    elif 'fixed-denials-ok' in operation:raw=b'fixed-denials-ok\n'
                    else:raw=b'candidate-cleanup-ok\n'
                    self.assertIn('65534:1001',args)
                else:raw=b''
                return Captured(raw,0)
            with patch('harnesslab.docker_fixture_adapter.os.getuid',return_value=1001), \
                 patch('harnesslab.docker_fixture_adapter.os.getgid',return_value=1001):
                adapter=DockerFixtureAdapter(image_policy=POLICY,socket_directory=directory,gateway_gid=1001,runner=runner)
                result=FixtureEditingSession(adapter).run(base=BASE,editable_names=NAMES)
            self.assertEqual(result['status'],'fixture_candidate_collected')
            self.assertEqual(result['candidate'],{'example.py':b'def answer():\n    return 1\n'})
            self.assertEqual(calls[-2][0][1:3],['rm','--force'])
            self.assertEqual(calls[-1][0][1:3],['ps','-aq'])
            self.assertFalse(any('pull' in a or 'build' in a for a,k in calls))
            export=next((a,k) for a,k in calls if a[1]=='exec' and a[-1]=='export')
            self.assertEqual(export[1]['max_bytes'],80*1024*1024)

    def test_fixed_fixture_rejects_other_tasks_or_exec_commands(self):
        with tempfile.TemporaryDirectory() as directory, \
             patch('harnesslab.docker_fixture_adapter.os.getuid',return_value=1001), \
             patch('harnesslab.docker_fixture_adapter.os.getgid',return_value=1001):
            calls=[]
            adapter=DockerFixtureAdapter(image_policy=POLICY,socket_directory=directory,gateway_gid=1001,
                runner=lambda *a,**k:calls.append(a))
            for action in (lambda:adapter.import_base(pack_sources({'different.py':b'x'}),('different.py',)),
                           lambda:adapter.exec('arbitrary'),lambda:adapter.export_sources(('different.py',))):
                with self.assertRaises(ValueError):action()
            self.assertEqual(calls,[])

    def test_wrapper_drops_source_and_never_qualifies_on_mocked_collection(self):
        class Adapter:
            def __init__(self,**kwargs): pass
        candidate={'example.py':b'def answer():\n    return 1\n'}
        with patch('harnesslab.docker_fixture_adapter.DockerFixtureAdapter',Adapter), \
             patch('harnesslab.docker_fixture_adapter.FixtureEditingSession.run',
                   return_value={'status':'fixture_candidate_collected','candidate':candidate,
                                 'qualification_complete':False,'real_provider_calls':0}):
            result=run_fixture(image_policy=POLICY)
        self.assertNotIn('candidate',result)
        self.assertNotIn('def answer',str(result))
        self.assertFalse(result['runtime_qualified'])
        self.assertEqual(result['status'],'fixture_failed') # no actual fixture request
