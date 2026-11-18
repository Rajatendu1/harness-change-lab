import copy
import unittest

from harnesslab.image_policy import ImagePolicy, validate_image

REFERENCE='python@sha256:'+'a'*64
CONTENT='sha256:'+'b'*64


def reviewed():
    return ImagePolicy(REFERENCE,CONTENT,('PATH=/usr/local/bin:/usr/bin:/bin','LANG=C.UTF-8'),1024**3)


def fixture():
    return {'Id':CONTENT,'RepoDigests':[REFERENCE],'Os':'linux','Architecture':'amd64','Size':1024,
            'Config':{'Env':['LANG=C.UTF-8','PATH=/usr/local/bin:/usr/bin:/bin'],
                      'Entrypoint':None,'User':'','Volumes':None,'OnBuild':None,'Healthcheck':None}}


class ImagePolicyTests(unittest.TestCase):
    def test_exact_identity_and_reviewed_environment_match_not_runtime_verdict(self):
        self.assertEqual(validate_image(fixture(),reviewed()),
                         {'identity':'matched_reviewed_manifest','inherited_configuration':'matched',
                          'runtime_safety':'not_verified'})

    def test_wrong_identity_arch_size_and_registry_digest_rejected(self):
        for key,value in (('Id','sha256:'+'c'*64),('RepoDigests',[]),('Os','windows'),
                          ('Architecture','arm64'),('Size',0),('Size',True),('Size',2*1024**3)):
            data=fixture();data[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError): validate_image(data,reviewed())

    def test_image_side_effects_and_unreviewed_environment_rejected(self):
        for key,value in (('Volumes',{'/work':{}}),('OnBuild',['RUN touch /x']),
                          ('Healthcheck',{'Test':['CMD','python3','/unexpected']}),
                          ('Entrypoint',['/unexpected']),('User','0'),
                          ('Env',['PATH=/unreviewed']),('Env',['PATH=/usr/local/bin:/usr/bin:/bin',
                           'LANG=C.UTF-8','TOKEN=dummy-not-secret'])):
            data=fixture();data['Config'][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError): validate_image(data,reviewed())

    def test_no_policy_means_no_provenance_pass(self):
        with self.assertRaises(ValueError): validate_image(fixture(),None)
        for values in (('python:latest',CONTENT,(),1024),(REFERENCE,'wrong',(),1024),
                       (REFERENCE,CONTENT,('A=1','A=2'),1024),(REFERENCE,CONTENT,(),0)):
            with self.assertRaises(ValueError): ImagePolicy(*values)

    def test_reviewed_local_build_content_id_needs_no_registry_publication(self):
        policy=ImagePolicy(CONTENT,CONTENT,reviewed().environment,1024**3)
        data=fixture();data['RepoDigests']=[]
        self.assertEqual(validate_image(data,policy)['identity'],'matched_reviewed_manifest')
        data['Id']='sha256:'+'c'*64
        with self.assertRaises(ValueError):validate_image(data,policy)
        with self.assertRaises(ValueError):ImagePolicy('sha256:'+'c'*64,CONTENT,(),1024)
