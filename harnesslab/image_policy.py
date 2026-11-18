"""Controller-side trusted image checks. No Docker call, build or download.

Policy comes from a reviewed manifest, NEVER the image being validated. Matching
metadata is a provenance/config check, not a malware or runtime-safety verdict.
"""
from dataclasses import dataclass
import re

DIGEST = re.compile(r'[a-z0-9./_-]+@sha256:[a-f0-9]{64}')
CONTENT = re.compile(r'sha256:[a-f0-9]{64}')


@dataclass(frozen=True)
class ImagePolicy:
    reference: str
    content_id: str
    environment: tuple
    maximum_bytes: int

    def __post_init__(self):
        if (not isinstance(self.reference,str)
                or not (DIGEST.fullmatch(self.reference) or self.reference==self.content_id)
                or not CONTENT.fullmatch(self.content_id)
                or type(self.maximum_bytes) is not int or not 0 < self.maximum_bytes <= 4*1024**3
                or not isinstance(self.environment, tuple)
                or any(not isinstance(x,str) or '=' not in x or '\x00' in x for x in self.environment)
                or len({x.split('=',1)[0] for x in self.environment}) != len(self.environment)):
            raise ValueError('Invalid reviewed image policy')


def validate_image(info, policy):
    """Reject inherited image mounts/hooks/healthchecks and unreviewed env."""
    if not isinstance(policy, ImagePolicy):
        raise ValueError('Explicit reviewed image policy required')
    config = info['Config']
    if (info.get('Id') != policy.content_id
            or (policy.reference!=policy.content_id and policy.reference not in info.get('RepoDigests', []))
            or info.get('Os') != 'linux' or info.get('Architecture') != 'amd64'
            or type(info.get('Size')) is not int or not 0 < info['Size'] <= policy.maximum_bytes
            or config.get('Volumes') or config.get('OnBuild') or config.get('Healthcheck')
            or config.get('Entrypoint') not in (None, [])
            or config.get('User') not in (None, '')
            or sorted(config.get('Env') or []) != sorted(policy.environment)):
        raise ValueError('Image provenance or inherited configuration mismatch')
    return {'identity':'matched_reviewed_manifest','inherited_configuration':'matched',
            'runtime_safety':'not_verified'}
