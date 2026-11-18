"""Separate editing-container construction, not wired/executed/qualified.

Keeper1001 and agent65534 are fixed reviewed candidates, not configurable claims.
Caller must verify image policy and host UID mapping before execution.
"""
from .candidate_cleanup import KEEPER_PROGRAM, CLEANUP_PROGRAM
from .docker_qualification import create_command, DockerPolicy

KEEPER_UID=1001
AGENT_UID=65534


def editing_create_command(name, image, socket_directory, *, gateway_gid):
    if type(gateway_gid) is not int or gateway_gid<=0 or gateway_gid==AGENT_UID:
        raise ValueError('Expected explicit nonroot controller group')
    args=create_command(name,image,socket_directory,KEEPER_UID,gateway_gid,DockerPolicy())
    # Preserve existing resource/network/capability restrictions. Workspace and
    # tmpfs belong to agent, not keeper. Socket directory remains read-only.
    args=[arg.replace('uid=1001,',f'uid={AGENT_UID},') if arg.startswith(('/work:','/tmp:')) else arg
          for arg in args]
    args[-1]=KEEPER_PROGRAM
    args[2:2]=['--group-add',str(gateway_gid)]
    return args


def fixed_exec_command(name, *, operation):
    from re import fullmatch
    if not fullmatch(r'harness-preflight-[a-f0-9]{32}',name):
        raise ValueError('Expected controlled container name')
    # Import/export need explicitly packaged fixed modules and bounded stdin;
    # this is deliberately not an arbitrary command or program option.
    if operation!='cleanup':
        raise ValueError('Only prepared fixed cleanup operation is available')
    return ['docker','exec','--user',f'{AGENT_UID}:{AGENT_UID}',name,
            'python3','-I','-c',CLEANUP_PROGRAM]
