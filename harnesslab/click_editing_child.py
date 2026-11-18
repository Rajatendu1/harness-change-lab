"""Prepared fixed Click editing helper. No provider credentials or hidden tests.

Never run on host. Actual Docker lifecycle integration is not yet qualified.
"""
import importlib.metadata
import json
from pathlib import Path
import subprocess
import sys
from threading import Thread
from http.server import ThreadingHTTPServer

from .click_task import BASE_NAMES, EDITABLE, ISSUE, MODEL, validate_base
from .docker_fixture_child import guard
from .isolated_child import Bridge
from .source_bundle import MAX_ARCHIVE, unpack_sources
from .source_io import import_sources, export_sources


def agent_command():
    return [sys.executable, '-I', '-m', 'aider.main', '--model', 'openai/'+MODEL,
            '--model-settings-file', '/work/.aider.controller.settings.yml',
            '--no-stream', '--no-analytics', '--no-check-update', '--no-gitignore',
            '--no-auto-commits', '--no-dirty-commits', '--no-auto-lint', '--no-auto-test',
            '--no-suggest-shell-commands', '--no-show-model-warnings', '--map-tokens', '0',
            '--edit-format', 'diff', '--yes-always', '--message', ISSUE, EDITABLE[0]]


def edit():
    if importlib.metadata.version('aider-chat') != '0.86.2':
        raise ValueError('Pinned agent required')
    from .click_tokenizer import verify_cache,CACHE_DIRECTORY
    verify_cache(CACHE_DIRECTORY)
    # Exact base source admitted before running Git/Aider; no hidden patch/test.
    raw=export_sources(expected_names=BASE_NAMES,root='/work')
    validate_base(unpack_sources(raw,expected_names=BASE_NAMES))
    settings=Path('/work/.aider.controller.settings.yml')
    if settings.exists() or settings.is_symlink():
        raise ValueError('Unexpected model configuration')
    settings.write_text('- name: openai/'+MODEL+'\n  extra_params:\n    max_tokens: 2048\n')
    env={'PATH':'/usr/local/bin:/usr/bin:/bin','HOME':'/work','TERM':'dumb',
         'OPENAI_API_KEY':'controller-boundary-not-a-provider-key',
         'LITELLM_LOCAL_MODEL_COST_MAP':'True','PYTEST_DISABLE_PLUGIN_AUTOLOAD':'1',
         'TIKTOKEN_CACHE_DIR':'/opt/tokenizer-cache'}
    bridge=ThreadingHTTPServer(('127.0.0.1',0),Bridge)
    thread=Thread(target=bridge.serve_forever,daemon=True);thread.start()
    env['OPENAI_API_BASE']='http://127.0.0.1:%d/v1'%bridge.server_port
    try:
        for command in (['git','init','-q'],['git','add','.'],
                        ['git','-c','user.name=Fixture','-c','user.email=fixture@example.invalid',
                         'commit','-qm','public-base']):
            subprocess.run(command,env=env,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL,check=True,timeout=10)
        subprocess.run(agent_command(),env=env,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL,check=True,timeout=180)
    finally:
        bridge.shutdown();bridge.server_close();thread.join(timeout=2)


def main():
    try:
        guard()
        if len(sys.argv)!=2:raise ValueError('Fixed operation required')
        operation=sys.argv[1]
        if operation=='import':
            raw=sys.stdin.buffer.read(MAX_ARCHIVE+1)
            validate_base(unpack_sources(raw,expected_names=BASE_NAMES))
            import_sources(raw,expected_names=BASE_NAMES,root='/work')
            print('source-import-ok')
        elif operation=='edit':
            edit()
            print('click-agent-finished')
        elif operation=='export':
            sys.stdout.buffer.write(export_sources(expected_names=EDITABLE,root='/work'))
        else:raise ValueError('Unknown fixed operation')
        return 0
    except Exception:
        return 3


if __name__=='__main__':raise SystemExit(main())
