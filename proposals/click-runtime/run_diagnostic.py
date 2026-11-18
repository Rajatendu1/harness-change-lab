"""One explicit bounded no-key Click diagnostic entry. No live-model option.

Public immutable input hydration only; no credential or artifact publication.
"""
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
import urllib.parse
import urllib.request

ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from harnesslab.bounded_process import capture
from harnesslab.click_diagnostic import qualify_click,select_protected_test
from harnesslab.click_image_build import build_click_images
from harnesslab.click_image_plan import click_recipe,validate_click_context
from harnesslab.click_tokenizer import CACHE_URL,CACHE_SHA256,CACHE_NAME,CACHE_BYTES
from harnesslab.helper_packaging import helper_wheel

HERE=Path(__file__).resolve().parent
RUNTIME=ROOT/'proposals/docker-runtime'


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):return None


def fetch(item,*,host):
    url=urllib.parse.urlsplit(item['url'])
    if (url.scheme!='https' or url.hostname!=host or url.username or url.password
            or url.query or url.fragment or type(item['bytes']) is not int
            or not 0<=item['bytes']<=64*1024*1024):raise ValueError('Unexpected public input')
    opener=urllib.request.build_opener(NoRedirect())
    with opener.open(item['url'],timeout=20) as response:
        if response.status!=200:raise ValueError('Input unavailable')
        raw=response.read(item['bytes']+1)
    if len(raw)!=item['bytes'] or hashlib.sha256(raw).hexdigest()!=item['sha256']:
        raise ValueError('Public input identity mismatch')
    return raw


def assemble(directory):
    load=lambda name:json.loads((RUNTIME/name).read_text())
    manifests={role:load(role+'-wheel-manifest.json') for role in ('agent','verifier')}
    expected=json.loads((HERE/'helper-manifest.json').read_text());total=0
    for role in ('agent','verifier'):
        wheelhouse=directory/(role+'-wheelhouse');wheelhouse.mkdir()
        for item in manifests[role]['artifacts']:
            name=item['filename']
            if Path(name).name!=name or not name.endswith('.whl'):raise ValueError('Unexpected wheel name')
            total+=item['bytes']
            if total>192*1024*1024:raise ValueError('Wheel transfer budget exceeded')
            raw=fetch(dict(item,url=item['artifact_url']),host='files.pythonhosted.org')
            (wheelhouse/name).write_bytes(raw)
        shutil.copyfile(RUNTIME/('agent-cp310-linux-x86_64.hashes.txt' if role=='agent' else 'verifier-cp310.hashes.txt'),directory/(role+'.hashes.txt'))
        raw,helper=helper_wheel(ROOT,role=role)
        if helper!=expected[role]:raise ValueError('Helper source revision changed')
        target=directory/(role+'-helper');target.mkdir();(target/helper['filename']).write_bytes(raw)
        (directory/(role+'-helper.hashes.txt')).write_text('harness-fixture-helpers==0.0.1 --hash=sha256:'+helper['sha256']+'\n')
    cache=directory/'tokenizer-cache';cache.mkdir()
    (cache/CACHE_NAME).write_bytes(fetch({'url':CACHE_URL,'sha256':CACHE_SHA256,'bytes':CACHE_BYTES},host='openaipublic.blob.core.windows.net'))
    shutil.copyfile(HERE/'tokenizer-LICENSE',directory/'tokenizer-LICENSE')
    license_hash=json.loads((HERE/'tokenizer-manifest.json').read_text())['license_sha256']
    base=load('base-metadata-candidate.json')
    (directory/'Dockerfile').write_text(click_recipe('python@'+base['amd64_manifest_digest']))
    validate_click_context(directory,base_metadata=base,agent_manifest=manifests['agent'],verifier_manifest=manifests['verifier'],helper_manifest=expected,license_sha256=license_hash)
    return base,manifests,expected,license_hash


def task_inputs():
    manifest=json.loads((HERE/'task-inputs.json').read_text())
    base={item['name']:fetch(item,host='raw.githubusercontent.com') for item in manifest['base_files']}
    fixed=fetch(manifest['fixed_source'],host='raw.githubusercontent.com')
    protected=select_protected_test(fetch(manifest['test_source'],host='raw.githubusercontent.com'))
    return base,fixed,protected


def main():
    policies={};created=[];cleanup=True;result={'status':'click_setup_unverified'}
    try:
        with tempfile.TemporaryDirectory(prefix='click-diagnostic-build-') as temporary:
            directory=Path(temporary);base,manifests,helpers,license_hash=assemble(directory)
            source,fixed,protected=task_inputs()
            reference='python@'+base['amd64_manifest_digest']
            capture(['docker','pull','--platform','linux/amd64',reference],timeout_s=180,max_bytes=2*1024*1024)
            policies,inputs=build_click_images(directory,base_metadata=base,agent_manifest=manifests['agent'],
                verifier_manifest=manifests['verifier'],helper_manifest=helpers,license_sha256=license_hash,created_ids=created)
            result=qualify_click(base=source,known_fixed_source=fixed,protected_test=protected,
                image_policy=policies['agent'],verifier_policy=policies['verifier'])
            result['input_summary']=inputs
    except Exception:
        result={'status':'click_setup_or_execution_unverified'}
    finally:
        for content in set(created):
            try:capture(['docker','image','rm','--force',content],timeout_s=20,max_bytes=4096)
            except Exception:cleanup=False
    result.update(real_provider_calls=0,real_model_repairs=0,
                  image_cleanup_confirmed=cleanup and len(policies)==2)
    if not result['image_cleanup_confirmed']:result['status']='click_image_cleanup_or_setup_unverified'
    print(json.dumps(result,sort_keys=True))
    return 0 if result.get('status')=='click_model_free_task_mapping_passed' else 3


if __name__=='__main__':raise SystemExit(main())
