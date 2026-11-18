"""PROPOSAL ONLY: bounded one-job hydration/build/fixed qualification.

Never run without separate exact model-free job approval. No model credentials.
No active workflow calls this. Public artifact URLs come from committed manifests.
"""
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
import urllib.parse
import urllib.request

sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from harnesslab.bounded_process import capture
from harnesslab.fixed_qualification import qualify_fixed
from harnesslab.helper_packaging import helper_wheel
from harnesslab.offline_build_plan import build_images,validate_context

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):return None


def hydrate(manifest,destination):
    destination.mkdir()
    opener=urllib.request.build_opener(NoRedirect())
    total=0
    for item in manifest['artifacts']:
        parsed=urllib.parse.urlsplit(item['artifact_url'])
        name=item['filename']
        if (parsed.scheme!='https' or parsed.hostname!='files.pythonhosted.org'
                or parsed.username or parsed.password or parsed.query or parsed.fragment
                or Path(name).name!=name or not name.endswith('.whl')
                or type(item['bytes']) is not int or not 0<item['bytes']<=64*1024*1024):
            raise ValueError('Unexpected artifact source/bound')
        digest=hashlib.sha256();count=0
        with opener.open(item['artifact_url'],timeout=15) as response, (destination/name).open('xb') as output:
            while True:
                chunk=response.read(65536)
                if not chunk:break
                count+=len(chunk);total+=len(chunk)
                if count>item['bytes'] or total>192*1024*1024:raise ValueError('Artifact transfer limit')
                digest.update(chunk);output.write(chunk)
        if count!=item['bytes'] or digest.hexdigest()!=item['sha256']:
            raise ValueError('Artifact hash/size mismatch')


def assemble(directory):
    load=lambda name:json.loads((HERE/name).read_text())
    manifests={role:load(role+'-wheel-manifest.json') for role in ('agent','verifier')}
    expected_helpers=load('helper-package-manifest.json')
    for role in ('agent','verifier'):
        hydrate(manifests[role],directory/(role+'-wheelhouse'))
        lock='agent-cp310-linux-x86_64.hashes.txt' if role=='agent' else 'verifier-cp310.hashes.txt'
        shutil.copyfile(HERE/lock,directory/(role+'.hashes.txt'))
        raw,helper=helper_wheel(ROOT,role=role)
        if helper['sha256']!=expected_helpers[role]['sha256']:
            raise ValueError('Helper revision does not match reviewed manifest')
        target=directory/(role+'-helper');target.mkdir();(target/helper['filename']).write_bytes(raw)
        (directory/(role+'-helper.hashes.txt')).write_text('harness-fixture-helpers==0.0.1 --hash=sha256:'+helper['sha256']+'\n')
    shutil.copyfile(HERE/'Dockerfile.prepared',directory/'Dockerfile')
    base=load('base-metadata-candidate.json')
    validate_context(directory,base_metadata=base,agent_manifest=manifests['agent'],
        verifier_manifest=manifests['verifier'],helper_manifest=expected_helpers)
    return base,manifests,expected_helpers


def main():
    policies={};created_ids=[];result={'status':'setup_unverified'};cleanup=True
    try:
        with tempfile.TemporaryDirectory(prefix='fixed-qualification-input-') as temporary:
            root=Path(temporary);base,manifests,helpers=assemble(root)
            # Explicit public immutable base retrieval, new effect in proposal.
            # No implicit docker-create/build pull fallback permitted.
            reference='python@'+base['amd64_manifest_digest']
            capture(['docker','pull','--platform','linux/amd64',reference],timeout_s=180,max_bytes=2*1024*1024)
            policies,inputs=build_images(root,base_metadata=base,agent_manifest=manifests['agent'],
                verifier_manifest=manifests['verifier'],helper_manifest=helpers,created_ids=created_ids)
            result=qualify_fixed(image_policy=policies['agent'],verifier_policy=policies['verifier'])
            result['input_summary']=inputs
    except Exception:
        result={'status':'qualification_setup_or_execution_failed','real_provider_calls':0,'real_model_repairs':0}
    finally:
        # Capture iidfile identities even if later inspect/second build fails.
        # Fresh ephemeral runner removes intermediate build cache at job end.
        for content_id in set(created_ids):
            try:capture(['docker','image','rm','--force',content_id],timeout_s=20,max_bytes=4096)
            except Exception:cleanup=False
    result['built_image_cleanup_confirmed']=cleanup and len(policies)==2
    if not result['built_image_cleanup_confirmed']:result['status']='cleanup_or_setup_unverified'
    print(json.dumps(result,sort_keys=True))
    return 0 if result.get('status')=='fixed_adapter_scope_passed' else 3


if __name__=='__main__':raise SystemExit(main())
