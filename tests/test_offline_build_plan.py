import hashlib
import tempfile
from pathlib import Path
import unittest

from harnesslab.offline_build_plan import expected_environment,validate_context
from harnesslab.offline_recipe import offline_recipe


class OfflineBuildInputTests(unittest.TestCase):
    def test_expected_env_comes_from_recipe_not_image(self):
        env=expected_environment(['PATH=/base','LANG=C.UTF-8'],'agent')
        self.assertIn('PATH=/opt/agent/bin:/usr/local/bin:/usr/bin:/bin',env)
        self.assertIn('LANG=C.UTF-8',env)
        self.assertIn('PIP_NO_CACHE_DIR=1',env)
        self.assertNotIn('PATH=/base',env)

    def test_exact_context_hashes_reject_extra_missing_changed_or_linked_input(self):
        base={'amd64_manifest_digest':'sha256:'+'a'*64}
        manifests={role:{'artifacts':[{'name':'fixture','version':'1','filename':'fixture.whl',
                                     'sha256':hashlib.sha256(b'wheel').hexdigest()}]} for role in ('agent','verifier')}
        helpers={role:{'filename':'helper.whl','sha256':hashlib.sha256(b'helper').hexdigest()} for role in ('agent','verifier')}
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'Dockerfile').write_text(offline_recipe('python@'+base['amd64_manifest_digest']))
            for role in ('agent','verifier'):
                (root/(role+'-wheelhouse')).mkdir();(root/(role+'-wheelhouse/fixture.whl')).write_bytes(b'wheel')
                (root/(role+'-helper')).mkdir();(root/(role+'-helper/helper.whl')).write_bytes(b'helper')
                (root/(role+'.hashes.txt')).write_text('fixture==1 --hash=sha256:'+hashlib.sha256(b'wheel').hexdigest()+'\n')
                (root/(role+'-helper.hashes.txt')).write_text('harness-fixture-helpers==0.0.1 --hash=sha256:'+hashlib.sha256(b'helper').hexdigest()+'\n')
            def validate():return validate_context(root,base_metadata=base,agent_manifest=manifests['agent'],verifier_manifest=manifests['verifier'],helper_manifest=helpers)
            self.assertEqual(validate()['files'],9)
            (root/'private-dummy').write_bytes(b'private')
            with self.assertRaises(ValueError):validate()
            (root/'private-dummy').unlink()
            target=root/'agent-helper/helper.whl';target.write_bytes(b'changed')
            with self.assertRaises(ValueError):validate()
            target.unlink()
            with self.assertRaises(ValueError):validate()
            target.symlink_to(root/'verifier-helper/helper.whl')
            with self.assertRaises(ValueError):validate()

    def test_partial_success_identity_is_available_for_cleanup_after_build_failure(self):
        from unittest.mock import patch
        from harnesslab.offline_build_plan import build_images
        from harnesslab.bounded_process import ControlledProcessError
        created=[]
        def runner(args,**kwargs):
            Path(args[args.index('--iidfile')+1]).write_text('sha256:'+'b'*64)
            raise ControlledProcessError('output_limit')
        with patch('harnesslab.offline_build_plan.validate_context',return_value={}):
            with self.assertRaises(ControlledProcessError):
                build_images('/unused',base_metadata={},agent_manifest={},verifier_manifest={},
                    helper_manifest={},runner=runner,created_ids=created)
        self.assertEqual(created,['sha256:'+'b'*64])
