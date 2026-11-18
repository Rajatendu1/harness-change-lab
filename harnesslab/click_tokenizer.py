"""Fixed local tokenizer artifact check. No fetch or credential IO.

Counter is conservative local framing estimate, never provider quota proof.
"""
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import stat
import sys

CACHE_NAME='fb374d419588a4632f3f557e76b4b70aebbca790'
CACHE_SHA256='446a9538cb6c348e3516120d7c08b09f57c36495e2acfffe59a5bf8b0cfb1a2d'
CACHE_BYTES=3613922
CACHE_URL='https://openaipublic.blob.core.windows.net/encodings/o200k_base.tiktoken'
CACHE_DIRECTORY='/opt/tokenizer-cache'


def verify_cache(directory):
    root=Path(directory)
    if root.is_symlink() or not root.is_dir():raise ValueError('Tokenizer cache missing')
    path=root/CACHE_NAME
    info=path.lstat()
    if (not stat.S_ISREG(info.st_mode) or info.st_nlink!=1 or info.st_size!=CACHE_BYTES
            or path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest()!=CACHE_SHA256):
        raise ValueError('Pinned tokenizer artifact mismatch')
    return True


def count_text_tokens(pairs,*,directory=CACHE_DIRECTORY):
    if importlib.metadata.version('tiktoken')!='0.12.0':raise ValueError('Pinned tokenizer required')
    verify_cache(directory)
    if (not isinstance(pairs,(list,tuple)) or not 0<len(pairs)<=16
            or any(not isinstance(p,(list,tuple)) or len(p)!=2
                   or p[0] not in ('system','user','assistant') or not isinstance(p[1],str)
                   for p in pairs)):
        raise ValueError('Bounded text pairs required')
    if len(json.dumps(pairs,ensure_ascii=False).encode())>32768:
        raise ValueError('Counter byte bound exceeded')
    # verify_cache fails BEFORE tiktoken can attempt a network fallback.
    os.environ['TIKTOKEN_CACHE_DIR']=str(directory)
    import tiktoken
    encoding=tiktoken.get_encoding('o200k_harmony')
    return 128+sum(len(encoding.encode(role,disallowed_special=()))
                   +len(encoding.encode(text,disallowed_special=()))+128 for role,text in pairs)


if __name__=='__main__':
    try:
        # Same fixed host/cache/UID/cgroup conditions as the editing image helper.
        from .docker_fixture_child import guard
        guard()
        raw=sys.stdin.buffer.read(32769)
        if len(raw)>32768:raise ValueError('Bounded input required')
        print(json.dumps({'estimated_tokens':count_text_tokens(json.loads(raw))},sort_keys=True))
    except Exception:raise SystemExit(3)
