"""Proposed offline build-to-policy binding. No automatic execution.

Calling build_images runs Docker build and requires separate approval. Expected
configuration comes from pinned base metadata plus reviewed recipe, not image.
"""
import hashlib
import json
from pathlib import Path
import re
import tempfile

from .bounded_process import capture
from .image_policy import ImagePolicy,validate_image
from .offline_recipe import offline_recipe


def expected_environment(base_environment,role):
    if role not in ('agent','verifier'):raise ValueError('Unknown image role')
    values={item.split('=',1)[0]:item.split('=',1)[1] for item in base_environment}
    values.update(PIP_DISABLE_PIP_VERSION_CHECK='1',PIP_NO_CACHE_DIR='1',
                  PATH='/opt/'+role+'/bin:/usr/local/bin:/usr/bin:/bin')
    return tuple(key+'='+value for key,value in sorted(values.items()))


def validate_context(context,*,base_metadata,agent_manifest,verifier_manifest,helper_manifest):
    root=Path(context)
    if root.is_symlink() or not root.is_dir():raise ValueError('Invalid build input directory')
    expected={'Dockerfile':offline_recipe('python@'+base_metadata['amd64_manifest_digest']).encode()}
    manifests={'agent':agent_manifest,'verifier':verifier_manifest}
    for role,manifest in manifests.items():
        lines=[]
        for item in sorted(manifest['artifacts'],key=lambda item:item['name']):
            expected[role+'-wheelhouse/'+item['filename']]=item['sha256']
            lines.append(item['name']+'=='+item['version']+' --hash=sha256:'+item['sha256']+'\n')
        expected[role+'.hashes.txt']=''.join(lines).encode()
        helper=helper_manifest[role]
        expected[role+'-helper/'+helper['filename']]=helper['sha256']
        expected[role+'-helper.hashes.txt']=('harness-fixture-helpers==0.0.1 --hash=sha256:'+helper['sha256']+'\n').encode()
    actual={}
    for file in root.rglob('*'):
        if file.is_symlink():raise ValueError('Linked build input rejected')
        if file.is_file():actual[file.relative_to(root).as_posix()]=file
    if actual.keys()!=expected.keys():raise ValueError('Unexpected or missing build inputs')
    total=0
    for name,identity in expected.items():
        path=actual[name];total+=path.stat().st_size
        if total>256*1024*1024:raise ValueError('Build inputs exceed bound')
        digest=hashlib.sha256(path.read_bytes()).hexdigest()
        wanted=hashlib.sha256(identity).hexdigest() if isinstance(identity,bytes) else identity
        if digest!=wanted:raise ValueError('Build input identity mismatch')
    return {'files':len(actual),'bytes':total,'input_policy':'exact_hash_allowlist'}


def build_images(context,*,base_metadata,agent_manifest,verifier_manifest,helper_manifest,runner=capture,created_ids=None):
    validation=validate_context(context,base_metadata=base_metadata,agent_manifest=agent_manifest,
        verifier_manifest=verifier_manifest,helper_manifest=helper_manifest)
    policies={}
    with tempfile.TemporaryDirectory(prefix='build-id-') as directory:
        for role in ('agent','verifier'):
            iid=Path(directory)/(role+'.id')
            try:
                runner(['docker','build','--network=none','--pull=false','--target',role,
                        '--iidfile',str(iid),str(Path(context).resolve())],timeout_s=300,max_bytes=2*1024*1024)
            finally:
                if created_ids is not None and iid.exists():
                    observed=iid.read_text().strip()
                    if re.fullmatch(r'sha256:[a-f0-9]{64}',observed):
                        created_ids.append(observed)
            content=iid.read_text().strip()
            if not re.fullmatch(r'sha256:[a-f0-9]{64}',content):raise ValueError('Build identity missing')
            policy=ImagePolicy(content,content,expected_environment(base_metadata['config']['Env'],role),4*1024**3)
            data=json.loads(runner(['docker','image','inspect',content],timeout_s=10,max_bytes=1024*1024).stdout)
            if len(data)!=1:raise ValueError('Unexpected built image identity')
            validate_image(data[0],policy)
            policies[role]=policy
    return policies,validation
