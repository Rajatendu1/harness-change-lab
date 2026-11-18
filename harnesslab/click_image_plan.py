"""Click-specific offline recipe/input review, no build or download operation.

Keeps the historical fixed-fixture recipe unchanged. New encoding input is
checksum-bound and includes its upstream license notice.
"""
import hashlib
from pathlib import Path

from .click_tokenizer import CACHE_NAME,CACHE_SHA256,CACHE_BYTES
from .offline_recipe import offline_recipe
from .offline_build_plan import expected_environment


def click_recipe(base_reference):
    source=offline_recipe(base_reference)
    marker='ENV PATH=/opt/agent/bin:/usr/local/bin:/usr/bin:/bin\n'
    if source.count(marker)!=1:raise ValueError('Agent recipe structure changed')
    return source.replace(marker,
        'COPY tokenizer-cache/ /opt/tokenizer-cache/\n'
        'COPY tokenizer-LICENSE /opt/licenses/tiktoken-LICENSE\n'
        'ENV TIKTOKEN_CACHE_DIR=/opt/tokenizer-cache\n'
        'RUN --network=none /opt/agent/bin/python -I -c "from harnesslab.click_tokenizer import count_text_tokens; assert count_text_tokens(((\'user\',\'cache preflight\'),))>0"\n'+marker)


def click_expected_environment(base_environment,role):
    values=dict(item.split('=',1) for item in expected_environment(base_environment,role))
    if role=='agent':values['TIKTOKEN_CACHE_DIR']='/opt/tokenizer-cache'
    return tuple(key+'='+value for key,value in sorted(values.items()))


def validate_click_context(context,*,base_metadata,agent_manifest,verifier_manifest,helper_manifest,license_sha256):
    # Exact files only. New sources are an explicit allowlist, never a tree copy.
    root=Path(context)
    if root.is_symlink() or not root.is_dir():raise ValueError('Invalid build context')
    if (not isinstance(license_sha256,str) or len(license_sha256)!=64
            or any(c not in '0123456789abcdef' for c in license_sha256)):
        raise ValueError('Reviewed license hash required')
    expected={'Dockerfile':hashlib.sha256(click_recipe('python@'+base_metadata['amd64_manifest_digest']).encode()).hexdigest(),
              'tokenizer-cache/'+CACHE_NAME:CACHE_SHA256,'tokenizer-LICENSE':license_sha256}
    for role,manifest in (('agent',agent_manifest),('verifier',verifier_manifest)):
        lines=[]
        for item in sorted(manifest['artifacts'],key=lambda value:value['name']):
            expected[role+'-wheelhouse/'+item['filename']]=item['sha256']
            lines.append(item['name']+'=='+item['version']+' --hash=sha256:'+item['sha256']+'\n')
        expected[role+'.hashes.txt']=hashlib.sha256(''.join(lines).encode()).hexdigest()
        helper=helper_manifest[role]
        expected[role+'-helper/'+helper['filename']]=helper['sha256']
        expected[role+'-helper.hashes.txt']=hashlib.sha256(('harness-fixture-helpers==0.0.1 --hash=sha256:'+helper['sha256']+'\n').encode()).hexdigest()
    actual={}
    for path in root.rglob('*'):
        if path.is_symlink():raise ValueError('Linked context input refused')
        if path.is_file():actual[path.relative_to(root).as_posix()]=path
    if set(actual)!=set(expected):raise ValueError('Unexpected/missing Click build input')
    total=0
    for name,digest in expected.items():
        total+=actual[name].stat().st_size
        if total>256*1024*1024 or hashlib.sha256(actual[name].read_bytes()).hexdigest()!=digest:
            raise ValueError('Input bytes/hash mismatch')
    if actual['tokenizer-cache/'+CACHE_NAME].stat().st_size!=CACHE_BYTES:
        raise ValueError('Tokenizer size mismatch')
    return {'files':len(actual),'bytes':total,'status':'prepared_exact_input_context_not_built'}
