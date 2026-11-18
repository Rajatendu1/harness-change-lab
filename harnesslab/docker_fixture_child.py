"""Fixed image-installed helper for the model-free Docker fixture only.

No CLI-supplied commands, names, provider/model or task. Never run on host: exact
identity, workspace path and cgroup checks precede every operation.
"""
import os
from pathlib import Path
import sys

BASE = {'example.py':b'def answer():\n    return 0\n'}
NAMES = ('example.py',)


def guard():
    if os.getuid()!=65534 or os.geteuid()!=65534 or Path.cwd()!=Path('/work'):
        raise ValueError('Fixed fixture identity/workspace mismatch')
    root=Path('/sys/fs/cgroup')
    if ((root/'memory.max').read_text().strip()!='2147483648'
            or (root/'memory.swap.max').read_text().strip()!='0'
            or (root/'pids.max').read_text().strip()!='64'):
        raise ValueError('Fixed fixture cgroup mismatch')


def canned_agent():
    import importlib.metadata
    import subprocess
    from threading import Thread
    from http.server import ThreadingHTTPServer
    from .isolated_child import Bridge
    if importlib.metadata.version('aider-chat')!='0.86.2':
        raise ValueError('Pinned Aider unavailable')
    # No writable home/root outside bounded tmpfs. Aider bookkeeping stays under
    # /work and is excluded from source-only fixed output by controller policy.
    env={'PATH':'/usr/local/bin:/usr/bin:/bin','HOME':'/work','TERM':'dumb',
         'OPENAI_API_KEY':'fixture-not-a-provider-key',
         'LITELLM_LOCAL_MODEL_COST_MAP':'True','PYTEST_DISABLE_PLUGIN_AUTOLOAD':'1'}
    server=ThreadingHTTPServer(('127.0.0.1',0),Bridge)
    thread=Thread(target=server.serve_forever,daemon=True);thread.start()
    env['OPENAI_API_BASE']='http://127.0.0.1:%d/v1'%server.server_port
    try:
        commands=[['git','init','-q'],['git','add','example.py'],
                  ['git','-c','user.name=Fixture','-c','user.email=fixture@example.invalid','commit','-qm','fixture'],
                  [sys.executable,'-I','-m','aider.main','--model','openai/fixture-model',
                   '--no-stream','--no-analytics','--no-check-update','--no-gitignore',
                   '--no-auto-commits','--no-dirty-commits','--no-auto-lint','--no-auto-test',
                   '--no-suggest-shell-commands','--no-show-model-warnings','--map-tokens','0',
                   '--edit-format','whole','--yes-always','--message',
                   'Change answer to return 1. Edit example.py only.','example.py']]
        for command in commands:
            subprocess.run(command,env=env,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL,check=True,timeout=30)
    finally:
        server.shutdown();server.server_close();thread.join(timeout=2)


def main():
    try:
        guard()
        if len(sys.argv)!=2:
            raise ValueError('Fixed operation required')
        operation=sys.argv[1]
        if operation=='import':
            from .source_io import import_sources
            from .source_bundle import MAX_ARCHIVE
            raw=sys.stdin.buffer.read(MAX_ARCHIVE+1)
            import_sources(raw,expected_names=NAMES,root='/work')
            print('source-import-ok')
        elif operation=='export':
            from .source_io import export_sources
            sys.stdout.buffer.write(export_sources(expected_names=NAMES,root='/work'))
        elif operation=='canned':
            canned_agent()
            print('canned-agent-finished')
        else:
            raise ValueError('Unknown operation')
        return 0
    except Exception:
        # No image/helper diagnostics or archive/source bytes in process logs.
        return 3


if __name__=='__main__':
    raise SystemExit(main())
