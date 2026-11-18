"""Prepared one-shot live Click entry. Importing performs no external IO.

This is not authorization. A separately approved workflow may set the explicit
scope marker and controller-only temporary credential after current preflight.
No retry/resume path, raw chat output or artifact publication is provided.
"""
import json
import os
from pathlib import Path
import runpy
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from harnesslab.bounded_process import capture
from harnesslab.click_docker_score import score_click
from harnesslab.click_image_build import build_click_images
from harnesslab.click_pilot import run_with_isolated_counter
from harnesslab.click_task import EDITABLE
from harnesslab.request_budget import https_transport

HERE=Path(__file__).resolve().parent
support=runpy.run_path(str(HERE/'run_diagnostic.py'))
assemble=support['assemble']
task_inputs=support['task_inputs']
SCOPE='one-public-click-request-no-retry'
ENDPOINT='https://api.groq.com/openai/v1/chat/completions'
SECRET_NAME='HARNESS_CLICK_TEMP_KEY'


def main():
    # Refuse before input fetching/building or touching the credential.
    if os.environ.get('HARNESS_CLICK_SCOPE')!=SCOPE:
        print(json.dumps({'status':'live_scope_marker_missing','live_request_authorized':False}))
        return 3
    policies={};created=[];cleanup=True
    # Remove the secret from inherited subprocess environments immediately.
    token=os.environ.pop(SECRET_NAME,'')
    result={'status':'live_click_setup_unverified','real_model_repairs':0}
    try:
        with tempfile.TemporaryDirectory(prefix='click-live-build-') as temporary:
            directory=Path(temporary)
            base,manifests,helpers,license_hash=assemble(directory)
            source,fixed,protected=task_inputs()
            reference='python@'+base['amd64_manifest_digest']
            capture(['docker','pull','--platform','linux/amd64',reference],timeout_s=180,max_bytes=2*1024*1024)
            policies,inputs=build_click_images(directory,base_metadata=base,agent_manifest=manifests['agent'],
                verifier_manifest=manifests['verifier'],helper_manifest=helpers,
                license_sha256=license_hash,created_ids=created)
            if policies['agent'].content_id==policies['verifier'].content_id:
                raise ValueError('Distinct agent/verifier images required')
            # Verify both reference controls before constructing a live transport.
            controls=[]
            for label,candidate,expected in [('unchanged_base',source,'reference_verifier_fail'),
                    ('known_upstream_fix',dict(source,**{EDITABLE[0]:fixed}),'reference_verifier_pass')]:
                row=score_click(candidate,base=source,protected_test=protected,
                    image_policy=policies['verifier'],reference_mode=True)
                controls.append({'stage':label,'score':row})
                if row.get('outcome')!=expected or row.get('tests')!=3 or row.get('skipped')!=0:
                    raise ValueError('Reference controls unverified')
            if not token or token.strip()!=token:
                raise ValueError('Temporary credential unavailable')
            transport=https_transport(ENDPOINT,token,timeout=60)
            try:
                result=run_with_isolated_counter(base=source,image_policy=policies['agent'],
                    transport=transport,scorer=lambda candidate:score_click(candidate,base=source,
                        protected_test=protected,image_policy=policies['verifier']))
            finally:
                # Python cannot promise in-memory erasure. The controller exits;
                # external key revocation/Actions-secret deletion is still owed.
                token=None;transport=None
            result['reference_controls']=controls
            result['public_input_files']=len(source)
            result['real_model_repairs']=int(result.get('status')=='scored' and
                result.get('outcome')=='source_patch_verifier_pass')
            result['evidence_class']='one_public_task_live_attempt_trusted_process_not_adversarial'
    except Exception:
        result={'status':'live_click_setup_or_execution_unverified','real_model_repairs':0,
                'provider_attempts':'unverified_do_not_retry'}
    finally:
        token=None
        os.environ.pop(SECRET_NAME,None)
        for content in set(created):
            try:capture(['docker','image','rm','--force',content],timeout_s=20,max_bytes=4096)
            except Exception:cleanup=False
    result['image_cleanup_confirmed']=cleanup and len(policies)==2
    result['credential_revocation_confirmed']=False
    result['actions_secret_removal_confirmed']=False
    result['credential_cleanup_owner']='external_operator_must_verify_after_every_terminal_outcome'
    if not result['image_cleanup_confirmed']:
        result.pop('outcome',None);result['real_model_repairs']=0
        result['status']='live_click_image_cleanup_or_setup_unverified'
    print(json.dumps(result,sort_keys=True))
    return 0 if result.get('status')=='scored' else 3


if __name__=='__main__':raise SystemExit(main())
