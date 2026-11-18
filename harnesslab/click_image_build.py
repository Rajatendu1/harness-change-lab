"""Explicit Click image build, never automatic. Requires approved runtime work.

No pull or package fallback. Input identities are independent of returned image.
"""
import json
from pathlib import Path
import re
import tempfile

from .bounded_process import capture
from .click_image_plan import validate_click_context,click_expected_environment
from .image_policy import ImagePolicy,validate_image


def build_click_images(context,*,base_metadata,agent_manifest,verifier_manifest,helper_manifest,
                       license_sha256,runner=capture,created_ids=None):
    validation=validate_click_context(context,base_metadata=base_metadata,
        agent_manifest=agent_manifest,verifier_manifest=verifier_manifest,
        helper_manifest=helper_manifest,license_sha256=license_sha256)
    policies={}
    with tempfile.TemporaryDirectory(prefix='click-build-id-') as directory:
        for role in ('agent','verifier'):
            iid=Path(directory)/(role+'.id')
            try:
                runner(['docker','build','--network=none','--pull=false','--target',role,
                        '--iidfile',str(iid),str(Path(context).resolve())],timeout_s=300,max_bytes=2*1024*1024)
            finally:
                if created_ids is not None and iid.exists():
                    content=iid.read_text().strip()
                    if re.fullmatch(r'sha256:[a-f0-9]{64}',content):created_ids.append(content)
            content=iid.read_text().strip()
            if not re.fullmatch(r'sha256:[a-f0-9]{64}',content):raise ValueError('Build identity missing')
            policy=ImagePolicy(content,content,click_expected_environment(base_metadata['config']['Env'],role),4*1024**3)
            data=json.loads(runner(['docker','image','inspect',content],timeout_s=10,max_bytes=1024*1024).stdout)
            if not isinstance(data,list) or len(data)!=1:raise ValueError('Unexpected image identity')
            validate_image(data[0],policy)
            policies[role]=policy
    return policies,validation
