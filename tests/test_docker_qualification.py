import copy
import json
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from harnesslab.docker_qualification import (DockerPolicy, PROBE, baseline_preflight,
                                            create_command, validate_inspect, baseline_summary)
from harnesslab.bounded_process import Captured, ControlledProcessError

from harnesslab.image_policy import ImagePolicy
IMAGE='python@sha256:'+'a'*64
POLICY=ImagePolicy(IMAGE,'sha256:'+'b'*64,(),1024**3)
IMAGE_INFO={'Id':POLICY.content_id,'RepoDigests':[IMAGE],'Os':'linux','Architecture':'amd64','Size':1024,'Config':{'Env':[]}}
NAME='harness-preflight-'+'b'*32


def inspected(directory):
    return {'HostConfig':{'ReadonlyRootfs':True,'NetworkMode':'none','Privileged':False,
            'Memory':2147483648,'MemorySwap':2147483648,'NanoCpus':1000000000,
            'PidsLimit':64,'Tmpfs':{'/work':'rw,noexec,nosuid,nodev,size=67108864,uid=1001,gid=1001','/tmp':'rw,noexec,nosuid,nodev,size=16777216,uid=1001,gid=1001'},'CapDrop':['ALL'],'SecurityOpt':['no-new-privileges'],
            'LogConfig':{'Type':'none'}},'Config':{'User':'1001:1001'},
            'Mounts':[{'Type':'bind','Source':directory,'Destination':'/gateway','RW':False}],
            'State':{'ExitCode':0,'OOMKilled':False}}


class DockerQualificationTests(unittest.TestCase):
    def test_command_has_no_pull_socket_or_host_workspace_escape(self):
        with tempfile.TemporaryDirectory() as directory:
            cmd=create_command(NAME,IMAGE,directory,1001,1001,DockerPolicy())
            self.assertEqual(cmd[:2],['docker','create'])
            self.assertNotIn('--env',cmd)
            self.assertNotIn('--privileged',cmd)
            self.assertEqual(cmd[cmd.index('--memory-swap')+1],'2147483648')
            self.assertEqual(cmd[cmd.index('--network')+1],'none')
            self.assertEqual(cmd[cmd.index('--log-driver')+1],'none')
            self.assertIn(f'type=bind,source={directory},target=/gateway,readonly',cmd)
            self.assertEqual(cmd[-3:],['-I','-c',PROBE])
            compile(PROBE,'fixed-docker-probe','exec')

    def test_invalid_image_identity_policy_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            for image,uid,gid in [('python:latest',1001,1001),(IMAGE,0,1001),(IMAGE,1001,0)]:
                with self.assertRaises(ValueError):
                    create_command(NAME,image,directory,uid,gid,DockerPolicy())
            with self.assertRaises(ValueError):
                DockerPolicy(pids=0)

    def test_mismatched_limits_and_privileges_fail(self):
        with tempfile.TemporaryDirectory() as directory:
            valid=inspected(directory)
            validate_inspect(valid,directory,1001,1001,DockerPolicy())
            for key,value in [('Memory',0),('MemorySwap',0),('NanoCpus',0),('PidsLimit',-1),
                    ('Privileged',True),('NetworkMode','host'),('ReadonlyRootfs',False),
                    ('SecurityOpt',['seccomp=unconfined']),('CapAdd',['SYS_ADMIN']),
                    ('LogConfig',{'Type':'json-file'}),('PidMode','host')]:
                bad=copy.deepcopy(valid); bad['HostConfig'][key]=value
                with self.subTest(key=key),self.assertRaises(ValueError):
                    validate_inspect(bad,directory,1001,1001,DockerPolicy())

    def test_writable_wrong_or_extra_mount_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            valid=inspected(directory)
            for mutate in (lambda d:d['Mounts'][0].update(RW=True),
                           lambda d:d['Mounts'][0].update(Source='/'),
                           lambda d:d['Mounts'].append({'Type':'bind','Source':'/var/run/docker.sock','Destination':'/var/run/docker.sock','RW':True}),
                           lambda d:d['Config'].update(User='0')):
                bad=copy.deepcopy(valid);mutate(bad)
                with self.assertRaises(ValueError):
                    validate_inspect(bad,directory,1001,1001,DockerPolicy())

    def test_no_docker_no_subprocess_or_network_fallback(self):
        with patch('harnesslab.docker_qualification.shutil.which',return_value=None), \
             patch('harnesslab.docker_qualification.capture') as run:
            result=baseline_preflight(IMAGE,reviewed_image=POLICY)
        run.assert_not_called()
        self.assertEqual(result,{'status':'unavailable','executed':False,'qualification_complete':False})

    def test_timeout_removes_container_and_checks_absence(self):
        calls=[]
        def fake(args,**kwargs):
            calls.append(args)
            if args[1:3]==['image','inspect']:
                return Captured(json.dumps([IMAGE_INFO]).encode(),0)
            if args[1:3]==['start','--attach']:
                raise ControlledProcessError('wall_timeout')
            if args[1]=='inspect':
                directory=next(a.split('source=')[1].split(',')[0] for cmd in calls if cmd[1]=='create' for a in cmd if 'type=bind,source=' in a)
                return Captured(json.dumps([inspected(directory)]).encode(),0)
            return Captured(b'',0)
        with patch('harnesslab.docker_qualification.shutil.which',return_value='/usr/bin/docker'), \
             patch('harnesslab.docker_qualification.os.getuid',return_value=1001), \
             patch('harnesslab.docker_qualification.os.getgid',return_value=1001), \
             patch('harnesslab.docker_qualification.capture',side_effect=fake):
            with self.assertRaises(ControlledProcessError):
                baseline_preflight(IMAGE,reviewed_image=POLICY)
        self.assertEqual(calls[-2][1:3],['rm','--force'])
        self.assertEqual(calls[-1][1:3],['ps','-aq'])
        self.assertFalse(any('pull' in c or 'build' in c for c in calls))

    def test_failed_cleanup_cannot_report_success(self):
        calls=[]
        def fake(args,**kwargs):
            calls.append(args)
            if args[1:3]==['image','inspect']:
                return Captured(json.dumps([IMAGE_INFO]).encode(),0)
            if args[1]=='create':
                raise ValueError('fixed create fixture fails')
            if args[1]=='rm':
                raise RuntimeError('cleanup unconfirmed')
            return Captured(b'',0)
        with patch('harnesslab.docker_qualification.shutil.which',return_value='/usr/bin/docker'), \
             patch('harnesslab.docker_qualification.os.getuid',return_value=1001), \
             patch('harnesslab.docker_qualification.os.getgid',return_value=1001), \
             patch('harnesslab.docker_qualification.capture',side_effect=fake):
            with self.assertRaisesRegex(RuntimeError,'cleanup unconfirmed'):
                baseline_preflight(IMAGE,reviewed_image=POLICY)
        self.assertEqual(calls[-1][1:3],['rm','--force'])

    def test_summary_never_exposes_raw_failure(self):
        for error,reason in ((ControlledProcessError('output_limit'),'output_limit'),
                             (ValueError('private-dummy-output'),'policy_or_probe_invalid'),
                             (OSError('private-dummy-path'),'policy_or_probe_invalid')):
            with patch('harnesslab.docker_qualification.baseline_preflight',side_effect=error):
                result=baseline_summary(IMAGE)
            self.assertEqual(result,{'status':'failed','reason':reason,'qualification_complete':False})
            self.assertNotIn('private',str(result))

    def test_suite_stops_first_failure_and_reports_no_qualification(self):
        from harnesslab.docker_qualification import fixed_suite_summary
        def fixed(image,*,probe_name,reviewed_image=None):
            if probe_name=='memory':
                raise ControlledProcessError('wall_timeout')
            return {'status':'probe_pass','probe':probe_name,'qualification_complete':False}
        with patch('harnesslab.docker_qualification.fixed_probe_preflight',side_effect=fixed) as run:
            result=fixed_suite_summary(IMAGE)
        self.assertEqual([call.kwargs['probe_name'] for call in run.call_args_list],['baseline','pids','memory'])
        self.assertEqual(result['status'],'incomplete_or_failed')
        self.assertFalse(result['qualification_complete'])
        self.assertEqual(result['records'][-1]['reason'],'wall_timeout')

    def test_all_fixed_probes_pass_still_not_adapter_qualification(self):
        from harnesslab.docker_qualification import fixed_suite_summary
        with patch('harnesslab.docker_qualification.fixed_probe_preflight',side_effect=lambda image,probe_name,reviewed_image=None: {'status':'probe_pass','probe':probe_name}):
            result=fixed_suite_summary(IMAGE)
        self.assertEqual(result['status'],'fixed_probes_pass')
        self.assertEqual(len(result['records']),5)
        self.assertFalse(result['qualification_complete'])
        self.assertEqual(result['aider_adapter'],'not_qualified')

    def test_no_docker_suite_does_not_invoke_any_subprocess(self):
        from harnesslab.docker_qualification import fixed_suite_summary
        with patch('harnesslab.docker_qualification.shutil.which',return_value=None), \
             patch('harnesslab.docker_qualification.capture') as run:
            result=fixed_suite_summary(IMAGE)
        run.assert_not_called()
        self.assertEqual(len(result['records']),1)
        self.assertEqual(result['records'][0]['status'],'unavailable')

    def test_missing_reviewed_image_policy_cannot_launch_docker(self):
        with patch('harnesslab.docker_qualification.shutil.which',return_value='/usr/bin/docker'), \
             patch('harnesslab.docker_qualification.capture') as run:
            result=baseline_summary(IMAGE)
        run.assert_not_called()
        self.assertEqual(result['reason'],'policy_or_probe_invalid')

    def test_inspect_requires_both_bounded_tmpfs_mounts_and_correct_owner(self):
        with tempfile.TemporaryDirectory() as directory:
            for tmpfs in (None,{}, {'/work':'rw,size=67108864'},
                          {'/work':'rw,noexec,nosuid,nodev,size=67108864,uid=0,gid=1001',
                           '/tmp':'rw,noexec,nosuid,nodev,size=16777216,uid=1001,gid=1001'}):
                bad=inspected(directory);bad['HostConfig']['Tmpfs']=tmpfs
                with self.assertRaises(ValueError):
                    validate_inspect(bad,directory,1001,1001,DockerPolicy())

    def test_local_content_id_creation_still_forbids_pull_and_tags(self):
        with tempfile.TemporaryDirectory() as directory:
            content='sha256:'+'c'*64
            args=create_command(NAME,content,directory,1001,1001,DockerPolicy())
            self.assertIn(content,args)
            self.assertEqual(args[args.index('--pull')+1],'never')
            for bad in ('sha256:short','local:latest','sha256:'+'g'*64):
                with self.assertRaises(ValueError):create_command(NAME,bad,directory,1001,1001,DockerPolicy())
